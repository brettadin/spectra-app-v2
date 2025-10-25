Goal
Download and stage real, citable spectra for: (1) the Sun, (2) Solar System giants, (3) 8–10 exoplanets, (4) 8–10 stars. Normalize axes, tag provenance, and register all files in the Library so they display with a single click.

Output directories
- data/preload/sun/
- data/preload/solar_system/
- data/preload/exoplanets/
- data/preload/stars/

Axis & units
- Store native wavelength in meters internally; expose toggles for nm, μm, and wavenumber ṽ (cm⁻¹).
- Conversions:  λ(μm) = 10⁴ / ṽ(cm⁻¹);  λ(nm) = 10⁷ / ṽ(cm⁻¹).
- Preserve flux units as served; add header fields `flux_unit_display` and `native_unit`.

Provenance
- For each file, record: `source`, `doi_or_landing`, `retrieved_utc`, and the exact download URL (decoded).
- Add a KnowledgeLog “Remote Import” entry per item.

--------------------------------------------------------------------------------
1) SUN
A. TSIS-1 HSRS high-res solar spectral irradiance (binned, 0.2–2.4 μm)
   - URL: https://lasp.colorado.edu/lisird/data/tsis1_hsrs_binned_fs/
   - Save as: data/preload/sun/tsis1_hsrs_binned_fs.json (keep original LISIRD JSON/IPAC; also export CSV for quick plots)
   - Metadata: {"source":"LASP LISIRD TSIS-1 HSRS","doi_or_landing":"https://lasp.colorado.edu/lisird/data/tsis1_hsrs_p1nm/"}

B. CALSPEC solar reference (UV–NIR STIS composite to ~2.7 μm)
   - URL: https://ssb.stsci.edu/cdbs/calspec/sun_reference_stis_002.fits
   - Save as: data/preload/sun/sun_reference_stis_002.fits
   - Metadata: {"source":"STScI CALSPEC"}

--------------------------------------------------------------------------------
2) SOLAR SYSTEM GIANTS (IRTF SpeX, reflectance/emission, ~0.8–5 μm)
Download the FITS listed here exactly; keep file names:
   - Jupiter:  https://irtfweb.ifa.hawaii.edu/~spex/IRTF_Spectral_Library/Data/plnt_Jupiter.fits
   - Saturn:   https://irtfweb.ifa.hawaii.edu/~spex/IRTF_Spectral_Library/Data/plnt_Saturn.fits
   - Uranus:   https://irtfweb.ifa.hawaii.edu/~spex/IRTF_Spectral_Library/Data/plnt_Uranus.fits
   - Neptune:  https://irtfweb.ifa.hawaii.edu/~spex/IRTF_Spectral_Library/Data/plnt_Neptune.fits
Place in data/preload/solar_system/ and tag metadata {"source":"IRTF SpeX Planetary Library","reference":"Rayner+2009 ApJS 185, 289"}.

--------------------------------------------------------------------------------
3) EXOPLANETS (transmission/emission spectra)
Use NASA Exoplanet Archive Atmospheric Spectroscopy interface to pull machine-readable spectra (.tbl). For each planet below:
- Open: https://exoplanetarchive.ipac.caltech.edu/cgi-bin/atmospheres/nph-firefly?atmospheres=
- In Panel 1: filter Planet Name to the exact planet and Type of Spectrum to “Transmission” or “Eclipse” as noted.
- Check all rows for that planet; click “Download All Checked Spectra” to get the wget script; execute it to fetch the .tbl files.
- Save into data/preload/exoplanets/<planet>/, preserving filenames.
- Also export the filtered metadata table as CSV to data/preload/exoplanets/<planet>/<planet>_metadata.csv.
- Record `reference` and `facility/instrument` from the metadata into our registry.

Planet list and recommended type:
   - WASP-39 b — Transmission (JWST NIRSpec/NIRISS/MIRI)
   - WASP-96 b — Transmission (JWST NIRISS)
   - HD 209458 b — Transmission (HST STIS/WFC3; multiple reductions)
   - HD 189733 b — Transmission + Eclipse (HST, Spitzer)
   - WASP-43 b — Eclipse (HST+Spitzer phase curve products)
   - HAT-P-26 b — Transmission (HST WFC3)
   - XO-1 b — Transmission (HST WFC3)
   - WASP-121 b — Transmission/Eclipse (HST/JWST)
   - KELT-9 b — Transmission (HST UV; ground-based optical)
   - WASP-18 b — Eclipse (JWST/NIRISS)

Notes:
- For WASP-39 b, also record that underlying raw/reduced data trace to JWST ERS program 1366 in MAST; keep that reference in provenance.
- If the service returns multiple reductions for a planet/instrument, keep all; the app can overlay them.

Post-download normalization for .tbl:
- Parse IPAC tables; harmonize columns:
  - Transmission: wavelength_(μm) → to nm; value = transit_depth or (Rp/R*) where present; store both raw columns.
  - Eclipse: wavelength_(μm) → to nm; value = eclipse_depth.
- Attach `type: "transmission"|"eclipse"`, `instrument`, `reference`, `bibcode/DOI` where available.

--------------------------------------------------------------------------------
4) STARS (CALSPEC spectrophotometric standards; HST/STIS)
Download these exact FITS from the “current_calspec” atlas (choose *_stis* or *_stiswfcnic*):
   - Vega:           https://archive.stsci.edu/hlsps/reference-atlases/cdbs/current_calspec/alpha_lyr_stis_011.fits
   - GD 71:          https://archive.stsci.edu/hlsps/reference-atlases/cdbs/current_calspec/gd71_stiswfcnic_004.fits
   - GD 153:         https://archive.stsci.edu/hlsps/reference-atlases/cdbs/current_calspec/gd153_stiswfcnic_004.fits
   - G191B2B:        https://archive.stsci.edu/hlsps/reference-atlases/cdbs/current_calspec/g191b2b_stiswfcnic_004.fits
   - BD+17 4708:     https://archive.stsci.edu/hlsps/reference-atlases/cdbs/current_calspec/bd_17d4708_stisnic_007.fits
   - 18 Sco:         https://archive.stsci.edu/hlsps/reference-atlases/cdbs/current_calspec/18sco_stis_006.fits
   - 109 Vir:        https://archive.stsci.edu/hlsps/reference-atlases/cdbs/current_calspec/109vir_stis_005.fits
   - HD 37962:       https://archive.stsci.edu/hlsps/reference-atlases/cdbs/current_calspec/hd37962_stis_011.fits
Place in data/preload/stars/ and tag metadata {"source":"STScI CALSPEC"}.

--------------------------------------------------------------------------------
Registration & one-button display
- Build a JSON registry at data/preload/manifest.json with entries:
  {
    "label": "<friendly name>",
    "category": "sun|solar_system|exoplanet|star",
    "path": "<relative file path>",
    "source": "<archive/service>",
    "doi_or_landing": "<URL or DOI>",
    "wavelength_unit_native": "<as served>",
    "flux_unit_native": "<as served>"
  }
- On app start, ingest manifest, verify files exist, and seed the Library with these items.
- Wire the “Spectral Demo” button to open an overlay chooser grouped by category and plot selected spectra, defaulting to wavelength in nm and a toggle to μm and cm⁻¹.

Quality gates
- Validate every URL returns 200.
- For FITS, confirm wavelength/flux column names; if needed, map to internal schema.
- For .tbl IPAC files, validate we preserved `reference` lines.
- KnowledgeLog gets one “Remote Import” entry per file with short reference strings.
