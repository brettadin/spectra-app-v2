# Workplan Overview

This document tracks active batches, QA runs, and recently completed work.
Historic batches remain at the bottom for reference. Use
`docs/reviews/workplan_backlog.md` for initiatives that are not yet scheduled.

## Batch 15 (2025-10-17) — Active
- [x] Realign coordinator/agent prompts with brains-ledger restructure and enforce
      real-time (America/New_York) logging guidance across docs.
- [x] Document brains-ledger usage so architectural notes have a single source
      (`docs/brains/README.md`).
- [ ] Block empty provider submissions in the Remote Data dialog and service
      (`_build_provider_query` + `_search_mast`) with regression coverage and UI
      messaging.
- [ ] Extend Library dock actions so cached entries expose manifest/log shortcuts
      and provenance links without re-importing.
- [ ] Draft calibration-manager RFC outline (service, dock, banner, provenance)
      based on Pass 3 findings and schedule implementation tasks.

### Batch 15 QA Log
- *(pending next feature delivery)*

## Batch 14 (2025-10-17) — Completed
- [x] Align Remote Data searches with provider-specific criteria so MAST queries
      pass `target_name` while NIST continues to use `spectra` filters, extending
      the regression suite to cover the translation.
- [x] Route MAST downloads through `astroquery.mast.Observations.download_file`,
      retaining the HTTP code path for direct URLs and persisting results via
      `LocalStore`.
- [x] Separate routine ingest bookkeeping from the Knowledge Log by introducing a
      cached-library view backed by `LocalStore` and limiting the log to distilled
      insights. Update the documentation to reflect the new policy.
- [x] Ensure Import/Remote Import history entries no longer persist to the
      canonical knowledge log by adding a non-persistent flag to
      `KnowledgeLogService` and updating ingest hooks plus regression tests.
- [x] Harden the knowledge-log runtime guard so Import/Remote Import components
      are treated as runtime-only even if callers omit `persist=False`, with
      regression coverage and a log audit to confirm the cleanup.
- [x] Restore the Remote Data provider-change slot, assert it under pytest, and
      inject spectroscopic defaults (`dataproduct_type="spectrum"`,
      `intentType="SCIENCE"`, `calib_level=[2, 3]`) so MAST queries prioritise
      calibrated spectra with matching documentation updates.
- [x] Extend the Library dock with a metadata preview pane, search-aware
      filtering, and documentation/test coverage so cached spectra can be
      inspected without re-ingesting files.

### Batch 14 QA Log
- 2025-10-17: ✅ `pytest`

## Batch 13 (2025-10-15) — Completed
- [x] Capture QA background spectra that still swapped axes and extend
      `CsvImporter` heuristics, fixtures, and cache coverage to eliminate the
      regression.
- [x] Improve IR functional-group overlay readability with legible
      legends/tooltips across themes.
- [x] Deduplicate duplicate Inspector dock panes on Windows and consolidate
      documentation log events.
- [x] Ensure reference overlays respect combo changes after multi-file ingest so
      hydrogen/IR/JWST traces stay in sync.
- [x] Confirm normalization/unit toolbar visibility persists across sessions and
      document the manual re-normalization workflow for QA operators.

### Batch 13 QA Log
- 2025-10-16: ✅ `pytest`

## Batch 12 (2025-10-15) — Completed
- [x] Keep the Reference inspector combo synchronised with the preview plot and
      overlay toggle.
- [x] Restore normalization controls with a View-menu toggle and support Unicode
      `cm⁻¹` unit inputs.
- [x] Add profile-based axis swapping so monotonic intensity columns no longer
      displace jittery wavenumber exports.

### Batch 12 QA Log
- 2025-10-15: ✅ `ruff check app tests`
- 2025-10-15: ✅ `mypy app --ignore-missing-imports`
- 2025-10-15: ✅ `pytest -q --maxfail=1 --disable-warnings`

## Batch 11 (2025-10-15) — Completed
- [x] Ensure Reference combo-box selection and overlays track the active dataset.
- [x] Restore JWST overlay payloads so quick-look curves display both in the
      inspector and main workspace.
- [x] Let sample loading and File → Open queue multiple files while throttling
      redraws.
- [x] Document normalization toolbar placement and the updated reference
      workflow.

### Batch 11 QA Log
- 2025-10-15: ✅ `pytest -q`

## Batch 10 (Backlog items moved to backlog file)
- [x] Wire Doppler, pressure, and Stark broadening models into the overlay
      service and provide inspector previews with regression tests.
- [ ] Remaining tasks now tracked in `docs/reviews/workplan_backlog.md`.

## Documentation Alignment Queue — In Progress
- [ ] Capture refreshed IR overlay screenshots for `docs/user/reference_data.md`
      after anchored rendering changes land on Windows builds.
- [ ] Publish Markdown summaries for historic QA reviews (e.g., launch-debugging
      PDF) with citations and source links.
- [ ] Reconcile `reports/roadmap.md` with the current importer, overlay, and
      documentation backlog, adding longer-term research goals.
- [ ] Schedule a documentation sweep covering reference data, patch notes, and
      roadmap updates with acceptance criteria tied to regression tests.

Historic batches (8 and earlier) are unchanged from prior revisions.
