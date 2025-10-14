"""Data ingestion pipeline for the Spectra application."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable

from .spectrum import Spectrum
from .units_service import UnitsService
from .importers import SupportsImport, CsvImporter, FitsImporter, JcampImporter


@dataclass
class DataIngestService:
    """Manage importer plugins and normalise spectra into canonical units."""

    units_service: UnitsService
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

    def ingest(self, path: Path) -> Spectrum:
        """Read a file from disk and return a canonical :class:`Spectrum`."""
        ext = path.suffix.lower()
        importer = self._registry.get(ext)
        if importer is None:
            raise ValueError(f"No importer registered for extension {ext!r}")

        raw = importer.read(path)
        canonical_x, canonical_y, metadata = self.units_service.to_canonical(
            raw.x, raw.y, raw.x_unit, raw.y_unit, metadata=raw.metadata
        )
        metadata.setdefault('ingest', {})
        metadata['ingest'].update({
            'source_path': str(raw.source_path or path),
            'importer': importer.__class__.__name__,
        })
        spectrum = Spectrum.create(
            name=raw.name,
            x=canonical_x,
            y=canonical_y,
            metadata=metadata,
            source_path=raw.source_path or path,
        )
        return spectrum

    def supported_extensions(self) -> Dict[str, str]:
        """Return mapping of extension → importer class name."""
        return {ext: imp.__class__.__name__ for ext, imp in self._registry.items()}
