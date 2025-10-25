# Spectroscopy Link Collection

This index gathers the remote catalogues, laboratory references, and instrument
handbooks that underpin Spectra’s analysis workflows. Use it alongside the
Inspector’s **Reference** tab, the **Remote Data** dialog, and the Library tab
within the **Data** dock
to keep imported datasets focused on calibrated spectroscopic products. Every
entry lists the primary URL plus integration notes so future agents can wire the
resource into build scripts or documentation updates quickly.

## Remote catalogues (API ready)

| Source | Scope | Notes |
| --- | --- | --- |
| [NIST Atomic Spectra Database](https://physics.nist.gov/asd) | Atomic line lists (UV/VIS/IR) | Backed by `astroquery.nist`; use for hydrogen/metal transitions and lab benchmarks. |
| [VAMDC TAP Registry](https://portal.vamdc.eu/vamdc_portal/home.seam) | Distributed atomic/molecular data | TAP/XSAMS service. Filter on spectroscopy nodes (e.g., CDMS, VALD) for line positions and intensities. |
| [JPL Molecular Spectroscopy](https://spec.jpl.nasa.gov/) | Millimetre/sub-mm rotational lines | Download via catalog files; ideal for astrochemical comparisons. |
| [HITRAN Online](https://hitran.org/) | High-resolution gas-phase spectra | Requires institutional login; export line lists for atmospheric retrievals. |
| [NASA Planetary Data System – Spectroscopy Nodes](https://pds.nasa.gov/datasearch/subscriptions-topics.shtml#spectroscopy) | Planetary/laboratory spectra | Each node offers CSV/FITS assets; reference the mission-specific processing guides. |
| [ESO Science Archive](https://archive.eso.org/cms.html) | Ground-based optical/IR spectra | Query via ESO TAP; retrieve reduced spectra (e.g., UVES, X-Shooter) for cross-checking stellar abundances. |
| [SDSS Science Archive Server](https://sas.sdss.org/) | Optical galaxy/star spectra | Use `SpecObjAll` or `spPlate` downloads; ensure units are converted to the Spectra baseline. |
| [IRTF Spectral Library](https://irtfweb.ifa.hawaii.edu/~spex/IRTF_Spectral_Library/) | Empirical near-IR stellar spectra | Download FITS/ASCII; document provenance in `docs/user/reference_data.md`. |

## Laboratory references & standards

- **NIST Chemistry WebBook** – IR absorption ranges, thermochemical data, and
  vibrational assignments for functional-group overlays.
- **PNNL Infrared Database** – Quantitative mid-IR cross sections for gases;
  complements HITRAN where absolute absorption coefficients are required.
- **NIST Mass Spectrometry Data Center** – EI/CI spectra and reference libraries
  for GC/MS comparison; cite when expanding into mass-spec ingest.
- **IUPAC Solubility/Atomic Weight reports** – Use for elemental abundance
  baselines or calibration constants when adding quantitative analysis features.

## Instrument & pipeline documentation

- **JWST Instrument Handbooks** (NIRSpec, NIRCam, MIRI, NIRISS) – Define modes,
  wavelength coverage, and calibration products. Link when replacing the JWST
  placeholders with calibrated `mast:` downloads.
- **ESO Reflex & pipeline guides** – Workflow references for UVES, X-Shooter,
  and MUSE reductions if we ingest ground-based spectra.
- **ALMA Science Pipeline** – For future radio/mm integrations; note CASA tasks
  and data-product structures.
- **HST STIS/COS Handbooks** – UV line-spread functions and flux calibration
  contexts that pair with lab references.

## Data processing libraries

- [`specutils`](https://specutils.readthedocs.io/) – Spectrum container and
  analysis utilities (binning, smoothing, centroiding).
- [`astropy`](https://docs.astropy.org/en/stable/) – Units, FITS IO, WCS; already
  a dependency for FITS ingest.
- [`astroquery`](https://astroquery.readthedocs.io/) – Remote catalogue access
  (NIST, MAST, VizieR). Our remote service currently relies on it for MAST.
- [`pyvo`](https://pyvo.readthedocs.io/) – VO TAP helper for VAMDC/ESO queries.
- [`scikit-spectra`](https://pypi.org/project/scikit-spectra/) – Exploratory tools
  for chemometric analysis; evaluate before integrating additional math modules.

## Interactive visualization and portals

- [IPAC Firefly (repo)](https://github.com/Caltech-IPAC/firefly) – Web-based astronomical visualization platform used by several archives (images, catalogs, spectra). Reference for future web export or remote visualization integrations.
- Exoplanet Archive Firefly Online Help – Feature-specific guides for the Firefly UI used by NASA Exoplanet Archive:
  - [Visualization](https://exoplanetarchive.ipac.caltech.edu/firefly/onlinehelp/#visualization)
  - [Catalogs](https://exoplanetarchive.ipac.caltech.edu/firefly/onlinehelp/#catalogs)
  - [Images](https://exoplanetarchive.ipac.caltech.edu/firefly/onlinehelp/#images)
  - [Spectra](https://exoplanetarchive.ipac.caltech.edu/firefly/onlinehelp/#spectra)
  - [Download](https://exoplanetarchive.ipac.caltech.edu/firefly/onlinehelp/#download)
  - [Job Monitor](https://exoplanetarchive.ipac.caltech.edu/firefly/onlinehelp/#jobmon)

## MAST notebooks and mission examples

Curated examples from the MAST Notebooks gallery to accelerate remote-search and ingest workflows. Use these as working references when expanding our Remote Data dialog and backend services.

- TESS
  - [Beginner overview](https://spacetelescope.github.io/mast_notebooks/notebooks/TESS/beginner.html)
  - [Beginner (astroquery DV)](https://spacetelescope.github.io/mast_notebooks/notebooks/TESS/beginner_astroquery_dv/beginner_astroquery_dv.html)
  - [How to use DVT](https://spacetelescope.github.io/mast_notebooks/notebooks/TESS/beginner_how_to_use_dvt/beginner_how_to_use_dvt.html)
  - [How to use FFI](https://spacetelescope.github.io/mast_notebooks/notebooks/TESS/beginner_how_to_use_ffi/beginner_how_to_use_ffi.html)
  - [How to use LC](https://spacetelescope.github.io/mast_notebooks/notebooks/TESS/beginner_how_to_use_lc/beginner_how_to_use_lc.html)
  - [How to use TP](https://spacetelescope.github.io/mast_notebooks/notebooks/TESS/beginner_how_to_use_tp/beginner_how_to_use_tp.html)
  - [Beginner TESS Exo.MAST](https://spacetelescope.github.io/mast_notebooks/notebooks/TESS/beginner_tess_exomast/beginner_tess_exomast.html)
  - [Beginner TESS TAP search](https://spacetelescope.github.io/mast_notebooks/notebooks/TESS/beginner_tess_tap_search/beginner_tess_tap_search.html)
  - [Beginner TIC search (HD 209458)](https://spacetelescope.github.io/mast_notebooks/notebooks/TESS/beginner_tic_search_hd209458/beginner_tic_search_hd209458.html)
  - [Beginner TESSCut (astroquery)](https://spacetelescope.github.io/mast_notebooks/notebooks/TESS/beginner_tesscut_astroquery/beginner_tesscut_astroquery.html)

- GALEX
  - [MIS mosaic](https://spacetelescope.github.io/mast_notebooks/notebooks/GALEX/mis_mosaic/mis_mosaic.html) ([imports section](https://spacetelescope.github.io/mast_notebooks/notebooks/GALEX/mis_mosaic/mis_mosaic.html#imports))

- Kepler
  - [Plotting images from TPF](https://spacetelescope.github.io/mast_notebooks/notebooks/Kepler/plotting_images_from_tpf/plotting_images_from_tpf.html)
  - [Plotting lightcurves](https://spacetelescope.github.io/mast_notebooks/notebooks/Kepler/plotting_lightcurves/plotting_lightcurves.html)
  - [Plotting DV Time Series](https://spacetelescope.github.io/mast_notebooks/notebooks/Kepler/plotting_dvts/plotting_dvts.html)

- JWST
  - [Engineering Database Retrieval](https://spacetelescope.github.io/mast_notebooks/notebooks/JWST/Engineering_Database_Retreival/EDB_Retrieval.html)
  - [SI keyword exoplanet search](https://spacetelescope.github.io/mast_notebooks/notebooks/JWST/SI_keyword_exoplanet_search/SI_keyword_exoplanet_search.html)
  - [MAST metadata search](https://spacetelescope.github.io/mast_notebooks/notebooks/JWST/MAST_metadata_search/MAST_metadata_search.html)
  - [Download by program ID](https://spacetelescope.github.io/mast_notebooks/notebooks/JWST/download_by_program_id/download_by_program_id.html)
  - [Duplication checking](https://spacetelescope.github.io/mast_notebooks/notebooks/JWST/duplication_checking/duplication_checking.html)

- IUE
  - [Exploring UV extinction curves](https://spacetelescope.github.io/mast_notebooks/notebooks/IUE/exploring_UV_extinction_curves/exploring_UV_extinction_curves.html)

- HSC (Hubble Source Catalog)
  - [Queries overview](https://spacetelescope.github.io/mast_notebooks/notebooks/HSC/queries.html)
  - [HSCv3 API](https://spacetelescope.github.io/mast_notebooks/notebooks/HSC/HSCV3_API/hscv3_api.html)
  - [HSCv3 SMC API](https://spacetelescope.github.io/mast_notebooks/notebooks/HSC/HSCV3_SMC_API/hscv3_smc_api.html)
  - [HSC TAP](https://spacetelescope.github.io/mast_notebooks/notebooks/HSC/HSC_TAP/HSC_TAP.html)
  - [SWEEPS HSCV3P1](https://spacetelescope.github.io/mast_notebooks/notebooks/HSC/SWEEPS_HSCV3P1/sweeps_hscv3p1.html)
  - [SWEEPS HSCV3P1 API](https://spacetelescope.github.io/mast_notebooks/notebooks/HSC/SWEEPS_HSCV3P1_API/sweeps_hscv3p1_api.html)
  - [HCV API demo](https://spacetelescope.github.io/mast_notebooks/notebooks/HSC/HCV_API/HCV_API_demo.html)
  - [HCV CasJobs demo](https://spacetelescope.github.io/mast_notebooks/notebooks/HSC/HCV_CASJOBS/HCV_casjobs_demo.html)

- PanSTARRS
  - [PS1 DR2 TAP](https://spacetelescope.github.io/mast_notebooks/notebooks/PanSTARRS/PS1_DR2_TAP/PS1_DR2_TAP.html)
  - [PS1 image](https://spacetelescope.github.io/mast_notebooks/notebooks/PanSTARRS/PS1_image/PS1_image.html)

- Visualizations
  - [MAST Sky](https://spacetelescope.github.io/mast_notebooks/notebooks/Visualizations/mast_sky/mast_sky.html#What-am-I-looking-at?)

- Multi-mission
  - [astroquery with MAST](https://spacetelescope.github.io/mast_notebooks/notebooks/multi_mission/astroquery.html)

## Usage guidelines

1. **Record provenance** – When importing data from these sources, capture the
   DOI/URL and retrieval timestamp in metadata and `docs/history/PATCH_NOTES.md`.
2. **Update documentation** – Link new resources from the appropriate user guide
   (e.g., importing, remote data, reference browser) so operators understand the
   workflow.
3. **Align with the workplan** – Check `docs/reviews/workplan.md` for open tasks
   (JWST regeneration, catalogue expansion, IR heuristics) before staging
   additional assets.
4. **Respect licensing** – Some catalogues (HITRAN, proprietary lab spectra)
   require credentials. Document access requirements and avoid committing
   restricted data.
5. **Leverage notebooks for prototypes** – Adapt the linked MAST notebooks into small, tested Python snippets that call our Remote Data services (prefer `astroquery` patterns). Attribute the original notebook in provenance.

## Maintenance checklist

- Run `pytest` after wiring a new source to confirm regression coverage still
  passes.
- Append an entry to `docs/history/KNOWLEDGE_LOG.md` describing the addition and
  cite this collection so future agents know where the data originated.
- Refresh this index whenever you discover a new spectroscopy portal or retire a
  legacy reference.
