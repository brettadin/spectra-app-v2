# Importing Local Spectra

The Import dialog accepts comma-separated text, JCAMP-DX, and FITS spectra. All
files are normalised into the app's canonical wavelength baseline of
nanometres while preserving the raw arrays on disk for provenance.

## Supported formats

- **CSV/TXT** – First column is wavelength, second is intensity. Units can be
  specified in parentheses (e.g. `wavelength(nm)` or `transmittance`).
- **FITS** – 1D binary tables with wavelength and flux columns. The importer
  looks for standard names such as `WAVELENGTH`, `WAVE`, or `FLUX`. Original
  header metadata is preserved in the provenance panel.
- **JCAMP-DX** – Compact infrared/UV spectral files using `##XYDATA` blocks.

## How to import

1. Choose **File → Open** and select one or more spectra.
2. Review the detected units shown in the preview banner.
3. Confirm the ingest. The data is copied into the local cache (see
   `docs/dev/ingest_pipeline.md`) so that reloading the same file is
   instantaneous.

Imported spectra always appear in canonical units inside the application. Use
 the unit toggle on the toolbar to view alternative axes without mutating the
 underlying data. The raw source file remains untouched in the provenance
 bundle created during export.

## Quick smoke workflow

Run File → Open on `samples/sample_spectrum.csv`, toggle the units toolbar to Ångström/Transmittance, and export a manifest via File → Export Manifest. This mirrors the automated regression in `tests/test_smoke_workflow.py`, ensuring the ingest pipeline and provenance export are healthy.
