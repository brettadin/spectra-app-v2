"""Generate and persist provenance manifests and export bundles."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path
import csv
from typing import Iterable, Dict, Any, List, Optional, Callable
import hashlib
import json

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
        manifest = self.create_manifest(spectra_list, transforms=transforms, citations=citations)

        manifest_path = Path(manifest_path)
        self.save_manifest(manifest, manifest_path)

        csv_file = Path(csv_path) if csv_path is not None else manifest_path.with_suffix('.csv')
        self._write_csv(csv_file, spectra_list)

        png_file = Path(png_path) if png_path is not None else manifest_path.with_suffix('.png')
        png_file.parent.mkdir(parents=True, exist_ok=True)
        if png_writer is not None:
            png_writer(png_file)
        else:
            png_file.touch(exist_ok=True)

        return {
            "manifest": manifest,
            "manifest_path": manifest_path,
            "csv_path": csv_file,
            "png_path": png_file,
        }

    # ------------------------------------------------------------------
    def _write_csv(self, path: Path, spectra: Iterable[Spectrum]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('w', newline='', encoding='utf-8') as handle:
            writer = csv.writer(handle)
            writer.writerow(['spectrum_id', 'name', 'wavelength_nm', 'intensity', 'x_unit', 'y_unit'])
            for spectrum in spectra:
                for x_val, y_val in zip(spectrum.x, spectrum.y):
                    writer.writerow([spectrum.id, spectrum.name, float(x_val), float(y_val), spectrum.x_unit, spectrum.y_unit])

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
