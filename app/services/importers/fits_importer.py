"""FITS importer for one-dimensional spectra."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import numpy as np
from astropy.io import fits

from .base import ImporterResult


class FitsImporter:
    """Load spectral columns from FITS binary tables."""

    _WAVELENGTH_COLUMNS: Iterable[str] = (
        "wavelength",
        "wave",
        "lambda",
        "lam",
        "x",
    )
    _FLUX_COLUMNS: Iterable[str] = (
        "flux",
        "intensity",
        "counts",
        "signal",
        "y",
    )

    def read(self, path: Path) -> ImporterResult:
        path = Path(path)
        with fits.open(path, memmap=False) as hdul:
            hdu = self._select_hdu(hdul)
            data = hdu.data
            if data is None:
                raise ValueError(f"No tabular data found in {path}")

            wave_col = self._find_column(hdu, self._WAVELENGTH_COLUMNS)
            flux_col = self._find_column(hdu, self._FLUX_COLUMNS)

            x = np.asarray(data[wave_col], dtype=np.float64)
            y = np.asarray(data[flux_col], dtype=np.float64)

            x_unit = self._column_unit(hdu, wave_col) or "nm"
            flux_unit = self._column_unit(hdu, flux_col) or hdu.header.get("BUNIT", "")

            name = hdu.header.get("OBJECT", path.stem)
            metadata = {
                "x_label": wave_col,
                "y_label": flux_col,
                "fits_header": {key: hdu.header.get(key) for key in ("OBJECT", "INSTRUME", "TELESCOP") if key in hdu.header},
            }
            if flux_unit:
                metadata["original_flux_unit"] = str(flux_unit).lower()

        y_unit = self._normalise_intensity_unit(flux_unit)
        return ImporterResult(
            name=name,
            x=x,
            y=y,
            x_unit=str(x_unit).lower(),
            y_unit=y_unit,
            metadata=metadata,
            source_path=path,
        )

    def description(self) -> str:
        return "FITS binary table importer"

    def _select_hdu(self, hdulist: fits.HDUList) -> fits.BinTableHDU:
        for hdu in hdulist:
            if isinstance(hdu, fits.BinTableHDU) and hdu.data is not None:
                return hdu
        raise ValueError("No binary table HDU found for spectral data")

    def _find_column(self, hdu: fits.BinTableHDU, candidates: Iterable[str]) -> str:
        names = {name.lower(): name for name in hdu.columns.names or []}
        for candidate in candidates:
            if candidate.lower() in names:
                return names[candidate.lower()]
        raise ValueError(f"Required column not found; expected one of {candidates}")

    def _column_unit(self, hdu: fits.BinTableHDU, column: str) -> str | None:
        try:
            unit = hdu.columns[column].unit
        except (KeyError, AttributeError):
            unit = None
        if unit:
            return str(unit)
        return None

    def _normalise_intensity_unit(self, unit: str | None) -> str:
        if not unit:
            return "absorbance"
        normalised = unit.strip().lower()
        supported = {"absorbance", "a10", "transmittance", "t", "percent_transmittance", "%t", "absorbance_e", "ae"}
        if normalised in supported:
            return normalised
        return "absorbance"
