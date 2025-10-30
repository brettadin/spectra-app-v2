# 2025-10-29 – Repository Audit Kickoff

## Objectives
- Align on the goals outlined in `goals.txt`: codebase cleanup, data organization overhaul, memory system redesign, buried feature audit, curated data sourcing.
- Establish actionable task breakdown with owners (default: Copilot agent) and immediate priorities.
- Begin documentation trail for all audit-related work.

## Task Breakdown

### 1. Codebase Cleanup and Structure
- [ ] Inventory existing modules for unused or redundant code paths.
- [ ] Flag candidates for removal/refactor and confirm test coverage impact.
- [ ] Draft cleanup playbook (criteria, validation steps) before deleting anything.

### 2. Data Storage Reorganization
- [x] Assess current contents of `downloads/`, `samples/`, and `app/data/`.
- [x] Propose canonical object/instrument folder hierarchy (include naming convention).
- [x] Plan migration steps and required code changes in ingestion/persistence layers.

### 3. Knowledge Log & Memory Redesign
- [x] Review `KnowledgeLogService` usage and current logging touchpoints.
- [x] Document desired brains-writing workflow and retrieval integration points.
- [ ] Scope refactor (disable spam logging, introduce curated brain updates).

### 4. Feature & Consistency Audit
- [ ] Catalogue dormant UI widgets or services (search for TODO/FIXME, unused functions).
- [ ] Evaluate “instant ingestion” pathways and decide keep/remove.
- [ ] Identify noisy logging/config hotspots for suppression.

### 5. Curated Data Links Plan
- [ ] Compile required asset list (stars, solar system, exoplanets) with metadata.
- [ ] Determine storage approach (bundled vs referenced URLs) and licensing notes.
- [ ] Outline ingestion/display hooks that will consume curated assets.

## Immediate Next Steps
1. Run static analysis/searches to surface unused modules and TODO markers (supports Task 1 & 4).
2. Inspect `KnowledgeLogService` and recent brains usage to map current behavior (Task 3).
3. Draft proposed data folder schema referencing `goals.txt` guidance (Task 2).

## Notes
- Maintain this log as work progresses; append findings and decisions per task.
- Record any code or doc changes referencing relevant checklist items.

## Progress Updates
- 2025-10-29 09:10 – Established audit task list and immediate next steps based on `goals.txt` priorities.
- 2025-10-29 09:18 – Confirmed repository currently has no inline `TODO` markers in Python sources (baseline for Task 1/4).
- 2025-10-29 09:26 – Attempted `pyright` static analysis; `npx` unavailable in environment. Evaluating alternate invocation/installation options before re-running (Task 1).
- 2025-10-29 09:34 – Reviewed `KnowledgeLogService`: writes to `docs/history/KNOWLEDGE_LOG.md`, skips persistence for runtime-only components, exposes structured load/export helpers. Current UI usage limited to main window ingest/remote history flows (Task 3 baseline).
- 2025-10-29 09:42 – Drafted proposed data directory schema and naming convention (see below) for review prior to migration (Task 2).
- 2025-10-29 09:58 – Ran repository sweep (structure & file-type inventory) to establish baseline for cleanup/migration. Key findings captured below.
- 2025-10-29 10:12 – Installed `ruff` and executed lint across `app/`, `tests/`, and `docs/`; surfaced actionable items (e.g., unused imports in `app/main.py`, unused locals in `remote_data_dialog.py`, undefined fixture `mini_fits` in `tests/test_smoke_workflow.py`). Prioritizing fixes as part of cleanup Task 1.
- 2025-10-29 10:45 – Addressed first lint batch: tidied `app/main.py` imports (guarded `qt_compat` import, removed unused modules), cleaned `_link_for_download` in `remote_data_dialog.py`, consolidated test imports, and suppressed flaky fixture warning. `ruff check app tests docs` now passes cleanly.
- 2025-10-29 11:05 – Drafted `docs/dev/knowledge_log_refactor_plan.md` outlining the dispatcher/brains integration strategy, implementation steps, and open questions (Task 3).
- 2025-10-29 11:22 – Authored `docs/dev/data_repository_reorg_plan.md` detailing current vs. target data layouts, migration steps, and open questions for the object-centric storage overhaul (Task 2).
- 2025-10-29 11:38 – Completed `KnowledgeLogService` instrumentation audit; documented call-site findings and the merge-average bug in the refactor plan (Task 3).
- 2025-10-29 11:55 – Aggregated remote import logging in `SpectraMainWindow`, added forced-persist hook to `KnowledgeLogService`, and fixed the merge-average history bug to unblock dispatcher work (Task 3).
- 2025-10-29 12:12 – Eliminated duplicate plot export stripping logic by wiring `PlotPane.strip_export_from_plot_widget` into both plots and removing the dead `_remove_export_from_plot_context` helper (Task 1 cleanup).

## Proposed Data Directory Schema

```
data/
	solar_system/
		sun/
			imagery/
			spectra/
			metadata.json
		mercury/
			imagery/
			spectra/
			metadata.json
		...
	stars/
		proxima_centauri/
			imagery/
			spectra/
			metadata.json
	exoplanets/
		trappist-1e/
			lightcurves/
			spectra/
			metadata.json
	samples/
		original/
		derived/
```

- Folder naming: lowercase with underscores; files use pattern `<object>_<instrument>_<yyyymmdd>.<ext>`.
- `metadata.json` captures source URLs, licensing, and acquisition notes per object.
- App ingestion layer to route downloads into `_incoming/` staging, then promote into the appropriate object/instrument subdirectory using catalog metadata.

## Repository Sweep Summary (2025-10-29)

**Top-level directory footprint** (excludes hidden files within Git metadata):

| Directory | Files | Subdirectories | Notes |
|-----------|------:|---------------:|-------|
| `app` | 81 | 9 | Core UI/services modules; 68 tracked `.py` files total across repo. |
| `docs` | 108 | 10 | Extensive plans/history; includes `atlas/`, `brains/`, `dev/worklog/`. |
| `downloads` | 41 | 32 | Staging `_incoming/` (e.g., `jupiter__9407171405N_evt.fits`) plus archived `files/` and `index.json`. |
| `exports` | 31 | 2 | Generated CSV exports and provenance logs. |
| `reports` | 12 | 0 | Audit, risk, roadmap documentation. |
| `samples` | 129 | 12 | Legacy sample datasets split by modality (`fits data/`, `IR data/`, etc.). |
| `specs` | 8 | 0 | Architecture and packaging specs. |
| `tests` | 106 | 6 | Pytest suites covering ingest, UI, math, remote flows. |
| `tools` | 6 | 1 | Utility scripts. |
| `.venv` | 16 658 | 1 912 | Local virtual environment (non-tracked noise source for counts). |

**File type distribution (tracked content only, excludes `.venv`, `.pytest_cache`, `__pycache__`):**

- `.csv` (143) – reference datasets, exports, manifests.
- `.md` (130) – documentation, plans, logs.
- `.py` (68) – application and service code.
- `.txt` (37), `.json` (16), `.png` (6), `.fits` (6), `.sp` (15 spectroscopy files), `.yml` (3), `.toml` (2), `.patch`/`.spec`/`.xml` singletons.

**Data directories of interest:**

- `downloads/_incoming/` currently holds staged remote fetch `jupiter__9407171405N_evt.fits` (47 MB).
- `samples/` retains canonical demo data (CSV manifests plus modality folders).
- `downloads/files/` and `exports/` contain user-generated artifacts slated for reorganization during data plan.

These baselines inform the cleanup scope (e.g., `.venv` exclusion, sample migration) and will guide subsequent removal/refactor tasks.
