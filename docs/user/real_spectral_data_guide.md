# Real Spectral Data Access Guide

This guide explains how to access legitimate, calibrated spectral data from credible astronomical archives for use in Spectra App. All data sources listed here are scientifically validated and suitable for research and analysis.

## Quick Access: Remote Data Dialog

The **Remote Data** dialog is your primary interface for fetching real spectral observations:

- **Menu**: File → Fetch Remote Data
- **Keyboard**: `Ctrl+Shift+R`
- **Documentation**: See [remote_data.md](remote_data.md) for detailed workflow

## Available Data Sources

### 1. Solar System Objects

Fetch calibrated spectral observations of planets, moons, and other solar system bodies from space-based telescopes.

**Access Method**: Search in **MAST ExoSystems** provider

**Available Targets**:
- **Jupiter** - JWST/MIRI mid-IR spectra, HST observations
- **Mars** - JWST/NIRSpec reflectance spectra
- **Saturn** - JWST observations, including ring and moon spectra
- **Venus**, **Neptune**, **Uranus** - various mission data when available
- **Moons**: Io, Europa, Ganymede, Callisto, Titan, Enceladus

**Wavelength Coverage**: UV to mid-IR (0.1–30 µm depending on instrument)

**Instruments**:
- JWST (NIRSpec, MIRI, NIRCam, NIRISS)
- HST (STIS, COS, WFC3)
- Other archived observations

**Example Search**: Type "Jupiter" in the MAST ExoSystems search box

### 2. Stellar Spectra

Access calibrated spectra of stars across different spectral types, useful for comparison, calibration, and stellar characterization.

**Access Method**: Search in **MAST ExoSystems** or **MAST** provider

**Curated Stars**:
- **Vega (A0V)** - Primary flux calibration standard from HST CALSPEC
- **Tau Ceti (HD 10700, G8V)** - Solar analog from Pickles stellar library
- Additional stars available through direct MAST searches

**Wavelength Coverage**: UV to near-IR (typically 0.1–2.5 µm)

**Sources**:
- HST CALSPEC calibration standards
- Pickles stellar spectral library (DOI: 10.1086/316293)
- IRTF Spectral Library (near-IR)
- MAST archive stellar observations

**Example Searches**:
- Type "Vega" for the A0V standard star
- Type "Tau Ceti" or "HD 10700" for a solar-type star
- Type stellar identifiers like "HD 12345" in MAST provider

### 3. Exoplanet Spectra

Retrieve transmission, emission, and phase curve spectra of exoplanets, primarily from JWST and HST observations.

**Access Method**: Search in **MAST ExoSystems** provider

**Available Exoplanets**:
- **WASP-39 b** - Hot Jupiter with JWST transmission spectra (multiple instruments)
- **TRAPPIST-1** system - Seven temperate terrestrial planets with JWST observations
- **Hot Jupiters** - HD 189733 b, HD 209458 b, WASP-96 b, and others
- **Mini-Neptunes** - K2-18 b, GJ 1214 b with atmospheric features
- Many others available through NASA Exoplanet Archive integration

**Wavelength Coverage**: UV to mid-IR (0.6–30 µm for JWST)

**Observation Types**:
- Transmission spectroscopy (planetary atmosphere backlit by star)
- Emission spectroscopy (thermal emission from dayside)
- Phase curves (varying thermal emission)

**Instruments**:
- JWST (NIRSpec PRISM/grating, MIRI LRS/MRS, NIRCam grism, NIRISS SOSS)
- HST (WFC3, STIS)

**Example Searches**:
- Type "WASP-39 b" (note: handles spaces automatically)
- Type "TRAPPIST-1"
- Type "K2-18 b"

### 4. NIST Atomic Spectral Lines

Access atomic emission and absorption line data from the NIST Atomic Spectra Database.

**Access Method**: Inspector → Reference tab → Spectral lines panel

**Note**: NIST line queries are now accessed through the Reference dock rather than the Remote Data dialog, allowing you to pin multiple element/ion queries and manage colour palettes directly on the preview plot.

**Available Elements**: All elements in the periodic table with known spectral lines

**Data Includes**:
- Wavelengths (vacuum and air)
- Relative intensities
- Transition probabilities
- Energy levels
- Line references

**Example**: Search for "H I" (neutral hydrogen), "Fe II" (singly-ionized iron), etc.

## Data Quality and Provenance

All spectral data accessed through the Remote Data dialog comes from scientifically validated sources:

### Calibration Levels

The MAST queries automatically filter for calibration levels 2 and 3:
- **Level 2**: Calibrated data (flux/wavelength calibrated, instrumental signatures removed)
- **Level 3**: Fully reduced, science-ready products

### Provenance Tracking

Every spectrum downloaded through the Remote Data dialog includes:
- Source provider and identifier
- Observation metadata (instrument, program, target coordinates)
- Download timestamp
- Cached file location
- Original data URI for re-validation

### Citations

When you use data from these archives in your research, please cite:
- **MAST**: Space Telescope Science Institute, Barbara A. Mikulski Archive for Space Telescopes
- **JWST**: Webb Space Telescope Science Institute and NASA
- **NASA Exoplanet Archive**: Akeson et al. 2013, PASP, 125, 989
- **NIST ASD**: Kramida, A., Ralchenko, Yu., Reader, J., and NIST ASD Team (YEAR). NIST Atomic Spectra Database (ver. X.X.X), [Online]. Available: https://physics.nist.gov/asd

Specific citations for individual datasets are included in the metadata preview panel of the Remote Data dialog.

## Wavelength Coverage Summary

| Source | UV (0.1–0.4 µm) | Visible (0.4–0.7 µm) | Near-IR (0.7–2.5 µm) | Mid-IR (2.5–30 µm) |
|--------|----------------|---------------------|---------------------|-------------------|
| JWST Solar System | - | ✓ | ✓ | ✓ |
| JWST Exoplanets | - | ✓ | ✓ | ✓ |
| HST Stars | ✓ | ✓ | ✓ | - |
| HST Exoplanets | ✓ | ✓ | ✓ | - |
| IRTF Stellar Library | - | - | ✓ | - |
| NIST Lines | ✓ | ✓ | ✓ | ✓ |

## Important Notes

### Bundled Reference Data

The `app/data/reference/jwst_targets.json` file contains **example-only** data digitized from JWST release graphics. These are provided for demonstration and structural reference only:

- **Status**: DEPRECATED - Example data only
- **Use Case**: UI testing, format examples, unit conversion verification
- **Scientific Use**: NOT RECOMMENDED - Always fetch real calibrated data from MAST

The bundled data explicitly notes this in the metadata:
```json
"metadata": {
  "status": "DEPRECATED - Example data only",
  "notes": "For real spectroscopic analysis, use the Remote Data dialog..."
}
```

### Network Requirements

- Remote data access requires an internet connection
- First-time downloads may take 30–60 seconds for large JWST observations
- All downloaded data is cached locally for offline re-use
- Cache location: System-dependent (typically `%LOCALAPPDATA%\Spectra\cache` on Windows)

### Data Formats

Downloaded files are typically:
- **FITS** format for space telescope observations (1D spectra)
- **CSV** format for NIST line lists
- All formats are automatically detected and ingested by the app

## Troubleshooting

**"MAST ExoSystems provider not available"**
- Ensure all dependencies are installed: `pip install -r requirements.txt`
- Required packages: `requests`, `astroquery`, `pandas`

**"No results found for target"**
- Verify target name spelling (use NASA Exoplanet Archive or SIMBAD for confirmation)
- Try alternative names (e.g., "WASP39b" vs "WASP-39 b")
- Use direct MAST provider with different search terms

**Download fails or times out**
- Check internet connection
- Large JWST products may take time - wait for progress indicator
- Try downloading fewer products at once

## Related Documentation

- [Remote Data Workflow](remote_data.md) - Detailed step-by-step guide
- [Quickstart Guide](quickstart.md) - Get started with sample and real data
- [Link Collection](../link_collection.md) - Additional spectroscopy resources and APIs
- [Reference Sources](../reference_sources/README.md) - Curated data sources and citations

## Getting Help

If you encounter issues accessing real spectral data:
1. Check the logs in the Log dock (View → Log)
2. Verify your internet connection and firewall settings
3. Review the Remote Data user guide for provider-specific tips
4. Report persistent issues with specific target names and error messages
