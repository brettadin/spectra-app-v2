
# Workplan Backlog (Pruned Nov 2025)

This backlog tracks only actionable, not-yet-done initiatives. Completed, obsolete, or superseded items have been removed or archived. For batch history, see the archive or `workplan.md`.


## Current Actionable Backlog

- [ ] Atlas integration: finalize anchors, mapping, and cross-links
  - Add anchor appendix and guidance to `docs/atlas/README.md`
  - Create `docs/atlas/anchors.yml` (seed topics; optional)
  - Add “Further reading” links in user guides to Atlas (in progress)
  - Add inline UI `?` links to Docs pane at anchors
- [ ] PathAlias rollout: refactor LocalStore and export centers to use path aliases; update tests
- [ ] Commenting/documentation pass: adopt `COMMENTING_GUIDE.md` in `app/services/` and `app/ui/`
- [ ] Link checker CI: add a docs link-check step to CI to guard against broken links as docs are consolidated/moved
- [ ] Consolidation: move large datasets to `storage/curated/`, update paths, and add README stubs for redirects
- [ ] UI/UX: add inline UI `?` links to Docs pane at Atlas anchors (phase 2 of Atlas integration)
- [ ] Continue modular documentation and review loop (Fresh Eyes reviews, inbox triage, backlog promotion)
- [ ] Calibration manager service & dock: FWHM, RV, σ propagation, manifest serialization, and tests
- [ ] Uncertainty ribbons: support import, math ops, and exports with propagated σ arrays
- [ ] Peak/scoring/identification: peak lists, cross-correlation, explainable weights, score cards, manifest logging
- [ ] Content-addressed LocalStore: sha256-named blobs, GC tool, manifest-indexed truth
- [ ] Export parity audit: ensure manifests capture all view state, round-trip replay test
- [ ] Manifest validator CI: expand coverage, enforce schema v1.2.0
- [ ] Library enhancements: faceted browsing, manifest/log actions, re-export
- [ ] IR functional-group ML integration: see `docs/specs/ml_functional_group_prediction.md` and roadmap doc

For batch history and long-form roadmaps, see `workplan.md` and referenced roadmap docs.
