"""Base classes and helpers for data importers."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Protocol

import numpy as np


@dataclass
class ImporterResult:
    """Raw spectral data returned by an importer before unit normalisation."""

    name: str
    x: np.ndarray
    y: np.ndarray
    x_unit: str
    y_unit: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    source_path: Path | None = None


class SupportsImport(Protocol):
    """Protocol describing the callable signature of importers."""

    def read(self, path: Path) -> ImporterResult:  # pragma: no cover - interface
        ...


# ---------------------------------------------------------------------------
# Compatibility helpers
# ---------------------------------------------------------------------------

# ``Importer`` was the legacy abstract base used before we switched to the
# ``SupportsImport`` protocol.  Some downstream environments still import the
# name directly (and even subclass it), so we expose it as an alias to maintain
# compatibility without changing the runtime behaviour.
Importer = SupportsImport


__all__ = ["ImporterResult", "SupportsImport", "Importer"]
