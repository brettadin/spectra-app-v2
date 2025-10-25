"""Data ingestion pipeline for the Spectra application."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, cast

from .spectrum import Spectrum
class OneOrMany(list):
    """List subclass that proxies attribute access to the sole element.

    When exactly one item is present, attribute access and common dunder
    lookups are forwarded to that element to ease call sites that expect a
    single object. Otherwise behaves as a normal list.
    """

    def __getattr__(self, name: str):  # pragma: no cover - behaviour validated via tests
        if len(self) == 1:
            return getattr(self[0], name)
        raise AttributeError(name)

from .units_service import UnitsService
from .importers import SupportsImport, CsvImporter, FitsImporter, JcampImporter
from .store import LocalStore


@dataclass
class DataIngestService:
    """Manage importer plugins and normalise spectra into canonical units."""

    units_service: UnitsService
    store: LocalStore | None = None
    _registry: Dict[str, SupportsImport] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self._registry:
            self.register_importer({'.csv', '.txt'}, CsvImporter())
            self.register_importer({'.fits', '.fit', '.fts'}, FitsImporter())
            self.register_importer({'.jdx', '.dx', '.jcamp'}, JcampImporter())

    # ------------------------------------------------------------------
    def register_importer(self, extensions: Iterable[str], importer: SupportsImport) -> None:
        """Register an importer for the provided file extensions."""
        for ext in extensions:
            key = ext.lower()
            if not key.startswith('.'):  # normalise to .ext format
                key = f'.{key}'
            self._registry[key] = importer

    def ingest(self, path: Path) -> List[Spectrum]:
        """Read a file from disk and return canonical :class:`Spectrum` objects."""
        ext = path.suffix.lower()
        importer = self._registry.get(ext)
        if importer is None:
            raise ValueError(f"No importer registered for extension {ext!r}")

        raw = importer.read(path)
        bundle_meta = raw.metadata.get("bundle") if isinstance(raw.metadata, dict) else None
        if isinstance(bundle_meta, dict) and bundle_meta.get("format") == "spectra-export-v1":
            members = bundle_meta.get("members", [])
            return self._ingest_bundle(path, importer, members)

        spectrum = self._build_spectrum(
            raw.name,
            raw.x,
            raw.y,
            raw.x_unit,
            raw.y_unit,
            raw.metadata,
            importer,
            raw.source_path or path,
        )
        return OneOrMany([spectrum])

    def ingest_bytes(
        self,
        content: bytes,
        *,
        suggested_name: str | None = None,
        extension: str | None = None,
    ) -> List[Spectrum]:
        """Ingest spectra from an in-memory byte buffer.

        Uses the file-based importer pipeline by writing the bytes to a
        temporary file with an appropriate suffix inferred from
        ``suggested_name`` or ``extension``. The temporary file is then
        parsed via :meth:`ingest` and, when a :class:`LocalStore` is
        configured, recorded into the persistent cache.

        Parameters
        - content: Raw file bytes
        - suggested_name: Optional filename hint (e.g. "spectrum.fits").
        - extension: Optional override like ".fits", ".csv", or ".jdx".

        Returns
        - List[Spectrum]: One or more canonical spectra
        """
        import tempfile

        # Resolve a usable extension for importer lookup
        ext = None
        if extension and extension.strip():
            ext = extension.strip()
        elif suggested_name:
            ext = Path(suggested_name).suffix
        if not ext:
            raise ValueError("Unable to determine file type: provide 'suggested_name' or 'extension'.")

        if not ext.startswith("."):
            ext = f".{ext}"

        if ext.lower() not in self._registry:
            raise ValueError(f"No importer registered for extension {ext!r}")

        # Persist bytes to a temporary file and delegate to the file pipeline
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as handle:
            handle.write(content)
            temp_path = Path(handle.name)

        try:
            return self.ingest(temp_path)
        finally:
            try:
                temp_path.unlink(missing_ok=True)
            except Exception:
                # Best-effort cleanup; the LocalStore may have already copied
                # the file into the persistent cache.
                pass

    def supported_extensions(self) -> Dict[str, str]:
        """Return mapping of extension → importer class name."""
        return {ext: imp.__class__.__name__ for ext, imp in self._registry.items()}

    # ------------------------------------------------------------------
    def _build_spectrum(
        self,
        name: str,
        x: Sequence[float],
        y: Sequence[float],
        x_unit: str,
        y_unit: str,
        metadata: Dict[str, Any] | None,
        importer: SupportsImport,
        source_path: Path,
        *,
        bundle_member: str | None = None,
        record_store: bool = True,
    ) -> Spectrum:
        canonical_x, canonical_y, meta = self.units_service.to_canonical(
            x, y, x_unit, y_unit, metadata=metadata
        )
        meta.setdefault('ingest', {})
        meta['ingest'].update({
            'source_path': str(source_path),
            'importer': importer.__class__.__name__,
        })
        if bundle_member is not None:
            ingest_meta = meta.setdefault('ingest', {})
            ingest_meta['bundle_member'] = bundle_member
            meta.setdefault('bundle_member', {})
            bundle_meta = meta['bundle_member']
            if isinstance(bundle_meta, dict):
                bundle_meta.setdefault('id', bundle_member)
        spectrum = Spectrum.create(
            name=name,
            x=canonical_x,
            y=canonical_y,
            metadata=meta,
            source_path=source_path,
        )
        if self.store is not None and record_store:
            source_summary = {
                "ingest": dict(meta.get("ingest", {})),
                "source_units": dict(meta.get("source_units", {})),
            }
            record = self.store.record(
                source_path,
                x_unit=spectrum.x_unit,
                y_unit=spectrum.y_unit,
                source=source_summary,
                alias=source_path.name,
            )
            ingest_meta = dict(spectrum.metadata.get("ingest", {}))
            ingest_meta["cache_record"] = {
                "sha256": record.get("sha256"),
                "created": record.get("created"),
                "updated": record.get("updated"),
            }
            spectrum = spectrum.with_metadata(
                ingest=ingest_meta,
                cache_record=record,
            )
        return spectrum

    def _ingest_bundle(
        self,
        bundle_path: Path,
        importer: SupportsImport,
        members: Sequence[Dict[str, Any]],
    ) -> List[Spectrum]:
        spectra: List[Spectrum] = []
        member_ids: List[str] = []
        for member in members:
            x = member.get("x", [])
            y = member.get("y", [])
            if (
                not isinstance(x, Sequence)
                or isinstance(x, (str, bytes))
                or not isinstance(y, Sequence)
                or isinstance(y, (str, bytes))
            ):
                continue
            name = cast(str, member.get("name")) if isinstance(member.get("name"), str) else None
            spectrum_id = cast(str, member.get("id")) if isinstance(member.get("id"), str) else None
            x_unit = cast(str, member.get("x_unit")) if isinstance(member.get("x_unit"), str) else "nm"
            y_unit = cast(str, member.get("y_unit")) if isinstance(member.get("y_unit"), str) else "absorbance"
            metadata = member.get("metadata") if isinstance(member.get("metadata"), dict) else {}
            resolved_name = name or f"{bundle_path.stem}-{spectrum_id or len(spectra)}"
            spectrum = self._build_spectrum(
                resolved_name,
                x,
                y,
                x_unit,
                y_unit,
                metadata,
                importer,
                bundle_path,
                bundle_member=spectrum_id,
                record_store=False,
            )
            spectra.append(spectrum)
            if spectrum_id:
                member_ids.append(spectrum_id)

        if self.store is not None and spectra:
            record = self.store.record(
                bundle_path,
                x_unit="nm",
                y_unit="absorbance",
                source={"bundle_members": member_ids},
                alias=bundle_path.name,
            )
            for idx, spectrum in enumerate(spectra):
                ingest_meta = dict(spectrum.metadata.get("ingest", {}))
                ingest_meta["cache_record"] = {
                    "sha256": record.get("sha256"),
                    "created": record.get("created"),
                    "updated": record.get("updated"),
                }
                spectra[idx] = spectrum.with_metadata(ingest=ingest_meta, cache_record=record)

        return OneOrMany(spectra)
