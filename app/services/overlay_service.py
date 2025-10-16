"""Overlay management for multiple spectra."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional

import numpy as np

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

    def overlay(
        self,
        spectrum_ids: Iterable[str],
        x_unit: str,
        y_unit: str,
        *,
        normalization: str = "None",
    ) -> List[Dict[str, object]]:
        views: List[Dict[str, object]] = []
        for sid in spectrum_ids:
            spectrum = self._spectra[sid]
            canonical_y, norm_meta = self._apply_normalization(spectrum, normalization)
            x_display, y_display = self.units_service.from_canonical(spectrum.x, canonical_y, x_unit, y_unit)
            metadata: Dict[str, Any] = dict(spectrum.metadata)
            if norm_meta:
                metadata = dict(metadata)  # shallow copy to avoid mutating cached metadata
                metadata["normalization"] = norm_meta
            view: Dict[str, object] = {
                "id": spectrum.id,
                "name": spectrum.name,
                "x": x_display,
                "y": y_display,
                "x_unit": x_unit,
                "y_unit": y_unit,
                "metadata": metadata,
                "x_canonical": np.array(spectrum.x, copy=True),
                "y_canonical": canonical_y,
            }
            views.append(view)
        return views

    def _apply_normalization(self, spectrum: Spectrum, mode: str) -> tuple[np.ndarray, Optional[Dict[str, object]]]:
        data = np.asarray(spectrum.y, dtype=np.float64)
        x = np.asarray(spectrum.x, dtype=np.float64)
        if mode.lower() in {"none", "", "identity"}:
            return data.copy(), None

        finite_mask = np.isfinite(data) & np.isfinite(x)
        if not np.any(finite_mask):
            return data.copy(), {"mode": mode, "applied": False, "reason": "no-finite-values"}

        mode_lower = mode.lower()
        if mode_lower == "max":
            scale = float(np.nanmax(np.abs(data[finite_mask])))
            if not np.isfinite(scale) or scale <= 0.0:
                return data.copy(), {"mode": "max", "applied": False, "reason": "degenerate-scale"}
            return data / scale, {"mode": "max", "applied": True, "scale": scale}

        if mode_lower == "area":
            x_finite = x[finite_mask]
            y_finite = np.abs(data[finite_mask])
            if x_finite.size < 2:
                return data.copy(), {"mode": "area", "applied": False, "reason": "insufficient-samples"}
            area = float(np.trapezoid(y_finite, x_finite))
            if not np.isfinite(area) or area <= 0.0:
                return data.copy(), {"mode": "area", "applied": False, "reason": "degenerate-area"}
            return data / area, {"mode": "area", "applied": True, "scale": area, "basis": "abs-trapezoid"}

        return data.copy(), {"mode": mode, "applied": False, "reason": "unknown-mode"}
