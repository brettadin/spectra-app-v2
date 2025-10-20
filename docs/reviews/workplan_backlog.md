# Workplan Backlog

This backlog tracks initiatives that require scheduling beyond the active batch.
All timestamps must use America/New_York (ISO-8601). Move items into
`workplan.md` when they enter an active sprint.

## High-priority epics

### Calibration & fidelity
- [ ] **Calibration manager service & dock**
  - Service with kernels/frames/resampling helpers
  - Dock controls for target FWHM, kernel selection, frame & RV metadata
  - Non-dismissable calibration banner + per-trace badges
  - Provenance serialization in manifest `applied_steps`
  - Tests for FWHM tolerance, RV Δλ, σ propagation, and 1e6-point performance guard
- [ ] **Uncertainty ribbons everywhere**
  - Support import, math operations, and exports with propagated σ arrays
  - Plot toggles + persistence; export parity in manifests and view state

### Identification & scoring
- [ ] **Peak, similarity, and scoring services**
  - Deterministic peak lists, cross-correlation RV search, explainable weight breakdown
  - Library of spectral catalogs (hydrogen + new species) with version hashes
- [ ] **Identification dock**
  - Catalog selection, RV grid, bandpass, peak thresholds
  - Score cards with component weights, clickable matches, manifest logging

### Data foundations
- [ ] **JWST quick-look regeneration** (requires calibrated FITS access)
- [ ] **Spectral-line catalogue expansion** (He I, O III, Fe II, etc.)
- [ ] **IR functional-group heuristics in importer axis detection**
- [ ] **Content-addressed LocalStore** with manifest cross-links and purge tooling
- [ ] **Library enhancements**
  - Faceted browsing (instrument/type)
  - Actions: open manifest, open knowledge log, re-export current view

### Provenance & replay
- [ ] **Export parity audit**
  - Ensure manifests capture view state (units, normalization, smoothing, palette, LOD, masks, calibration banner)
  - Round-trip replay test reproduces `view.png` within pixel RMSE tolerance
- [ ] **Manifest validator CI hardening**
  - Expand `tools/validate_manifest.py` coverage
  - Enforce schema v1.2.0 through `.github/workflows/provenance.yml`

### UI/UX polish
- [ ] **Snap-to-peak & brush-to-mask** interactions with persistence
- [ ] **Accessible palette presets** (colour-blind friendly, dark/light aware)
- [ ] **Teaching preset** toggling key UI hints, docs integration
- [ ] **Keybinding audit** with updated shortcuts and documentation

### Research & extensions
- [ ] **Native extension prototype** (PyO3/pybind11) for convolution/xcorr kernels
  - Optional build documented in `specs/foreign_language_integration.md`
  - Benchmarks + equivalence tests
- [ ] **Machine-learning tagging exploration**
  - Outline dataset requirements, labelling strategy, and reproducibility plan

## Documentation & knowledge alignment
- [ ] Refresh Atlas chapters to reflect brains entries and recent code
- [ ] Summarize external reviews (Pass 1–4) with actionable deltas
- [ ] Expand docs/user education sections (spectroscopy primers, provenance walkthroughs)
- [ ] Catalogue remote data dependencies (astroquery, astropy) with install paths and troubleshooting

## Monitoring
- [ ] Establish regression dashboards for importer accuracy, calibration fidelity, and identification scoring
- [ ] Track remote data availability (NIST/MAST uptime) and cache refresh cadence

Record movement of each item (scheduled, in progress, done) in the knowledge log
with ISO timestamps so the backlog remains auditable.
