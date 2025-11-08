# pyright: ignore[reportUnknownMemberType,reportUnknownVariableType,reportUnknownArgumentType]
"""Importer for MODIS Surface Reflectance HDF4 (HDF-EOS) products.

This importer extracts a single 7-band reflectance "spectrum" suitable for
comparison with continuous laboratory/field spectra. It aggregates the scene
spatially (median per band over valid pixels), converts to physical
reflectance (0..1), and assigns representative band centre wavelengths in nm.

Supported products (heuristic): MOD09*/MYD09* collections that expose SDS
named "sur_refl_b01" .. "sur_refl_b07". Files are expected to be HDF4 (HDF-EOS)
format. If the file doesn't look like MODIS Surface Reflectance, the importer
will raise a descriptive error and suggest alternatives.

Implementation notes and future roadmap:
- QA masking: We currently mask using value ranges (0..10000) and fill values
  (<0). A future enhancement can parse "QC_500m"/"state_1km" bitfields to mask
  clouds, shadows, high aerosols, etc. Keep the interface stable: aggregation
  strategy can be provided via metadata and later via importer config.
- Spatial sampling: For now, we compute the global median for each band. Later
  we can accept ROIs or pixel coordinates to extract per-pixel spectra.
- Wavelengths: We use representative centre wavelengths (nm) for bands B01..B07
  from MODIS documentation. If band-specific metadata attributes are present in
  the file, prefer them.
- Dependencies: Prefer ``pyhdf`` for HDF4. If unavailable, try GDAL/OSGeo with
  HDF4 support. If neither is present, raise an actionable error message.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional, cast

import numpy as np

try:  # pragma: no cover - optional runtime dependency
    from pyhdf.SD import SD, SDC  # type: ignore
except Exception:  # pragma: no cover - optional runtime dependency
    SD = None  # type: ignore
    SDC = None  # type: ignore

from .base import ImporterResult


# Representative centre wavelengths (nm) for MODIS Surface Reflectance bands 1-7
# Sources: MODIS Level-1B User Guide and SR product docs
_MODIS_BAND_CENTERS_NM: Dict[str, float] = {
    "sur_refl_b01": 645.0,  # Red (620–670 nm)
    "sur_refl_b02": 858.5,  # NIR (841–876 nm)
    "sur_refl_b03": 469.0,  # Blue (459–479 nm)
    "sur_refl_b04": 555.0,  # Green (545–565 nm)
    "sur_refl_b05": 1240.0, # SWIR (1230–1250 nm)
    "sur_refl_b06": 1640.0, # SWIR (1628–1652 nm)
    "sur_refl_b07": 2130.0, # SWIR (2105–2155 nm)
}


from typing import Any, Optional

def _try_import_gdal() -> Optional[Any]:  # pragma: no cover - optional code path
    try:
        from osgeo import gdal  # type: ignore
        return gdal  # type: ignore[no-any-return]
    except Exception:
        return None


@dataclass
class ModisHdfImporter:
    """Read MODIS SR HDF4 files and return a 7-point reflectance spectrum.

    Behaviour:
    - Loads sur_refl_b01..b07 datasets
    - Masks invalid/fill values (raw < 0 or > 10000)
    - Applies scaling 0.0001
    - Aggregates with median across all valid pixels per band
    - Emits ImporterResult with x=band_centres_nm, y=median_reflectance
    - y_unit = "reflectance" (dimensionless fraction)
    """

    def read(self, path: Path) -> ImporterResult:
        path = Path(path)
        bands, meta, using = self._read_with_best_backend(path)
        # Sort by wavelength for nicer plotting
        ordered: List[Tuple[str, float, float, int]] = []  # (band_name, lam_nm, value, n_valid)
        for name, arr in bands.items():
            lam_nm = self._band_centre_nm(name, meta)
            # Mask invalid and scale
            raw = np.asarray(arr, dtype=float)
            mask = (raw >= 0) & (raw <= 10000)
            valid = raw[mask]
            if valid.size:
                scaled = valid * 0.0001
                value = float(np.nanmedian(scaled))
                n_valid = int(valid.size)
            else:
                value = float("nan")
                n_valid = 0
            ordered.append((name, lam_nm, value, n_valid))
        ordered.sort(key=lambda t: t[1])
        x_nm = np.array([t[1] for t in ordered], dtype=float)
        y_reflectance = np.array([t[2] for t in ordered], dtype=float)
        n_valid = [t[3] for t in ordered]

        # Attempt a robust uncertainty using MAD / sqrt(N)
        # This is a single value per band; pack into metadata (Spectrum supports per-point uncertainty later)
        # Optional: MAD/sqrt(N) uncertainty per band (kept in metadata in future)
        # (Not used presently to avoid type-checker noise.)
        _uncertainties: List[float] = []
        for name, lam_nm, _val, _ in ordered:
            arr = np.asarray(bands[name], dtype=float)
            mask = (arr >= 0) & (arr <= 10000)
            v = arr[mask] * 0.0001
            if v.size:
                med = np.nanmedian(v)
                mad = np.nanmedian(np.abs(v - med))
                sigma = float(1.4826 * mad / np.sqrt(max(1, v.size)))
            else:
                sigma = float("nan")
            _uncertainties.append(sigma)

        name = meta.get("short_name") or path.stem
        product = meta.get("product") or "MODIS Surface Reflectance"
        metadata: Dict[str, Any] = {
            "instrument": "MODIS",
            "product": product,
            "ingest_backend": using,
            "band_centres_nm": {k: self._band_centre_nm(k, meta) for k in bands.keys()},
            "valid_counts": {k: int(c) for k, c in zip([t[0] for t in ordered], n_valid)},
            "source_format": "HDF4",
            "notes": "Reflectance aggregated with median over valid pixels; scale factor 0.0001 applied.",
        }

        return ImporterResult(
            name=name,
            x=x_nm,
            y=y_reflectance,
            x_unit="nm",
            y_unit="reflectance",
            metadata=metadata,
            source_path=path,
        )

    # ------------------ Backend loaders ------------------
    def _read_with_best_backend(self, path: Path) -> tuple[Dict[str, np.ndarray], Dict[str, Any], str]:
        # Prefer pyhdf
        if SD is not None and SDC is not None:
            try:
                return self._read_with_pyhdf(path), self._read_metadata_pyhdf(path), "pyhdf"
            except Exception:
                # Fall back to GDAL if available
                pass
        gdal = _try_import_gdal()
        if gdal is not None:
            return self._read_with_gdal(path, gdal), {"short_name": path.stem}, "gdal"
        # Nothing available
        raise RuntimeError(
            "HDF4 support not available. Install 'pyhdf' (preferred) or 'gdal' with HDF4 driver.\n"
            "Windows tip: conda install -c conda-forge pyhdf (or gdal)."
        )

    def _read_with_pyhdf(self, path: Path) -> Dict[str, np.ndarray]:  # pragma: no cover - requires pyhdf
        assert SD is not None and SDC is not None
        hdf = SD(str(path), SDC.READ)  # type: ignore[attr-defined]
        names_any = cast(List[Any], list(hdf.datasets().keys()))  # type: ignore[call-arg]
        wanted: List[str] = [str(n) for n in names_any if str(n).startswith("sur_refl_b0")]  # b01..b07
        if not wanted:
            raise ValueError("File does not expose 'sur_refl_b0*' datasets; not a MODIS Surface Reflectance file?")
        bands: Dict[str, np.ndarray] = {}
        for name in sorted(wanted):
            ds = hdf.select(name)  # type: ignore[attr-defined]
            arr = ds.get()  # type: ignore[attr-defined]
            bands[name] = np.asarray(cast(Any, arr))
        return bands

    def _read_metadata_pyhdf(self, path: Path) -> Dict[str, Any]:  # pragma: no cover - requires pyhdf
        assert SD is not None and SDC is not None
        hdf = SD(str(path), SDC.READ)  # type: ignore[attr-defined]
        # Attributes may be provided by pyhdf; coerce to a dict for typing
        try:
            attrs_raw = hdf.attributes(full=1)  # type: ignore[attr-defined]
        except Exception:
            attrs_raw = {}
        attrs: Dict[str, Any] = {}
        if isinstance(attrs_raw, dict):
            # keys can be bytes; normalise to str
            for k, v in list(attrs_raw.items()):
                attrs[str(k)] = v
        short_name = None
        try:
            for k, v in list(attrs.items()):
                key = str(k).lower()
                if key in {"shortname", "short_name", "productname", "product"}:
                    try:
                        short_name = str(v[0]) if isinstance(v, (list, tuple)) else str(v)
                    except Exception:
                        short_name = None
                    break
        except Exception:
            pass
        return {"short_name": short_name or path.stem, "product": "MOD09/MYD09"}

    def _read_with_gdal(self, path: Path, gdal: Any) -> Dict[str, np.ndarray]:  # pragma: no cover - optional
        # Open dataset and list subdatasets
        ds = gdal.Open(str(path))  # type: ignore[attr-defined]
        if ds is None:
            raise RuntimeError("GDAL failed to open HDF4 file")
        subdatasets = ds.GetSubDatasets() or []  # type: ignore[attr-defined]
        # Find sur_refl_b0* subdatasets
        bands: Dict[str, np.ndarray] = {}
        subdatasets_list: List[Tuple[Any, Any]] = list(subdatasets)
        for name, _desc in subdatasets_list:
            # Each subdataset name is like: HDF4_EOS:...:sur_refl_b01
            if ":sur_refl_b0" in name:
                sub = gdal.Open(name)  # type: ignore[attr-defined]
                if sub is None:
                    continue
                arr = sub.ReadAsArray()  # type: ignore[attr-defined]
                key = str(name).split(":")[-1]
                bands[str(key)] = np.asarray(cast(Any, arr))
        if not bands:
            raise ValueError("No MODIS 'sur_refl_b0*' subdatasets found via GDAL")
        return bands

    # ------------------ Helpers ------------------
    def _band_centre_nm(self, band_name: str, meta: Dict[str, Any]) -> float:
        # If the file provides a per-band centre, prefer it (future improvement)
        return float(_MODIS_BAND_CENTERS_NM.get(band_name, np.nan))
