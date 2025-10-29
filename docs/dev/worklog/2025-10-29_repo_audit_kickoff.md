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
- [ ] Assess current contents of `downloads/`, `samples/`, and `app/data/`.
- [ ] Propose canonical object/instrument folder hierarchy (include naming convention).
- [ ] Plan migration steps and required code changes in ingestion/persistence layers.

### 3. Knowledge Log & Memory Redesign
- [ ] Review `KnowledgeLogService` usage and current logging touchpoints.
- [ ] Document desired brains-writing workflow and retrieval integration points.
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
