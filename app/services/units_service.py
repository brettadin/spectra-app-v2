"""Unit conversion utilities for spectra.

This module centralises conversions for wavelength and intensity units as
specified in ``specs/units_and_conversions.md``.  Conversions are performed on
demand so that ingested data can remain in its original units until the user
requests alternative representations.
"""


from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Tuple, TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from .spectrum import Spectrum
else:
    Spectrum = Any


_CANONICAL_X_UNIT = "nm"
_CANONICAL_Y_UNIT = "absorbance"  # Base-10 absorbance (A10)


class UnitError(ValueError):
    """Raised when an unsupported unit is encountered."""


@dataclass
class UnitsService:
    """Perform conversions between spectral units without mutating inputs."""

    float_dtype: np.dtype = field(default_factory=lambda: np.dtype(np.float64))

    # --- Public API -----------------------------------------------------
    def convert(self, spectrum: Spectrum, x_unit: str, y_unit: str) -> Tuple[np.ndarray, np.ndarray, Dict[str, Any]]:
        """Convert a spectrum from its stored units to the requested display units."""

        return self.convert_arrays(spectrum.x, spectrum.y, spectrum.x_unit, spectrum.y_unit, x_unit, y_unit)

    def convert_arrays(
        self,
        x: np.ndarray,
        y: np.ndarray,
        src_x_unit: str,
        src_y_unit: str,
        dst_x_unit: str,
        dst_y_unit: str,
    ) -> Tuple[np.ndarray, np.ndarray, Dict[str, Any]]:
        """Convert arbitrary arrays between two unit systems using canonical pivots."""

        src_x = self._normalise_x_unit(src_x_unit)
        dst_x = self._normalise_x_unit(dst_x_unit)
        src_y = self._normalise_y_unit(src_y_unit)
        dst_y = self._normalise_y_unit(dst_y_unit)

        canonical_x = self._to_canonical_wavelength(np.asarray(x, dtype=self.float_dtype), src_x)
        intensity_meta: Dict[str, Any] = {}
        canonical_y = self._to_canonical_intensity(np.asarray(y, dtype=self.float_dtype), src_y, intensity_meta)

        converted_x = self._from_canonical_wavelength(canonical_x, dst_x)
        converted_y = self._from_canonical_intensity(canonical_y, dst_y)

        metadata: Dict[str, Any] = {}
        if src_x != dst_x:
            metadata["x_conversion"] = f"{src_x}→{dst_x}"
        if src_y != dst_y:
            metadata["y_conversion"] = f"{src_y}→{dst_y}"
        if intensity_meta:
            metadata.update(intensity_meta)
        if metadata:
            metadata.setdefault("source_units", {"x": src_x, "y": src_y})
        return converted_x, converted_y, metadata

    def from_canonical(
        self,
        x_nm: np.ndarray,
        y_absorbance: np.ndarray,
        x_unit: str,
        y_unit: str,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Convert canonical arrays into alternate display units."""

        converted_x, converted_y, _ = self.convert_arrays(
            np.asarray(x_nm, dtype=self.float_dtype),
            np.asarray(y_absorbance, dtype=self.float_dtype),
            _CANONICAL_X_UNIT,
            _CANONICAL_Y_UNIT,
            x_unit,
            y_unit,
        )
        return converted_x, converted_y

    def to_canonical(
        self,
        x: np.ndarray,
        y: np.ndarray,
        x_unit: str,
        y_unit: str,
        metadata: Dict[str, Any] | None = None,
    ) -> Tuple[np.ndarray, np.ndarray, Dict[str, Any]]:
        """Convert arbitrary units into the canonical baseline without mutating inputs."""

        canon_metadata: Dict[str, Any] = dict(metadata) if metadata is not None else {}
        source_units = canon_metadata.setdefault("source_units", {})
        source_units.update({"x": self._normalise_x_unit(x_unit), "y": self._normalise_y_unit(y_unit)})

        canonical_x = self._to_canonical_wavelength(np.asarray(x, dtype=self.float_dtype), x_unit)
        canonical_y = self._to_canonical_intensity(np.asarray(y, dtype=self.float_dtype), y_unit, canon_metadata)
        return canonical_x, canonical_y, canon_metadata

    def normalise_x_unit(self, unit: str) -> str:
        """Expose axis unit normalisation for importers and UI components."""

        return self._normalise_x_unit(unit)

    def normalise_y_unit(self, unit: str) -> str:
        """Expose intensity unit normalisation for importers and UI components."""

        return self._normalise_y_unit(unit)

    # --- Wavelength helpers ---------------------------------------------
    def _to_canonical_wavelength(self, data: np.ndarray, src: str) -> np.ndarray:
        unit = self._normalise_x_unit(src)
        if unit == "nm":
            return data.copy()
        if unit in {"um", "µm"}:
            return data * 1e3
        if unit in {"angstrom", "å", "Å"}:
            return data / 10.0
        if unit in {"cm^-1", "1/cm", "wavenumber"}:
            # ν̅ (cm^-1) → λ (nm): λ_nm = 1e7 / ν̅
            data = np.asarray(data, dtype=self.float_dtype)
            result = np.empty_like(data)
            with np.errstate(divide="ignore", invalid="ignore"):
                np.divide(1e7, data, out=result, where=data != 0)
            if np.any(data == 0):
                result = result.astype(self.float_dtype, copy=False)
                result[data == 0] = np.inf
            return result
        raise UnitError(f"Unsupported source x unit: {src}")

    def _from_canonical_wavelength(self, data_nm: np.ndarray, dst: str) -> np.ndarray:
        unit = self._normalise_x_unit(dst)
        if unit == "nm":
            return np.array(data_nm, dtype=self.float_dtype, copy=True)
        if unit in {"um", "µm"}:
            return np.array(data_nm / 1e3, dtype=self.float_dtype)
        if unit in {"angstrom", "å", "Å"}:
            return np.array(data_nm * 10.0, dtype=self.float_dtype)
        if unit in {"cm^-1", "1/cm", "wavenumber"}:
            data_nm = np.asarray(data_nm, dtype=self.float_dtype)
            result = np.empty_like(data_nm)
            with np.errstate(divide="ignore", invalid="ignore"):
                np.divide(1e7, data_nm, out=result, where=data_nm != 0)
            if np.any(data_nm == 0):
                result = result.astype(self.float_dtype, copy=False)
                result[data_nm == 0] = np.inf
            return result
        raise UnitError(f"Unsupported destination x unit: {dst}")

    def _normalise_x_unit(self, unit: str) -> str:
        u = unit.strip().lower()
        # Normalise common Unicode minus signs (⁻, −) to ASCII '-'.
        u = u.replace("⁻", "-").replace("−", "-").replace("¹", "1")
        mappings = {
            "nanometre": "nm",
            "nanometer": "nm",
            "micrometre": "um",
            "micrometer": "um",
            "angstrom": "angstrom",
            "ångström": "angstrom",
            "å": "angstrom",
            "cm-1": "cm^-1",
        }
        return mappings.get(u, u)

    # --- Intensity helpers ----------------------------------------------
    def _to_canonical_intensity(self, data: np.ndarray, src: str, metadata: Dict[str, Any] | None) -> np.ndarray:
        unit = self._normalise_y_unit(src)
        meta = metadata if metadata is not None else None
        if unit in {"absorbance", "a10"}:
            return data.copy()
        if unit in {"transmittance", "t"}:
            if meta is not None:
                meta.setdefault("intensity_conversion", {})
                meta["intensity_conversion"].setdefault("transformation", "T→A10")
            return -np.log10(np.clip(data, 1e-12, None))
        if unit in {"percent_transmittance", "%t"}:
            if meta is not None:
                meta.setdefault("intensity_conversion", {})
                meta["intensity_conversion"].setdefault("transformation", "%T→A10")
            fraction = data / 100.0
            return -np.log10(np.clip(fraction, 1e-12, None))
        if unit in {"absorbance_e", "ae"}:
            if meta is not None:
                meta.setdefault("intensity_conversion", {})
                meta["intensity_conversion"].setdefault("transformation", "Ae→A10")
            return data / 2.303
        raise UnitError(f"Unsupported source y unit: {src}")

    def _from_canonical_intensity(self, data: np.ndarray, dst: str) -> np.ndarray:
        unit = self._normalise_y_unit(dst)
        if unit in {"absorbance", "a10"}:
            return np.array(data, dtype=self.float_dtype, copy=True)
        if unit in {"transmittance", "t"}:
            return np.array(10 ** (-data), dtype=self.float_dtype)
        if unit in {"percent_transmittance", "%t"}:
            return np.array(10 ** (-data) * 100.0, dtype=self.float_dtype)
        if unit in {"absorbance_e", "ae"}:
            return np.array(data * 2.303, dtype=self.float_dtype)
        raise UnitError(f"Unsupported destination y unit: {dst}")

    def _normalise_y_unit(self, unit: str) -> str:
        return unit.strip().lower()
