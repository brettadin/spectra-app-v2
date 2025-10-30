"""Representation of a single spectrum."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Dict, Any, Tuple, TYPE_CHECKING
import uuid

import numpy as np


def _blank_metadata() -> Dict[str, Any]:
    return {}

if TYPE_CHECKING:  # pragma: no cover - used only for typing
    from .units_service import UnitsService


@dataclass(frozen=True)
class Spectrum:
    """Immutable spectral dataset with provenance and unit tracking."""

    id: str
    name: str
    x: np.ndarray
    y: np.ndarray
    x_unit: str
    y_unit: str
    metadata: Dict[str, Any] = field(default_factory=_blank_metadata)
    source_path: Path | None = None
    parents: Tuple[str, ...] = field(default_factory=tuple)
    transforms: Tuple[Dict[str, Any], ...] = field(default_factory=tuple)

    @staticmethod
    def create(
        name: str,
        x: np.ndarray,
        y: np.ndarray,
        *,
        x_unit: str,
        y_unit: str,
        metadata: Dict[str, Any] | None = None,
        source_path: Path | None = None,
    ) -> "Spectrum":
        """Factory that records the provided units without conversion."""
        return Spectrum(
            id=str(uuid.uuid4()),
            name=name,
            x=np.array(x, dtype=np.float64, copy=True),
            y=np.array(y, dtype=np.float64, copy=True),
            x_unit=str(x_unit),
            y_unit=str(y_unit),
            metadata=dict(metadata or {}),
            source_path=source_path,
        )

    # ------------------------------------------------------------------
    def view(self, units_service: "UnitsService", x_unit: str, y_unit: str) -> Dict[str, Any]:
        """Return a view of the spectrum converted to the requested units."""
        x_view, y_view, info = units_service.convert(self, x_unit, y_unit)
        combined_meta = dict(self.metadata)
        if info:
            combined_meta = dict(combined_meta)
            combined_meta.update(info)
        return {
            "x": x_view,
            "y": y_view,
            "x_unit": x_unit,
            "y_unit": y_unit,
            "metadata": combined_meta,
            "name": self.name,
            "id": self.id,
        }

    def derive(
        self,
        name: str,
        x: np.ndarray,
        y: np.ndarray,
        transform: Dict[str, Any],
        *,
        x_unit: str | None = None,
        y_unit: str | None = None,
    ) -> "Spectrum":
        """Create a derived spectrum preserving provenance and selected units."""
        return Spectrum(
            id=str(uuid.uuid4()),
            name=name,
            x=np.array(x, dtype=np.float64, copy=True),
            y=np.array(y, dtype=np.float64, copy=True),
            x_unit=x_unit if x_unit is not None else self.x_unit,
            y_unit=y_unit if y_unit is not None else self.y_unit,
            metadata=dict(self.metadata),
            source_path=self.source_path,
            parents=self.parents + (self.id,),
            transforms=self.transforms + (transform,),
        )

    def with_metadata(self, **metadata_updates: Any) -> "Spectrum":
        """Return a new spectrum with metadata updated in a copy."""
        new_metadata = dict(self.metadata)
        new_metadata.update(metadata_updates)
        return replace(self, metadata=new_metadata)
