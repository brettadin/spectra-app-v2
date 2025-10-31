# Knowledge Log & Memory Refactor Plan

## Current State
- `KnowledgeLogService` writes markdown entries to `docs/history/KNOWLEDGE_LOG.md`. It skips persistence for components registered in `runtime_only_components` (default: Import, Remote Import) but otherwise records every call site.
- `SpectraMainWindow` calls `record_event` for most ingest flows. Remote imports invoke `KnowledgeLogService.record_event` indirectly, duplicating entries when multiple spectra arrive, and the history pane mirrors the same data.
- The brains directory (`docs/brains/`) contains manually curated “neuron” markdown files but there is no automated pipeline linking UI actions to these files. Agents rely on ad hoc updates instead of structured memory writes.
- Tests expect the history log to record ingest activity (see `tests/test_smoke_workflow.py`) so outright removal of logging would break the suite without providing an alternative memory hook.

## Pain Points
- Every ingest or remote import floods the knowledge log with near-identical summaries, making it hard to surface higher-level insights.
- Logging user operations risks capturing sensitive content and bloats the markdown file beyond usable size (~5K lines today).
- Lack of cross-links: knowledge log entries do not automatically spawn or update neurons, so the long-term memory and the log diverge quickly.
- No mechanism exists to summarise multiple related events into a single durable memory item (e.g., “Completed Jupiter dataset ingest and analysis”).

## Target Architecture
1. **Event Filtering Layer**
   - Introduce a lightweight dispatcher that classifies events (ingest, remote import, analysis, doc updates) and decides whether to persist, summarise, or discard.
   - Default policy: suppress per-spectrum ingest events, batch them into periodic summaries (e.g., once per session or per object).
   - Provide extension hooks so future features (e.g., ML inference) can register new event types without touching logging internals.

2. **Brains Synchronisation**
   - Add a `BrainsRepository` helper that writes/upserts neuron files using the template in `docs/brains/README.md`.
   - When an event is marked “knowledge-worthy,” the dispatcher should invoke the brains repository with structured content (context, decision, references).
   - Maintain an index JSON/YAML mapping topics to neuron files for quick lookup and to prevent duplicate neuron creation.

3. **Knowledge Log Slimming**
   - Retain `KNOWLEDGE_LOG.md` as a human-readable digest but limit entries to batched summaries and cross-links to the corresponding neuron files.
   - Update `KnowledgeLogService.record_event` to accept an enum or flags indicating log level (`transient`, `summary`, `neuron_update`). Transient events populate UI history only; summary events write to the markdown log; neuron updates delegate to the brains repository and append a short pointer to the log.

4. **UI Integration**
   - The history pane should display both transient session entries (for immediate feedback) and persistent summaries tagged with their neuron references. Provide filters to toggle view modes.
   - Ensure remote download/import progress uses the transient channel; once the batch completes, the dispatcher emits a single summary with total counts and the staging destination.

## Implementation Steps
1. **Instrumentation Audit**
   - Catalogue every `record_event` call and classify the event type.
   - Identify UI components that display log content (history pane, CLI output) and note required behaviour changes.

2. **Service Refactor**
   - Extend `KnowledgeLogService` with new event-level semantics and optional brains repository integration (feature-flagged until the repository helper ships).
   - Deprecate direct writes to `_runtime_only_components`; replace with the dispatcher filter.

3. **Brains Repository Helper**
   - Implement helpers to create/update neuron files with timestamped headers, maintain an index, and ensure idempotent updates when the same topic is revisited within a session.
   - Provide CLI/testing utilities for validating neuron format (lint).

4. **UI & Tests Update**
   - Adjust history view tests to expect batched summaries rather than per-file spam (update fixtures accordingly).
   - Add new unit tests verifying dispatcher behaviour, neuron creation, and cross-link logging.

5. **Migration & Cleanup**
   - Write a one-off script to condense existing repetitive log entries into a smaller set of summaries and generate seed neurons where appropriate.
   - Document the new workflow in `docs/dev/knowledge_log_refactor_plan.md`, `docs/brains/README.md`, and update contributor guides.

## Instrumentation Audit – 2025-10-29
| Call site | Component label | Persist behaviour | Notes |
| --- | --- | --- | --- |
| `SpectraMainWindow._ingest_path` | `"Ingest"` | Always persists because `"Ingest"` is not part of `DEFAULT_RUNTIME_ONLY_COMPONENTS`. | Emits one entry per imported file with filename as the only reference, creating log spam during batch imports. |
| `SpectraMainWindow._record_remote_history_event` (per spectrum) | `"Remote Import"` | Forces persistence by instantiating a fresh `KnowledgeLogService` with `runtime_only_components=()`; bypasses runtime-only guard. | Called for each spectrum returned by remote ingest; duplicates provider entries when multiple spectra arrive in one batch. |
| `SpectraMainWindow._record_remote_history_event` (fallback) | `"Remote Import"` | Same forced persistence path. | Emits a generic "Imported remote data" entry when metadata is missing, adding low-value noise. |
| `SpectraMainWindow._on_merge_average` | `"merge_average"` (lowercase) | Would attempt to persist, but the call uses `self.knowledge_log.log(...)` (method absent on `KnowledgeLogService`). | Bug: hitting the merge-average action will raise `AttributeError`; needs alignment with the dispatcher API during refactor. |

**Key observations**
- Per-spectrum ingest and remote import hooks flood `KNOWLEDGE_LOG.md`; both should shift to transient events with batched summaries.
- Remote imports intentionally sidestep the runtime-only component guard, so any new dispatcher must re-introduce policy control to avoid regressions.
- The merge-average path is currently broken; the dispatcher refactor should supply a single entry point (e.g., `log_event`) and tests must exercise this UI branch.

## Open Questions
- How granular should neuron topics be for ingest events (per object, per observing campaign, per analysis session)?
- Where should the event dispatcher live (`app/services` vs. new `app/memory` package)?
- Do we need user-facing controls to opt in/out of persistent logging for privacy reasons?

Record these answers in the worklog and update this plan as decisions land.
