"""Shared types for importer implementations."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Protocol, Tuple
import numpy as np


@dataclass(frozen=True)
class ImporterResult:
    """Raw values returned by an importer before canonical conversion."""

    wavelengths: np.ndarray
    flux: np.ndarray
    wavelength_unit: str
    flux_unit: str
    metadata: Dict[str, object]
    source_path: Path


class Importer(Protocol):
    """Protocol implemented by importer plugins."""

    supported_extensions: Tuple[str, ...]

    def description(self) -> str: ...

    def read(self, path: Path) -> ImporterResult: ...
