"""Differential and mathematical operations on spectra."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

import numpy as np

from .spectrum import Spectrum
from .units_service import UnitsService


@dataclass
class MathService:
    """Provide subtraction and ratio operations with provenance logging."""

    units_service: UnitsService
    epsilon: float = 1e-9

    def subtract(self, a: Spectrum, b: Spectrum) -> Tuple[Spectrum | None, Dict[str, object]]:
        """Compute ``a - b`` if non-trivial, otherwise suppress result."""
        x_canon, a_canon_y, b_canon_y = self._aligned_canonical(a, b)
        diff = a_canon_y - b_canon_y
        if np.allclose(diff, 0.0, atol=self.epsilon):
            return None, {
                'status': 'suppressed_trivial',
                'operation': 'subtract',
                'message': 'Spectra are identical within tolerance; result suppressed.',
                'parents': [a.id, b.id],
            }

        metadata: Dict[str, Any] = {
            'operation': {
                'name': 'subtract',
                'parameters': {'epsilon': self.epsilon},
                'parents': [a.id, b.id],
            },
            'primary_metadata': dict(a.metadata),
            'secondary_metadata': dict(b.metadata),
        }
        result_x, result_y, _ = self.units_service.convert_arrays(
            x_canon,
            diff,
            'nm',
            'absorbance',
            a.x_unit,
            a.y_unit,
        )
        spectrum = Spectrum.create(
            name=f"{a.name} - {b.name}",
            x=result_x,
            y=result_y,
            x_unit=a.x_unit,
            y_unit=a.y_unit,
            metadata=metadata,
        )
        return spectrum, {'status': 'ok', 'operation': 'subtract', 'result_id': spectrum.id}

    def ratio(self, a: Spectrum, b: Spectrum) -> Tuple[Spectrum, Dict[str, object]]:
        """Compute ``a / b`` with epsilon protection."""
        x_canon, a_canon_y, b_canon_y = self._aligned_canonical(a, b)
        denom = b_canon_y.copy()
        mask = np.abs(denom) < self.epsilon
        denom[mask] = np.nan  # mark invalid points
        values = np.divide(a_canon_y, denom)
        metadata: Dict[str, Any] = {
            'operation': {
                'name': 'ratio',
                'parameters': {'epsilon': self.epsilon, 'masked_points': int(mask.sum())},
                'parents': [a.id, b.id],
            },
            'primary_metadata': dict(a.metadata),
            'secondary_metadata': dict(b.metadata),
        }
        result_x, result_y, conversion_meta = self.units_service.convert_arrays(
            x_canon,
            values,
            'nm',
            'absorbance',
            a.x_unit,
            a.y_unit,
        )
        if conversion_meta:
            metadata['unit_conversions'] = dict(conversion_meta)
        spectrum = Spectrum.create(
            name=f"{a.name} / {b.name}",
            x=result_x,
            y=result_y,
            x_unit=a.x_unit,
            y_unit=a.y_unit,
            metadata=metadata,
        )
        return spectrum, {
            'status': 'ok',
            'operation': 'ratio',
            'result_id': spectrum.id,
            'masked_points': int(mask.sum()),
        }

    def _aligned_canonical(self, a: Spectrum, b: Spectrum) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        ax, ay, _ = self.units_service.to_canonical(a.x, a.y, a.x_unit, a.y_unit)
        bx, by, _ = self.units_service.to_canonical(b.x, b.y, b.x_unit, b.y_unit)
        if ax.shape != bx.shape or not np.allclose(ax, bx, atol=self.epsilon):
            raise ValueError('Spectra must share the same wavelength grid for math operations.')
        return ax, ay, by

    def average(self, spectra: List[Spectrum], name: str | None = None) -> Tuple[Spectrum, Dict[str, object]]:
        """Compute average of multiple spectra by interpolating to common wavelength grid.
        
        Args:
            spectra: List of spectra to average
            name: Optional name for the result (defaults to "Average of N spectra")
            
        Returns:
            Tuple of (averaged spectrum, operation metadata)
        """
        if not spectra:
            raise ValueError('Cannot average empty list of spectra')

        if len(spectra) == 1:
            spec = spectra[0]
            result_name = name or f"Copy of {spec.name}"
            metadata: Dict[str, Any] = {
                'operation': {
                    'name': 'average',
                    'parameters': {'count': 1},
                    'parents': [spec.id],
                },
                'primary_metadata': dict(spec.metadata),
            }
            result = Spectrum.create(
                name=result_name,
                x=spec.x.copy(),
                y=spec.y.copy(),
                x_unit=spec.x_unit,
                y_unit=spec.y_unit,
                metadata=metadata,
            )
            return result, {'status': 'ok', 'operation': 'average', 'result_id': result.id, 'count': 1}

        canonical_sets: List[Tuple[Spectrum, np.ndarray, np.ndarray]] = []
        for spec in spectra:
            x_canon, y_canon, _ = self.units_service.to_canonical(spec.x, spec.y, spec.x_unit, spec.y_unit)
            canonical_sets.append((spec, x_canon, y_canon))

        min_wl = max(arr.min() for _, arr, _ in canonical_sets)
        max_wl = min(arr.max() for _, arr, _ in canonical_sets)

        if min_wl >= max_wl:
            raise ValueError('Spectra have no overlapping wavelength range')

        target_x = None
        min_spacing = float('inf')

        for spec, x_canon, _ in canonical_sets:
            mask = (x_canon >= min_wl) & (x_canon <= max_wl)
            x_range = x_canon[mask]
            if x_range.size > 1:
                spacing = np.median(np.diff(x_range))
                if spacing < min_spacing:
                    min_spacing = spacing
                    target_x = x_range

        if target_x is None or target_x.size < 2:
            raise ValueError('Insufficient data in overlapping range')

        interpolated_y: List[np.ndarray] = []
        for _, x_canon, y_canon in canonical_sets:
            mask = (x_canon >= min_wl) & (x_canon <= max_wl)
            interpolated_y.append(np.interp(target_x, x_canon[mask], y_canon[mask]))

        y_avg = np.mean(interpolated_y, axis=0)

        result_name = name or f"Average of {len(spectra)} spectra"
        parent_ids = [spec.id for spec in spectra]
        metadata: Dict[str, Any] = {
            'operation': {
                'name': 'average',
                'parameters': {
                    'count': len(spectra),
                    'wavelength_range': [float(min_wl), float(max_wl)],
                    'points': int(target_x.size),
                },
                'parents': parent_ids,
            },
            'source_spectra': [{'id': spec.id, 'name': spec.name} for spec in spectra],
        }

        baseline = spectra[0]
        result_x, result_y, conversion_meta = self.units_service.convert_arrays(
            target_x,
            y_avg,
            'nm',
            'absorbance',
            baseline.x_unit,
            baseline.y_unit,
        )
        if conversion_meta:
            metadata['unit_conversions'] = dict(conversion_meta)

        result = Spectrum.create(
            name=result_name,
            x=result_x,
            y=result_y,
            x_unit=baseline.x_unit,
            y_unit=baseline.y_unit,
            metadata=metadata,
        )

        return result, {
            'status': 'ok',
            'operation': 'average',
            'result_id': result.id,
            'count': len(spectra),
            'wavelength_range': [float(min_wl), float(max_wl)],
        }
