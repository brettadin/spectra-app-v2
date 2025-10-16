"""Utility helpers for applying bundled line-shape placeholder models."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Optional, Sequence

import numpy as np

C_LIGHT_KMS = 299_792.458


@dataclass(frozen=True)
class LineShapeOutcome:
    """Container for transformed arrays and provenance metadata."""

    x: np.ndarray
    y: np.ndarray
    metadata: Dict[str, Any]


class LineShapeModel:
    """Apply Doppler, pressure, and Stark placeholders to spectral arrays."""

    def __init__(
        self,
        placeholders: Sequence[Mapping[str, Any]],
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        self._definitions: Dict[str, Mapping[str, Any]] = {
            str(entry.get("id")): entry for entry in placeholders if "id" in entry
        }
        meta = metadata or {}
        references = meta.get("references") if isinstance(meta, Mapping) else None
        if isinstance(references, list):
            self._references = [ref for ref in references if isinstance(ref, Mapping)]
        else:
            self._references = []
        self._notes = str(meta.get("notes", "")) if isinstance(meta, Mapping) else ""

    # ------------------------------------------------------------------
    def definition(self, model_id: str) -> Optional[Mapping[str, Any]]:
        return self._definitions.get(model_id)

    def example_parameters(self, model_id: str) -> Dict[str, Any]:
        definition = self.definition(model_id)
        if not isinstance(definition, Mapping):
            return {}
        params = definition.get("example_parameters")
        if isinstance(params, Mapping):
            return {str(k): v for k, v in params.items()}
        return {}

    # ------------------------------------------------------------------
    def apply(
        self,
        model_id: str,
        x: np.ndarray,
        y: np.ndarray,
        parameters: Mapping[str, Any] | None = None,
    ) -> LineShapeOutcome:
        model_id = str(model_id)
        parameters = parameters or {}
        params = {str(k): parameters[k] for k in parameters.keys()}
        x_in = np.asarray(x, dtype=np.float64)
        y_in = np.asarray(y, dtype=np.float64)

        if model_id == "doppler_shift":
            outcome = self._apply_doppler_shift(x_in, y_in, params)
        elif model_id == "pressure_broadening":
            outcome = self._apply_pressure_broadening(x_in, y_in, params)
        elif model_id == "stark_broadening":
            outcome = self._apply_stark_broadening(x_in, y_in, params)
        else:
            meta = {
                "model": model_id,
                "applied": False,
                "reason": "unknown-model",
                "parameters": params,
            }
            return LineShapeOutcome(np.array(x_in, copy=True), np.array(y_in, copy=True), meta)

        outcome.metadata.setdefault("model", model_id)
        outcome.metadata.setdefault("parameters", params)
        if self._references:
            outcome.metadata.setdefault(
                "references",
                [ref.get("citation") for ref in self._references if isinstance(ref, Mapping)],
            )
        if self._notes:
            outcome.metadata.setdefault("notes", self._notes)
        return outcome

    def apply_sequence(
        self,
        x: np.ndarray,
        y: np.ndarray,
        specifications: Iterable[Mapping[str, Any]] | None,
    ) -> Optional[LineShapeOutcome]:
        specs = list(specifications or [])
        if not specs:
            return None

        current_x = np.array(x, dtype=np.float64, copy=True)
        current_y = np.array(y, dtype=np.float64, copy=True)
        applied: List[Dict[str, Any]] = []

        for spec in specs:
            if not isinstance(spec, Mapping):
                applied.append({"applied": False, "reason": "invalid-spec", "spec": spec})
                continue
            model_id = str(spec.get("model", ""))
            params = spec.get("parameters")
            params_map = params if isinstance(params, Mapping) else {}
            outcome = self.apply(model_id, current_x, current_y, params_map)
            current_x = outcome.x
            current_y = outcome.y
            applied.append({
                "model": model_id,
                "parameters": dict(params_map),
                "result": outcome.metadata,
            })

        combined_meta: Dict[str, Any] = {
            "applied": True,
            "models": applied,
        }
        if self._references:
            combined_meta["references"] = [
                ref.get("citation") for ref in self._references if isinstance(ref, Mapping)
            ]
        return LineShapeOutcome(current_x, current_y, combined_meta)

    # ------------------------------------------------------------------
    def sample_profile(
        self,
        model_id: str,
        parameters: Mapping[str, Any] | None = None,
        grid: np.ndarray | None = None,
    ) -> Optional[LineShapeOutcome]:
        params = self.example_parameters(model_id)
        if parameters:
            for key, value in parameters.items():
                params[str(key)] = value

        centre = self._coerce_float(
            params.get("rest_wavelength_nm")
            or params.get("line_centre_nm")
            or 656.281
        )
        if not np.isfinite(centre):
            centre = 656.281

        if grid is not None:
            base_x = np.asarray(grid, dtype=np.float64)
        else:
            span = 3.0 if model_id == "doppler_shift" else 2.0
            base_x = np.linspace(centre - span, centre + span, 801, dtype=np.float64)

        sigma = 0.18 if model_id == "doppler_shift" else 0.12
        base_profile = np.exp(-0.5 * ((base_x - centre) / sigma) ** 2)

        outcome = self.apply(model_id, base_x, base_profile, params)
        y = np.array(outcome.y, copy=True)
        peak = float(np.nanmax(np.abs(y))) if y.size else 0.0
        if peak > 0.0 and np.isfinite(peak):
            y /= peak
        outcome_meta = dict(outcome.metadata)
        outcome_meta.setdefault("normalisation_peak", peak if peak else 1.0)
        outcome_meta.setdefault("parameters", params)
        return LineShapeOutcome(outcome.x, y, outcome_meta)

    # ------------------------------------------------------------------
    def _apply_doppler_shift(
        self,
        x: np.ndarray,
        y: np.ndarray,
        parameters: MutableMapping[str, Any],
    ) -> LineShapeOutcome:
        velocity = self._coerce_float(parameters.get("radial_velocity_kms"), default=0.0)
        beta = float(np.clip(velocity / C_LIGHT_KMS, -0.95, 0.95))
        factor = math.sqrt((1.0 + beta) / (1.0 - beta)) if abs(beta) < 1.0 else 1.0
        shifted_x = x * factor
        metadata: Dict[str, Any] = {
            "applied": True,
            "beta": beta,
            "doppler_factor": factor,
            "radial_velocity_kms": velocity,
        }
        rest_wavelength = self._coerce_float(parameters.get("rest_wavelength_nm"))
        if rest_wavelength is not None and np.isfinite(rest_wavelength):
            observed = rest_wavelength * factor
            metadata["rest_wavelength_nm"] = rest_wavelength
            metadata["observed_wavelength_nm"] = observed
            metadata["delta_nm"] = observed - rest_wavelength
        return LineShapeOutcome(shifted_x, np.array(y, copy=True), metadata)

    def _apply_pressure_broadening(
        self,
        x: np.ndarray,
        y: np.ndarray,
        parameters: MutableMapping[str, Any],
    ) -> LineShapeOutcome:
        gamma_l = abs(self._coerce_float(parameters.get("gamma_L"), default=0.0) or 0.0)
        density = abs(self._coerce_float(parameters.get("perturber_density"), default=0.0) or 0.0)
        width = gamma_l * density
        spacing = self._characteristic_spacing(x)
        width = max(width, spacing * 0.25)

        kernel = self._lorentz_kernel(width, spacing, size=401)
        kernel_sum = float(kernel.sum())
        if kernel_sum == 0.0 or not np.isfinite(kernel_sum):
            kernel = np.zeros_like(kernel)
            kernel[len(kernel) // 2] = 1.0
            kernel_sum = 1.0
        kernel /= kernel_sum

        filled = np.nan_to_num(y, nan=0.0, posinf=0.0, neginf=0.0)
        broadened = np.convolve(filled, kernel, mode="same")
        metadata = {
            "applied": True,
            "gamma_L": gamma_l,
            "perturber_density": density,
            "width_nm": width,
            "kernel_size": int(kernel.size),
            "kernel_sum": float(np.sum(kernel)),
            "spacing_nm": spacing,
        }
        centre = self._coerce_float(parameters.get("line_centre_nm"))
        if centre is not None and np.isfinite(centre):
            metadata["line_centre_nm"] = centre
        return LineShapeOutcome(np.array(x, copy=True), broadened, metadata)

    def _apply_stark_broadening(
        self,
        x: np.ndarray,
        y: np.ndarray,
        parameters: MutableMapping[str, Any],
    ) -> LineShapeOutcome:
        electron_density = max(self._coerce_float(parameters.get("electron_density"), default=0.0) or 0.0, 0.0)
        temperature = max(self._coerce_float(parameters.get("temperature_K"), default=10_000.0) or 10_000.0, 1.0)
        spacing = self._characteristic_spacing(x)
        base_width = 0.08
        width = base_width * (electron_density / 1e14) ** 0.66 * (temperature / 10_000.0) ** 0.2
        width = max(width, spacing * 0.35)

        kernel = self._stark_kernel(width, spacing, size=401)
        kernel_sum = float(kernel.sum())
        if kernel_sum == 0.0 or not np.isfinite(kernel_sum):
            kernel = np.zeros_like(kernel)
            kernel[len(kernel) // 2] = 1.0
            kernel_sum = 1.0
        kernel /= kernel_sum

        filled = np.nan_to_num(y, nan=0.0, posinf=0.0, neginf=0.0)
        broadened = np.convolve(filled, kernel, mode="same")
        metadata = {
            "applied": True,
            "electron_density": electron_density,
            "temperature_K": temperature,
            "stark_width_nm": width,
            "kernel_size": int(kernel.size),
            "kernel_sum": float(np.sum(kernel)),
            "spacing_nm": spacing,
            "kernel_exponent": 2.5,
        }
        centre = self._coerce_float(parameters.get("line_centre_nm"))
        if centre is not None and np.isfinite(centre):
            metadata["line_centre_nm"] = centre
        return LineShapeOutcome(np.array(x, copy=True), broadened, metadata)

    # ------------------------------------------------------------------
    @staticmethod
    def _characteristic_spacing(x: np.ndarray) -> float:
        finite = np.asarray(x[np.isfinite(x)], dtype=np.float64)
        if finite.size < 2:
            return 0.1
        sorted_vals = np.sort(finite)
        diffs = np.diff(sorted_vals)
        diffs = diffs[np.isfinite(diffs) & (diffs > 0)]
        if diffs.size == 0:
            return max(float(np.nanmean(np.abs(sorted_vals))) * 0.01, 0.1)
        return float(np.median(diffs))

    @staticmethod
    def _lorentz_kernel(width: float, spacing: float, *, size: int) -> np.ndarray:
        half = size // 2
        offsets = (np.arange(size) - half) * spacing
        denom = offsets**2 + width**2
        with np.errstate(divide="ignore"):
            kernel = width / np.pi / denom
        kernel[~np.isfinite(kernel)] = 0.0
        return kernel

    @staticmethod
    def _stark_kernel(width: float, spacing: float, *, size: int) -> np.ndarray:
        half = size // 2
        offsets = np.abs((np.arange(size) - half) * spacing)
        exponent = 2.5
        with np.errstate(divide="ignore"):
            kernel = 1.0 / (1.0 + (offsets / width) ** exponent)
        kernel[~np.isfinite(kernel)] = 0.0
        return kernel

    @staticmethod
    def _coerce_float(value: Any, *, default: Optional[float] = None) -> Optional[float]:
        if value is None:
            return default
        try:
            result = float(value)
        except (TypeError, ValueError):
            return default
        return result
