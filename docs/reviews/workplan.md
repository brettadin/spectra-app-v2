# Workplan Overview

This document tracks feature batches, validation status, and outstanding backlog items for the Spectra app.

## Batch 15 (2025-11-02) — In Progress

### Scope

- [ ] Documentation pass: update Remote Data (tab in Inspector), Quickstart, Plot tools (dataset removal toolbar), and shortcut summary
- [ ] History panel UX: add filter + toolbar (Refresh, Copy, Export) and wire actions
- [ ] Calibration service: clarify goals, add minimal spec and service scaffold
- [ ] Shortcut audit: add logical, non-intrusive defaults and document them
 - [ ] Entity previews (backlog): optional image/metadata card for the focused library entity (planet/star/molecule) when a single item is selected, gated to avoid clutter; persisted in Library metadata

### QA Log

# Workplan Overview (Pruned Nov 2025)

This document tracks the current feature batch, validation status, and a summary of recent completions. Old batches and long-form roadmaps have been archived or moved to referenced docs for clarity.

## Current Batch (2025-11-02) — In Progress

### Scope

- [ ] Documentation pass: update Remote Data (tab in Inspector), Quickstart, Plot tools (dataset removal toolbar), and shortcut summary
- [ ] History panel UX: add filter + toolbar (Refresh, Copy, Export) and wire actions
- [ ] Calibration service: clarify goals, add minimal spec and service scaffold
- [ ] Shortcut audit: add logical, non-intrusive defaults and document them
- [ ] Entity previews (backlog): optional image/metadata card for the focused library entity (planet/star/molecule) when a single item is selected, gated to avoid clutter; persisted in Library metadata

### QA Log

- 2025-11-02: ✅ `pytest -q` (94 passed, 29 skipped)

---

## Recently Completed

- Documented the repository inventory, updated patch notes, and refreshed the knowledge log for provenance
- Authored `docs/app_capabilities.md` as a comprehensive capability atlas
- Decoupled DatasetPanel and ReferencePanel from main_window, moved UI logic into panels, validated with full test suite
- Added dataset removal toolbar to Data dock with "Remove Selected" and "Clear All" buttons, confirmation dialog, and regression tests
- Refreshed onboarding docs and dependency prerequisites
- Patched numpy bootstrap for pip recursion, added Solar System quick-picks, and extended regression coverage
- Hardened knowledge log, improved Remote Data dialog, and consolidated Datasets/Library views

---

## Batch Archive

All previous batches, detailed QA logs, and long-form roadmaps have been archived for clarity. For full history, see the batch archive or request a summary from the agent.
- [ ] Implement contextual rules for group interactions (e.g., COOH = broad O-H + sharp C=O)
- [ ] Add UI panel for displaying predictions with evidence
- [ ] Write unit tests for peak detection on synthetic spectra
- [ ] Write integration tests on known compounds (benzoic acid, acetone, ethanol)
- [ ] Performance validation: 80% precision, 70% recall target
- [ ] Documentation: User guide for rule-based functional group analysis

### Phase 2: Data Collection & Preparation (6 weeks)
- [ ] Script to download NIST WebBook IR spectra (~18K spectra with SMILES)
- [ ] Script to download SDBS IR spectra (~34K spectra with structures)
- [ ] Implement RDKit-based label generation (parse SMILES → functional group presence/absence)
- [ ] Preprocess spectra: baseline correction, normalization, resampling to 4000-400 cm⁻¹
- [ ] Implement data augmentation: baseline shifts, noise, spectral shifting (±5 cm⁻¹), intensity scaling
- [ ] Create train/validation/test splits (60/20/20)
- [ ] Store dataset in HDF5/Parquet format with metadata and provenance
- [ ] Documentation: Data preparation pipeline and dataset schema

### Phase 3: Neural Network Prototype (8 weeks)
- [ ] Implement 1D CNN architecture with residual connections
- [ ] Add multi-head self-attention mechanism for diagnostic region focus
- [ ] Implement multi-label classification output (sigmoid activation)
- [ ] Train initial model on subset (5K spectra) for proof-of-concept
- [ ] Tune hyperparameters (learning rate, batch size, regularization)
- [ ] Train full model on complete dataset (~52K spectra)
- [ ] Evaluate on hold-out test set: 90% precision, 85% recall target
- [ ] Implement model persistence and loading
- [ ] Create prediction API for integration
- [ ] Documentation: Model architecture, training procedure, performance metrics

### Phase 4: UI Integration (4 weeks)
- [ ] Create "Analyze Functional Groups" button/panel in UI
- [ ] Display predictions with confidence bars and color-coded groups
- [ ] Show supporting evidence: diagnostic peaks, attention maps, rule contributions
- [ ] Implement annotated spectrum view with color-coded regions
- [ ] Add export functionality for predictions (CSV/JSON with provenance)
- [ ] Implement batch processing for multiple spectra
- [ ] Write Qt integration tests for analysis panel
- [ ] Performance validation: <500ms GPU, <2s CPU latency
- [ ] Documentation: User guide for ML-powered functional group analysis

### Phase 5: Hybrid Ensemble (4 weeks)
- [ ] Implement ensemble prediction logic combining rule-based and neural network
- [ ] Tune ensemble weights (default 40% rules, 60% neural; user-adjustable)
- [ ] Add interpretability features: show method contribution per prediction
- [ ] Implement comparison mode: side-by-side rule-based vs neural predictions
- [ ] Add user feedback collection for active learning
- [ ] Performance validation: 92% precision, 88% recall target
- [ ] Write comprehensive test suite for ensemble system
- [ ] Documentation: Ensemble methodology, interpretability guide, user feedback workflow

### Long-Term Enhancements (6+ months)
- [ ] Active learning: user corrections improve model continuously
- [ ] Multi-modal fusion: combine IR with NMR, MS, UV-Vis for compound-level identification
- [ ] Transfer learning: pre-train on large databases, fine-tune for specific domains
- [ ] Bayesian uncertainty: upgrade to probabilistic neural networks for better confidence estimates
- [ ] Compound suggestion: from functional groups + molecular formula → suggest structures
- [ ] Literature integration: link predictions to reference papers and spectral databases

**Dependencies to Add for ML Phases**:
```toml
rdkit >= 2023.3.1        # Phase 2: Molecular structure parsing for label generation
tensorflow >= 2.13.0     # Phase 3: Neural network training/inference (or pytorch)
scikit-learn >= 1.3.0    # Phase 2-3: Preprocessing, metrics, cross-validation
h5py >= 3.9.0            # Phase 2: Efficient dataset storage
```

**Documentation References**:
- Extended database: `app/data/reference/ir_functional_groups_extended.json`
- ML design: `docs/specs/ml_functional_group_prediction.md`
- Architectural decision: `docs/brains/2025-10-25T0230-ir-ml-integration.md`
- User guide updates: `docs/user/reference_data.md`
- Atlas coverage: Chapter 1 (§3.1a), Chapter 7 (§7a)

## Batch 9 (2025-10-15)

- [x] Add reproducible build scripts for NIST hydrogen lines, IR functional groups, and JWST quick-look spectra.
- [x] Propagate provenance (generator, retrieval timestamps, planned MAST URIs) into the reference JSON assets and inspector UI.
- [x] Expand spectroscopy documentation (primer, reference guide) to explain the provenance and regeneration flow.

### Batch 9 QA Log

- 2025-10-15: ✅ `ruff check app tests`
- 2025-10-15: ✅ `mypy app --ignore-missing-imports`
- 2025-10-15: ✅ `pytest -q --maxfail=1 --disable-warnings`

## Batch 8 (2025-10-15)

- [x] Bundle NIST hydrogen spectral lines and IR functional group references into the application data store.
- [x] Stage JWST quick-look spectra (WASP-96 b, Jupiter, Mars, Neptune, HD 84406) with resolution metadata for offline use.
- [x] Surface the reference library through a new Inspector tab and publish spectroscopy/JWST documentation.

### Batch 8 QA Log

- 2025-10-15: ✅ `ruff check app tests`
- 2025-10-15: ✅ `mypy app --ignore-missing-imports`
- 2025-10-15: ✅ `pytest -q --maxfail=1 --disable-warnings`

## Batch 7 (2025-10-15)

- [x] Honour wavelength/wavenumber units embedded in headers to prevent swapped axes.
- [x] Record column-selection rationale in importer metadata with regression coverage.
- [x] Update user documentation and patch notes to describe the new safeguards.

### Batch 7 QA Log

- 2025-10-15: ✅ `ruff check app tests`
- 2025-10-15: ✅ `mypy app --ignore-missing-imports`
- 2025-10-15: ✅ `pytest -q --maxfail=1 --disable-warnings`

## Batch 6 (2025-10-15)

- [x] Correct importer axis selection when intensity columns precede wavelength data.
- [x] Wire the Normalize toolbar to overlay scaling (None/Max/Area) and document the behaviour.

### Batch 6 QA Log

- 2025-10-15: ✅ `ruff check app tests`
- 2025-10-15: ✅ `mypy app --ignore-missing-imports`
- 2025-10-15: ✅ `pytest -q --maxfail=1 --disable-warnings`

## Batch 5 (2025-10-15)

- [x] Teach the CSV/TXT importer to recover wavelength/intensity pairs from messy reports with heuristic unit detection.
- [x] Surface user documentation inside the app via a Docs inspector tab and Help menu entry.

### Batch 5 QA Log

- 2025-10-15: ✅ `ruff check app tests`
- 2025-10-15: ✅ `mypy app --ignore-missing-imports`
- 2025-10-15: ✅ `pytest -q --maxfail=1 --disable-warnings`

## Batch 4 (2025-10-15)

- [x] Harden provenance export bundles by copying sources and per-spectrum CSVs with regression coverage.

### Batch 4 QA Log

- 2025-10-15: ✅ `pytest -q`

# 2025-10-20 — Remote data regression checks

- 2025-10-20: ✅ `pytest`
- 2025-10-21: ✅ `pytest tests/test_remote_data_dialog.py tests/test_remote_data_service.py`

## Batch 3 (2025-10-14)

- [x] Draft a user quickstart walkthrough covering launch → ingest → unit toggle → export.
- [x] Author a units & conversions reference with idempotency callouts.
- [x] Document plot interaction tools and LOD expectations.
- [x] Expand the importing guide with a provenance export appendix.

### Batch 3 QA Log

- 2025-10-14: ✅ `pytest -q`

## Batch 2 (2025-10-14)

- [x] Close out the Batch 1 smoke-check and capture the state of CI gates on the latest branch.
- [x] Inventory pending documentation deltas before the next feature work.

### Batch 2 QA Log

- 2025-10-14: ✅ `ruff check app tests`
- 2025-10-14: ✅ `mypy app --ignore-missing-imports`
- 2025-10-14: ✅ `pytest -q --maxfail=1 --disable-warnings`

## Batch 1 (2025-10-14)

- [x] Seed tiny fixtures for tests (`tests/data/mini.*`).
- [x] Lock in unit round-trip behaviour and implement the LocalStore service with cache index tests.
- [x] Ensure provenance export emits a manifest bundle and guard plot performance with an LOD cap test.
- [x] Update user/developer documentation for importing and the ingest pipeline.
- [x] Run lint/type/test suites locally and smoke-check app launch, CSV/FITS ingest, unit toggle, and export manifest.

### Batch 1 QA Log

- 2025-10-14: ✅ `ruff check app tests`
- 2025-10-14: ✅ `mypy app --ignore-missing-imports`
- 2025-10-14: ✅ `pytest -q --maxfail=1 --disable-warnings`
- 2025-10-14: ⚠️ `pytest -q --maxfail=1 --disable-warnings --cov=app --cov-report=term-missing` (fails: coverage plugin unavailable)
- 2025-10-14: ✅ `pip install -r requirements.txt`
