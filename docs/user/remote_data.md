# Remote Data Guide

The **Remote Data** tab lets you search and download calibrated spectra from NASA MAST archives. The interface stays fully responsive during searches thanks to subprocess-based execution.

*Last updated: January 2026*

---

## Requirements

Remote searches require astroquery and astropy:

`ash
pip install -r requirements.txt
`

---

## Quick Start

1. Press **Ctrl+Shift+R** (or **File -> Show Remote Data Tab**)
2. Enter a target name (e.g., Jupiter, Vega, WASP-39 b)
3. Click **Search**
4. Select results and click **Download**

---

## Search Tips

### Supported Targets

| Type | Examples |
|------|----------|
| Solar system | Jupiter, Mars, Saturn, Uranus, Neptune |
| Stars | Vega, Tau Ceti, Sirius, HD 189733 |
| Exoplanets | WASP-39 b, HD 189733 b, TRAPPIST-1 |

### Automatic Filtering

Searches automatically filter for:
- Spectral data only (dataproduct_type=spectrum)
- Science observations (intentType=science)
- Calibrated products (calib_level=[2, 3])
- Known spectral file patterns (_x1d.fits, _spec.fits, etc.)

---

## Responsive Interface

Searches run in a separate subprocess via QProcess:
- **Never freezes** the main window
- **Cancel instantly** - no waiting for network timeouts
- **Progress feedback** in the status bar

---

## Results Table

| Column | Description |
|--------|-------------|
| Name | Filename or identifier |
| Title | Observation description |
| Target | Astronomical target name |
| Telescope | Mission (JWST, HST, etc.) |
| Instrument | Instrument name |
| Download | File size (approximate) |

---

## Downloading Spectra

1. Select one or more rows in the results table
2. Click **Download** to fetch the FITS files

Downloaded files are:
- Cached locally with SHA256 deduplication
- Automatically imported through the standard ingestion pipeline
- Organized into the **Remote Data** group in the Datasets panel

---

## Dataset Organization

Downloaded spectra appear in the **Remote Data** group automatically. You can:
- Right-click to move datasets between groups
- Create custom groups for organization
- Rename or delete groups as needed

The **Library** tab shows all cached downloads organized by provider and target.

---

## Offline Behavior

Every download is cached locally. If you request the same file again, the cached copy is reused:
- Offline access to previously downloaded spectra
- Fast re-import without network requests
- Persistent collections across sessions

Cache location: storage/cache/

---

## Troubleshooting

### Search returns no results
- Try a simpler target name (e.g., Jupiter instead of Jupiter atmosphere)
- Check your internet connection
- Verify astroquery is installed: pip install astroquery

### Download fails
- Some FITS files may be image data, not spectra
- Check the file size - very large files may timeout
- Try downloading fewer files at once

### UI freezes during search
- This should not happen with the new QProcess architecture
- If it does, please report the issue with your search term
