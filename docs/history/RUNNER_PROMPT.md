# RUNNER PROMPT — Autonomous Improve/Fix/Add Loop (safe, test-first)

**Repo:** `C:\Code\spectra-app-beta`  
**Start:** Read `docs\history\MASTER PROMPT.md`. Treat it as spec + acceptance criteria.

## CI Loop (repeat)

1) **PLAN**
   - Update `docs\reviews\workplan.md` (checkboxes).
   - For non-trivial changes, write `docs\rfc\RFC-YYYYMMDD-bN.md` (problem, proposal, tests, risks/rollback, Acceptance Criteria).

2) **BRANCH**  
   `improve/YYMMDD-bN-<shortname>`

3) **IMPLEMENT (small commits)**
   - Touch only the module owning the change.
   - Add code + tests together.
   - Keep unit canon, provenance, and performance budgets intact.
   - Prefer feature flags for experimental providers.

4) **QUALITY GATES**
   ```bash
   ruff check app tests
   mypy app --ignore-missing-imports
   pytest -q --maxfail=1 --disable-warnings --cov=app --cov-report=term-missing
