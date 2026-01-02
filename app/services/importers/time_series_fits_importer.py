"""FITS light-curve importer for TESS/Kepler-style files."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

import numpy as np
from astropy.io import fits

from .base import SupportsImport  # type: ignore
from ..time_series import TimeSeries
from ..passband import find_passband_file, effective_wavelength_from_passband


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

            def _safe_float(val: object) -> Optional[float]:
                try:
                    return float(val)
                except Exception:
                    return None

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

            channel_id: Optional[str] = None
            band: Optional[str] = None
            wavelength: Optional[float] = None
            passband_path: Optional[Path] = None

            if header is not None:
                channel_val = header.get("CHANNEL") or header.get("CHNL")
                module = header.get("MODULE")
                output = header.get("OUTPUT")
                if channel_val is not None:
                    channel_id = str(channel_val)
                elif module is not None and output is not None:
                    channel_id = f"{module}-{output}"

                band_raw = header.get("FILTER") or header.get("BAND") or header.get("PHOTMODE") or header.get("INSTRUME")
                if band_raw:
                    band = str(band_raw)

                wl = _safe_float(header.get("PHOTPLAM"))
                if wl is None:
                    wl = _safe_float(header.get("WAVELEN") or header.get("WAVELENGTH"))
                if wl is None:
                    wmin = _safe_float(header.get("WAVEMIN"))
                    wmax = _safe_float(header.get("WAVEMAX"))
                    if wmin is not None and wmax is not None:
                        wl = 0.5 * (wmin + wmax)
                wavelength = wl

                # If wavelength is absent, attempt to load a passband file and derive it
                if wavelength is None:
                    instrument = None
                    try:
                        instrument = header.get("INSTRUME")
                    except Exception:
                        instrument = None
                    passband_path = find_passband_file(band, instrument)
                    if passband_path is not None:
                        eff = effective_wavelength_from_passband(passband_path)
                        if eff is not None:
                            wavelength = eff
                            metadata["passband_path"] = str(passband_path)
                if wavelength is None:
                    metadata["wavelength_missing"] = True

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
                channel_id=channel_id,
                band=band,
                wavelength=wavelength,
            )
