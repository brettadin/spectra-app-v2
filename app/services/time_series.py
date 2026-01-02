"""Light curve / time-series data container.

This module keeps time-series data separate from the spectral `Spectrum`
representation so we can ingest and plot light curves without forcing
wavelength/unit canonicalisation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np


@dataclass
class TimeSeries:
    """Container for 1-D time series (e.g., light curves).

    Attributes
    ----------
    name: str
        Identifier used for display.
    time: np.ndarray
        Time values (e.g., BTJD/BJD days).
    values: np.ndarray
        Measured quantity (e.g., relative flux).
    time_unit: str
        Unit string for the time axis (default: "day").
    value_unit: str
        Unit string for the measurement (default: "relative_flux").
    errors: Optional[np.ndarray]
        1-sigma errors matching `values`.
    quality: Optional[np.ndarray]
        Quality flags (mission-specific bitmasks or boolean mask).
    metadata: Dict[str, Any]
        Arbitrary metadata (headers, target identifiers, etc.).
    source_path: Optional[Path]
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
        Originating file path, if known.
    """

    name: str
    time: np.ndarray
    values: np.ndarray
    time_unit: str = "day"
    value_unit: str = "relative_flux"
    errors: Optional[np.ndarray] = None
    quality: Optional[np.ndarray] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    source_path: Optional[Path] = None
