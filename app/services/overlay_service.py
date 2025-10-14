"""Overlay management for multiple spectra."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List

from .spectrum import Spectrum
from .units_service import UnitsService


@dataclass
class OverlayService:
    """Store spectra and provide overlay-ready views."""

    units_service: UnitsService
    _spectra: Dict[str, Spectrum] = field(default_factory=dict)

    def add(self, spectrum: Spectrum) -> None:
        self._spectra[spectrum.id] = spectrum

    def remove(self, spectrum_id: str) -> None:
        self._spectra.pop(spectrum_id, None)

    def clear(self) -> None:
        self._spectra.clear()

    def get(self, spectrum_id: str) -> Spectrum:
        return self._spectra[spectrum_id]

    def list(self) -> List[Spectrum]:
        return list(self._spectra.values())

    def overlay(self, spectrum_ids: Iterable[str], x_unit: str, y_unit: str) -> List[Dict[str, object]]:
        views = []
        for sid in spectrum_ids:
            spectrum = self._spectra[sid]
            views.append(spectrum.view(self.units_service, x_unit, y_unit))
        return views
