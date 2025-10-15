"""Unit conversion utilities for spectra.

This module centralises conversions for wavelength and intensity units as
specified in ``specs/units_and_conversions.md``.  The application stores
spectral data internally using the canonical baseline of nanometres for the
independent axis and base-10 absorbance for the dependent axis.  All derived
views are generated from the canonical arrays so that round-trips are free of
numerical drift and the original data is never mutated.
"""


from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Any, Tuple, TYPE_CHECKING

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
    """Perform conversions between spectral units.

    The service exposes helpers to convert arbitrary wavelength and intensity
    units into the canonical representation as well as utilities to derive new
    views from a canonical :class:`~app.services.spectrum.Spectrum` instance.
    No method mutates the input arrays; new :class:`numpy.ndarray` instances are
    returned for every conversion.
    """

    float_dtype: np.dtype = field(default_factory=lambda: np.dtype(np.float64))

    # --- Public API -----------------------------------------------------
    def convert(self, spectrum: Spectrum, x_unit: str, y_unit: str) -> Tuple[np.ndarray, np.ndarray, Dict[str, Any]]:
        """Convert a canonical spectrum to the requested display units."""

        if spectrum.x_unit != _CANONICAL_X_UNIT:
            raise UnitError(
                "Spectrum.x_unit must be canonical 'nm' before conversion; received "
                f"{spectrum.x_unit!r}"
            )
        if spectrum.y_unit != _CANONICAL_Y_UNIT:
            raise UnitError(
                "Spectrum.y_unit must be canonical 'absorbance' before conversion; received "
                f"{spectrum.y_unit!r}"
            )

        x = self._from_canonical_wavelength(spectrum.x, x_unit)
        y = self._from_canonical_intensity(spectrum.y, y_unit)
        metadata: Dict[str, Any] = {}
        if x_unit != _CANONICAL_X_UNIT:
            metadata["x_conversion"] = f"{_CANONICAL_X_UNIT}→{x_unit}"
        if y_unit != _CANONICAL_Y_UNIT:
            metadata["y_conversion"] = f"{_CANONICAL_Y_UNIT}→{y_unit}"
        return x, y, metadata

    def from_canonical(
        self,
        x_nm: np.ndarray,
        y_absorbance: np.ndarray,
        x_unit: str,
        y_unit: str,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Convert canonical arrays into alternate display units."""

        x_nm = np.asarray(x_nm, dtype=self.float_dtype)
        y_absorbance = np.asarray(y_absorbance, dtype=self.float_dtype)
        x = self._from_canonical_wavelength(x_nm, x_unit)
        y = self._from_canonical_intensity(y_absorbance, y_unit)
        return x, y

    def to_canonical(self, x: np.ndarray, y: np.ndarray, x_unit: str, y_unit: str,
                     metadata: Dict[str, Any] | None = None) -> Tuple[np.ndarray, np.ndarray, Dict[str, Any]]:
        """Convert arbitrary units into the canonical baseline.

        Args:
            x: Independent-axis values.
            y: Dependent-axis values.
            x_unit: Unit describing ``x``.
            y_unit: Unit describing ``y``.
            metadata: Optional metadata dictionary to update with provenance.

        Returns:
            Tuple of ``(canonical_x, canonical_y, metadata)`` where the arrays
            are in nanometres and base-10 absorbance respectively.
        """

        canon_metadata: Dict[str, Any] = dict(metadata or {})
        canon_metadata.setdefault("source_units", {})
        canon_metadata["source_units"].update({"x": x_unit, "y": y_unit})

        canonical_x = self._to_canonical_wavelength(np.asarray(x, dtype=self.float_dtype), x_unit)
        canonical_y = self._to_canonical_intensity(np.asarray(y, dtype=self.float_dtype), y_unit, canon_metadata)
        return canonical_x, canonical_y, canon_metadata

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
            return 1e7 / data
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
            return np.array(1e7 / data_nm, dtype=self.float_dtype)
        raise UnitError(f"Unsupported destination x unit: {dst}")

    def _normalise_x_unit(self, unit: str) -> str:
        raw = unit.strip().lower().replace(" ", "")

        wavenumber_aliases = {
            "cm^-1",
            "cm-1",
            "cm^−1",
            "cm^–1",
            "cm^﹣1",
            "cm^－1",
            "cm^⁻1",
            "cm−1",
            "cm–1",
            "cm﹣1",
            "cm－1",
            "cm⁻1",
            "cm^-¹",
            "cm^−¹",
            "cm^–¹",
            "cm^﹣¹",
            "cm^－¹",
            "cm^⁻¹",
            "cm-¹",
            "cm−¹",
            "cm–¹",
            "cm﹣¹",
            "cm－¹",
            "cm⁻¹",
        }
        if raw in wavenumber_aliases:
            return "cm^-1"

        u = raw

        # Normalise Unicode minus/superscript characters that commonly appear in
        # wavenumber annotations (e.g. ``cm⁻¹``) so they map onto the ASCII token
        # handled by the conversion logic.
        for minus_variant in ("⁻", "−", "﹣", "－", "–", "—"):
            u = u.replace(minus_variant, "-")
        superscript_digits = {
            "⁰": "0",
            "¹": "1",
            "²": "2",
            "³": "3",
            "⁴": "4",
            "⁵": "5",
            "⁶": "6",
            "⁷": "7",
            "⁸": "8",
            "⁹": "9",
        }
        for superscript, digit in superscript_digits.items():
            u = u.replace(superscript, digit)
        if u == "cm-1":
            u = "cm^-1"

        mappings = {
            "nanometre": "nm",
            "nanometer": "nm",
            "micrometre": "um",
            "micrometer": "um",
            "angstrom": "angstrom",
            "ångström": "angstrom",
            "å": "angstrom",
        }
        return mappings.get(u, u)

    # --- Intensity helpers ----------------------------------------------
    def _to_canonical_intensity(self, data: np.ndarray, src: str, metadata: Dict[str, Any]) -> np.ndarray:
        unit = self._normalise_y_unit(src)
        if unit in {"absorbance", "a10"}:
            return data.copy()
        if unit in {"transmittance", "t"}:
            metadata.setdefault("intensity_conversion", {})
            metadata["intensity_conversion"].setdefault("transformation", "T→A10")
            return -np.log10(np.clip(data, 1e-12, None))
        if unit in {"percent_transmittance", "%t"}:
            metadata.setdefault("intensity_conversion", {})
            metadata["intensity_conversion"].setdefault("transformation", "%T→A10")
            fraction = data / 100.0
            return -np.log10(np.clip(fraction, 1e-12, None))
        if unit in {"absorbance_e", "ae"}:
            metadata.setdefault("intensity_conversion", {})
            metadata["intensity_conversion"].setdefault("transformation", "Ae→A10")
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
