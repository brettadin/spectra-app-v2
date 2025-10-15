# Workplan — Batch 13 (2025-10-15)

- [ ] Capture the QA-provided background spectra that still swap X/Y axes and extend `CsvImporter` heuristics, fixtures, and cache coverage to eliminate the regression.
- [ ] Improve IR functional-group overlay readability (legend or tooltip callouts) so shaded bands remain legible on dark themes.
- [ ] Investigate duplicate Inspector dock panes reported on Windows startup and deduplicate repeated documentation log events.
- [ ] Verify reference overlays respect combo changes after multi-file ingest so hydrogen/IR/JWST traces never reuse the first dataset payload.
- [ ] Confirm normalization/unit toolbar visibility persists across sessions and document the manual re-normalization workflow for QA operators.

# Workplan — Batch 12 (2025-10-15)

- [x] Keep the Reference inspector combo in sync with the preview plot and overlay toggle, including JWST quick-look curves and labelled IR regions.
- [x] Restore normalization controls by adding a View-menu toggle for the plot toolbar and accepting Unicode `cm⁻¹` inputs in unit conversions.
- [x] Add profile-based axis swapping so monotonic intensity columns no longer displace jittery wavenumber exports.

## Batch 12 QA Log

- 2025-10-15: ✅ `ruff check app tests`
- 2025-10-15: ✅ `mypy app --ignore-missing-imports`
- 2025-10-15: ✅ `pytest -q --maxfail=1 --disable-warnings`

# Workplan — Batch 1 (2025-10-14)

- [x] Seed tiny fixtures for tests (`tests/data/mini.*`).
- [x] Lock in unit round-trip behavior (`tests/test_units_roundtrip.py`).
- [x] Implement local store service and cache index tests.
- [x] Ensure provenance export emits manifest bundle.
- [x] Guard plot performance with LOD cap test.
- [x] Update user and developer documentation (importing + ingest pipeline).
- [x] Run lint/type/test suite locally; confirm CI configuration.
- [x] Smoke-check app launch, CSV/FITS ingest, unit toggle, export manifest (automated in tests/test_smoke_workflow.py).

## Batch 1 QA Log

- 2025-10-14: ✅ `ruff check app tests`
- 2025-10-14: ✅ `mypy app --ignore-missing-imports`
- 2025-10-14: ✅ `pytest -q --maxfail=1 --disable-warnings`
- 2025-10-14: ✅ `pip install -r requirements.txt`
- 2025-10-14: ✅ `ruff check app tests`
- 2025-10-14: ✅ `mypy app --ignore-missing-imports`
- 2025-10-14: ⚠️ `pytest -q --maxfail=1 --disable-warnings --cov=app --cov-report=term-missing` (fails: coverage plugin unavailable in test harness)
- 2025-10-14: ✅ `pytest -q --maxfail=1 --disable-warnings`

# Workplan — Batch 2 (2025-10-14)

- [x] Close out Batch 1 smoke-check (launch app, ingest CSV/FITS, toggle units, export manifest).
- [x] Capture current state of CI gates (ruff, mypy, pytest) on the latest branch.
- [x] Inventory pending documentation deltas required before next feature work. (See `docs/reviews/doc_inventory_2025-10-14.md`.)

## Batch 2 QA Log

- 2025-10-14: ✅ `ruff check app tests`
- 2025-10-14: ✅ `mypy app --ignore-missing-imports`
- 2025-10-14: ❌ `pytest -q --maxfail=1 --disable-warnings --cov=app --cov-report=term-missing` (fails: pytest-cov plugin missing)
- 2025-10-14: ✅ `pytest -q --maxfail=1 --disable-warnings`

# Workplan — Batch 3 (2025-10-14)

- [x] Draft user quickstart walkthrough covering launch → ingest → unit toggle → export.
- [x] Author units & conversions reference with idempotency callouts (`docs/user/units_reference.md`).
- [x] Document plot interaction tools and LOD expectations (`docs/user/plot_tools.md`).
- [x] Expand importing guide with provenance export appendix.

## Batch 3 QA Log

- 2025-10-14: ✅ `pytest -q`

# Workplan — Batch 4 (2025-10-15)

- [x] Harden provenance export bundle by copying sources and per-spectrum CSVs with regression coverage.

## Batch 4 QA Log

- 2025-10-15: ✅ `pytest -q`

# Workplan — Batch 5 (2025-10-15)

- [x] Teach the CSV/TXT importer to recover wavelength/intensity pairs from messy reports with heuristic unit detection.
- [x] Surface the user documentation inside the app via a Docs inspector tab and Help menu entry.

## Batch 5 QA Log

- 2025-10-15: ✅ `ruff check app tests`
- 2025-10-15: ✅ `mypy app --ignore-missing-imports`
- 2025-10-15: ⚠️ `pytest -q --maxfail=1 --disable-warnings --cov=app --cov-report=term-missing` (fails: pytest-cov plugin unavailable)
- 2025-10-15: ✅ `pytest -q --maxfail=1 --disable-warnings`

# Workplan — Batch 6 (2025-10-15)

- [x] Correct importer axis selection when intensity columns precede wavelength data, with regression coverage.
- [x] Wire the Normalize toolbar to overlay scaling (None/Max/Area) and document the behaviour.

## Batch 6 QA Log

- 2025-10-15: ✅ `ruff check app tests`
- 2025-10-15: ✅ `mypy app --ignore-missing-imports`
- 2025-10-15: ⚠️ `pytest -q --maxfail=1 --disable-warnings --cov=app --cov-report=term-missing` (fails: pytest-cov plugin unavailable)
- 2025-10-15: ✅ `pytest -q --maxfail=1 --disable-warnings`

# Workplan — Batch 7 (2025-10-15)

- [x] Honour wavelength/wavenumber units embedded in headers to prevent swapped axes.
- [x] Record column-selection rationale in importer metadata and add regression coverage for header-driven swaps.
- [x] Update user documentation and patch notes to describe the new safeguards.

## Batch 7 QA Log

- 2025-10-15: ✅ `ruff check app tests`
- 2025-10-15: ✅ `mypy app --ignore-missing-imports`
- 2025-10-15: ⚠️ `pytest -q --maxfail=1 --disable-warnings --cov=app --cov-report=term-missing` (fails: pytest-cov plugin unavailable)
- 2025-10-15: ✅ `pytest -q --maxfail=1 --disable-warnings`

# Workplan — Batch 8 (2025-10-15)

- [x] Bundle NIST hydrogen spectral lines and IR functional group references into the application data store.
- [x] Stage JWST quick-look spectra (WASP-96 b, Jupiter, Mars, Neptune, HD 84406) with resolution metadata for offline use.
- [x] Surface the reference library through a new Inspector tab and publish spectroscopy/JWST documentation for users and agents.

## Batch 8 QA Log

- 2025-10-15: ✅ `ruff check app tests`
- 2025-10-15: ✅ `mypy app --ignore-missing-imports`
- 2025-10-15: ⚠️ `pytest -q --maxfail=1 --disable-warnings --cov=app --cov-report=term-missing` (fails: pytest-cov plugin unavailable)
- 2025-10-15: ✅ `pytest -q --maxfail=1 --disable-warnings`

# Workplan — Batch 9 (2025-10-15)

- [x] Add reproducible build scripts for NIST hydrogen lines, IR functional groups, and JWST quick-look spectra.
- [x] Propagate provenance (generator, retrieval timestamps, planned MAST URIs) into the reference JSON assets and inspector UI.
- [x] Expand spectroscopy documentation (primer, reference guide) to explain the new provenance metadata and regeneration flow.

## Batch 9 QA Log

- 2025-10-15: ✅ `ruff check app tests`
- 2025-10-15: ✅ `mypy app --ignore-missing-imports`
- 2025-10-15: ⚠️ `pytest -q --maxfail=1 --disable-warnings --cov=app --cov-report=term-missing` (fails: pytest-cov plugin unavailable)
- 2025-10-15: ✅ `pytest -q --maxfail=1 --disable-warnings`

# Workplan — Batch 10 (Backlog)

- [ ] Wire Doppler/pressure/Stark broadening models into the overlay service using the placeholder parameter scaffolding.
- [ ] Replace digitised JWST tables with calibrated FITS ingestion and provenance links once the pipeline module is ready.
- [ ] Expand the spectral line catalogue beyond hydrogen (e.g. He I, O III, Fe II) with citations and regression coverage.
- [ ] Integrate IR functional group heuristics into importer header parsing for automated axis validation.
- [x] Plot bundled reference datasets inside the Reference tab so users can preview hydrogen lines, IR bands, and JWST spectra.
  - Add a `pyqtgraph.PlotWidget` beneath the reference table, rendering vertical markers for hydrogen transitions, shaded spans for IR bands, and line/error-bar plots for JWST targets.
  - Provide a toggle to overlay the selected reference dataset on the main plot pane using a deterministic `reference::` trace prefix and clean up overlays when deselected.
  - Extend `tests/test_smoke_workflow.py` (plus targeted unit tests) to assert plot rendering, and document the workflow in `docs/user/reference_data.md`.

# Workplan — Batch 11 (2025-10-15)

- [x] Ensure Reference combo-box selection and overlays track the active dataset (spectral lines, IR bands, JWST spectra).
- [x] Restore JWST overlay payloads so quick-look curves plot both in-panel and on the main workspace.
- [x] Let sample loading and File → Open queue multiple files while throttling redraws.
- [x] Document the toolbar location for normalization controls and the updated reference workflow.

## Batch 11 QA Log

- 2025-10-15: ✅ `ruff check app tests`
- 2025-10-15: ✅ `mypy app --ignore-missing-imports`
- 2025-10-15: ✅ `pytest -q --maxfail=1 --disable-warnings`
