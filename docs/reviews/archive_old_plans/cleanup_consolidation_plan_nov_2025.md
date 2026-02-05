# Cleanup & Consolidation Master Plan (Nov 4, 2025)

This living plan enumerates every major path, folder, and document family in the repo; proposes a consolidated, logical structure; and defines concrete, staged actions to remove redundancy, migrate content, and keep future agents aligned. It covers code, docs (user/developer/history), data locations (downloads/exports/samples), UI design assets, references, patches, and agent operations.

Status: Draft v1 (ready for execution in phases). Owners: current agents. Timestamps in ET.

---

## Guiding principles
- Canonical maps: One obvious place for each concept. Index and redirects updated when content moves.
- Non-destructive migrations: Keep git history; add stubs/redirect notes in old locations during transition windows.
- Tests/docs-first: Move docs safely before code; run tests between steps; no broken imports or links.
- Scientific rigor: Preserve provenance, units, and citations throughout.

### Modular paths via aliases
Use logical path aliases in code and docs to decouple plans from physical folders. See `docs/specs/path_aliases.md`.
Aliases: `storage://cache`, `storage://exports`, `storage://curated`, and `samples://`.
Code MUST resolve via a central helper (PathAlias); docs SHOULD reference aliases parenthetically alongside current paths during migration.

## Current top-level structure (snapshot)
- app/ … runtime code: UI widgets (ui/), services/, utils/, workers/, data/ (bundled reference JSON)
- docs/ … user guides, developer notes, specs, reviews, atlas/brains/history, worklogs
- downloads/ … cache store (files/, _incoming/, _cache/, index.json)
- exports/ … previous manifest/CSV/plot bundles
- packaging/ … PyInstaller/MSIX config
- reports/ … audits, roadmap, matrices
- samples/ … mixed: small examples (should remain) + large real data (should move out or be treated as curated fixtures)
- tests/ … unit/integration/manual harnesses
- spectra-data/ … research notes separate from app repo (OK but cross-reference)

## Target structure (consolidated)
- app/ (unchanged high-level)
  - ui/ … MainWindow, panels, plot; Qt-only logic
  - services/ … ingest, units, overlays, remote data, reference library, calibration
  - utils/, workers/, data/ (bundled references only)
- docs/
  - user/ … app-facing guides only
  - dev/ … worklog/, housekeeping/, engineering docs
  - specs/ … technical specifications (units, UI contract, packaging, analysis toolkit)
  - reviews/ … workplan, cleanup plan, audits
  - history/ … patch notes, knowledge log, archives
  - atlas/, brains/ … research narratives and design notes
- storage/ (new umbrella; replaces ad-hoc data sprawl; see migration)
  - cache/ … previously downloads/ (store index + files/_cache/_incoming)
  - exports/ … previously exports/ (manifest bundles, plots)
  - curated/ … large curated datasets used in tests/demos (replaces oversize content under samples/)
- samples/ … kept small and strictly for quick-start examples (≤ a few MB)
- packaging/, reports/, tools/ … unchanged

Alias mapping (informative):
- storage://cache → storage/cache/ (compat: downloads/)
- storage://exports → storage/exports/ (compat: exports/)
- storage://curated → storage/curated/
- samples:// → samples/

## Migration map (existing → target)
- downloads/ → storage/cache/
- exports/ → storage/exports/
- samples/ (large real data: SOLAR SYSTEM/, fits data/, IR data/, lamp data/, many planet tables) → storage/curated/
- samples/ (keep): sample_manifest.json, sample_spectrum.csv, sample_transmittance.csv, a few tiny files under calibration_standards/
- docs duplications
  - Patch notes: keep canonical in docs/history/PATCH_NOTES.md; remove/redirect any duplicates under docs/user/patch_notes.md
  - App capabilities: archived; link only from INDEX; no edits
- Agent manuals: keep AGENTS.md root; add short “Consolidation Rules” section pointing to this plan

## Documentation consolidation
- Single map: docs/INDEX.md remains the canonical hub; ensure all sections link to only one living copy of each topic.
- Backlog routing: Add all consolidation tasks to docs/reviews/workplan_backlog.md; promote to workplan.md when scheduled.
- Developer docs
  - Keep specs/ for stable contracts (units, UI, packaging, analysis toolkit)
  - Keep dev/ for worklogs, housekeeping, engineering procedures
  - reviews/ for orchestration: workplan, cleanup plan, audits
- User docs
  - user/ hosts guides referenced in Help menu; avoid history/policy content here

## Storage & paths policy (definitive)
- storage/cache/
  - _incoming/ transient downloads
  - files/ content-addressed blobs; index.json maps metadata
  - _cache/ submodules (e.g., line_lists/ for NIST)
- storage/exports/
  - Manifest bundles, wide/composite CSVs, plot images, logs
- storage/curated/
  - Large curated data for demos/regression (plan size limits; avoid committing giant binaries)
- samples/
  - Quick-start only; tiny CSVs/FITS; referenced by user quickstart

Acceptance criteria: At the end of migration, samples/ is ≤ few MB; downloads/ and exports/ are gone (replaced by storage/ subfolders); importer and UI paths updated; docs reflect new locations; tests green.

Alias acceptance: A repo-wide search for `downloads/` or `exports/` in code yields no live references (archives/stubs allowed). Docs
prefer alias notation.

## UI and functionality notes (to align with consolidation)
- Plot: live cursor readout (done). Planned: pre-scale y readout when Y-scale non-linear; copy coordinates; snap-to-peak toggle.
- Peak helpers: Find local peak near cursor; Jump to max; measurement pane with centroid/FWHM/EW; exportable results.
- Overlays: NIST cache (done); clear button (done); planned: overlay tooltips with line meta; color legend for pinned sets; quick hide/show.
- Normalization: Global/per-spectrum toggle (done); ensure status badge in readout.
- Calibration: Display-time FWHM and RV (done); planned manager dock with presets, σ propagation.

## Redundancy inventory (high-level)
- Duplicate/archived docs: patch notes duplicates, legacy summaries, atlas copies → keep canonical + redirect stub.
- Samples vs curated: non-sample large data in samples/ → storage/curated/
- Reference docs split across user/dev: migrate decisions/roadmaps under reviews/; keep user guides clean.

## Phased execution plan
- Phase 0 — Prep (1 day)
  - Freeze doc links; land this plan; add link to INDEX; add backlog items
- Phase 1 — Storage renames (safe) (1–2 days)
  - Create storage/{cache,exports,curated}; move directories; add redirect stubs (README pointers) in old roots
  - Update app paths (LocalStore default path, export centers) to new locations; run tests
  - Introduce PathAlias helper; switch LocalStore/export centers to alias resolution (backward-compatible defaults)
- Phase 2 — Samples diet (1 day)
  - Move heavy samples to storage/curated/; update quickstart/user docs to limited examples
- Phase 3 — Docs consolidation (ongoing)
  - Remove duplicates; add redirects; update INDEX and links
- Phase 4 — Cleanup & delete old roots (after soak)
  - Remove downloads/ and exports/ stubs after one milestone; ensure CI and docs fully aligned
  - Remove compatibility code in PathAlias; lock aliases to storage/*

## Detailed task backlog (summary; mirrored in workplan_backlog.md)
- Create storage/ tree; adjust LocalStore base paths
- Migrate downloads/ → storage/cache/, exports/ → storage/exports/
- Migrate large samples → storage/curated/; diet samples/
- Update docs (quickstart, importing, remote_data, plot_tools) with new paths
- Remove docs/user/patch_notes.md duplicate; link to history/PATCH_NOTES.md
- Add status badges in status bar readout (norm mode, global flag) (QOL)
- Implement Jump to max; find-peak near cursor; copy coords (QOL)
- Add overlay tooltips for NIST lines (QOL)
- Calibration Manager dock & σ propagation plan
 - Implement PathAlias registry; add environment overrides for CI; unit tests for resolution
 - Refactor tests/fixtures to use samples:// and storage:// aliases where practical

## Risks & mitigations
- Broken links/paths → run link checker; add redirect stubs; search/replace with review
- Large repo churn → split PRs by phase; keep CI green between phases
- User disruption → patch notes + migration notes; keep help docs precise

## Ownership & handoff
- PR template: require update to this plan and to workplan_backlog.md when touching storage/docs structure.
- Agents: follow AGENTS.md; stamp ET/UTC times in worklogs; reference this plan in commit messages.

---

Appendix A — Proposed redirect stubs
- downloads/README.md → points to storage/cache/
- exports/README.md → points to storage/exports/
- samples/* heavy directories → README noting move to storage/curated/

Appendix B — Link audit checklist
- README badges/paths
- docs/INDEX.md links
- User guides: quickstart, importing, remote_data, plot_tools
- Tests referencing sample paths

