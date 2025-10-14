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
