"""Overlay management for multiple spectra."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, cast

import numpy as np

from .spectrum import Spectrum
from .units_service import UnitsService
from .line_shapes import LineShapeModel


def _blank_spectra() -> Dict[str, Spectrum]:
    return {}


@dataclass
class OverlayService:
    """Store spectra and provide overlay-ready views."""

    units_service: UnitsService
    line_shape_model: LineShapeModel | None = None
    _spectra: Dict[str, Spectrum] = field(default_factory=_blank_spectra)

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
            canonical_x, canonical_y, _ = self.units_service.to_canonical(
                spectrum.x,
                spectrum.y,
                spectrum.x_unit,
                spectrum.y_unit,
                metadata=None,
            )
            working_y, norm_meta = self._apply_normalization(canonical_x, canonical_y, normalization)
            working_x = np.array(canonical_x, dtype=np.float64, copy=True)
            raw_line_shapes = spectrum.metadata.get("line_shapes")
            line_shape_specs = cast(Optional[List[Dict[str, Any]]], raw_line_shapes if isinstance(raw_line_shapes, list) else None)
            line_shape_metadata: Optional[Dict[str, Any]] = None
            if self.line_shape_model and line_shape_specs is not None:
                outcome = self.line_shape_model.apply_sequence(working_x, working_y, line_shape_specs)
                if outcome is not None:
                    working_x = outcome.x
                    working_y = outcome.y
                    line_shape_metadata = outcome.metadata
            x_display, y_display, conversion_meta = self.units_service.convert_arrays(
                working_x,
                working_y,
                "nm",
                "absorbance",
                x_unit,
                y_unit,
            )
            metadata: Dict[str, Any] = dict(spectrum.metadata)
            if norm_meta:
                metadata = dict(metadata)  # shallow copy to avoid mutating cached metadata
                metadata["normalization"] = norm_meta
            if line_shape_metadata is not None:
                metadata = dict(metadata)
                metadata["line_shapes"] = {
                    "specifications": list(line_shape_specs) if line_shape_specs is not None else [],
                    "results": line_shape_metadata,
                }
            if conversion_meta:
                metadata = dict(metadata)
                metadata["display_conversions"] = dict(conversion_meta)
            view: Dict[str, object] = {
                "id": spectrum.id,
                "name": spectrum.name,
                "x": x_display,
                "y": y_display,
                "x_unit": x_unit,
                "y_unit": y_unit,
                "metadata": metadata,
                "x_canonical": np.array(working_x, copy=True),
                "y_canonical": working_y,
            }
            views.append(view)
        return views

    def _apply_normalization(
        self,
        canonical_x: np.ndarray,
        canonical_y: np.ndarray,
        mode: str,
    ) -> tuple[np.ndarray, Optional[Dict[str, object]]]:
        data = np.asarray(canonical_y, dtype=np.float64)
        x = np.asarray(canonical_x, dtype=np.float64)
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
            return data / area, {"mode": "area", "applied": True, "scale": area, "basis": "abs-trapz"}

        return data.copy(), {"mode": mode, "applied": False, "reason": "unknown-mode"}
