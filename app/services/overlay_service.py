"""Manage loaded spectra and overlay state."""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Iterable, List, Optional
import logging

from .spectrum import Spectrum

logger = logging.getLogger(__name__)


@dataclass
class OverlayService:
    """Maintain an ordered collection of spectra for display and operations."""

    _spectra: "OrderedDict[str, Spectrum]" = field(default_factory=OrderedDict)

    def add(self, spectrum: Spectrum) -> Spectrum:
        if spectrum.id in self._spectra:
            logger.info("Spectrum %s already loaded; skipping duplicate", spectrum.id)
            return self._spectra[spectrum.id]
        self._spectra[spectrum.id] = spectrum
        return spectrum

    def replace(self, spectrum: Spectrum) -> None:
        self._spectra[spectrum.id] = spectrum

    def remove(self, spectrum_id: str) -> None:
        self._spectra.pop(spectrum_id, None)

    def clear(self) -> None:
        self._spectra.clear()

    def spectra(self) -> List[Spectrum]:
        return list(self._spectra.values())

    def get(self, spectrum_id: str) -> Optional[Spectrum]:
        return self._spectra.get(spectrum_id)

    def rename(self, spectrum_id: str, new_name: str) -> Optional[Spectrum]:
        spectrum = self._spectra.get(spectrum_id)
        if spectrum is None:
            return None
        updated = spectrum.with_name(new_name)
        self._spectra[spectrum_id] = updated
        return updated

    def order(self, ordered_ids: Iterable[str]) -> None:
        new_order = OrderedDict()
        for key in ordered_ids:
            if key in self._spectra:
                new_order[key] = self._spectra[key]
        # append any missing ones at the end preserving existing order
        for key, value in self._spectra.items():
            if key not in new_order:
                new_order[key] = value
        self._spectra = new_order
