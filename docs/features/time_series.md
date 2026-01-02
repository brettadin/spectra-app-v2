# Time Series (Light Curves)

This feature adds lightweight ingestion and viewing of time-series data (e.g., TESS/Kepler light curves).

## Components
- `app/services/time_series.py`: Container for time-series data.
- Importers:
  - CSV: `app/services/importers/time_series_csv_importer.py`
  - FITS (PDCSAP/SAP): `app/services/importers/time_series_fits_importer.py`
- Demo viewers:
  - `python -m examples.time_series_demo [file] [--normalize] [--mask-quality] [--bin N]`
  - `python -m examples.time_series_fetch_tess TARGET [--normalize] [--mask-quality] [--bin N]`
- Sample data: `samples/exoplanets/time_series_sample.csv`

## Usage examples
```powershell
cd C:\Code\spectra-app-beta
.\.venv\Scripts\Activate.ps1

# Bundled sample
python -m examples.time_series_demo samples\exoplanets\time_series_sample.csv --normalize --mask-quality --bin 3

# FITS light curve (PDCSAP/SAP)
python -m examples.time_series_demo path\to\lightcurve.fits --mask-quality --normalize

# Fetch first available TESS light curve for a target/TIC and plot
python -m examples.time_series_fetch_tess TIC123456789 --normalize --mask-quality --bin 5
```

## Notes
- FITS importer looks for TIME and PDCSAP_FLUX/SAP_FLUX columns, plus optional *_ERR and QUALITY.
- Quality mask drops QUALITY != 0; normalization divides by median; binning averages in fixed-size bins.
- The fetch helper stores downloads under `.timeseries_cache`.
