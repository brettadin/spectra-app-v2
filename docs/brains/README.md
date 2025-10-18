# Brains Ledger (Architecture & Reasoning Notes)

The legacy `docs/atlas/brains.md` file has been replaced by this directory so we
can capture design decisions and scientific rationale as focused, timestamped
entries.  Each note documents one architectural topic (e.g., calibration
pipelines, identification scoring, cache layout) with links back to the code,
Atlas chapters, and user documentation it affects.

## How to add a new entry

1. **Create a markdown file** named `YYYY-MM-DDTHHMM-topic.md` (24-hour clock,
   America/New_York timezone).  Example: `2025-10-17T1930-calibration-dock.md`.
2. **Populate the header** using this template:
   ```markdown
   # Title
   _Recorded: 2025-10-17T19:30:00-04:00 (America/New_York)_

   ## Context
   Reference the relevant Atlas chapters (see below), specs, tests, and any
   external research links or DOIs.

   ## Decisions
   - Bullet the agreed constraints or selected approach.

   ## Follow-up
   - List tasks that must appear in `docs/reviews/workplan.md` or the backlog.
   ```
3. **Cross-link** the entry from:
   - `docs/history/KNOWLEDGE_LOG.md` (summary of what changed, why).
   - Any affected user or developer documentation.
4. **Update the workplan** so actionable items land in Batch planning or the
   backlog.

## Atlas alignment

The Atlas still provides canonical guidance for units, calibration, provenance,
UI ergonomics, and programming standards.  Before writing or revising a brains
entry, review:

- `docs/atlas/0_index_stec_master_canvas_index_numbered.md`
- Chapter 5 (Units), 6 (Calibration/LSF/frames), 7 (Identification),
  8 (Provenance), 10 (Campus workflows), 11 (Rubric), 14 (Application),
  22 (UI design), 29 (Programming standards)

If a chapter is missing or outdated, document the gap and add a workplan task to
refresh it.  The brains entries are meant to complement—not replace—the Atlas.

## File naming & housekeeping

- Keep filenames lowercase with hyphens; avoid spaces so cross-links stay
  shell-friendly.
- Delete or archive superseded entries instead of editing history silently;
  record the supersession in the knowledge log for traceability.
- The old `placeholder.txt` remains only to remind editors that entries now live
  here.  Do not store decisions back in `docs/atlas/`.

By funnelling architectural reasoning through this directory, agents can trace
why a decision was made, which experiments were run, and where to plug follow-up
work into the planning documents.
