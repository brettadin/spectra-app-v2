# MODIS Surface Reflectance (HDF4) Ingestion

This app supports ingesting MODIS Surface Reflectance (SR) HDF4 files (e.g., `MOD09*/MYD09*`).

What you get:
- A 7-point reflectance "spectrum" with wavelengths at the band centres of B01..B07 (nm)
- Values are median reflectance across all valid pixels per band
- Units: x = nm; y = reflectance (0..1)

How it works (short):
- Reads SDS datasets named `sur_refl_b01` .. `sur_refl_b07` via `pyhdf` (preferred) or GDAL if available
- Masks invalid or fill values (raw < 0 or > 10000) and applies scale factor 0.0001
- Aggregates using the median per band (robust). We also compute a MAD-based uncertainty per band
- Emits a single Spectrum so you can compare directly to your lab spectra

Why not per-pixel? Because MODIS SR is a multi-band image, not a continuous spectrum. For quick spectral comparison, the scene median across valid pixels is usually the most robust summary. Future versions can add ROI selection or pixel picking to produce per-pixel spectra.

Dependencies:
- Preferred: `pyhdf` (Conda users: `conda install -c conda-forge pyhdf`)
- Fallback: `gdal` with HDF4 plugin (Conda users: `conda install -c conda-forge gdal`)

Edge cases & TODOs:
- QA masking (clouds/shadows/aerosols): parse `QC_500m` and/or `state_1km` bitfields (not yet)
- Use per-band centre wavelengths from file attributes if present (currently hard-coded canonical centres)
- Allow ROI-based aggregation (median/mean) or per-pixel extraction
- Support CMG/global products (different geogrids but the SDS names are consistent)

Notes for agents:
- The importer lives at `app/services/importers/modis_hdf_importer.py`
- It is registered for the `.hdf` extension in `DataIngestService.__post_init__`
- If the file is not a MODIS SR file, raise a clear error so future format routers can be added
- Keep this module minimal and stable; add product-specific logic here (not in the generic FITS/CSV importers)
