"""Differential and mathematical operations on spectra."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple

import numpy as np

from .spectrum import Spectrum


@dataclass
class MathService:
    """Provide subtraction and ratio operations with provenance logging."""

    epsilon: float = 1e-9

    def subtract(self, a: Spectrum, b: Spectrum) -> Tuple[Spectrum | None, Dict[str, object]]:
        """Compute ``a - b`` if non-trivial, otherwise suppress result."""
        self._ensure_aligned(a, b)
        diff = a.y - b.y
        if np.allclose(diff, 0.0, atol=self.epsilon):
            return None, {
                'status': 'suppressed_trivial',
                'operation': 'subtract',
                'message': 'Spectra are identical within tolerance; result suppressed.',
                'parents': [a.id, b.id],
            }

        metadata = {
            'operation': {
                'name': 'subtract',
                'parameters': {'epsilon': self.epsilon},
                'parents': [a.id, b.id],
            },
            'primary_metadata': dict(a.metadata),
            'secondary_metadata': dict(b.metadata),
        }
        spectrum = Spectrum.create(
            name=f"{a.name} - {b.name}",
            x=a.x,
            y=diff,
            metadata=metadata,
        )
        return spectrum, {'status': 'ok', 'operation': 'subtract', 'result_id': spectrum.id}

    def ratio(self, a: Spectrum, b: Spectrum) -> Tuple[Spectrum, Dict[str, object]]:
        """Compute ``a / b`` with epsilon protection."""
        self._ensure_aligned(a, b)
        denom = b.y.copy()
        mask = np.abs(denom) < self.epsilon
        denom[mask] = np.nan  # mark invalid points
        values = np.divide(a.y, denom)
        metadata = {
            'operation': {
                'name': 'ratio',
                'parameters': {'epsilon': self.epsilon, 'masked_points': int(mask.sum())},
                'parents': [a.id, b.id],
            },
            'primary_metadata': dict(a.metadata),
            'secondary_metadata': dict(b.metadata),
        }
        spectrum = Spectrum.create(
            name=f"{a.name} / {b.name}",
            x=a.x,
            y=values,
            metadata=metadata,
        )
        return spectrum, {'status': 'ok', 'operation': 'ratio', 'result_id': spectrum.id, 'masked_points': int(mask.sum())}

    def _ensure_aligned(self, a: Spectrum, b: Spectrum) -> None:
        if a.x.shape != b.x.shape or not np.allclose(a.x, b.x, atol=self.epsilon):
            raise ValueError('Spectra must share the same wavelength grid for math operations.')

    def average(self, spectra: list[Spectrum], name: str | None = None) -> Tuple[Spectrum, Dict[str, object]]:
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
            # Single spectrum - just return a copy
            spec = spectra[0]
            result_name = name or f"Copy of {spec.name}"
            metadata = {
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
                metadata=metadata,
            )
            return result, {'status': 'ok', 'operation': 'average', 'result_id': result.id, 'count': 1}
        
        # Find common wavelength range (intersection of all spectra)
        min_wl = max(spec.x.min() for spec in spectra)
        max_wl = min(spec.x.max() for spec in spectra)
        
        if min_wl >= max_wl:
            raise ValueError('Spectra have no overlapping wavelength range')
        
        # Use the finest wavelength grid among all spectra
        # This preserves the best resolution
        target_x = None
        min_spacing = float('inf')
        
        for spec in spectra:
            # Filter to common range
            mask = (spec.x >= min_wl) & (spec.x <= max_wl)
            x_range = spec.x[mask]
            if len(x_range) > 1:
                spacing = np.median(np.diff(x_range))
                if spacing < min_spacing:
                    min_spacing = spacing
                    target_x = x_range
        
        if target_x is None or len(target_x) < 2:
            raise ValueError('Insufficient data in overlapping range')
        
        # Interpolate all spectra to the target wavelength grid
        interpolated_y = []
        for spec in spectra:
            # Use linear interpolation
            y_interp = np.interp(target_x, spec.x, spec.y)
            interpolated_y.append(y_interp)
        
        # Compute average
        y_avg = np.mean(interpolated_y, axis=0)
        
        # Build metadata
        result_name = name or f"Average of {len(spectra)} spectra"
        parent_ids = [spec.id for spec in spectra]
        metadata = {
            'operation': {
                'name': 'average',
                'parameters': {
                    'count': len(spectra),
                    'wavelength_range': [float(min_wl), float(max_wl)],
                    'points': len(target_x),
                },
                'parents': parent_ids,
            },
            'source_spectra': [{'id': spec.id, 'name': spec.name} for spec in spectra],
        }
        
        result = Spectrum.create(
            name=result_name,
            x=target_x,
            y=y_avg,
            metadata=metadata,
        )
        
        return result, {
            'status': 'ok',
            'operation': 'average',
            'result_id': result.id,
            'count': len(spectra),
            'wavelength_range': [float(min_wl), float(max_wl)],
        }
