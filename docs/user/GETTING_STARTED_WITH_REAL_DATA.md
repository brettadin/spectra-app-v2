# Getting Started with Real Spectral Data

**Updated**: 2025-10-23

## Overview

Spectra App provides direct access to real spectroscopic data from NASA's MAST archives and other credible sources. This guide shows you how to fetch, display, and analyze authentic spectra from space telescopes and ground-based observatories.

## Why Use Real Data?

- **Scientific Authenticity**: Work with calibrated observations from professional instruments
- **Wide Wavelength Coverage**: UV to mid-infrared (0.1–30 µm)
- **Educational Value**: Compare lab spectra with planetary/stellar observations
- **Research Quality**: Level 2+ calibrated data with full provenance

## Quick Start: Fetching Your First Spectrum

### Step 1: Open the Remote Data Dialog

**Method 1**: Menu bar
- Go to **File → Fetch Remote Data**

**Method 2**: Keyboard shortcut
- Press **Ctrl+Shift+R** (Windows/Linux) or **Cmd+Shift+R** (macOS)

### Step 2: Choose a Provider

The Remote Data dialog offers three providers:

1. **MAST (NASA)**: Space telescope observations (JWST, HST, Spitzer)
2. **NIST Atomic Spectra Database**: Laboratory spectral lines
3. **Solar System Archive**: Curated sample spectra (bundled with app)

Select **MAST** for this tutorial.

### Step 3: Search for a Target

**Example Searches**:

#### Solar System Objects
- `Jupiter` - Gas giant with strong atmospheric features
- `Mars` - Terrestrial planet with CO₂, H₂O signatures
- `Saturn` - Ring system and atmosphere
- `Europa` - Icy moon with water ice features

#### Stars (Spectral Standards)
- `Vega` - A0V star, flux calibration standard
- `Tau Ceti` - G8V star, solar analog
- `Sirius` - A1V star, brightest in night sky

#### Exoplanets
- `WASP-39 b` - Hot Jupiter with JWST transmission spectrum
- `TRAPPIST-1` - Cool dwarf with multiple transiting planets
- `HD 189733 b` - Well-studied hot Jupiter

### Step 4: Browse Results

The dialog shows available observations with:
- **Title**: Target name and instrument
- **Mission**: Telescope (JWST, HST, Spitzer)
- **Wavelength**: Spectral coverage
- **Date**: Observation timestamp

Click on a row to see details in the preview pane.

### Step 5: Download and Import

1. **Select** the observation you want
2. Click **Download** button
3. The file is cached locally (check status bar for progress)
4. Click **OK** to import into workspace
5. The spectrum appears in the **Datasets** pane and is plotted automatically

## Data Sources Explained

### MAST Archives

**What it includes**:
- **JWST** (2022–present): NIRSpec, NIRCam, MIRI, NIRISS
  - Wavelength: 0.6–28 µm (near-IR to mid-IR)
  - Targets: Solar System, exoplanets, stars, galaxies
  
- **Hubble Space Telescope (HST)** (1990–present):
  - STIS: 0.115–1.03 µm (UV to near-IR)
  - COS: 0.09–0.32 µm (far-UV to near-UV)
  - WFC3: 0.2–1.7 µm (grism spectroscopy)
  
- **Spitzer** (2003–2020):
  - IRS: 5–40 µm (mid-IR molecular bands)

**Data Quality**:
- Calibration Level 2 or 3 (science-ready)
- Flux units: Janskys, erg/s/cm²/Å, or instrumental
- Full provenance: DOI, processing version, citation info

### NIST Atomic Spectra Database

**What it includes**:
- Atomic emission/absorption lines for all elements
- Wavelength: UV, visible, infrared
- Accurate transition data (vacuum/air wavelengths)

**Use cases**:
- Identify emission lines in lab spectra
- Reference for plasma diagnostics
- Overlay on stellar spectra for element identification

**Note**: NIST returns line lists (wavelength + intensity), not continuous spectra. These appear as vertical markers when overlaid on the plot.

### Solar System Archive (Bundled)

**What it includes**:
- Curated sample spectra from JWST early release observations
- Pre-downloaded for offline use
- Examples: Jupiter, Mars, Neptune, select exoplanets

**Purpose**:
- Quick demos when internet is unavailable
- Educational examples with known spectral features
- Placeholder until you fetch real MAST data

**Important**: These are digitized from published graphics for demonstration only. For research, always fetch the original FITS files from MAST.

## Example Workflow: Comparing Jupiter Lab Data with JWST Observations

### Scenario
You have a lab spectrum of methane (CH₄) and want to compare it with Jupiter's atmospheric features.

### Steps

1. **Import Your Lab Data**
   - File → Import... → Select your CH₄ CSV/FITS file
   - The spectrum appears in the Datasets pane

2. **Fetch Jupiter JWST Observation**
   - Ctrl+Shift+R to open Remote Data
   - Provider: MAST
   - Search: `Jupiter`
   - Filter by: JWST NIRSpec or MIRI (mid-IR coverage)
   - Download one observation
   - Click OK to import

3. **Align Wavelength Units**
   - Both spectra should now appear in the plot
   - Use the Units dropdown in the toolbar to select common units (e.g., µm)
   - Both traces update automatically

4. **Normalize for Comparison**
   - Normalize toolbar dropdown → Select "Max" or "Area"
   - Spectra scale to comparable amplitudes

5. **Identify Methane Bands**
   - Look for matching absorption/emission features
   - JWST Jupiter: Strong CH₄ bands near 3.3 µm, 7.7 µm
   - Your lab data: Should show same band centers

6. **Export Your Comparison**
   - File → Export Session... → Choose CSV bundle
   - Includes both spectra + provenance metadata
   - Can re-import later or share with collaborators

## Tips & Tricks

### Efficient Searching

- **Use Quick-Picks**: Click the "Quick Pick" button for pre-vetted targets
- **Filter by Mission**: JWST for mid-IR, HST for UV/optical
- **Calibration Level**: Stick with Level 2+ for science use
- **Spectrum Type**: Filter on "spectrum" product type (default)

### Managing Downloads

- **Local Cache**: Downloaded files stored in `~/.spectra/cache/` (or temp dir if persistence disabled)
- **Library Tab**: View cached spectra without re-downloading
- **Re-import**: CSV export bundles can be re-imported (see `docs/user/importing.md`)

### Performance

- **Level-of-Detail**: Large spectra automatically downsample for display
- **Max Points Setting**: Plot toolbar → adjust max points per trace
- **Hide Traces**: Uncheck datasets in the Datasets pane to declutter plot

### Troubleshooting

#### "No results found"
- Check spelling of target name
- Try shorter query (e.g., "Jupiter" instead of "Jupiter atmosphere")
- Some targets have multiple names (e.g., "HD 209458" = "Osiris")

#### "Download failed"
- Check internet connection
- MAST may be temporarily unavailable (retry later)
- Some observations require authentication (not currently supported)

#### "Could not ingest file"
- FITS file may have unsupported structure
- Check error message in status bar
- Report issue with sample file for investigation

#### "Spectral line search not working"
- NIST queries require element name or wavelength range
- Example: `Fe` or `Hydrogen` or `500-600 nm`
- Results appear as line markers, not continuous spectra

## Going Further

### Advanced Topics

- **Unit Conversions**: See `docs/user/units_reference.md`
- **Provenance Export**: See `docs/user/importing.md#provenance-bundles`
- **Reference Data**: See `docs/user/reference_data.md` for IR functional groups, line lists
- **Plot Tools**: See `docs/user/plot_tools.md` for crosshair, region selection

### More Data Sources (Future)

The following archives are planned for future integration:

- **ESO Archive**: Ground-based spectra (UVES, X-Shooter)
- **SDSS**: Optical galaxy and stellar spectra
- **IRTF**: Near-IR stellar library
- **VizieR**: Astronomical catalogs and published spectra

Check the workplan (`docs/reviews/workplan.md`) for implementation status.

## Real Data Examples by Science Goal

### Planetary Atmospheric Composition
- **Targets**: Jupiter, Saturn, Mars, Venus
- **Instruments**: JWST MIRI (CH₄, CO₂, H₂O bands), HST STIS (UV ozone)
- **Wavelengths**: 2–20 µm for molecular features

### Exoplanet Transit Spectroscopy
- **Targets**: WASP-39 b, TRAPPIST-1 planets, HD 189733 b
- **Instruments**: JWST NIRSpec, NIRISS, HST WFC3
- **Wavelengths**: 0.6–5 µm (H₂O, CO₂, CH₄, clouds)

### Stellar Classification
- **Targets**: Vega (A0V), Tau Ceti (G8V), Betelgeuse (M2Iab)
- **Instruments**: HST STIS, SDSS (future)
- **Wavelengths**: UV to near-IR (Balmer lines, metal lines)

### Solar System Small Bodies
- **Targets**: Asteroids, comets, TNOs
- **Instruments**: HST, Spitzer (legacy), ground-based (future)
- **Wavelengths**: Visible to mid-IR (silicates, organics)

## Citation & Attribution

When using data from MAST in publications:

1. **Cite the mission**: e.g., "Based on observations made with the NASA/ESA/CSA James Webb Space Telescope..."
2. **Include DOI**: Each MAST observation has a DOI (see provenance export)
3. **Acknowledge archive**: "This research has made use of the MAST archive at STScI..."
4. **Calibration pipeline**: Reference pipeline version (included in FITS headers)

Spectra App automatically tracks provenance metadata in exported bundles. See the `manifest.json` file in any export for full attribution chain.

## Questions or Issues?

- **User Guides**: Browse `docs/user/*.md` for detailed feature docs
- **Known Issues**: Check `docs/reviews/workplan.md` for current status
- **Feature Requests**: See `docs/Comprehensive Enhancement Plan for Spectra App.md`

---

**Last Updated**: 2025-10-23T00:49 EDT  
**Spectra App Version**: v2 (Desktop Preview)  
**Documentation Path**: `docs/user/GETTING_STARTED_WITH_REAL_DATA.md`
