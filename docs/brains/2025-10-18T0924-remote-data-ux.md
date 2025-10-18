# Remote Data UX: provider availability and knowledge-log hygiene
_recorded: 2025-10-18T09:24:00-04:00 (America/New_York)_

## Context

Remote catalogue integration (NIST ASD, MAST) exposes optional-dependency
surface area (requests, astroquery). UX decisions about whether controls are
enabled or disabled affect discoverability and perceived responsiveness.

Affected files:
- `app/ui/remote_data_dialog.py`
- `app/services/remote_data_service.py`
- `app/services/knowledge_log_service.py`
- `docs/history/KNOWLEDGE_LOG.md`
- `docs/history/PATCH_NOTES.md`

## Decisions

- Keep provider combo and search edit enabled so users can select providers and
  compose queries even when optional dependencies are missing. Annotate
  unavailable providers as `(dependencies missing)` and only enable the Search
  button for providers whose dependencies are present.
- Maintain guarded imports in `RemoteDataService` and ensure `providers()` and
  `unavailable_providers()` provide clear signals to the UI.
- Update knowledge-log writing so intentional imports persist when requested;
  runtime-only components remain respected by default.

## Follow-up

- Add a tooltip or inline help for annotated providers explaining how to
  install optional dependencies (e.g. `pip install astroquery`).
- Consider adding an automatic check button to attempt installing optional
  dependencies in the dev environment (opt-in only).
- Run a full `pytest` suite to ensure the change doesn't regress existing tests
  that mock provider availability.
