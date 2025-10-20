"""Generate and persist provenance manifests and export bundles."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path
import csv
import shutil
from typing import Iterable, Dict, Any, List, Optional, Callable
import hashlib
import json

import numpy as np

from .spectrum import Spectrum


@dataclass
class ProvenanceService:
    """Service for creating and persisting provenance manifests."""

    app_name: str = "SpectraApp"
    app_version: str = "0.1.0"

    def create_manifest(
        self,
        spectra: Iterable[Spectrum],
        transforms: Optional[List[Dict[str, Any]]] = None,
        citations: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Create a provenance manifest for the provided spectra."""

        spectra_list = list(spectra)
        source_entries = [self._source_entry(spec) for spec in spectra_list]
        manifest = {
            "version": "1.0",
            "app": self._app_metadata(),
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "sources": source_entries,
            "transforms": [self._normalise_transform(t) for t in (transforms or [])],
            "citations": citations or [],
        }
        return manifest

    def save_manifest(self, manifest: Dict[str, Any], path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)

    def export_bundle(
        self,
        spectra: Iterable[Spectrum],
        manifest_path: Path,
        *,
        transforms: Optional[List[Dict[str, Any]]] = None,
        citations: Optional[List[Dict[str, Any]]] = None,
        csv_path: Path | None = None,
        png_path: Path | None = None,
        png_writer: Callable[[Path], None] | None = None,
    ) -> Dict[str, Any]:
        """Create a provenance bundle containing manifest, data, and plot artefacts."""

        spectra_list = list(spectra)
        manifest_path = Path(manifest_path)
        base_dir = manifest_path.parent
        base_dir.mkdir(parents=True, exist_ok=True)

        manifest = self.create_manifest(spectra_list, transforms=transforms, citations=citations)

        spectra_dir = base_dir / "spectra"
        per_spectrum_csvs = self._write_per_spectrum_csvs(spectra_dir, spectra_list)

        sources_dir = base_dir / "sources"
        copied_sources = self._copy_sources(sources_dir, spectra_list)

        self._annotate_manifest_sources(manifest, base_dir, per_spectrum_csvs, copied_sources)

        self.save_manifest(manifest, manifest_path)

        csv_file = Path(csv_path) if csv_path is not None else manifest_path.with_suffix('.csv')
        self._write_csv(csv_file, spectra_list)

        png_file = Path(png_path) if png_path is not None else manifest_path.with_suffix('.png')
        png_file.parent.mkdir(parents=True, exist_ok=True)
        if png_writer is not None:
            png_writer(png_file)
        else:
            png_file.touch(exist_ok=True)

        log_path = base_dir / "log.txt"
        self._write_log(
            log_path,
            manifest_path,
            csv_file,
            spectra_list,
            per_spectrum_csvs,
            copied_sources,
        )

        return {
            "manifest": manifest,
            "manifest_path": manifest_path,
            "csv_path": csv_file,
            "png_path": png_file,
            "log_path": log_path,
            "spectra_dir": spectra_dir if per_spectrum_csvs else None,
            "sources_dir": sources_dir if copied_sources else None,
        }

    # ------------------------------------------------------------------
    def _write_csv(self, path: Path, spectra: Iterable[Spectrum]) -> None:
        """Write a combined CSV where wavelength/intensity lead each row.

        The exporter previously placed identifier columns before the numeric
        values which caused the CSV importer to mis-detect the axes when the
        bundle was reloaded.  By leading with wavelength/intensity and keeping
        provenance fields to the right we preserve the tabular metadata while
        ensuring the file round-trips through the default CSV heuristics.
        """

        path.parent.mkdir(parents=True, exist_ok=True)
        spectra_list = list(spectra)
        with path.open('w', newline='', encoding='utf-8') as handle:
            writer = csv.writer(handle)
            writer.writerow(
                [
                    'wavelength_nm',
                    'intensity',
                    'spectrum_id',
                    'spectrum_name',
                    'point_index',
                    'x_unit',
                    'y_unit',
                ]
            )
            for spectrum in spectra_list:
                for idx, (x_val, y_val) in enumerate(zip(spectrum.x, spectrum.y)):
                    writer.writerow(
                        [
                            float(x_val),
                            float(y_val),
                            spectrum.id,
                            spectrum.name,
                            idx,
                            spectrum.x_unit,
                            spectrum.y_unit,
                        ]
                    )

    def write_wide_csv(self, path: Path, spectra: Iterable[Spectrum]) -> Path:
        """Write paired wavelength/intensity columns per spectrum.

        The resulting CSV can be re-imported by :class:`CsvImporter`, which
        detects the ``spectra-wide-v1`` comment header and reconstructs bundle
        members from the paired columns.
        """

        spectra_list = list(spectra)
        if not spectra_list:
            raise ValueError("No spectra supplied for wide CSV export")

        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('w', encoding='utf-8', newline='') as handle:
            handle.write('# spectra-wide-v1\n')
            for spectrum in spectra_list:
                meta = {
                    'id': spectrum.id,
                    'name': spectrum.name,
                    'x_unit': spectrum.x_unit,
                    'y_unit': spectrum.y_unit,
                }
                handle.write(f"# member {json.dumps(meta, ensure_ascii=False)}\n")

            writer = csv.writer(handle)
            header: List[str] = []
            for spectrum in spectra_list:
                header.append(f"wavelength_nm::{spectrum.id}")
                header.append(f"intensity::{spectrum.id}")
            writer.writerow(header)

            max_length = max(len(spec.x) for spec in spectra_list)
            for row_index in range(max_length):
                row: List[object] = []
                for spectrum in spectra_list:
                    if row_index < len(spectrum.x):
                        row.append(float(spectrum.x[row_index]))
                        row.append(float(spectrum.y[row_index]))
                    else:
                        row.extend(["", ""])
                writer.writerow(row)

        return path

    def write_composite_csv(
        self,
        path: Path,
        spectra: Iterable[Spectrum],
        *,
        strategy: str = "mean",
    ) -> Path:
        """Write a composite CSV derived from multiple spectra.

        The default strategy computes the mean intensity on the wavelength grid
        of the first spectrum, interpolating additional spectra where needed and
        skipping regions with insufficient coverage.
        """

        spectra_list = list(spectra)
        if len(spectra_list) < 2:
            raise ValueError("At least two spectra are required for a composite export")

        base = spectra_list[0]
        base_x = np.asarray(base.x, dtype=float)
        base_y = np.asarray(base.y, dtype=float)
        if base_x.size == 0:
            raise ValueError("Composite export requires non-empty spectra")

        base_order = np.argsort(base_x)
        base_x = base_x[base_order]
        base_y = base_y[base_order]

        aligned: List[np.ndarray] = []
        counts = np.zeros_like(base_x, dtype=int)

        base_values = base_y.astype(float)
        base_mask = np.isfinite(base_values)
        counts[base_mask] += 1
        aligned.append(np.where(base_mask, base_values, np.nan))

        for spectrum in spectra_list[1:]:
            src_x = np.asarray(spectrum.x, dtype=float)
            src_y = np.asarray(spectrum.y, dtype=float)
            if src_x.size == 0 or src_y.size == 0:
                continue

            order = np.argsort(src_x)
            src_x = src_x[order]
            src_y = src_y[order]
            if np.array_equal(src_x, base_x):
                interpolated = src_y.astype(float)
            else:
                interpolated = np.interp(base_x, src_x, src_y, left=np.nan, right=np.nan)
            mask = np.isfinite(interpolated)
            counts[mask] += 1
            aligned.append(np.where(mask, interpolated, np.nan))

        if not aligned:
            raise ValueError("Composite export could not align any spectra")

        stack = np.vstack(aligned)
        if strategy == "mean":
            composite = np.nanmean(stack, axis=0)
        elif strategy == "median":
            composite = np.nanmedian(stack, axis=0)
        else:
            raise ValueError(f"Unsupported composite strategy: {strategy}")

        mask = np.isfinite(composite) & (counts > 0)
        composite_x = base_x[mask]
        composite_y = composite[mask]
        composite_counts = counts[mask]

        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('w', encoding='utf-8', newline='') as handle:
            writer = csv.writer(handle)
            writer.writerow(['wavelength_nm', 'intensity', 'source_count'])
            for x_val, y_val, count in zip(composite_x, composite_y, composite_counts):
                writer.writerow([float(x_val), float(y_val), int(count)])

        return path

    def _write_per_spectrum_csvs(self, directory: Path, spectra: Iterable[Spectrum]) -> Dict[str, Path]:
        mapping: Dict[str, Path] = {}
        spectra_list = list(spectra)
        if not spectra_list:
            return mapping
        directory.mkdir(parents=True, exist_ok=True)
        for spectrum in spectra_list:
            filename = f"{self._slugify(spectrum.name)}-{spectrum.id}.csv"
            dest = directory / filename
            with dest.open('w', newline='', encoding='utf-8') as handle:
                writer = csv.writer(handle)
                writer.writerow(['wavelength_nm', 'intensity'])
                for x_val, y_val in zip(spectrum.x, spectrum.y):
                    writer.writerow([float(x_val), float(y_val)])
            mapping[spectrum.id] = dest
        return mapping

    def _copy_sources(self, directory: Path, spectra: Iterable[Spectrum]) -> Dict[str, Path]:
        mapping: Dict[str, Path] = {}
        for spectrum in spectra:
            src = spectrum.source_path
            if src is None or not src.exists():
                continue
            if not directory.exists():
                directory.mkdir(parents=True, exist_ok=True)
            filename = f"{self._slugify(spectrum.name)}-{spectrum.id}{src.suffix}"
            dest = directory / filename
            shutil.copy2(src, dest)
            mapping[spectrum.id] = dest
        return mapping

    def _source_entry(self, spectrum: Spectrum) -> Dict[str, Any]:
        entry: Dict[str, Any] = {
            "id": spectrum.id,
            "name": spectrum.name,
            "units": {
                "wavelength": spectrum.x_unit,
                "intensity": spectrum.y_unit,
            },
            "metadata": spectrum.metadata,
            "parents": list(getattr(spectrum, 'parents', [])),
            "transforms": list(getattr(spectrum, 'transforms', [])),
        }
        if spectrum.source_path and spectrum.source_path.exists():
            entry.update({
                "path": str(spectrum.source_path),
                "size_bytes": spectrum.source_path.stat().st_size,
                "checksum_sha256": self._sha256(spectrum.source_path),
            })
        return entry

    def _annotate_manifest_sources(
        self,
        manifest: Dict[str, Any],
        base_dir: Path,
        per_spectrum_csvs: Dict[str, Path],
        copied_sources: Dict[str, Path],
    ) -> None:
        for source in manifest.get("sources", []):
            spec_id = source.get("id")
            if spec_id in per_spectrum_csvs:
                source["canonical_csv"] = str(per_spectrum_csvs[spec_id].relative_to(base_dir))
            if spec_id in copied_sources:
                source["exported_copy"] = str(copied_sources[spec_id].relative_to(base_dir))

    def _app_metadata(self) -> Dict[str, Any]:
        libraries = {}
        for package in ("numpy", "pyside6", "pytest"):
            try:
                libraries[package] = metadata.version(package)
            except metadata.PackageNotFoundError:
                continue
        return {
            "name": self.app_name,
            "version": self.app_version,
            "build_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "libraries": libraries,
        }

    def _normalise_transform(self, transform: Dict[str, Any]) -> Dict[str, Any]:
        entry = dict(transform)
        entry.setdefault("timestamp_utc", datetime.now(timezone.utc).isoformat())
        return entry

    def _sha256(self, path: Path) -> str:
        h = hashlib.sha256()
        with path.open('rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                h.update(chunk)
        return h.hexdigest()

    def _write_log(
        self,
        log_path: Path,
        manifest_path: Path,
        combined_csv: Path,
        spectra: Iterable[Spectrum],
        per_spectrum_csvs: Dict[str, Path],
        copied_sources: Dict[str, Path],
    ) -> None:
        timestamp = datetime.now(timezone.utc).isoformat()
        spectra_list = list(spectra)
        lines = [f"[{timestamp}] Export started ({len(spectra_list)} spectra)"]
        for spectrum in spectra_list:
            spec_id = spectrum.id
            csv_path = per_spectrum_csvs.get(spec_id)
            if csv_path is not None:
                lines.append(
                    f"[{timestamp}] Canonical CSV written for {spec_id} -> {csv_path.name}"
                )
            if spec_id in copied_sources:
                lines.append(
                    f"[{timestamp}] Source copied for {spec_id} -> {copied_sources[spec_id].name}"
                )
        lines.append(f"[{timestamp}] Manifest saved -> {manifest_path.name}")
        lines.append(f"[{timestamp}] Aggregate CSV saved -> {combined_csv.name}")
        log_path.write_text("\n".join(lines) + "\n", encoding='utf-8')

    def _slugify(self, name: str) -> str:
        cleaned = [ch.lower() if ch.isalnum() else '-' for ch in name]
        slug = ''.join(cleaned).strip('-')
        # Collapse duplicate separators
        while '--' in slug:
            slug = slug.replace('--', '-')
        return slug or 'spectrum'
