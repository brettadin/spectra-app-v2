# Spectroscopy Reference Link Collection

This index consolidates the external resources and internal primers referenced across the Spectra project. Keep it nearby when
researching new catalogues, validating importer behaviour, or extending the physics toolchain.

## Space- and ground-based observatories
- **MAST (Mikulski Archive for Space Telescopes)** – https://mast.stsci.edu/. Primary portal for JWST, HST, and GALEX products.
  The remote data service relies on `astroquery.mast`. See `docs/dev/reference_build.md` for the quick-look builder wiring.
- **ESO Science Archive** – https://archive.eso.org/cms.html. Target for future VLT/ELT ingestion once remote fetchers support
  credentialled downloads.
- **SDSS SkyServer** – https://skyserver.sdss.org/. Contains UV/optical spectra suitable for laboratory comparisons and
  instrument calibration exercises.

## Laboratory spectroscopy and standards
- **NIST Atomic Spectra Database (ASD)** – https://physics.nist.gov/PhysRefData/ASD/lines_form.html. Source of hydrogen and
  planned He I/O III/Fe II line lists. Builder scripts live under `tools/reference_build/`.
- **NIST Chemistry WebBook** – https://webbook.nist.gov/chemistry/. Provides IR functional-group ranges captured in
  `app/data/reference/ir_functional_groups.json`.
- **USGS Spectral Library** – https://www.usgs.gov/spectral-library. Broad mineral/organic reflectance data for upcoming
  cross-comparison workflows.
- **Sigma-Aldrich IR Library** – https://www.sigmaaldrich.com/technical-documents/articles/biology/ir-library.html. Useful for
  validating IR importer heuristics and axis detection.

## Instrument techniques to align with
- **UV/Vis Spectrophotometry overview** – https://chem.libretexts.org/Bookshelves/Analytical_Chemistry/Supplemental_Modules_
  (Analytical_Chemistry)/Instrumental_Analysis/Spectrophotometry/Ultraviolet-Visible_Spectroscopy. Background for matching
  laboratory datasets with remote observations.
- **Infrared Spectroscopy primer** – https://chem.libretexts.org/Bookshelves/Analytical_Chemistry/Instrumental_Analysis/Infrared
  Spectroscopy. Complements the functional-group heuristics documented in `docs/user/importing.md`.
- **Mass Spectrometry tutorial** – https://chem.libretexts.org/Bookshelves/Analytical_Chemistry/Mass_Spectrometry. Use when
  planning new importer backends beyond optical/IR spectra.

## Internal Spectra references
- **Reference build pipeline** – `docs/dev/reference_build.md` collects the scripts, staging assets, and provenance rules for
  regenerating bundled datasets.
- **Remote data workflow** – `docs/user/remote_data.md` explains provider requirements, caching, and the in-app Library panel.
- **Importer heuristics & provenance** – `docs/user/importing.md` covers canonicalisation, cache behaviour, and the Knowledge
  Log policy.
- **Plot interaction & styling** – `docs/user/plot_tools.md` now documents palette controls alongside LOD tuning.
- **Workplan & backlog** – `docs/reviews/workplan.md` tracks outstanding tasks including JWST FITS regeneration, expanded line
  catalogues, and importer heuristics.

Keep this file updated when new resources or internal primers are introduced. Mention it in onboarding docs so future agents know
where to start their research.
