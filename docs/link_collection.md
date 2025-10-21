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
