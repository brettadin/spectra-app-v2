"""FITS light-curve importer for TESS/Kepler-style files."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

import numpy as np
from astropy.io import fits

from .base import SupportsImport  # type: ignore
from ..time_series import TimeSeries


@dataclass
class TimeSeriesFitsImporter(SupportsImport):
    """Read a FITS light curve into :class:`TimeSeries`."""

    default_time_unit: str = "day"
    default_value_unit: str = "relative_flux"

    def read(self, path: Path) -> TimeSeries:
        if not path.exists():
            raise FileNotFoundError(path)

        with fits.open(path) as hdul:
            if len(hdul) < 2 or not hasattr(hdul[1], "data"):
                raise ValueError("FITS light curve missing expected table extension")
            data = hdul[1].data
            header = hdul[0].header if len(hdul) > 0 else None

            def _col(name: str) -> Optional[np.ndarray]:
                if name in data.columns.names:
                    return np.asarray(data[name], dtype=float)
                return None

            time = _col("TIME")
            if time is None:
                raise ValueError("TIME column not found in FITS light curve")

            # Choose the first available flux column without triggering numpy truthiness errors
            flux = _col("PDCSAP_FLUX")
            if flux is None:
                flux = _col("SAP_FLUX")
            if flux is None:
                flux = _col("FLUX")
            if flux is None:
                raise ValueError("No flux column (PDCSAP_FLUX/SAP_FLUX/FLUX) found in FITS light curve")

            flux_err = _col("PDCSAP_FLUX_ERR")
            if flux_err is None:
                flux_err = _col("SAP_FLUX_ERR")
            if flux_err is None:
                flux_err = _col("FLUX_ERR")
            quality = _col("QUALITY")

            # Remove rows with non-finite time or flux
            mask = np.isfinite(time) & np.isfinite(flux)
            time = time[mask]
            flux = flux[mask]
            if flux_err is not None:
                flux_err = flux_err[mask]
            if quality is not None:
                quality = quality[mask]

            metadata: Dict[str, object] = {
                "source": "fits-lightcurve",
                "columns": list(data.columns.names),
            }
            if header is not None:
                metadata["primary_header"] = {k: header[k] for k in header.keys()}  # type: ignore[arg-type]

            return TimeSeries(
                name=path.stem,
                time=time,
                values=flux,
                time_unit=self.default_time_unit,
                value_unit=self.default_value_unit,
                errors=flux_err,
                quality=quality.astype(int) if quality is not None else None,
                metadata=metadata,
                source_path=path,
            )
