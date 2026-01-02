"""CSV light-curve importer (time vs flux).

The importer is intentionally lenient: it searches headers for time and flux
columns using common names from TESS/Kepler-style exports. Errors and quality
flags are optional.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

from .base import SupportsImport  # type: ignore
from ..time_series import TimeSeries


_TIME_HEADERS = {
    "time",
    "bjd",
    "bkjd",
    "btjd",
    "t_bjd",
    "t_btjd",
    "jd",
    "mjd",
}

_FLUX_HEADERS = {
    "flux",
    "pdcsap_flux",
    "sap_flux",
    "relative_flux",
    "norm_flux",
}

_FLUX_ERR_HEADERS = {"flux_err", "pdcsap_flux_err", "sap_flux_err", "error", "err"}
_QUALITY_HEADERS = {"quality", "flags", "flag"}


def _normalise_header(name: str) -> str:
    return name.strip().lower().replace(" ", "_")


def _find_column(headers: Sequence[str], candidates: set[str]) -> Optional[int]:
    for idx, name in enumerate(headers):
        if _normalise_header(name) in candidates:
            return idx
    return None


@dataclass
class TimeSeriesCsvImporter(SupportsImport):
    """Read a CSV light curve into :class:`TimeSeries`."""

    default_time_unit: str = "day"
    default_value_unit: str = "relative_flux"

    def read(self, path: Path) -> TimeSeries:
        headers: List[str] = []
        rows: List[List[str]] = []
        with path.open("r", encoding="utf-8") as handle:
            reader = csv.reader(handle)
            try:
                headers = next(reader)
            except StopIteration:
                raise ValueError(f"File {path} is empty") from None
            for row in reader:
                if not row or all(not cell.strip() for cell in row):
                    continue
                rows.append(row)

        if not headers:
            raise ValueError(f"File {path} missing header row")

        time_idx = _find_column(headers, _TIME_HEADERS)
        flux_idx = _find_column(headers, _FLUX_HEADERS)
        err_idx = _find_column(headers, _FLUX_ERR_HEADERS)
        qual_idx = _find_column(headers, _QUALITY_HEADERS)

        if time_idx is None or flux_idx is None:
            raise ValueError("Could not locate time and flux columns in CSV header")

        time_vals: List[float] = []
        flux_vals: List[float] = []
        err_vals: List[float] = []
        qual_vals: List[int] = []

        for row in rows:
            def _safe_float(idx: int) -> Optional[float]:
                try:
                    return float(row[idx])
                except Exception:
                    return None

            t = _safe_float(time_idx)
            f = _safe_float(flux_idx)
            if t is None or f is None:
                continue
            time_vals.append(t)
            flux_vals.append(f)

            if err_idx is not None:
                err_val = _safe_float(err_idx)
                err_vals.append(np.nan if err_val is None else err_val)
            if qual_idx is not None:
                try:
                    qual_vals.append(int(float(row[qual_idx])))
                except Exception:
                    qual_vals.append(0)

        time_arr = np.asarray(time_vals, dtype=float)
        flux_arr = np.asarray(flux_vals, dtype=float)
        err_arr = np.asarray(err_vals, dtype=float) if err_idx is not None else None
        qual_arr = np.asarray(qual_vals, dtype=int) if qual_idx is not None else None

        metadata: Dict[str, object] = {
            "columns": headers,
            "source": "csv-lightcurve",
        }
        if err_idx is not None:
            metadata["flux_error_column"] = headers[err_idx]
        if qual_idx is not None:
            metadata["quality_column"] = headers[qual_idx]

        return TimeSeries(
            name=path.stem,
            time=time_arr,
            values=flux_arr,
            time_unit=self.default_time_unit,
            value_unit=self.default_value_unit,
            errors=err_arr,
            quality=qual_arr,
            metadata=metadata,
            source_path=path,
        )
