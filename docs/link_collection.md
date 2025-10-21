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
  analysis utilities (binning, smoothing, centroiding). Pair with the exoplanet
  retrieval frameworks below to keep post-fit spectra aligned with Spectra’s
  unit conventions.
- [`astropy`](https://docs.astropy.org/en/stable/) – Units, FITS IO, WCS; already
  a dependency for FITS ingest.
- [`astroquery`](https://astroquery.readthedocs.io/) – Remote catalogue access
  (NIST, MAST, VizieR). Our remote service currently relies on it for MAST and
  dovetails with the JWST notebooks listed below.
- [`pyvo`](https://pyvo.readthedocs.io/) – VO TAP helper for VAMDC/ESO queries.
- [`scikit-spectra`](https://pypi.org/project/scikit-spectra/) – Exploratory tools
  for chemometric analysis; evaluate before integrating additional math modules.

## JWST analysis notebooks & toolkits

> **Check maintenance status** – Many JWST utilities evolve alongside CRDS
> context updates. Confirm the repository’s README or release notes were updated
> for the CRDS version you plan to use before reproducing a workflow.

- [`gbrammer/msaexp`](https://github.com/gbrammer/msaexp) – JWST/NIRSpec
  reduction and extraction pipeline. Use it to generate calibrated 1D spectra
  and slit metadata before ingesting the products via the Remote Data dialog.
  - **Usage**: Install into the same environment as the JWST pipeline (`pip install msaexp`), follow the QuickStart notebook to
    run `msaexp stage3` on level-2 products, then export the `*_msaexp.fits` traces for Spectra.
  - **Maintenance tip**: Review the project’s `requirements.txt` and open issues for CRDS compatibility notes; apply the
    suggested `crds` context before reprocessing archival data.
- [`spacetelescope/jdat_notebooks`](https://github.com/spacetelescope/jdat_notebooks)
  – Worked examples from the JWST Data Analysis Tools initiative. Reference
  their calibration and visualisation recipes when documenting Spectra workflows
  for JWST cubes or mosaics.
  - **Usage**: Clone the repository and launch Jupyter Lab with the supplied environment file; adapt the notebooks to produce
    calibrated spectra (e.g., `datamodels.SlitModel`) you can export as FITS/CSV for ingest.
  - **Maintenance tip**: Notebook branches map to specific JWST pipeline releases—verify the branch tags against the CRDS context
    you target and refresh the environment if dependencies are pinned to older versions.
- [`spacetelescope/jwst`](https://github.com/spacetelescope/jwst) – The official
  JWST calibration pipeline. Align Spectra’s provenance notes with its stages
  (Detector1, Spec2, Spec3) when importing calibrated FITS.
  - **Usage**: Follow STScI’s installation guide (`pip install jwst` or `conda install jwst`) and run `strun` with the
    observation-specific association files; Spectra expects the Spec3 products when available.
  - **Maintenance tip**: Monitor the release notes for breaking changes in configuration file formats and update any local
    pipeline scripts before regenerating cached spectra.
- [`spacetelescope/jwst_mast_query`](https://github.com/spacetelescope/jwst_mast_query)
  – Helper scripts for constructing MAST API queries. Combine with our MAST
  adapter to script batch downloads that feed Spectra’s cache.
  - **Usage**: Use the provided Python snippets to compose `Observations.query_criteria` calls or to fetch product manifests that
    you can feed directly into Spectra’s Remote Data dialog.
  - **Maintenance tip**: Confirm example notebooks still authenticate successfully—MAST occasionally rotates token workflows, so
    refresh environment variables and scripts accordingly.

## Exoplanet retrieval & astrochemistry packages

> **Prototype hygiene** – Retrieval and chemistry codes often depend on
> research-grade branches. Pin commit hashes or release tags in your notebooks
> and record them in provenance metadata so future analysts can reproduce the
> results even if upstream APIs change.

- [`natashabatalha/PandExo`](https://github.com/natashabatalha/PandExo) – JWST
  exposure time and noise simulator. Export model spectra to compare predicted
  SNR against imported observations inside Spectra.
  - **Usage**: Run the web UI or the Python API to generate spectra (`PandExo(pandora).run_pandexo()`), then export the
    transmission/emission spectra as CSV for overlay.
  - **Maintenance tip**: Confirm the instrument throughput files match the JWST observation date—regenerate the instrument grid if
    the repository lags behind recent detector calibrations.
- [`OpenExoplanetCatalogue/open_exoplanet_catalogue`](https://github.com/OpenExoplanetCatalogue/open_exoplanet_catalogue)
  – Curated planetary parameters in XML. Map key fields (radius, equilibrium
  temperature) into Spectra metadata before running retrieval tools.
  - **Usage**: Clone the repository and parse the XML catalogue with the provided Python helpers to seed metadata for Remote Data
    imports or manifest creation.
  - **Maintenance tip**: Pull upstream regularly; contributors merge manually curated updates rather than automated ingest, so new
    discoveries may arrive in batches.
- [`google-research/exoplanet-ml`](https://github.com/google-research/exoplanet-ml)
  – Machine-learning models for transit detection. Use its vetting notebooks to
  pre-select targets whose spectra will be analysed in Spectra.
  - **Usage**: Execute the TensorFlow notebooks to score TESS/Kepler light curves, then prioritise the confirmed planets for
    spectroscopic follow-up you ingest into Spectra.
  - **Maintenance tip**: Some notebooks target specific TensorFlow releases—review the README for pinned versions and adjust GPU
    dependencies before running on modern hardware.
- [`MartianColonist/POSEIDON`](https://github.com/MartianColonist/POSEIDON) –
  Atmospheric retrieval framework. Export posterior spectra and overlay the
  credible intervals within Spectra traces.
  - **Usage**: Install via `pip install poseidon` (or clone for development) and follow the QuickStart retrieval to produce
    posterior samples; export the median/credible-band spectra to CSV for comparison.
  - **Maintenance tip**: The codebase evolves with publications—track the DOI referenced in the README and cite the version tag in
    Spectra manifests when using published retrievals.
- [`ucl-exoplanets/Spectra_Sensitivity_analysis`](https://github.com/ucl-exoplanets/Spectra_Sensitivity_analysis)
  – Sensitivity studies for transmission spectra. Plug the generated perturbation
  grids into Spectra’s math tools to validate feature robustness.
  - **Usage**: Run the included notebooks to compute perturbation grids for atmospheric parameters, then export the synthetic
    spectra for overlay against observational data.
  - **Maintenance tip**: Validate that the dependency versions referenced in `environment.yml` still resolve—update pinned package
    names if conda-forge reorganises them.
- [`uclchem/UCLCHEM`](https://github.com/uclchem/UCLCHEM) – Time-dependent
  astrochemical modelling. Compare predicted abundances with lab references to
  inform Spectra’s line-identification overlays.
  - **Usage**: Compile or install the Python interface, run grid simulations for the relevant density/temperature ranges, and
    export species abundances to overlay with observational diagnostics.
  - **Maintenance tip**: Some branches require Fortran toolchains; check the issue tracker for compiler compatibility notes before
    attempting a build on Windows.
- [`laserkelvin/astrochem_embedding`](https://github.com/laserkelvin/astrochem_embedding)
  – Embedding models for molecular spectra. Use embeddings to cluster imported
  laboratory datasets before linking them to observational spectra.
  - **Usage**: Train the provided autoencoder on laboratory spectra sets and export the latent-space coordinates to drive clustering
    inside Spectra’s analysis notebooks.
  - **Maintenance tip**: Inspect the repository’s dependencies; some JAX/Flax releases move quickly, so pin versions to avoid API
    drift.
- [`yqiuu/spectuner`](https://github.com/yqiuu/spectuner) – Spectral neural
  network tuner for molecular features. Apply trained models to refine line
  identifications and feed the outputs back into Spectra overlays.
  - **Usage**: Follow the training scripts to fine-tune models on custom spectra, then export peak-frequency corrections you can
    import as overlay annotations.
  - **Maintenance tip**: Verify that CUDA/cuDNN requirements align with your hardware—spectuner’s training scripts assume recent
    PyTorch builds.

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
