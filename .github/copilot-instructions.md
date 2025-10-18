# Copilot / AI Agent Instructions for Spectra App

This file tells AI coding agents how to be immediately productive in this repository. Keep guidance concise and focused on repository-specific patterns, files, and workflows.

1. Start by reading these mandatory docs before editing code:
   - `AGENTS.md` (repo root) — operating manual and dev expectations.
   - `docs/history/MASTER PROMPT.md` and `docs/brains/README.md` — project guardrail/context.
   - `docs/dev/reference_build.md` and `docs/developer_notes.md` — build/test/debug hints.

2. Architecture quick summary (high-level):
   - UI & entry: `app/main.py` (SpectraMainWindow). Typical pattern: UI wiring → services → inspectors/docks.
   - Services: `app/services/` contains core business logic (ingest, units, provenance, remote fetchers, store, knowledge log). Services are tested under `tests/`.
   - Plotting: `app/ui/plot_pane.py` uses PyQtGraph; traces are added via `PlotPane.add_trace(key, alias, x_nm, y, style)`.
   - Persistence: Local cache via `LocalStore` (in `app/services`) and `KnowledgeLogService` writes `docs/history/KNOWLEDGE_LOG.md` by default.

3. Key conventions and patterns (do not change without updating docs):
   - Docs-first: Any code changes must be accompanied by docs/patch notes and knowledge log updates (see `AGENTS.md`).
   - Provenance: Use `ProvenanceService` and `KnowledgeLogService.record_event(...)` to add audit entries. By default, remote imports may be treated runtime-only (see `KnowledgeLogService.DEFAULT_RUNTIME_ONLY_COMPONENTS`).
   - Tests: Add tests close to the feature (e.g., remote services → `tests/test_remote_data_service.py`, ingesters → importer tests).
   - UI-only changes: prefer Qt smoke tests (headless/offscreen) in `tests/` for regression coverage.

4. Important developer workflows & commands:
   - Run tests: `pytest` from repository root. Offscreen Qt: set `QT_QPA_PLATFORM=offscreen` in environment when running GUI-related tests.
   - Run app (manual): `python -m app.main` from repository root. (Do not run from `app/` folder.)
   - Windows quick-launch: `RunSpectraApp.cmd` auto-creates virtualenv and installs deps.

5. Project-specific notes and examples:
   - Ingest path helper: `SpectraMainWindow._ingest_path(path: Path)` wires DataIngestService.ingest → overlay → history. If recording a history event, use `_record_history_event(component, summary, references, persist=...)` so the UI and knowledge log stay consistent.
   - Knowledge log parsing: `KnowledgeLogService.load_entries()` parses `docs/history/KNOWLEDGE_LOG.md` via HEADER_PATTERN; keep headings/format when writing entries.
   - Unit conversions: `UnitsService` stores canonical units (nm) and conversion helpers are used at display time (see `app/services/units_service.py` and usages in `PlotPane` and `_to_nm`).
   - Remote data: `RemoteDataService` expects provider-specific query building; extend `_build_provider_query` and accompanying tests in `tests/test_remote_data_service.py`.

6. When editing code:
   - Use small, focused commits on feature branches: `feature/YYMMDD-bN-shortname` (see `AGENTS.md`).
   - Run and update targeted tests locally before committing (pytest). For UI changes include a smoke test where feasible.
   - Update `docs/history/PATCH_NOTES.md` and append an entry in `docs/history/KNOWLEDGE_LOG.md` with America/New_York timestamps.

7. Where to look for examples:
   - Recording events & history UI: `app/main.py` (methods `_record_history_event`, `_load_history_entries`, `_build_history_dock`).
   - Persisted cache & library view: `app/main.py` (`_refresh_library_view`) and `app/services/LocalStore`.
   - Tests demonstrating usage: `tests/test_smoke_workflow.py`, `tests/test_knowledge_log_service.py`, `tests/test_remote_data_service.py`.

8. If you need to add dependencies:
   - Avoid native-only packages unless necessary. Update `requirements.txt`, add guarded imports, and include tests to avoid breaking minimal installs (see `AGENTS.md`).

If anything here is unclear or you want more detail on a specific area (tests, ingesters, provenance patterns, or CI), tell me which part to expand and I will iterate.