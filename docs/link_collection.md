# Spectroscopy Link Collection

This index gathers the remote catalogues, laboratory references, and instrument
handbooks that underpin Spectra’s analysis workflows. Use it alongside the
Inspector’s **Reference** tab, the **Remote Data** dialog, and the Library dock
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

## Maintenance checklist

- Run `pytest` after wiring a new source to confirm regression coverage still
  passes.
- Append an entry to `docs/history/KNOWLEDGE_LOG.md` describing the addition and
  cite this collection so future agents know where the data originated.
- Refresh this index whenever you discover a new spectroscopy portal or retire a
  legacy reference.
# Curated Link Collection

Centralised starting point for JWST and Astropy ecosystem resources that recur in Spectra planning sessions. Entries retain their original annotations so future agents can extend or reorganise the catalogue without losing context.

## Core stack to get work done

### Astroquery + MAST
- [Astroquery (repo)](https://github.com/astropy/astroquery) — primary client for MAST programme, catalogue, and observation queries.
- [MAST module overview](https://astroquery.readthedocs.io/en/latest/mast/mast.html) — entry point for the Astroquery MAST interface.
- [Observations query](https://astroquery.readthedocs.io/en/latest/mast/mast_obsquery.html) — examples covering observation search parameters.
- [Missions](https://astroquery.readthedocs.io/en/latest/mast/mast_missions.html) — catalogue of supported missions and dataset types.
- [Catalog](https://astroquery.readthedocs.io/en/latest/mast/mast_catalog.html) — guidance for catalogue queries and filters.
- [Cutouts](https://astroquery.readthedocs.io/en/latest/mast/mast_cut.html) — how to request image cutouts from MAST holdings.
- [General MAST query](https://astroquery.readthedocs.io/en/latest/mast/mast_mastquery.html) — low-level API surface for bespoke queries.

### JWST pipeline & docs
- [JWST pipeline (repo)](https://github.com/spacetelescope/jwst) — STScI calibration pipeline source and issue tracker.
- [Known issues](https://jwst-docs.stsci.edu/known-issues-with-jwst-data) — live catalogue of calibration caveats.
- [Science calibration pipeline](https://jwst-docs.stsci.edu/jwst-science-calibration-pipeline#gsc.tab=0) — processing stage reference.
- [Calibration status](https://jwst-docs.stsci.edu/jwst-calibration-status#gsc.tab=0) — instrument-by-instrument readiness tracker.
- [Post-pipeline analysis](https://jwst-docs.stsci.edu/jwst-post-pipeline-data-analysis#gsc.tab=0) — tips for science-ready follow-up.

### Visualisation and analysis (Jdaviz)
- [Jdaviz docs](https://jdaviz.readthedocs.io/en/stable/) — landing page for the suite.
- [Jdaviz (repo)](https://github.com/spacetelescope/jdaviz) — codebase and issue tracker.
- [Imviz](https://jdaviz.readthedocs.io/en/stable/imviz/index.html) — imaging viewer configuration.
- [Specviz](https://jdaviz.readthedocs.io/en/stable/specviz/index.html) — 1D spectroscopy workflows.
- [Specviz2d](https://jdaviz.readthedocs.io/en/stable/specviz2d/index.html) — 2D spectral visualisation.
- [Cubeviz](https://jdaviz.readthedocs.io/en/stable/cubeviz/index.html) — integral field cube tooling.
- [Mosviz](https://jdaviz.readthedocs.io/en/stable/mosviz/index.html) — multi-object spectroscopy reviewer.

### Spectral utilities
- [specutils (repo)](https://github.com/astropy/specutils) — spectral container and analysis primitives.
- [specutils docs](https://specutils.readthedocs.io/en/stable/) — API and user guide.
- [synphot (legacy refactor repo)](https://github.com/spacetelescope/synphot_refactor/blob/master/docs/index.rst) — synthetic photometry reference implementation.
- [synphot docs](https://synphot.readthedocs.io/en/latest/index.html) — user and developer documentation.

## Data access: MAST portals, APIs, and examples
- [MAST Notebooks (gallery)](https://github.com/spacetelescope/mast_notebooks/tree/main) — curated examples for MAST services.
- [JWST duplication checking notebook](https://spacetelescope.github.io/mast_notebooks/notebooks/JWST/duplication_checking/duplication_checking.html) — concrete notebook demonstrating duplication review.
- [MAST Portal Guide](https://outerspace.stsci.edu/display/MASTDOCS/Portal+Guide) — official portal documentation.
- [MAST JWST portal (UI)](https://mast.stsci.edu/search/ui/#/jwst/) — web user interface for JWST searches.
- [MAST API Python examples](https://mast.stsci.edu/api/v0/pyex.html) — practical REST and Python snippets.

## JWST access, citation, instruments, observatory

### Access & citation
- [Citing JWST data](https://jwst-docs.stsci.edu/accessing-jwst-data/citing-jwst-data#gsc.tab=0) — acknowledgement requirements.
- [Accessing JWST data (overview)](https://jwst-docs.stsci.edu/accessing-jwst-data#gsc.tab=0) — retrieving data from MAST.

### Instruments
- [MIRI](https://jwst-docs.stsci.edu/jwst-mid-infrared-instrument#gsc.tab=0) — Mid-Infrared Instrument handbook.
- [NIRCam](https://jwst-docs.stsci.edu/jwst-near-infrared-camera#gsc.tab=0) — Near-Infrared Camera documentation.
- [NIRISS](https://jwst-docs.stsci.edu/jwst-near-infrared-imager-and-slitless-spectrograph#gsc.tab=0) — instrument overview.
- [NIRSpec](https://jwst-docs.stsci.edu/jwst-near-infrared-spectrograph#gsc.tab=0) — spectrograph operations and modes.

### Observatory & performance
- [JWST observatory hardware](https://jwst-docs.stsci.edu/jwst-observatory-hardware#gsc.tab=0) — spacecraft architecture reference.
- [Characteristics & performance](https://jwst-docs.stsci.edu/jwst-observatory-characteristics-and-performance#gsc.tab=0) — engineering and performance notes.
- [Other JWST tools](https://jwst-docs.stsci.edu/jwst-other-tools#gsc.tab=0) — catalogue of supplementary utilities.

## JWST opportunities, policies, review
- [Opportunities & policies (hub)](https://jwst-docs.stsci.edu/jwst-opportunities-and-policies#gsc.tab=0) — central index for programme calls.
- [Call for Proposals (Cycle 5)](https://jwst-docs.stsci.edu/jwst-opportunities-and-policies/jwst-call-for-proposals-for-cycle-5#gsc.tab=0) — latest solicitation details.
- [General science policies](https://jwst-docs.stsci.edu/jwst-opportunities-and-policies/jwst-general-science-policies#gsc.tab=0) — participation and data rights.
- [Peer review information](https://jwst-docs.stsci.edu/jwst-opportunities-and-policies/jwst-peer-review-information#gsc.tab=0) — review process and logistics.

## Astropy ecosystem: foundations and big tools

### Astropy core
- [Astropy project hub](https://github.com/astropy/astropy-project) — governance and working group info.
- [Astropy website repo](https://github.com/astropy/astropy.github.com) — source for astropy.org.
- [Astropy docs](https://docs.astropy.org/en/stable/index.html) — API reference and tutorials.

### Optics / PSF modelling
- [poppy (JWST optics & PSFs)](https://github.com/spacetelescope/poppy) — diffraction and PSF simulation toolkit.

### Images, viewers, and linked data
- [glue (repo)](https://github.com/glue-viz/glue) — linked data visualisation framework.
- [glue docs](https://docs.glueviz.org/en/stable/index.html) — documentation for glue-viz workflows.
- [ginga (repo)](https://github.com/ejeschke/ginga) — FITS viewer and plugin system.
- [ginga docs](https://ginga.readthedocs.io/en/stable/) — ginga user guide.

### Image analysis & photometry
- [photutils (repo)](https://github.com/astropy/photutils) — photometry algorithms and tools.
- [photutils docs](https://photutils.readthedocs.io/en/stable/) — API reference and examples.
- [astroimtools (repo)](https://github.com/spacetelescope/astroimtools) — image processing utilities.
- [astroimtools docs](https://astroimtools.readthedocs.io/en/stable/) — documentation for astroimtools.
- [imexam (repo)](https://github.com/spacetelescope/imexam) — interactive image examination suite.
- [imexam docs](https://imexam.readthedocs.io/en/0.9.1/) — usage guide.

## JWST notebooks and JDAT
- [JDAT notebooks](https://github.com/spacetelescope/jdat_notebooks) — JWST Data Analysis Team examples and tutorials.
- [MAST notebooks (gallery)](https://github.com/spacetelescope/mast_notebooks/tree/main) — repeated here for quick cross-linking.
- [JWST duplication checking notebook](https://spacetelescope.github.io/mast_notebooks/notebooks/JWST/duplication_checking/duplication_checking.html) — duplication workflow walkthrough.

## Misc infrastructure you'll thank later
- **File formats & coordinates**
  - [ASDF (repo)](https://github.com/asdf-format/asdf) — extensible data format foundation.
  - [ASDF docs](https://www.asdf-format.org/projects/asdf/en/latest/) — official specification and guides.
  - [gwcs (repo)](https://github.com/spacetelescope/gwcs) — generalized WCS transform framework.
  - [gwcs docs](https://gwcs.readthedocs.io/en/latest/) — documentation for coordinate modelling.

## Citation helpers
- [MAST citing guidance](https://jwst-docs.stsci.edu/accessing-jwst-data/citing-jwst-data#gsc.tab=0) — cross-listed to emphasise acknowledgements.

