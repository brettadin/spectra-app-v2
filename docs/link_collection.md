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

