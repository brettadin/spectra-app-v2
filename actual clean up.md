**Guiding Principles**
- Bold minimalism: prioritize clarity, remove cruft, keep what users need.
- Canon above all: nm storage, display-time conversions; no mutating data.
- Documentation-first: every change updates docs + patch notes with real ET/UTC timestamps.
- Atomic, reversible steps: small PRs (<~300 LOC) with tests and redirects.
- Don’t break runtime: validate with pytest + headless UI smoke runs.
- Path indirection: route at-rest data via path aliases; never hardcode moving folders.
- keep and eye out for additional changes as you work. 
- before you start going through and deleteting/moving things, ask for manual verififcation for each file/folder. and explain what it does, why it does it, where it is, where its going, why youre doing that. this is to make sure your changes are in line with the human agents requests. You will provide a quick, user friendly list for this reports to the user can easily reference each suggestion. 
- when you make changes to code/file structure, you will update your to that file/folder in appropriate documentation. both in patch notes and in folder/documentation directories.
- ALL CHANGES YOU MAKE NEED TO BE FUTURE PROOF. So like, if we make changes to a document or file or whatever. any time it is referenced we need to update that information as well. dont lose track of functionality and logic. this codebase will be worked on primarily humans in the near future. So think of ease of access, clear and defined comments for code base/structure. Logical/easy to use. Clean and organized. Help future coders to the best of your abilities with clear and descriptive changes/comments/documentation. 

**Target Structure**
- app/: core source, PySide6 UI + services
  - app/services/: business logic only (ingest, units, overlay, provenance, math, remote, store)
  - app/ui/: widgets, panes, panels, theme/style config
  - app/data/: bundled reference datasets only (kept small, curated)
  - app/utils/: helpers (error handling, analysis)
  - app/workers/: thread/async helpers
- storage/: data at rest (aliases resolve paths)
  - storage/cache/: cached downloads (was downloads/)
  - storage/exports/: export artifacts (was exports/)
  - storage/curated/: large demo/fixtures (trim or move heavy samples/)
- docs/: single canonical documentation tree
  - docs/user/: user guides (in-app docs pull only from here)
  - docs/specs/: stable contracts, schemas, APIs
  - docs/reviews/: workplans, cleanup plan, PR checklists
  - docs/history/: patch notes, knowledge logs, dated history
  - docs/brains/: architectural decisions
  - docs/atlas/: domain knowledge (spectroscopy guides)
  - docs/dev/: developer how-tos, worklogs, QA checklists
- tests/: all tests (migrate root test_*.py files here)
- samples/: small sample data only (move large/long-lived datasets to storage/curated)
- examples/: runnable examples and scripts
- packaging/: build/distribution tooling
- reports/: fold into docs/ (taxonomy below)
- root: README.md, requirements.txt, environment.yml, pyproject.toml, sitecustomize.py, RunSpectraApp*.cmd

**Folder Consolidation Rules**
- downloads/ → storage/cache/ (update code + docs references; add alias)
- exports/ → storage/exports/ (preserve internal subdirs; add alias)
- samples/ large content → storage/curated/; keep samples/ for tiny demos
- reports/ → docs/history/ (historical), docs/reviews/ (planning), or docs/dev/ (developer notes) depending on content
- Root-level tests (e.g., test_*.py) → tests/
- Stray root docs (e.g., IR_EXPANSION_SUMMARY.md, IMPLEMENTATION_SUMMARY.md, HOUSEKEEPING_PLAN.md, goals.txt) → absorb into docs per taxonomy or merge into workplan/history; delete duplicates
- patch.patch and any abandoned scaffolds → delete if subsumed by PR history or specs

**Naming & Taxonomy**
- Files: snake_case for Python, hyphenated lowercase for docs where appropriate; keep `.md` titles matching nav intent.
- Dirs: pluralized and descriptive (services, utils, tests, specs).
- QSettings: namespaced keys with consistent prefixes (ui/*, palette/*, plot/*, persistence/*).
- Paths: resolve `storage://cache` and `storage://exports` centrally; never hardcode storage absolutes.
- Themes: themes.py registry; names are stable keys used in settings and menu.

**Code Hygiene Targets**
- Eliminate dead imports and unused modules (safe remove with grep coverage).
- Ensure every public API has docstrings with expected inputs/outputs; module headers describe role.
- Consolidate duplicate helper logic; avoid cross-layer coupling (UI never performs business logic).
- Centralize constants in constants.py where shared across modules (e.g., units, QSettings keys).
- Normalize error handling with `ui_action` decorator for user-facing actions.
- Align logging: channelized messages via app logger; keep UI logging non-blocking.

**Documentation Cleanup**
- Single source: docs/user is the only in-app surfaced content.
- Update INDEX.md to reflect the new layout.
- Add redirect stubs for moved guides (short Markdown pointers).
- Reconcile reports/ content:
  - Historical recaps → docs/history/
  - Work tracking → docs/reviews/
  - Developer notes → docs/dev/
- Refresh all user guides (importing, plot tools, units, remote data) for accuracy.
- Add a cleanup consolidation plan file in docs/reviews/ and keep it as the canonical tracker.

**Process & Safety**
- Branching: create a dedicated cleanup branch.
- Migrations via git mv: preserve history; move in phases (per domain).
- Redirects: add Markdown pointers for moved docs to avoid broken links.
- Path alias helper: implement central resolver (Python + docs guidance).
- Testing gates:
  - Run pytest locally after each phase
  - Run headless UI smoke (`QT_QPA_PLATFORM=offscreen`) for main flows
  - Basic manual run: Light/Dark themes, import, switch units, export
- Patch notes and knowledge logging: add entries with real ET/UTC timestamps.

**Phased Execution Plan**
- Phase 1: Plan and guardrails
  - Confirm cleanup branch; record intent in cleanup_consolidation_plan.md
  - Freeze external-facing behavior; no feature changes
- Phase 2: Storage consolidation
  - Add path alias helper (storage://cache, storage://exports)
  - Move downloads/ → storage/cache; exports/ → storage/exports; update code + docs
  - Verify ingest, remote downloads, export bundles
- Phase 3: Tests and samples
  - Move root-level tests (test_*.py) → tests/
  - Trim samples/ and relocate heavy assets to storage/curated; update docs
- Phase 4: Docs taxonomy
  - Migrate reports/ content into docs/ per taxonomy; add redirects
  - Normalize user/dev/history/brains/reviews layout and update INDEX.md
- Phase 5: Code hygiene and naming
  - Remove strays (patch.patch, stale scaffolds); consolidate constants and docstrings
  - Run dead-code sweep; apply minimal, safe refactors only
- Phase 6: Final verification and housekeeping
  - pytest; offscreen UI smoke; manual runs
  - Update patch notes; knowledge log; workplan checkbox updates
  - Open PR with checklist and mapping documentation

**Acceptance Criteria**
- Paths:
  - No references to old downloads/ or exports/ paths remain in code/docs.
  - Path aliases resolve correctly across OSes; UI can run cold.
- Tests:
  - All tests pass post-migration; smoke workflow runs headlessly.
- Docs:
  - In-app docs point only to docs/user; INDEX.md up-to-date.
  - Redirect stubs working; no broken internal links in docs.
- Code:
  - No runtime regressions: ingest, theme switch, NIST overlays, math, export OK.
- Repo hygiene:
  - No stray files; clear directory naming; root is decluttered.

**Agent Playbook (Do-Until-Done)**
- Before starting:
  - Create branch `cleanup/<short-scope>`; timestamp entry in worklog and PATCH_NOTES.md
- For each phase:
  - Draft mapping (current → target) in the cleanup plan
  - Apply `git mv` changes; update references in code and docs
  - Run `pytest -q --maxfail=1`
  - Headless UI smoke: run `QT_QPA_PLATFORM=offscreen pytest tests/test_smoke_workflow.py`
  - Manual run locally: `python -m app.main` (light/dark themes; ingest; export)
  - Update INDEX.md + redirect stubs
  - Append to PATCH_NOTES.md and knowledge log with ET/UTC
- Don’t proceed to next phase until green on tests + smoke
- Keep each PR under ~300 LOC; link mapping and test results in description

**Stray Files Likely to Triage**
- Root-level tests: move to tests (e.g., test_exoplanet_manual.py, test_global_normalization.py, etc.)
- patch.patch: delete if superseded by VCS history
- Root planning docs (goals.txt, HOUSEKEEPING_PLAN.md, IMPLEMENTATION_SUMMARY.md, IR_EXPANSION_SUMMARY.md): migrate into reviews or history (as appropriate), then remove originals
- reports contents: rehome into history, reviews, or dev

**Commands agents will use**
- Create branch:
```pwsh
git checkout -b cleanup/storage-and-path-aliases
```
- Run tests:
```pwsh
pytest -q --maxfail=1
```
- Headless smoke:
```pwsh
$env:QT_QPA_PLATFORM="offscreen"
pytest -q tests/test_smoke_workflow.py
Remove-Item Env:QT_QPA_PLATFORM
```
- Manual run:
```pwsh
python -m app.main
```
