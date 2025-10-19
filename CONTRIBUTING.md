# Contributing to Spectra App

This guide distils the day-to-day expectations for human and AI contributors. For historical context and extended background,
start with the documentation called out below before making any changes.

## Essential Reading

- `docs/history/MASTER_PROMPT.md` and `docs/history/RUNNER_PROMPT.md`
- `AGENTS.md` for repository-wide operating rules
- `START_HERE.md` and `README.md` for onboarding and environment details
- `docs/reviews/workplan.md` plus the pass dossiers in `docs/reviews/` when planning work

## Environment Setup

```bash
# Windows quick launch
RunSpectraApp.cmd

# Manual virtual environment (cross-platform)
python -m venv .venv
# Windows: .\.venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

Verify the install before you begin feature work:

```bash
pytest
python -m app.main
```

## Workflow Expectations

1. **Plan first** – capture your intent and acceptance criteria in `docs/reviews/workplan.md`.
2. **Branching** – create a focused branch such as `feature/<short-summary>` (humans) or `ai/<short-summary>` (AI agents).
3. **Implementation loop** – follow the PLAN → IMPLEMENT → TEST → DOCUMENT → REVIEW cadence from the RUNNER_PROMPT.
4. **Tests** – extend `tests/` alongside every behaviour change and consult `specs/testing.md` for strategy guidance.
5. **Versioning** – bump the project version in `pyproject.toml` and synchronise `ProvenanceService.app_version` in `app/services/provenance_service.py` whenever user-visible changes ship.

## Documentation & Logging

- Update user and developer documentation that describes the behaviour you touched (see `docs/user/` and `docs/dev/`).
- Record outcomes and validation in `docs/history/PATCH_NOTES.md` with real America/New_York and UTC timestamps.
- Summarise learnings, links, and provenance in `docs/history/KNOWLEDGE_LOG.md`, citing the quick-start or specs you updated.
- Cross-check the work plan, closing completed items and noting any follow-up tasks in `docs/reviews/workplan.md` or `workplan_backlog.md`.

## Submission Checklist

Before opening a pull request:

- [ ] `pytest` (and any targeted scripts) pass locally
- [ ] Documentation updates committed and cross-referenced in PATCH_NOTES and KNOWLEDGE_LOG
- [ ] Version metadata synchronised for user-facing releases
- [ ] Self-review completed against acceptance criteria and UI contracts in `specs/ui_contract.md`

PRs should link to the relevant work plan entry, include a summary of user-visible impact, and enumerate the validation steps you
ran.
