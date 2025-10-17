# Agent Operating Manual

This repository is documentation-heavy and the Spectra desktop preview depends
on accurate provenance. Before editing code or docs, work through the sections
below—future agents rely on these conventions to maintain continuity.

## 0. Mandatory reading

- `docs/link_collection.md` – Curated spectroscopy resources. Use it to source
  UV/VIS, IR, mass-spec, or JWST data that align with the project goals.
- `docs/user/remote_data.md`, `docs/user/importing.md`, `docs/user/reference_data.md`,
  `docs/user/plot_tools.md` – User-facing behaviour that must stay in sync with
  code changes.
- `docs/developer_notes.md`, `docs/dev/reference_build.md` – Extension points and
  build scripts for ingesting new reference assets.
- `docs/reviews/workplan.md` – Tracks open tasks and backlog items (including the
  native-extension exploration). Update it whenever you deliver or scope new work.
- `docs/history/PATCH_NOTES.md` & `docs/history/KNOWLEDGE_LOG.md` – Append entries
  for every meaningful change; the knowledge log is reserved for high-level
  insights, not raw file listings.

## 1. Implementation guidelines

- **Remote catalogues**: The dialog now sends provider-specific queries. NIST
  expects `spectra`; MAST expects `target_name`. If you add providers, extend
  `app/services/remote_data_service.py`, update
  `tests/test_remote_data_service.py`, and refresh the user guide.
- **Downloads**: MAST products must flow through
  `astroquery.mast.Observations.download_file`; HTTP URLs still use
  `requests`. Honour `_fetch_remote` when wiring new sources.
- **Cache & Library**: `_ingest_path` and `_record_remote_history_event` only log
  concise summaries. File-level metadata appears in the Library dock (tabified
  with the Datasets view). Keep this separation intact and refresh the Library
  after any ingest pipeline changes.
- **Trace colouring**: The Style tab exposes high-contrast and uniform colour
  modes. Respect `_use_uniform_palette` / `_display_color` when touching plot
  rendering or dataset icon logic.
- **Spectroscopy first**: Prioritise calibrated spectra (UV/VIS/IR, line lists,
  mass-spec standards). Avoid populating the app with photometric light curves or
  brightness/time products unless explicitly required.
- **Native extensions**: The backlog tracks a pybind11/C++ prototype. If you
  explore it, document the Windows 11 build toolchain and keep bindings optional.

## 2. Documentation & logging

- Every code change needs matching docs: update the relevant user guide, add a
  patch-notes entry, and append a knowledge-log summary with citations.
- When adding resources, cross-link them in `docs/link_collection.md` and note
  provenance (DOIs/URLs) so future agents can revalidate the source.
- The workplan should always reflect the current backlog. Close completed
  checkboxes and record QA runs (ruff/mypy/pytest) with timestamps.

## 3. Testing expectations

- Run `pytest` locally before committing. Add or update tests alongside feature
  work—remote catalogue changes belong in `tests/test_remote_data_service.py`;
  UI tweaks should be covered by the existing Qt smoke tests where possible.
- If you introduce native code or optional dependencies, gate imports with
  dependency checks and extend the test suite accordingly.

## 4. Commit & PR etiquette

- Keep commits scoped and well-described. After committing, update
  `docs/history/PATCH_NOTES.md`, `docs/history/KNOWLEDGE_LOG.md`, and the workplan
  before opening a PR.
- PR descriptions should summarise user-facing changes and list the tests you
  ran. Cite relevant documentation updates so reviewers can verify alignment.

By following this manual you ensure Spectra’s documentation, provenance, and
spectroscopy focus remain coherent for every agent and human collaborator.
