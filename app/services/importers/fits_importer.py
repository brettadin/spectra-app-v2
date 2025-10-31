"""FITS importer for one-dimensional spectra."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import numpy as np

try:  # pragma: no cover - optional dependency in CI
    from astropy.io import fits  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - optional dependency in CI
    fits = None  # type: ignore[assignment]

from .base import ImporterResult


class FitsImporter:
    """Load spectral columns from FITS binary tables."""

    _WAVELENGTH_COLUMNS: Iterable[str] = (
        "wavelength",
        "wave",
        "lambda",
        "lam",
        "x",
        "time",
        "mjd",
        "bjd",
        "bjdt",
        "bjd_tdb",
        "hjd",
        "phase",
        "frequency",
        "freq",
        "wavenumber",
        "wn",
    )
    _FLUX_COLUMNS: Iterable[str] = (
        "pdcsap_flux",
        "sap_flux",
        "flux",
        "flux_density",
        "fluxdensity",
        "intensity",
        "counts",
        "rate",
        "signal",
        "y",
        "data",  # Sometimes FITS uses generic "DATA" column
    )
    _ERROR_TOKENS: tuple[str, ...] = ("err", "error", "unc", "uncert", "sigma", "stddev")

    def _require_fits(self):
        if fits is None:
            raise RuntimeError(
                "FITS support requires the 'astropy' package. Install it to enable FITS ingestion."
            )
        return fits

    def read(self, path: Path) -> ImporterResult:
        path = Path(path)
        fits_mod = self._require_fits()
        with fits_mod.open(path, memmap=False) as hdul:
            hdu = self._select_hdu(hdul)
            data = hdu.data
            if data is None:
                raise ValueError(f"No tabular data found in {path}")

            wave_col = self._find_column(hdu, self._WAVELENGTH_COLUMNS)
            flux_col = self._find_column(hdu, self._FLUX_COLUMNS)

            x = self._column_to_array(data[wave_col], flatten=True)
            y = self._column_to_array(data[flux_col], flatten=True)

            x_unit_raw = self._column_unit(hdu, wave_col) or ""
            flux_unit_raw = self._column_unit(hdu, flux_col) or hdu.header.get("BUNIT", "")
            x_unit = self._normalise_wavelength_unit(x_unit_raw)
            flux_unit = self._normalise_flux_unit(flux_unit_raw)

            name = hdu.header.get("OBJECT", path.stem)
            metadata = {
                "x_label": wave_col,
                "y_label": flux_col,
                "fits_header": {key: hdu.header.get(key) for key in ("OBJECT", "INSTRUME", "TELESCOP") if key in hdu.header},
                "fits_columns": {"x": wave_col, "y": flux_col},
            }
            if flux_unit:
                metadata["original_flux_unit"] = str(flux_unit_raw)
            if x_unit_raw:
                metadata["original_x_unit"] = str(x_unit_raw)

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

    def _select_hdu(self, hdulist: "fits.HDUList") -> "fits.BinTableHDU":
        fits_mod = self._require_fits()
        for hdu in hdulist:
            if isinstance(hdu, fits_mod.BinTableHDU) and hdu.data is not None:
                return hdu
        raise ValueError("No binary table HDU found for spectral data")

    def _find_column(self, hdu: "fits.BinTableHDU", candidates: Iterable[str]) -> str:
        columns = list(hdu.columns.names or [])
        normalised = {self._normalise_column_key(col): col for col in columns}
        lowered = {col.lower(): col for col in columns}

        for candidate in candidates:
            norm_candidate = self._normalise_column_key(candidate)
            lower_candidate = candidate.lower()
            if lower_candidate in lowered:
                return lowered[lower_candidate]
            if norm_candidate in normalised:
                return normalised[norm_candidate]

            if len(norm_candidate) <= 1:
                continue

            ranked: list[tuple[int, str, str]] = []
            for norm_col, original in normalised.items():
                if not norm_candidate:
                    continue
                if norm_col == norm_candidate:
                    return original
                if norm_col.endswith(norm_candidate):
                    ranked.append((0, original, norm_col))
                elif norm_candidate in norm_col:
                    ranked.append((1, original, norm_col))
            if ranked:
                ranked.sort(key=lambda item: (item[0], len(item[2])))
                for _, original, norm_col in ranked:
                    if self._looks_like_error_column(norm_col):
                        continue
                    return original
                return ranked[0][1]

        available = ", ".join(columns) if columns else "(none)"
        candidates_list = ", ".join(f"'{c}'" for c in candidates)
        raise ValueError(
            f"Required column not found; expected one of [{candidates_list}]. "
            f"Available columns: {available}"
        )

    def _column_unit(self, hdu: "fits.BinTableHDU", column: str) -> str | None:
        try:
            unit = hdu.columns[column].unit
        except (KeyError, AttributeError):
            unit = None
        if unit:
            return str(unit)
        return None

    def _column_to_array(self, column_data: object, *, flatten: bool) -> np.ndarray:
        if hasattr(column_data, "to_value"):
            try:
                column_data = column_data.to_value()
            except Exception:
                pass

        array = np.asanyarray(column_data)
        if np.ma.isMaskedArray(array):
            array = np.ma.filled(array, np.nan)
        array = np.asarray(array, dtype=np.float64)
        if flatten or array.ndim == 1:
            return array.reshape(-1)
        if array.ndim == 2 and 1 in array.shape:
            return array.reshape(-1)
        return array

    def _normalise_wavelength_unit(self, unit: str | None) -> str:
        if not unit:
            return "nm"
        raw = str(unit).strip()
        lowered = raw.lower().replace("µ", "u")
        synonyms = {
            "angstrom": "angstrom",
            "angstroms": "angstrom",
            "ang": "angstrom",
            "a": "angstrom",
            "a0": "angstrom",
            "nm": "nm",
            "nanometer": "nm",
            "nanometre": "nm",
            "nanometers": "nm",
            "nanometres": "nm",
            "um": "um",
            "micron": "um",
            "microns": "um",
            "micrometer": "um",
            "micrometre": "um",
            "micrometers": "um",
            "micrometres": "um",
            "wavenumber": "cm^-1",
            "cm-1": "cm^-1",
            "cm^-1": "cm^-1",
            "1/cm": "cm^-1",
        }
        return synonyms.get(lowered, raw)

    def _normalise_flux_unit(self, unit: str | None) -> str:
        if unit is None:
            return ""
        text = str(unit).strip()
        lowered = text.lower()
        mappings = {
            "absorbance": "absorbance",
            "a10": "absorbance",
            "transmittance": "transmittance",
            "t": "transmittance",
            "percent_transmittance": "percent_transmittance",
            "%t": "percent_transmittance",
            "absorbance_e": "absorbance_e",
            "ae": "absorbance_e",
        }
        if lowered in mappings:
            return mappings[lowered]
        return lowered

    def _normalise_column_key(self, name: str) -> str:
        return "".join(ch for ch in name.lower() if ch.isalnum())

    def _looks_like_error_column(self, normalised_name: str) -> bool:
        return any(token in normalised_name for token in self._ERROR_TOKENS)

    def _normalise_intensity_unit(self, unit: str | None) -> str:
        if not unit:
            return "absorbance"
        normalised = unit.strip().lower()
        supported = {"absorbance", "a10", "transmittance", "t", "percent_transmittance", "%t", "absorbance_e", "ae"}
        if normalised in supported:
            return normalised
        return unit.strip()
