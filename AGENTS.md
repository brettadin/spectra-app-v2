# Agent Orientation

Welcome to the Spectra workspace. Follow these guidelines before editing:

## Read first
- **START_HERE.md** – high-level overview of repository layout and launch scripts.
- **docs/link_collection.md** – curated index of external spectroscopy resources and internal primers.
- **docs/reviews/workplan.md** – current batch priorities and backlog, including JWST FITS regeneration and importer heuristics.
- **docs/history/PATCH_NOTES.md** – recent changes; append new entries when you land noteworthy features.
- **docs/history/KNOWLEDGE_LOG.md** – reserve for distilled insights (architecture decisions, scientific findings). Routine file
  ingests now belong in the Library panel, not the knowledge log.

## Coding guidelines
- Prefer existing services: use `DataIngestService`, `OverlayService`, and `LocalStore` rather than duplicating logic.
- Optional dependencies (`requests`, `astroquery`, `astropy`) must remain guarded. Follow the patterns in
  `app/services/remote_data_service.py`.
- Keep new UI components accessible through the View menu and documented under `docs/user/`.
- Run `pytest` after modifications that touch code or tests. Capture the command in your summary with a ✅/⚠️/❌ prefix.

## Documentation & provenance
- Update relevant user/developer docs whenever behaviour changes (importer heuristics, remote workflow, plot styling, etc.). The
  importing, remote-data, and plot guides live under `docs/user/`.
- Append concise summaries to `docs/history/PATCH_NOTES.md` and add a knowledge-log entry only when you have a significant
  takeaway or architectural lesson.
- Refresh `docs/reviews/workplan.md` when you complete or add tasks so future agents know the project state.

## Library & caching
- The in-app Library dock surfaces cached files from `LocalStore`. Do not log raw file paths to the Knowledge Log; rely on the
  Library for bookkeeping and mention notable datasets in patch notes if needed.

## QA expectations
- Respect new palette and remote-data behaviours when editing the plot or Remote Data dialog. Update or extend
  `tests/test_remote_data_service.py` and related suites if your changes touch those paths.
- Honour the Git history: keep commits focused and reference updated docs/tests in summaries.

Coordinate with these resources and keep documentation in sync to preserve continuity for subsequent agents.
