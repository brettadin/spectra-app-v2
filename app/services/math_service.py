"""Mathematical operations on spectra."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple
import logging

import numpy as np

from .spectrum import Spectrum
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MathResult:
    """Result of a math operation, with suppression information."""

    spectrum: Optional[Spectrum]
    suppressed: bool
    message: str


@dataclass
class MathService:
    """Perform differential operations on spectra."""

    epsilon: float = 1e-9

    def difference(self, a: Spectrum, b: Spectrum, *, label: Optional[str] = None) -> MathResult:
        grid, a_flux, b_flux = self._aligned_flux(a, b)
        diff = a_flux - b_flux
        if np.allclose(diff, 0.0, atol=self.epsilon):
            logger.info("Difference suppressed: spectra %s and %s nearly identical", a.id, b.id)
            return MathResult(spectrum=None, suppressed=True, message="difference_below_epsilon")
        spectrum = Spectrum.create(
            name=label or f"{a.name} − {b.name}",
            wavelength_nm=grid,
            flux=diff,
            flux_unit=a.flux_unit,
            metadata={
                "operation": "difference",
                "operands": [a.id, b.id],
            },
            provenance=[
                {
                    "event": "math_difference",
                    "inputs": [a.id, b.id],
                    "epsilon": self.epsilon,
                }
            ],
        )
        return MathResult(spectrum=spectrum, suppressed=False, message="ok")

    def ratio(self, a: Spectrum, b: Spectrum, *, label: Optional[str] = None) -> MathResult:
        grid, a_flux, b_flux = self._aligned_flux(a, b)
        mask = np.abs(b_flux) < self.epsilon
        ratio = np.empty_like(a_flux)
        ratio[mask] = np.nan
        np.divide(a_flux, b_flux, out=ratio, where=~mask)
        valid = ratio[~np.isnan(ratio)]
        if (valid.size == 0 and not mask.any()) or (np.allclose(valid, 1.0, atol=self.epsilon) and not mask.any()):
            logger.info("Ratio suppressed: spectra %s and %s nearly identical", a.id, b.id)
            return MathResult(spectrum=None, suppressed=True, message="ratio_near_unity")
        metadata = {
            "operation": "ratio",
            "operands": [a.id, b.id],
            "epsilon_mask_count": int(mask.sum()),
        }
        provenance = [
            {
                "event": "math_ratio",
                "inputs": [a.id, b.id],
                "epsilon": self.epsilon,
                "masked_points": int(mask.sum()),
            }
        ]
        spectrum = Spectrum.create(
            name=label or f"{a.name} ÷ {b.name}",
            wavelength_nm=grid,
            flux=np.nan_to_num(ratio, nan=0.0, posinf=0.0, neginf=0.0),
            flux_unit=a.flux_unit,
            metadata=metadata,
            provenance=provenance,
        )
        return MathResult(spectrum=spectrum, suppressed=False, message="ok")

    def _aligned_flux(self, a: Spectrum, b: Spectrum) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        if not np.allclose(a.wavelength_nm, b.wavelength_nm):
            grid = self._common_grid(a.wavelength_nm, b.wavelength_nm)
            a_flux = np.interp(grid, a.wavelength_nm, a.flux)
            b_flux = np.interp(grid, b.wavelength_nm, b.flux)
            return grid, a_flux, b_flux
        return a.wavelength_nm, a.flux, b.flux

    @staticmethod
    def _common_grid(a: np.ndarray, b: np.ndarray) -> np.ndarray:
        start = max(a.min(), b.min())
        stop = min(a.max(), b.max())
        if start >= stop:
            raise ValueError("Spectra do not overlap; cannot compute common grid")
        points = max(len(a), len(b))
        return np.linspace(start, stop, points)
