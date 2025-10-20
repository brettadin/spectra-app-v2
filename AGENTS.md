# Agent Operating Manual

This repository is documentation-heavy and the Spectra desktop preview depends
on accurate provenance. Before editing code or docs, work through the sections
below—future agents rely on these conventions to maintain continuity.

## 0. Mandatory reading

- `START_HERE.md` – Session primer. Confirms tooling setup, branch workflow,
  and how to use this manual in practice.
- `docs/history/MASTER PROMPT.md` & `docs/history/RUNNER_PROMPT.md` – Core
  product charter and iteration loop. Keep them aligned with any behavioural
  changes you introduce.
- `docs/brains/README.md` – Defines how architectural “brain” entries are
  recorded now that `atlas/brains.md` has been decomposed. Review existing
  entries before proposing competing decisions.
- `docs/link_collection.md` and `docs/reference_sources/` – Curated resources
  for spectroscopy datasets and background reading. Cite them when ingesting
  new reference material.
- User guides: `docs/user/remote_data.md`, `docs/user/importing.md`,
  `docs/user/reference_data.md`, `docs/user/plot_tools.md`, and
  `docs/user/units_reference.md`. Behavioural changes must keep these in sync.
- Developer guides: `docs/developer_notes.md`, `docs/dev/reference_build.md`,
  and the pass-review dossiers under `docs/reviews/`. They capture backlog
  priorities (calibration manager, identification stack, provenance parity,
  UI accessibility) and acceptance criteria drawn from the Atlas.
- Logging & planning: `docs/reviews/workplan.md`,
  `docs/history/PATCH_NOTES.md`, and `docs/history/KNOWLEDGE_LOG.md`.
  Update all three with real timestamps (see §2) whenever you land work.

## 1. Implementation guidelines

- **Remote catalogues**: The dialog now sends provider-specific queries. NIST
  expects `spectra`; MAST expects `target_name`. Install the optional
  dependencies (`requests`, `astroquery`, and `pandas`) so both catalogues stay
  available. If you add providers, extend
  `app/services/remote_data_service.py`, update
  `tests/test_remote_data_service.py`, and refresh the user guide. Never fire an
  empty query—validate inputs in the dialog and service.
- **Python wheels first**: `RunSpectraApp.cmd` installs requirements with
  `--prefer-binary` and clears any inherited `PIP_NO_BINARY` value while forcing
  `PIP_ONLY_BINARY=numpy`. If Windows still tries to build `numpy` from source,
  run `python -m pip install --prefer-binary "numpy>=1.26,<3"` (or install the
  latest Microsoft C++ Build Tools) before re-running the launcher, then report
  the failure in patch notes so future agents know the environment state.
- **Downloads**: MAST products must flow through
  `astroquery.mast.Observations.download_file`; HTTP URLs still use
  `requests`. Honour `_fetch_remote` when wiring new sources.
- **Cache & Library**: `_ingest_path` and `_record_remote_history_event` record
  runtime history entries with `persist=False`; the canonical knowledge log
  stays focused on curated insights. File-level metadata appears in the Library
  dock (tabified with the Datasets view). Keep this separation intact, avoid
  spawning duplicate Library tabs, and refresh the view after any ingest
  pipeline changes.
- **Trace colouring**: The Style tab exposes high-contrast and uniform colour
  modes. Respect `_use_uniform_palette` / `_display_color` when touching plot
  rendering or dataset icon logic.
- **Spectroscopy first**: Prioritise calibrated spectra (UV/VIS/IR, line lists,
  mass-spec standards). Avoid photometric-only or brightness/time products
  unless the workplan explicitly calls them out. Log provenance and citations
  for every new dataset.
- **Native extensions**: The backlog tracks a pybind11/C++ prototype. If you
  explore it, document the Windows 11 build toolchain and keep bindings optional.

## 2. Documentation & logging

- Every code change needs matching docs: update the relevant user guide, add a
  patch-notes entry, and append a knowledge-log summary with citations.
- Timestamps must be real. Capture the current time in America/New_York when
  drafting patch-note and workplan updates, and include the corresponding UTC
  time in knowledge-log or brains entries. Use the commands that match your
  platform:

  - **Windows PowerShell**

    ```powershell
    [System.TimeZoneInfo]::ConvertTimeBySystemTimeZoneId([DateTime]::UtcNow,"Eastern Standard Time").ToString("o")
    (Get-Date).ToUniversalTime().ToString("o")
    ```

  - **macOS/Linux shells**

    ```bash
    TZ=America/New_York date --iso-8601=seconds
    date -u --iso-8601=seconds
    ```

  - **Python fallback (any platform)**

    ```bash
    python - <<'PY'
    from datetime import UTC, datetime
    import zoneinfo

    ny = zoneinfo.ZoneInfo("America/New_York")
    print(datetime.now(ny).isoformat())
    print(datetime.now(UTC).isoformat())
    PY
    ```

- When adding resources, cross-link them in `docs/link_collection.md` and note
  provenance (DOIs/URLs) so future agents can revalidate the source.
- Keep the workplan and backlog honest. Close completed checkboxes, record QA
  runs (ruff/mypy/pytest) with timestamps, and surface new ideas in the
  brainstorming queue before promoting them to committed work.

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
