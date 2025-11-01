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
    """Load spectral columns from FITS files (tables or images).

    Preferred path is a binary table HDU. If no suitable table HDU is found,
    falls back to primary/image HDUs when they contain 1D/2D numeric arrays
    that can be interpreted as (x[, y[, err]]).
    """

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
            table_hdu = self._select_table_hdu(hdul)
            if table_hdu is not None:
                hdu = table_hdu
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
                    "fits_header": {key: hdu.header.get(key) for key in ("OBJECT", "INSTRUME", "TELESCOP", "TIMESYS") if key in hdu.header},
                    "fits_columns": {"x": wave_col, "y": flux_col},
                }
                if flux_unit_raw:
                    metadata["original_flux_unit"] = str(flux_unit_raw)
                if x_unit_raw:
                    metadata["original_x_unit"] = str(x_unit_raw)
                # Special-case: time-like axes (BJD/MJD/HJD/TIME) → mark unit accordingly
                x_unit = self._coerce_time_like_unit(x_unit, wave_col, hdu)
            else:
                # Fallback: attempt to parse primary/image HDU arrays
                hdu = self._select_image_hdu(hdul)
                if hdu is None or hdu.data is None:
                    raise ValueError("No suitable HDU found for spectral data")
                x, y, img_meta = self._extract_from_image_hdu(hdu)
                # Units from header keywords
                # Prefer axis 1 unit for x, BUNIT for y
                x_unit_raw = hdu.header.get("CUNIT1") or hdu.header.get("WAVEUNIT") or ""
                flux_unit_raw = hdu.header.get("BUNIT", "")
                x_unit = self._normalise_wavelength_unit(x_unit_raw)
                flux_unit = self._normalise_flux_unit(flux_unit_raw)
                name = hdu.header.get("OBJECT", path.stem)
                metadata = {
                    "x_label": img_meta.get("x_label", "x"),
                    "y_label": img_meta.get("y_label", "y"),
                    "fits_header": {key: hdu.header.get(key) for key in ("OBJECT", "INSTRUME", "TELESCOP", "CTYPE1", "CUNIT1") if key in hdu.header},
                    "fits_image_shape": tuple(getattr(hdu.data, "shape", ()) or ()),
                }
                if flux_unit_raw:
                    metadata["original_flux_unit"] = str(flux_unit_raw)
                if x_unit_raw:
                    metadata["original_x_unit"] = str(x_unit_raw)
                x_unit = self._coerce_time_like_unit(x_unit, str(metadata.get("x_label", "")), hdu)

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

    def _select_table_hdu(self, hdulist: "fits.HDUList") -> "fits.BinTableHDU" | None:
        fits_mod = self._require_fits()
        for hdu in hdulist:
            if isinstance(hdu, fits_mod.BinTableHDU) and hdu.data is not None:
                return hdu
        return None

    def _select_image_hdu(self, hdulist: "fits.HDUList") -> "fits.PrimaryHDU | fits.ImageHDU | None":
        fits_mod = self._require_fits()
        # Prefer primary with data, else first ImageHDU with data
        primary = hdulist[0] if len(hdulist) else None
        if isinstance(primary, (fits_mod.PrimaryHDU, fits_mod.ImageHDU)) and getattr(primary, "data", None) is not None:
            return primary
        for hdu in hdulist:
            if isinstance(hdu, (fits_mod.ImageHDU,)) and getattr(hdu, "data", None) is not None:
                return hdu
        return None

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

    # ------------------ Image HDU helpers ------------------
    def _extract_from_image_hdu(self, hdu: "fits.ImageBaseHDU") -> tuple[np.ndarray, np.ndarray, dict[str, str]]:
        """Extract (x, y) arrays from an image-like HDU.

        Supports common cases:
        - 2D array shaped (N, 2) or (N, 3): columns represent x, y[, err]
        - 2D array shaped (2, N) or (3, N): rows represent x, y[, err]
        - 1D array with WCS keywords: synthesise x via CRVAL1/CRPIX1/CDELT1
        """
        data = np.asanyarray(hdu.data)
        meta: dict[str, str] = {}
        if data.ndim == 2:
            n0, n1 = data.shape
            # Orient as (N, C)
            arr = data
            if n0 in (2, 3) and n1 > 3:
                arr = data.T
                n0, n1 = arr.shape
            if n1 in (2, 3) and n0 >= 2:
                x = np.asarray(arr[:, 0], dtype=float)
                y = np.asarray(arr[:, 1], dtype=float)
                # If x is not monotonic but y is, swap
                if not self._is_monotonic(x) and self._is_monotonic(y):
                    x, y = y, x
                meta["x_label"] = hdu.header.get("CTYPE1", "x")
                meta["y_label"] = hdu.header.get("BTYPE", "y")
                return x.reshape(-1), y.reshape(-1), meta
        if data.ndim == 1 or (data.ndim == 2 and 1 in data.shape):
            # Flatten and use WCS-like keywords to construct x
            y = np.asarray(data).reshape(-1).astype(float)
            crval = self._safe_float(hdu.header.get("CRVAL1"))
            cdelt = self._safe_float(hdu.header.get("CDELT1"))
            crpix = self._safe_float(hdu.header.get("CRPIX1"))
            if cdelt is not None and (crval is not None or crpix is not None):
                n = y.size
                # FITS uses 1-based pixel coordinates
                indices = np.arange(1, n + 1, dtype=float)
                if crpix is None:
                    crpix = 1.0
                if crval is None:
                    crval = 0.0
                x = crval + (indices - crpix) * cdelt
            else:
                # Fallback: ordinal index
                x = np.arange(y.size, dtype=float)
            meta["x_label"] = hdu.header.get("CTYPE1", "x")
            meta["y_label"] = hdu.header.get("BTYPE", "y")
            return x.reshape(-1), y.reshape(-1), meta
        # Unsupported shape
        raise ValueError("Unsupported FITS image data shape for spectral extraction")

    def _is_monotonic(self, arr: np.ndarray) -> bool:
        if arr.size < 3:
            return False
        diffs = np.diff(arr)
        return bool(diffs.size) and (np.all(diffs >= 0) or np.all(diffs <= 0))

    def _safe_float(self, value: object) -> float | None:
        try:
            if value is None:
                return None
            return float(value)
        except Exception:
            return None

    def _coerce_time_like_unit(self, x_unit: str, x_label: str, hdu: "fits.BinTableHDU | fits.ImageBaseHDU") -> str:
        """If the x axis represents time (e.g., BJD/MJD/HJD), normalise to a clear token.

        This improves downstream labelling and satisfies tests expecting BJD-like units
        for lightcurves (e.g., TESS PDCSAP_FLUX).
        """
        label = (x_label or "").strip().lower()
        unit_raw = str(x_unit or "").strip().lower()
        header = getattr(hdu, "header", {})
        # TESS and other missions often encode units like "BJD - 2457000" in TUNIT
        tunit = str(header.get("TUNIT1", "") or header.get("CUNIT1", "")).strip().lower()
        if "bjd" in label or unit_raw.startswith("bjd") or "bjd" in tunit:
            timesys = str(header.get("TIMESYS", "")).strip().lower()
            return "bjd_tdb" if "tdb" in timesys else "bjd"
        if "mjd" in label or unit_raw.startswith("mjd") or "mjd" in tunit:
            return "mjd"
        if "hjd" in label or unit_raw.startswith("hjd") or "hjd" in tunit:
            return "hjd"
        if label == "time" and ("bjd" in tunit or "mjd" in tunit or "hjd" in tunit):
            if "bjd" in tunit:
                return "bjd"
            if "mjd" in tunit:
                return "mjd"
            return "hjd"
        return x_unit
