# Patch Notes

## 2025-10-15 (JWST Jupiter quick-look refresh) (05:26 am UTC)

- Regenerated `app/data/reference/jwst_targets.json` using calibrated JWST Program 1022 spectra for Jupiter (NIRSpec IFU
  G140H/F100LP and MIRI MRS Channel 2 Short) with pipeline v1.19.1 provenance metadata.
- Patched `tools/reference_build/build_jwst_quicklook.py` to rely on `Observations.download_file`, avoiding the MAST
  varchar→bigint conversion errors encountered with `download_products`.
- Documented the new Jupiter coverage, outstanding targets, and regeneration workflow updates across the user reference,
  developer guide, and workplan.

## 2025-10-15 (Reference regeneration scaffolding) (4:18 am UTC)

- Added `tools/reference_build` scripts for NIST ASD, IR functional groups, and JWST quick-look spectra, recording build
  provenance inside each JSON asset and documenting usage in `docs/dev/reference_build.md`.
- Enriched the bundled reference datasets with per-target provenance (curation status, planned MAST URIs, retrieval
  timestamps) and expanded line-shape placeholders for Zeeman, collisional shift, and turbulence scaffolding.
- Updated the inspector UI to surface provenance details, refreshed user primers with the new workflow, and extended
  regression tests to assert the generator metadata for hydrogen, IR, and JWST entries.

## 2025-10-15 (Reference library & JWST quick-look data) (3:24 am UTC)

- Added a reference data service, inspector tab, and local JSON assets covering NIST hydrogen lines, IR functional groups,
  line-shape placeholders, and digitised JWST spectra for WASP-96 b, Jupiter, Mars, Neptune, and HD 84406.
- Bundled spectroscopy/JWST primers plus developer documentation so agents can extend the data store and cite sources from the
  in-app viewer.
- Logged regression coverage for the reference library to guard bundled IDs, metadata, and bibliographic entries.

## 2025-10-15 (Importer header conflict safeguards) (1:27 am UTC)

- Extended the CSV/TXT importer to honour unit hints inside headers, swap
  misidentified axes when intensity and wavelength labels conflict, and record
  the column-selection rationale in ingest metadata.
- Added regression coverage for unit-only headers and header-driven swaps while
  documenting the new safeguards in the importing guide.

## 2025-10-15 (Normalization pipeline & axis heuristics) (1:04 am UTC)

- Tightened CSV/TXT column scoring so wavelength/wavenumber spans outrank intensity-first exports, preventing swapped axes.
- Routed the plot toolbar's Normalize control through overlay service scaling with Max/Area modes, updating the data table and provenance metadata.
- Added unit tests for normalization math and importer regression, refreshed the importing and plot documentation to match, and logged the fixes in the workplan.

## 2025-10-15 (Importer heuristics & embedded docs) (12:37 am UTC)

- Reworked the CSV/TXT importer to scan messy files for contiguous numeric blocks,
  infer wavelength/intensity units from prose, and normalise descending wavenumber tables.
- Added regression coverage for heuristic parsing edge cases in `tests/test_csv_importer.py`
  and extended the Qt smoke test to assert the Docs tab renders repository guides.
- Introduced an in-app documentation viewer (Help → View Documentation) and documented
  the workflow in `docs/user/in_app_documentation.md`.

## 2025-10-15 (Provenance bundle structure hardening) (12:17 am UTC)

- `ProvenanceService.export_bundle` now creates per-spectrum CSVs under `spectra/`, copies original uploads into `sources/`, and records a structured `log.txt` inside each export bundle.
- Manifest source entries now include relative paths to the canonical CSV and copied source file, aligning behaviour with the importing guide appendix.
- Added regression coverage for the new bundle layout to ensure the manifest, CSVs, PNG snapshot, and provenance log are all emitted together.

## 2025-10-15 (Importing Guide Provenance Appendix) (9:10 am)

- Expanded `docs/user/importing.md` with a provenance export appendix covering the structure of the manifest bundle.
- Clarified that exported directories include canonical CSVs, original sources, and a chronological log for audit trails.
- Highlighted unit round-trip safety when sharing exported spectra with collaborators.

## 2025-10-14 (Plot Interaction Guide) (8:45 pm)

- Added `docs/user/plot_tools.md` covering pan/zoom gestures, crosshair usage, legend management, and the 120k-point LOD cap.
- Wired the Cursor toolbar toggle and new **View → Reset Plot** action to the plot pane so the documentation matches the UI.
- Linked the new guide from the quickstart and README documentation index.
- Extended the plot performance stub tests to exercise the crosshair visibility API.

## 2025-10-14 (Units Reference) (7:38 pm est)

- Authored `docs/user/units_reference.md` to document supported spectral units, idempotent conversions, and provenance guarantees.
- Linked the quickstart guide to the new reference and marked the Batch 3 workplan item complete.

## 2025-10-14 (Quickstart Guide) (7:24 pm est)

- Added `docs/user/quickstart.md` with a step-by-step walkthrough covering launch, ingest, unit toggles, and provenance export using the bundled sample spectrum.
- Updated the Batch 3 workplan to track remaining documentation gaps and recorded the pytest run that validates the smoke workflow.
- Linked upcoming documentation sprint items back to the inventory for traceability.

## 2025-10-14 (7:20 pm est)

- Logged the latest CI gate outcomes (lint, type-check, pytest) and noted the missing coverage plugin.
- Made FITS ingestion optional when `astropy` is absent, providing a clear runtime error instead of import failures.
- Updated user guidance to call out the optional dependency and created a developer snapshot documenting the CI results.

## 2025-10-14 (Documentation Inventory) (7:00 pm est)

- Catalogued missing user, developer, and historical documentation deliverables in `docs/reviews/doc_inventory_2025-10-14.md` to prep for the next feature batch.
- Marked the Batch 2 workplan item complete with a reference to the new inventory document to aid scheduling.

## 2025-10-14 (6:30 pm est)

- Added an automated smoke workflow test that instantiates the preview shell, ingests CSV/FITS data, exercises unit toggles, and exports a provenance bundle.
- Centralised the reusable FITS fixture under `tests/conftest.py` to support regression suites.
- Documented the new smoke validation loop for developers and provided a matching user checklist.
