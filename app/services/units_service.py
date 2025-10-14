"""Unit conversion utilities for spectra."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any
import numpy as np


class UnitError(ValueError):
    """Raised when an unsupported unit conversion is requested."""


@dataclass
class UnitsService:
    """Perform conversions between canonical and display units."""

    canonical_wavelength_unit: str = "nm"
    canonical_flux_unit: str = "absorbance"
    epsilon: float = 1e-12

    def convert_wavelength(self, data: np.ndarray, src: str, dst: str) -> np.ndarray:
        """Convert wavelength arrays using the canonical nm baseline."""

        src_norm = src.lower()
        dst_norm = dst.lower()
        nm = self._to_nm(np.asarray(data, dtype=float), src_norm)
        return self._from_nm(nm, dst_norm)

    def _to_nm(self, data: np.ndarray, unit: str) -> np.ndarray:
        if unit in {"nm", "nanometre", "nanometer"}:
            return np.array(data, copy=True)
        if unit in {"µm", "um", "micrometre", "micrometer"}:
            return data * 1_000.0
        if unit in {"å", "angstrom", "angström"}:
            return data / 10.0
        if unit in {"cm^-1", "1/cm", "wavenumber", "cm-1"}:
            with np.errstate(divide="ignore"):
                return 1e7 / data
        raise UnitError(f"Unsupported wavelength unit: {unit}")

    def _from_nm(self, nm: np.ndarray, unit: str) -> np.ndarray:
        if unit in {"nm", "nanometre", "nanometer"}:
            return np.array(nm, copy=True)
        if unit in {"µm", "um", "micrometre", "micrometer"}:
            return nm / 1_000.0
        if unit in {"å", "angstrom", "angström"}:
            return nm * 10.0
        if unit in {"cm^-1", "1/cm", "wavenumber", "cm-1"}:
            with np.errstate(divide="ignore"):
                return 1e7 / nm
        raise UnitError(f"Unsupported wavelength unit: {unit}")

    def convert_flux(
        self,
        data: np.ndarray,
        src: str,
        dst: str,
        *,
        context: Dict[str, Any],
    ) -> np.ndarray:
        """Convert flux/intensity arrays using base-10 absorbance as canonical."""

        src_norm = src.lower()
        dst_norm = dst.lower()
        canonical = self._to_absorbance(np.asarray(data, dtype=float), src_norm, context)
        return self._from_absorbance(canonical, dst_norm, context)

    def _to_absorbance(self, data: np.ndarray, unit: str, context: Dict[str, Any]) -> np.ndarray:
        if unit in {"absorbance", "a10", "absorbance_base10"}:
            return np.array(data, copy=True)
        if unit in {"transmittance", "t"}:
            clipped = np.clip(data, self.epsilon, None)
            return -np.log10(clipped)
        if unit in {"percent_transmittance", "%t", "pct_t"}:
            frac = np.clip(data / 100.0, self.epsilon, None)
            return -np.log10(frac)
        if unit in {"absorbance_e", "ae"}:
            return np.array(data, copy=True) / np.log(10.0)
        if unit in {"absorption_coefficient", "alpha"}:
            path = context.get("path_length_m")
            mole_fraction = context.get("mole_fraction")
            if path is None or mole_fraction is None:
                raise UnitError("Absorption coefficient conversion requires 'path_length_m' and 'mole_fraction'.")
            base = context.get("absorption_base", "10").lower()
            product = np.array(data, copy=True) * float(path) * float(mole_fraction)
            if base == "e":
                return product / np.log(10.0)
            return product
        raise UnitError(f"Unsupported flux unit: {unit}")

    def _from_absorbance(self, data: np.ndarray, unit: str, context: Dict[str, Any]) -> np.ndarray:
        if unit in {"absorbance", "a10", "absorbance_base10"}:
            return np.array(data, copy=True)
        if unit in {"transmittance", "t"}:
            return np.power(10.0, -data)
        if unit in {"percent_transmittance", "%t", "pct_t"}:
            return np.power(10.0, -data) * 100.0
        if unit in {"absorbance_e", "ae"}:
            return np.array(data, copy=True) * np.log(10.0)
        if unit in {"absorption_coefficient", "alpha"}:
            path = context.get("path_length_m")
            mole_fraction = context.get("mole_fraction")
            if path is None or mole_fraction is None:
                raise UnitError("Absorption coefficient conversion requires 'path_length_m' and 'mole_fraction'.")
            base = context.get("absorption_base", "10").lower()
            if base == "e":
                return data * np.log(10.0) / (float(path) * float(mole_fraction))
            return data / (float(path) * float(mole_fraction))
        raise UnitError(f"Unsupported flux unit: {unit}")
