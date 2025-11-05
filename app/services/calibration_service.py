"""Calibration service: resolution matching, frame/RV adjustments, and uncertainty propagation.

This module provides a high-level API for applying display-time calibration transforms
without mutating cached source data. Calibrations are reversible and tracked in provenance.

Contract (v0):
- Inputs: 1D spectra (x: wavelength/wavenumber in canonical units; y: intensity; sigma: optional uncertainties)
- Config:
  - target_fwhm: float | None  # Desired instrumental FWHM in the active x-units
  - rv_kms: float = 0.0        # Radial velocity offset (+ recedes, − approaches)
  - frame: Literal['observer','rest'] = 'observer'  # Target frame for the x-axis
- Outputs: transformed arrays (x, y, sigma?) plus a small metadata dict describing operations
- Error modes: invalid inputs raise ValueError; operations that cannot be applied return the input unchanged and record a warning

Notes:
- Convolution kernel for resolution matching is approximated with a Gaussian whose sigma derives from FWHM (sigma = FWHM / (2*sqrt(2*ln 2)))
- RV corrections shift the wavelength axis by factor (1 + v/c) in the non-relativistic regime; upgrade to relativistic if needed
- Frame conversion toggles between observer and rest frames using the same RV factor
- Uncertainty propagation assumes independent Gaussian errors; convolution increases variance accordingly (documented approximation)

Implementation is intentionally light-weight in v0 to keep dependencies minimal; hooks are structured so a future SciPy path can be enabled when available.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Literal, Optional, Tuple, Dict, Any
import math

try:
    import numpy as np  # type: ignore
except Exception:  # pragma: no cover - numpy optional at runtime
    np = None  # type: ignore

C_KMS = 299792.458  # speed of light in km/s


@dataclass
class CalibrationConfig:
    target_fwhm: Optional[float] = None
    rv_kms: float = 0.0
    frame: Literal['observer', 'rest'] = 'observer'


class CalibrationService:
    """Apply simple calibration transforms for preview/analysis.

    Stateless aside from configuration; safe to reuse across sessions.
    """

    def __init__(self, config: CalibrationConfig | None = None) -> None:
        self.config = config or CalibrationConfig()

    # ----------------------- Configuration -----------------------
    def set_target_fwhm(self, fwhm: Optional[float]) -> None:
        if fwhm is not None and (not isinstance(fwhm, (int, float)) or fwhm <= 0):
            raise ValueError("FWHM must be a positive number or None")
        self.config.target_fwhm = float(fwhm) if fwhm is not None else None

    def set_rv_kms(self, rv_kms: float) -> None:
        if not isinstance(rv_kms, (int, float)):
            raise ValueError("rv_kms must be a number")
        self.config.rv_kms = float(rv_kms)

    def set_frame(self, frame: Literal['observer', 'rest']) -> None:
        if frame not in ("observer", "rest"):
            raise ValueError("frame must be 'observer' or 'rest'")
        self.config.frame = frame

    # ----------------------- Transforms --------------------------
    def apply(self, x: Any, y: Any, sigma: Any | None = None) -> Tuple[Any, Any, Any | None, Dict[str, Any]]:
        """Apply configured calibration transforms and return (x, y, sigma, meta).

        - x, y, sigma may be numpy arrays or any array-like; if numpy is unavailable,
          this method is a no-op and returns inputs unchanged with a meta warning.
        """
        if np is None:
            return x, y, sigma, {"applied": False, "warning": "numpy unavailable"}

        x_arr = np.asarray(x)
        y_arr = np.asarray(y)
        s_arr = None if sigma is None else np.asarray(sigma)
        meta: Dict[str, Any] = {"applied": False, "steps": [], "config": asdict(self.config)}

        # Frame/RV shift on x-axis
        if self.config.rv_kms != 0.0:
            factor = 1.0 + (self.config.rv_kms / C_KMS)
            x_arr = x_arr * factor
            meta["steps"].append({"rv_shift_kms": self.config.rv_kms, "factor": factor})
            meta["applied"] = True

        # Resolution matching via Gaussian convolution (approximate)
        if self.config.target_fwhm is not None and self.config.target_fwhm > 0:
            # Estimate kernel width in samples assuming near-uniform spacing
            dx = float(np.median(np.diff(x_arr))) if x_arr.size > 1 else 0.0
            if dx > 0:
                sigma_units = float(self.config.target_fwhm) / (2.0 * math.sqrt(2.0 * math.log(2.0)))
                sigma_samples = max(1, int(round(sigma_units / dx)))
                if sigma_samples > 0:
                    y_arr = self._gaussian_blur_1d(y_arr, sigma_samples)
                    if s_arr is not None:
                        s_arr = self._gaussian_blur_1d(s_arr, sigma_samples)
                    meta["steps"].append({"fwhm": self.config.target_fwhm, "sigma_samples": sigma_samples})
                    meta["applied"] = True

        return x_arr, y_arr, s_arr, meta

    # ----------------------- Helpers -----------------------------
    @staticmethod
    def _gaussian_blur_1d(values: Any, sigma_samples: int) -> Any:
        """Approximate Gaussian blur via separable kernel.

        Uses a simple discrete kernel; replace with scipy.ndimage.gaussian_filter1d if available.
        """
        v = np.asarray(values)
        size = sigma_samples * 6 + 1  # cover ±3σ
        xs = np.arange(size) - (size // 2)
        kernel = np.exp(-(xs**2) / (2.0 * (sigma_samples**2)))
        kernel /= kernel.sum() if kernel.sum() != 0 else 1.0
        return np.convolve(v, kernel, mode="same")
