# Workplan Overview

This document tracks feature batches, validation status, and outstanding backlog items for the Spectra app.

## Batch 14 (2025-10-17) — In Progress

- [ ] Land the calibration service (`app/services/calibration_service.py`) and
      calibration dock with non-dismissable banner, FWHM targets, frame/RV
      controls, and σ propagation. Update documentation and schema accordingly.
- [ ] Implement the identification stack (peak/similarity/scoring services,
      identification dock, explainable score cards) with provenance + tests.
- [ ] Add snap-to-peak, brush-to-mask, uncertainty ribbons, palette presets, and
      persistence for crosshair/teaching mode as outlined in `docs/reviews/pass2.md`.
- [ ] Achieve export/view parity: manifest view-state, replay test, and Library
      actions for opening manifests/logs/re-exporting the current state.
- [ ] Reorganise datasets/library presentation so cached entries, sample data,
      and user ingests are categorised by instrument/type with working search
      (Data dock consolidation + filter landed 2025-10-19; grouping backlog
      remains).
- [ ] Validate remote catalogue UX: expand the provider roster beyond MAST once
      dependency checks stabilise and new spectroscopy sources are vetted.
- [x] Refresh START_HERE, MASTER PROMPT, AGENTS, and brains documentation so
      onboarding instructions match the current repository layout (AGENTS and
      START_HERE refreshed 2025-10-19; MASTER PROMPT timestamp guidance synced
      2025-10-20; brains entries continue per docs/brains/README.md cadence).
- [x] Document dependency prerequisites (requests, astroquery, pandas, astropy)
      and add installation verification guidance for Windows 11 users.

### Recently Completed (2025-10-21)

- [x] Bootstrapped CI numpy availability with `sitecustomize.py` so missing wheels no longer break test collection, and registered pytest `roundtrip`/`ui_contract` markers to eliminate unknown mark warnings.
- [x] Ensured the Remote Data dialog joins active search/download threads when closing so Qt no longer warns about workers being
      destroyed mid-run and the asynchronous UX stays stable.
- [x] Taught the Remote Data dialog cancel flow to poll worker shutdown with a Qt timer so the window closes responsively while
      background network calls finish, and surfaced busy/status messaging during the wait.
- [x] Fixed Exo.MAST file-list requests so planet names with spaces no longer
      double-encode, guarded the preview summary against `NaN` discovery years,
      refreshed the regression tests, and documented the behaviour in the remote
      data user guide.
- [x] Renamed the curated remote provider and bundled samples to the Solar
      System Archive label, refreshed manifest paths plus descriptions, updated
      Remote Data dialog copy, and aligned regression tests/documentation with
      the new terminology.
- [x] Gated the Remote Data dialog to list only MAST and curated ExoSystems catalogues, shifting NIST ASD retrieval to the
      Reference dock while updating provider tests, UI coverage, and the user guide to reflect the new workflow.
- [x] Restored the NIST ASD provider in the Remote Data dialog with refreshed
      hints/placeholders, keyword-aware query parsing, Qt coverage for NIST-only
      services, and user-guide updates directing persistent overlays back to the
      Inspector reference tab.
- [x] Added a curated Solar System Archive provider backed by bundled manifests/sample
      spectra, refreshed the Remote Data dialog hints/examples, rendered
      citations in the preview pane, and extended regression coverage for the
      local search/download path.
- [x] Extended `docs/link_collection.md` with JWST notebook/toolkit and
      exoplanet/astrochemistry sections, then cross-linked the resources from the
      Remote Data user guide and developer notes so ingestion work references the
      curated pipelines.
- [x] Documented usage steps and maintenance checks for each JWST/exoplanet tool
      in the link collection so agents know how to run the pipelines and verify
      upstream dependencies before relying on them.
- [x] Consolidated the Remote Data dialog's download/preview cell helpers so tooltip handling stays consistent, guarded empty
      URIs, extended quicklook key coverage, refreshed the user guide, and added a regression test for the rendered links.
- [x] Hardened the Solar System Archive search branch so missing curated manifests or assets are skipped instead of aborting the
      provider, added regression coverage for missing bundles, and documented the resilient behaviour for analysts.

### Recently Completed (2025-10-19)

- [x] Offloaded Remote Data searches/downloads to background workers, locked the dialog controls while jobs execute, aggregated
      warnings, refreshed the remote data guide, and updated Qt smoke tests to wait for asynchronous results.
- [x] Redesigned the Reference tab with dedicated Spectral lines/IR/Line-shape panels, wired the embedded NIST query form to
      astroquery, refreshed the reference data guide, and extended Qt regression tests for the new workflow.
- [x] Ensured the data table remains opt-in so dataset selections no longer force the panel open; cached the last overlay views
      for manual repopulation and updated the plot tools guide, patch notes, and knowledge log to explain the behaviour.
- [x] Added pinned NIST spectral-line sets with palette controls so multiple queries persist on the inspector plot, removed the
      redundant NIST option from the Remote Data dialog, taught the overlay toggle to project all pinned sets simultaneously,
      and updated documentation/tests to steer line-list retrieval through the Reference tab.
- [x] Filtered provenance exports to the datasets left visible in the workspace, refreshed user documentation to explain the
      behaviour, and added a Qt regression that patches the save dialog to verify hidden traces are excluded.
- [x] Allowed provenance CSV bundles to re-import as individual spectra by teaching the CSV importer to expose bundle metadata,
      updating the ingest service/UI to handle list-based ingestion, expanding tests, and documenting the revised workflow.
- [x] Forced CI dependency installs to prefer binary wheels and aligned the master prompt with cross-platform timestamp
      guidance so onboarding instructions remain consistent with the agent manual.
- [x] Fixed the Remote Data dialog's signal binding so PySide6 environments launch cleanly without referencing `pyqtSignal`,
      with patch notes and knowledge log entries capturing the regression fix.
- [x] Wrapped the Remote Data status banner in a progress layout with a busy indicator so startup no longer raises an undefined
      `progress_container` error and the asynchronous workflow matches the documented UI.
- [x] Fixed the Library hint label height/word wrap so cached selections stay
      within the dock and updated installation guidance (`RunSpectraApp.cmd`,
      `START_HERE`, `AGENTS`) to use `pip --prefer-binary`, keeping numpy
      `<3` and requests `<3` so Windows developers avoid source builds.
- [x] Hid the History dock by default so dataset browsing no longer collapses the inspector pane; the panel remains accessible
      from View → History and the user guide now explains the opt-in workflow.
- [x] Added export options for wide/composite CSV variants, wired `ProvenanceService`
      helpers and importer detection for the new layouts, updated the user guides,
      and extended regression coverage for wide/composite round-trips.
- [x] Added a dataset-dock filter for large sessions, updated plot tools/user
      onboarding docs with cross-platform timestamp guidance, and recorded the
      workflow in patch notes and the knowledge log.
- [x] Reoriented the Library metadata pane into a side-by-side layout so cached
      selections keep the log dock visible, and synced the importing/remote data
      guides plus historical logs with the new UI.
- [x] Consolidated the Datasets and Library views into a single Data dock with
      tabbed navigation, rebuilt the library tab so it disables cleanly when
      persistence is off, updated user/developer guides, and extended Qt
      coverage for the reorganised layout.

### Recently Completed (2025-10-18)

- [x] Ported the Remote Data NIST adapter to the astroquery line-list helper,
      aggregated each query into a single record with line counts, and
      synthesised CSV downloads so the existing importer can ingest the
      spectroscopy payload. Updated the remote data guide, regression suite,
      patch notes, and knowledge log with the new workflow.
- [x] Align Remote Data searches with provider-specific criteria so MAST queries pass `target_name` while NIST continues to use `spectra` filters, and extend the regression suite to cover the translation.
- [x] Route MAST downloads through `astroquery.mast.Observations.download_file`, retaining the HTTP code path for direct URLs and persisting results via `LocalStore`.
- [x] Separate routine ingest bookkeeping from the Knowledge Log by introducing a cached-library view backed by `LocalStore` and limiting the log to distilled insights. Update the documentation to reflect the new policy.
- [x] Ensure Import/Remote Import history entries no longer persist to the canonical knowledge log by adding a non-persistent flag to `KnowledgeLogService` and updating ingest hooks plus regression tests.
- [x] Harden the knowledge-log runtime guard so Import/Remote Import components are treated as runtime-only even if callers omit `persist=False`, with regression coverage and a log audit to confirm the cleanup.
- [x] Restore the Remote Data provider-change slot, assert it under pytest, and inject spectroscopic defaults (`dataproduct_type="spectrum"`, `intentType="SCIENCE"`, `calib_level=[2, 3]`) so MAST queries prioritise calibrated spectra with matching documentation updates.
- [x] Extend the Library dock with a metadata preview pane, search-aware filtering, and documentation/test coverage so cached spectra can be inspected without re-ingesting files.
- [x] Block empty Remote Data submissions, surface curated example queries per
      provider, and raise service-level errors for missing criteria so remote
      searches stay scoped to spectroscopy use-cases.
- [x] Declare remote catalogue dependencies (`requests`, `astroquery`,
      `pandas`), surface pandas-aware availability hints, wire the **Include
      imaging** toggle into the Remote Data dialog, and expand regression tests
      and user docs to cover the new mode.

### Batch 14 QA Log

- 2025-10-21: ✅ `pytest -q`
- 2025-10-19: ✅ `pytest`
- 2025-10-17: ✅ `pytest`

## Batch 13 (2025-10-15)

- [x] Capture QA background spectra that still swapped axes and extend `CsvImporter` heuristics, fixtures, and cache coverage to eliminate the regression.
- [x] Improve IR functional-group overlay readability with legible legends/tooltips across themes.
- [x] Deduplicate duplicate Inspector dock panes on Windows and consolidate documentation log events.
- [x] Ensure reference overlays respect combo changes after multi-file ingest so hydrogen/IR/JWST traces stay in sync.
- [x] Confirm normalization/unit toolbar visibility persists across sessions and document the manual re-normalization workflow for QA operators.

### Batch 13 QA Log

- 2025-10-16: ✅ `pytest`

## Batch 12 (2025-10-15)

- [x] Keep the Reference inspector combo synchronised with the preview plot and overlay toggle.
- [x] Restore normalization controls with a View-menu toggle and support Unicode `cm⁻¹` unit inputs.
- [x] Add profile-based axis swapping so monotonic intensity columns no longer displace jittery wavenumber exports.

### Batch 12 QA Log

- 2025-10-15: ✅ `ruff check app tests`
- 2025-10-15: ✅ `mypy app --ignore-missing-imports`
- 2025-10-15: ✅ `pytest -q --maxfail=1 --disable-warnings`

## Batch 11 (2025-10-15)

- [x] Ensure Reference combo-box selection and overlays track the active dataset.
- [x] Restore JWST overlay payloads so quick-look curves display both in the inspector and main workspace.
- [x] Let sample loading and File → Open queue multiple files while throttling redraws.
- [x] Document normalization toolbar placement and the updated reference workflow.

### Batch 11 QA Log

- 2025-10-15: ✅ `pytest -q`

## Batch 10 (Backlog)

- [x] Wire Doppler, pressure, and Stark broadening models into the overlay service and provide inspector previews with regression tests.
- [ ] Replace digitised JWST tables with calibrated FITS ingestion and provenance links once the pipeline can access MAST data.
- [ ] Expand the spectral-line catalogue beyond hydrogen (e.g., He I, O III, Fe II) with citations and regression coverage.
- [ ] Integrate IR functional-group heuristics into importer header parsing for automated axis validation.
- [x] Plot bundled reference datasets inside the Reference tab and allow overlay toggles on the main plot pane.
- [ ] Prototype a native extension hook (e.g., `pybind11`/C++) for high-throughput spectral transforms and document the Windows build toolchain.

## Documentation Alignment Queue

- [ ] Capture refreshed IR overlay screenshots for `docs/user/reference_data.md` after anchored rendering changes land on Windows builds.
- [ ] Publish Markdown summaries for historic QA reviews (e.g., launch-debugging PDF) with citations and source links.
- [ ] Reconcile `reports/roadmap.md` with the current importer, overlay, and documentation backlog, adding longer-term research goals.
- [ ] Schedule a documentation sweep covering reference data, patch notes, and roadmap updates with acceptance criteria tied to regression tests.

## Batch 9 (2025-10-15)

- [x] Add reproducible build scripts for NIST hydrogen lines, IR functional groups, and JWST quick-look spectra.
- [x] Propagate provenance (generator, retrieval timestamps, planned MAST URIs) into the reference JSON assets and inspector UI.
- [x] Expand spectroscopy documentation (primer, reference guide) to explain the provenance and regeneration flow.

### Batch 9 QA Log

- 2025-10-15: ✅ `ruff check app tests`
- 2025-10-15: ✅ `mypy app --ignore-missing-imports`
- 2025-10-15: ✅ `pytest -q --maxfail=1 --disable-warnings`

## Batch 8 (2025-10-15)

- [x] Bundle NIST hydrogen spectral lines and IR functional group references into the application data store.
- [x] Stage JWST quick-look spectra (WASP-96 b, Jupiter, Mars, Neptune, HD 84406) with resolution metadata for offline use.
- [x] Surface the reference library through a new Inspector tab and publish spectroscopy/JWST documentation.

### Batch 8 QA Log

- 2025-10-15: ✅ `ruff check app tests`
- 2025-10-15: ✅ `mypy app --ignore-missing-imports`
- 2025-10-15: ✅ `pytest -q --maxfail=1 --disable-warnings`

## Batch 7 (2025-10-15)

- [x] Honour wavelength/wavenumber units embedded in headers to prevent swapped axes.
- [x] Record column-selection rationale in importer metadata with regression coverage.
- [x] Update user documentation and patch notes to describe the new safeguards.

### Batch 7 QA Log

- 2025-10-15: ✅ `ruff check app tests`
- 2025-10-15: ✅ `mypy app --ignore-missing-imports`
- 2025-10-15: ✅ `pytest -q --maxfail=1 --disable-warnings`

## Batch 6 (2025-10-15)

- [x] Correct importer axis selection when intensity columns precede wavelength data.
- [x] Wire the Normalize toolbar to overlay scaling (None/Max/Area) and document the behaviour.

### Batch 6 QA Log

- 2025-10-15: ✅ `ruff check app tests`
- 2025-10-15: ✅ `mypy app --ignore-missing-imports`
- 2025-10-15: ✅ `pytest -q --maxfail=1 --disable-warnings`

## Batch 5 (2025-10-15)

- [x] Teach the CSV/TXT importer to recover wavelength/intensity pairs from messy reports with heuristic unit detection.
- [x] Surface user documentation inside the app via a Docs inspector tab and Help menu entry.

### Batch 5 QA Log

- 2025-10-15: ✅ `ruff check app tests`
- 2025-10-15: ✅ `mypy app --ignore-missing-imports`
- 2025-10-15: ✅ `pytest -q --maxfail=1 --disable-warnings`

## Batch 4 (2025-10-15)

- [x] Harden provenance export bundles by copying sources and per-spectrum CSVs with regression coverage.

### Batch 4 QA Log

- 2025-10-15: ✅ `pytest -q`

# 2025-10-20 — Remote data regression checks

- 2025-10-20: ✅ `pytest`
- 2025-10-21: ✅ `pytest tests/test_remote_data_dialog.py tests/test_remote_data_service.py`

## Batch 3 (2025-10-14)

- [x] Draft a user quickstart walkthrough covering launch → ingest → unit toggle → export.
- [x] Author a units & conversions reference with idempotency callouts.
- [x] Document plot interaction tools and LOD expectations.
- [x] Expand the importing guide with a provenance export appendix.

### Batch 3 QA Log

- 2025-10-14: ✅ `pytest -q`

## Batch 2 (2025-10-14)

- [x] Close out the Batch 1 smoke-check and capture the state of CI gates on the latest branch.
- [x] Inventory pending documentation deltas before the next feature work.

### Batch 2 QA Log

- 2025-10-14: ✅ `ruff check app tests`
- 2025-10-14: ✅ `mypy app --ignore-missing-imports`
- 2025-10-14: ✅ `pytest -q --maxfail=1 --disable-warnings`

## Batch 1 (2025-10-14)

- [x] Seed tiny fixtures for tests (`tests/data/mini.*`).
- [x] Lock in unit round-trip behaviour and implement the LocalStore service with cache index tests.
- [x] Ensure provenance export emits a manifest bundle and guard plot performance with an LOD cap test.
- [x] Update user/developer documentation for importing and the ingest pipeline.
- [x] Run lint/type/test suites locally and smoke-check app launch, CSV/FITS ingest, unit toggle, and export manifest.

### Batch 1 QA Log

- 2025-10-14: ✅ `ruff check app tests`
- 2025-10-14: ✅ `mypy app --ignore-missing-imports`
- 2025-10-14: ✅ `pytest -q --maxfail=1 --disable-warnings`
- 2025-10-14: ⚠️ `pytest -q --maxfail=1 --disable-warnings --cov=app --cov-report=term-missing` (fails: coverage plugin unavailable)
- 2025-10-14: ✅ `pip install -r requirements.txt`
