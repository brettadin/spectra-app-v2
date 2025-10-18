# Agent Operating Manual

Spectra is documentation-first. Read the required sources before editing code or
docs so provenance, spectroscopy focus, and UI coherence remain intact.

## 0. Mandatory reading
- `docs/history/MASTER PROMPT.md` — Coordinator mandate and guardrails.
- `docs/brains/README.md` plus the most recent entries in `docs/brains/` —
  architectural decisions and follow-ups.
- `docs/link_collection.md` and `docs/reference_sources/README.md` — curated
  spectroscopy catalogues and acquisition notes.
- User guides: `docs/user/remote_data.md`, `docs/user/importing.md`,
  `docs/user/reference_data.md`, `docs/user/plot_tools.md`, `docs/user/units_reference.md`.
- Developer notes: `docs/developer_notes.md`, `docs/dev/reference_build.md`.
- Planning: `docs/reviews/workplan.md` and `docs/reviews/workplan_backlog.md`.
- Historical context: `docs/history/PATCH_NOTES.md`,
  `docs/history/KNOWLEDGE_LOG.md`, `docs/history/RUNNER_PROMPT.md`.

If any referenced doc is missing or stale, file a workplan task and log the gap
in the knowledge log before proceeding.

## 1. Implementation guidelines
- **Remote catalogues**: `_build_provider_query` enforces provider-specific
  criteria. NIST expects `spectra`; MAST requires `target_name` and rejects empty
  submissions. Extend `app/services/remote_data_service.py` and
  `tests/test_remote_data_service.py` when adding providers.
- **Downloads**: Use `astroquery.mast.Observations.download_file` for `mast:`
  URIs. HTTP/HTTPS links continue through the shared `requests` session.
- **Cache & Library**: Local ingest metadata lives in the Library dock. Keep the
  knowledge log focused on distilled insights—imports call
  `KnowledgeLogService.record_event(..., persist=False)` by design.
- **Spectroscopy-first samples**: Store lab-calibrated spectra (UV/VIS/IR,
  mass-spec) in `samples/`. Surface them in the UI under a dedicated Samples
  node; do not auto-load them at startup.
- **Trace colouring**: Respect palette options wired through `_display_color`
  and `_use_uniform_palette`. New palettes must update dataset icons and plot
  pens together.
- **Atlas compliance**: Units, calibration honesty, provenance completeness, and
  explainable identification rules from the Atlas are mandatory. Reference the
  relevant chapters in docs and commits.

## 2. Documentation & logging
- Every change needs matching documentation (user + dev/spec as appropriate).
- Append patch-note and knowledge-log entries with the actual
  `America/New_York` timestamp (ISO-8601 with offset). Mention the files or
  features touched and cite supporting docs/tests.
- Cross-link new resources in `docs/link_collection.md` with provenance (DOI or
  URL) so future agents can verify sources.
- Keep the workplan and backlog in sync with delivered tasks and new findings.

## 3. Testing expectations
- Run `pytest` locally before committing. Add or update regression coverage next
  to the code you touch (remote services → `tests/test_remote_data_service.py`,
  UI tweaks → Qt smoke tests, ingest logic → importer suite).
- When introducing optional dependencies or native code, guard imports and add
  targeted tests to avoid breaking minimal installs.

## 4. Commit & PR etiquette
- Work on branches (`feature/YYMMDD-bN-shortname`).
- Keep commits scoped; cite documentation updates in commit messages and PR
  bodies.
- After committing, update the workplan, patch notes, and knowledge log before
  calling the PR tooling.
- PR descriptions must summarise user-facing changes and list executed tests.
- Never commit binaries or machine-specific paths.

Following this manual keeps Spectra’s provenance chain reliable and ensures the
UI, documentation, and scientific tooling evolve together.
