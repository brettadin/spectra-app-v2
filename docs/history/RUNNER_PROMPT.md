# RUNNER PROMPT — Iteration Loop (docs-first, test-first)

**Repo:** `C:\Code\spectra-app-beta`

**Start every loop by reading**:
- `docs/history/MASTER PROMPT.md`
- Latest entries in `docs/brains/`
- `docs/reviews/workplan.md` and `docs/reviews/workplan_backlog.md`
- Relevant user/dev guides for the feature under consideration

## CI Loop (repeat until work is delivered)
1. **PLAN**
   - Update `docs/reviews/workplan.md` with precise, atomic tasks and acceptance
     criteria.
   - For broad changes, draft `docs/rfc/RFC-YYYYMMDD-bN.md` (problem, proposal,
     tests, risks, rollback).
2. **BRANCH**
   - `feature/YYMMDD-bN-shortname`
3. **DOCS-FIRST IMPLEMENTATION**
   - Update user and developer docs before or alongside code.
   - Touch only the module that owns the behaviour.
   - Keep Atlas rules in mind: units canon, calibration honesty, provenance
     completeness, explainable identification, UI clarity.
4. **QUALITY GATES**
   ```bash
   ruff check app tests
   mypy app --ignore-missing-imports
   pytest -q --maxfail=1 --disable-warnings
   ```
   - Run targeted suites (`pytest -k roundtrip`, `pytest -k ui_contract`) when
     touching exports or UI contracts.
   - Validate manifests with `tools/validate_manifest.py` whenever an export or
     provenance change is introduced.
5. **LOG & SHIP**
   - Update `docs/history/PATCH_NOTES.md` and `docs/history/KNOWLEDGE_LOG.md`
     using real America/New_York timestamps (ISO-8601 with offset).
   - Record QA runs (command + timestamp) in the workplan.
   - Verify the backlog reflects new discoveries or follow-ups.
   - Open a PR summarising behaviour changes and executed tests.

Stay within the small-PR budget (≈300 LOC), keep the tree text-only, and ensure
provenance/units/UI principles remain intact.
