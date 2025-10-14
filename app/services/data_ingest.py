"""Service responsible for ingesting spectra via registered importers."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional
import hashlib
import logging

from .spectrum import Spectrum
from .units_service import UnitsService
from .provenance_service import ProvenanceService
from . import importers

logger = logging.getLogger(__name__)


@dataclass
class DataIngestService:
    """Load spectra from disk while preserving provenance."""

    units_service: UnitsService
    provenance_service: ProvenanceService
    _importers: Dict[str, importers.Importer] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self._importers:
            self.register_importer(importers.CsvImporter())

    def register_importer(self, importer: importers.Importer) -> None:
        for ext in importer.supported_extensions:
            self._importers[ext.lower()] = importer

    def available_formats(self) -> List[str]:
        return sorted(set(self._importers.keys()))

    def ingest(self, path: Path, *, display_name: Optional[str] = None) -> Spectrum:
        importer = self._select_importer(path)
        result = importer.read(path)
        logger.info("Ingesting %s via %s", path, importer.description())

        wavelength_nm = self.units_service.convert_wavelength(
            result.wavelengths, result.wavelength_unit, self.units_service.canonical_wavelength_unit
        )
        flux_context = dict(result.metadata.get("flux_context", {}))
        flux = self.units_service.convert_flux(
            result.flux,
            result.flux_unit,
            self.units_service.canonical_flux_unit,
            context=flux_context,
        )

        checksum = self._sha256(path)
        metadata = {
            "source": {
                "path": str(path),
                "checksum": checksum,
                "importer": importer.__class__.__name__,
                "wavelength_unit": result.wavelength_unit,
                "flux_unit": result.flux_unit,
            },
            "comments": result.metadata.get("comments", []),
            "x_label": result.metadata.get("x_label"),
            "y_label": result.metadata.get("y_label"),
            "flux_context": flux_context,
        }

        provenance_entry = {
            "event": "ingest",
            "importer": importer.__class__.__name__,
            "timestamp": self.provenance_service.timestamp(),
            "checksum": checksum,
        }

        return Spectrum.create(
            name=display_name or path.stem,
            wavelength_nm=wavelength_nm,
            flux=flux,
            flux_unit=self.units_service.canonical_flux_unit,
            metadata=metadata,
            provenance=[provenance_entry],
        )

    def _select_importer(self, path: Path) -> importers.Importer:
        ext = path.suffix.lower()
        if ext in self._importers:
            return self._importers[ext]
        raise ValueError(f"No importer registered for extension '{ext}'")

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(8192), b""):
                digest.update(chunk)
        return digest.hexdigest()
