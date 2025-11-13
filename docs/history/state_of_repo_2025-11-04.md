# State of the Repo — 2025‑11‑04

This report summarizes the current status of the Spectra app repository: what’s done, what’s in‑flight, quick wins, priorities, and risks. It’s intended to guide the next 1–2 weeks of development.

## Snapshot

- App/UI
  - Stable normalization controls (per‑spectrum and global), unit conversions, and plot LOD.
  - Remote Data and Reference overlays guarded with async handling and documentation.
  - New analysis utilities in `app/utils/analysis.py` (peaks, centroid, FWHM, noise sigma, SNR) with tests.
- Architecture
  - Path alias helper (`app/utils/path_alias.py`) and tests are in; rollout through services/export pending.
- Documentation
  - Central index (`docs/INDEX.md`), repo inventory (`docs/repo_inventory.md`).
  - Fresh Eyes review workflow (guide, PR template, inbox).
  - Atlas integration plan (`docs/reviews/atlas_integration_plan.md`), anchors index (`docs/atlas/anchors.yml`), updated contributor guidance.
  - Workplan and backlog are pruned, focused, and current.
- Tests/CI
  - New analysis tests pass; normalization/math subset green locally. Link‑checker CI is planned.
- Packaging
  - Windows build notes and PyInstaller spec present; no known breakages.

## Recent changes (highlights)

- Analysis foundations landed (peak detection near cursor, centroid, FWHM, noise sigma, SNR) with synthetic‑data tests.
- Atlas made actionable: plan doc, anchors registry, contributor workflow; linked from the docs index.
- Backlog/workplan cleaned and modernized; only actionable items remain.

## Quick wins (next few days)

- Wire analysis into UI
  - “Find peak near cursor” and “Jump to max” using `peak_near`.
  - Small readout for centroid/FWHM over selection; export measurements.
- Path alias rollout (targeted)
  - Replace raw paths in LocalStore/export with `storage://` aliases; update tests.
- Docs polish
  - Add “Further reading” links from user guides to Atlas anchors.
  - Add link‑checker CI to guard docs/Atlas cross‑refs.
- Dataset hygiene
  - Move large static bundles to `storage://curated` with README stubs and provenance notes.

## Priorities (1–2 weeks)

1. Identification stack (phase 1)
   - Peak‑list service (prominence/width), basic scoring vs. reference ranges, explainable score cards scaffold.
   - Tests on synthetic + samples; export identified peaks into manifests.
2. Calibration manager (scaffold)
   - Target FWHM + RV shift controls, σ propagation; small dock; document the contract.
3. Export/view parity
   - Ensure manifests capture all view state; add replay test.
4. Path aliases in core services
   - Adopt aliases in LocalStore/export centers; update docs/tests.

## Risks and mitigations

- Optional deps (astroquery/astropy/pandas): continue to guard providers and degrade gracefully.
- Analysis footprint: NumPy‑only by design (no SciPy) for phase 1; revisit if fitting/filters needed.
- Alias rollout touches many code paths: do it incrementally with tests.

## Quality gates

- Build: PASS (no build pipeline changes this week).
- Lint/Typecheck: PASS for new modules/tests.
- Tests: PASS for new analysis tests and normalization/math subset; full run on demand.

## Links

- Index: `docs/INDEX.md`
- Backlog (current): `docs/reviews/workplan_backlog.md`
- Workplan (current batch): `docs/reviews/workplan.md`
- Atlas plan: `docs/reviews/atlas_integration_plan.md`
- Atlas anchors: `docs/atlas/anchors.yml`
- Analysis utils: `app/utils/analysis.py`
- Analysis tests: `tests/test_analysis.py`
