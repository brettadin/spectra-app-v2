# Developer Notes – Service Extension Points

## Documentation map
- `AGENTS.md` – Top-level operating manual; review before editing code or docs.
- `docs/link_collection.md` – Curated spectroscopy datasets, standards, and
  instrument handbooks. Start here when sourcing new material.
- `docs/user/*.md` – User guides (importing, remote data, reference overlays,
  plot tools). Keep behaviour changes in sync.
- `docs/dev/reference_build.md` – Scripts and manifests for regenerating the
  bundled reference assets.
- `docs/history/PATCH_NOTES.md` & `docs/history/KNOWLEDGE_LOG.md` – Chronological
  change log and distilled insights; update alongside code.
- `docs/reviews/workplan.md` + `workplan_backlog.md` – Tactical batch tracker for features/tasks. Mark progress here.
- `docs/dev/worklog/YYYY-MM-DD.md` – Daily narrative logs (what/why/how for each session). See `docs/dev/worklog/README.md`.

## Importers
- Implement `SupportsImport` protocol (`app/services/importers/base.py`) and register via `DataIngestService.register_importer`. Each importer should return `ImporterResult` with raw arrays, units, metadata, and optional `source_path`.
- Keep parsing non-destructive: do not mutate arrays; let `UnitsService.to_canonical` normalise units.

## Units & Conversions
- `UnitsService` maintains the nm / base-10 absorbance baseline. Add new units by updating `_normalise_x_unit`, `_to_canonical_wavelength`, and `_from_canonical_wavelength`, plus corresponding intensity helpers.
- When adding complex flux types (e.g. absorption coefficient), capture required parameters (path length, mole fraction) in metadata before conversion.

## Overlay Engine
- `OverlayService` stores canonical `Spectrum` objects and returns view dictionaries for UI consumption. Additional derived overlays (e.g. normalised traces) can wrap `Spectrum.view` to compute temporary arrays without modifying stored spectra.

## Math Operations
- `MathService` currently supports subtract and ratio on aligned grids. Extend with interpolation by introducing a resampling utility before invoking math operations. Ensure epsilon rules are respected and add metadata about masked points or suppressed results.

## Provenance
- `ProvenanceService.create_manifest` accepts iterable spectra and optional transform/citation lists. New services should append transform descriptors (name, parameters, timestamp) so they appear in exports. When adding ML features, include `ml_predictions` block per the schema in `specs/provenance_schema.md`.

## UI Shell
- `app/main.py` composes the services. Widgets can subscribe to overlay updates by calling `refresh_overlay()` after making service changes. When adding new tabs, reuse `OverlayService` views and update selectors to keep keyboard navigation consistent.

## Cache & Library
- `LocalStore` persists every ingest; the Library tab inside the Data dock
   queries it via `LocalStore.list_entries()` so operators can reload cached
  spectra. When you extend ingest logic, refresh the Library view and avoid
  logging raw file paths in the knowledge log—keep that file for high-level
  insights.
- Remote downloads now branch: HTTP requests still use `requests`, while MAST
  records go through `astroquery.mast.Observations.download_file`. Update tests
  in `tests/test_remote_data_service.py` if you add new providers.
- The MAST adapter injects `dataproduct_type="spectrum"`, `intentType="SCIENCE"`,
  and `calib_level=[2, 3]` and prunes non-spectroscopic rows to keep the results
  focused on slit/grism/IFS products that align with laboratory references. Only
  override these defaults when a workflow explicitly requires imaging products
  and document the change in the workplan/user guide.
- Curated targets for quick-picks and host-star scaffolding live in
  `RemoteDataService._CURATED_TARGETS`. Each entry now carries a `category`
  (`"solar_system"`, `"host_star"`, `"exoplanet"`, etc.), canonical `names`, and
  citation metadata. Use `RemoteDataService.curated_targets()` to retrieve
  filtered copies in the UI. When adding moons or additional systems, extend the
  curated list, keep queries short (canonical name only), and update the quick
  pick tests in `tests/test_remote_data_dialog.py` plus the integration suite
  under `tests/integration/`.
- The Solar System quick-pick button in `RemoteDataDialog` reads from the
  curated targets. When extending the list, surface the new labels in the user
  guide and ensure `RemoteDataDialog._refresh_quick_pick_state` remains
  dependency-aware so the menu disables cleanly when ExoSystems support is
  absent.
- Trace colouring can be toggled between the high-contrast palette and a uniform
  colour via the Style tab combo box; respect the `_use_uniform_palette`
  attribute when adding new plot interactions.

## 2025-10-22 — Remote Data stability and streaming ingest
- Filters in Remote Data (All/Spectra/Images/Other), selection guards, and non-blocking worker cleanup
- Non-spectral skip during bulk ingest
- MAST: isolated temp-dir + persistent temp copy; fallback to direct HTTP (MAST Download API) on empty astroquery result
- NIST: registration fix; UI slots on main thread; CSV generation and ingest
- In-memory ingest: `DataIngestService.ingest_bytes` to support streaming/quick-plot flows

See also: `docs/atlas/remote_data_flow.md` and `docs/brains/*` neurons.

## Packaging
- Update `packaging/spectra_app.spec` when adding new data assets. Keep `requirements.txt` aligned with runtime dependencies to ensure PyInstaller bundles the correct versions.

## IR Functional Groups and ML Integration (Added 2025-10-25)

### Extended IR Database
- **Location**: `app/data/reference/ir_functional_groups_extended.json`
- **Coverage**: 50+ functional groups organized into 8 chemical families (hydroxyl, carbonyl, amine, aromatic, aliphatic, nitrogen, sulfur, halogen)
- **Auto-detection**: `ReferenceLibrary.ir_groups` property automatically uses extended database when available, falls back to basic 8-group database
- **Structure**: Each group includes wavenumber ranges (min/max/peak), intensity descriptors, vibrational modes, chemical classes, related groups, diagnostic value (1-5), and identification notes
- **Provenance**: Compiled from NIST Chemistry WebBook, Pavia et al. (2015), Silverstein et al. (2015), and SDBS (AIST Japan)

### ML Integration Phases (Planned)

When implementing ML features for automated functional group identification:

**Phase 1: Rule-Based Analyzer** (4 weeks, depends on: scipy)
- Implement peak detection using `scipy.signal.find_peaks` with prominence/width filtering
- Create `IRFunctionalGroupAnalyzer` class in new `app/services/ir_analysis.py`
- Match detected peaks to database ranges using Gaussian likelihood scoring
- Apply contextual rules (e.g., broad O-H + sharp C=O at 1710 cm⁻¹ = carboxylic acid)
- Return predictions with confidence scores and supporting evidence (diagnostic peaks)
- Performance target: 80% precision, 70% recall, <100ms latency
- Update UI: Add "Analyze Functional Groups" button in Reference tab → IR panel
- Tests: Unit tests on synthetic spectra + integration tests on known compounds (benzoic acid, acetone, ethanol)

**Phase 2: Data Collection** (6 weeks, new dependencies: rdkit, pandas)
- Script to download NIST WebBook IR spectra (~18K with SMILES): `tools/data/fetch_nist_ir.py`
- Script to download SDBS spectra (~34K): `tools/data/fetch_sdbs_ir.py`
- Implement `tools/data/generate_fg_labels.py` using RDKit `Fragments` module to parse SMILES → functional group presence/absence
- Preprocessing pipeline: baseline correction, normalization, resampling to 4000-400 cm⁻¹ at 2 cm⁻¹ resolution (1800 points)
- Data augmentation: baseline shifts, realistic noise, spectral shifting (±5 cm⁻¹), intensity scaling
- Storage: HDF5 or Parquet format in `data/ml_training/` (not committed to repo; document download/regeneration process)
- Create train/validation/test splits (60/20/20) with metadata and provenance

**Phase 3: Neural Network** (8 weeks, new dependencies: tensorflow or pytorch, scikit-learn, h5py)
- Implement 1D CNN architecture in `app/services/ml/functional_group_predictor.py`
- Architecture: Conv1D layers + multi-head self-attention + global pooling + dense layers
- Multi-label classification with sigmoid output (independent probabilities per group)
- Training script: `tools/ml/train_fg_model.py` with hyperparameter tuning
- Model persistence: save weights to `app/models/ir_fg_predictor_vX.h5` (or `.pt` for PyTorch)
- Performance target: 90% precision, 85% recall on hold-out test set
- Interpretability: Attention weights + SHAP values for explainability
- Tests: Model loading, prediction API, performance benchmarks

**Phase 4: UI Integration** (4 weeks)
- Create `app/ui/functional_group_analysis_panel.py` with confidence bars and evidence display
- Add "Analyze" button to Reference tab → IR Functional Groups
- Display predictions color-coded by functional group family
- Show supporting evidence: diagnostic peaks, attention maps, rule contributions
- Annotated spectrum view: overlay color-coded regions on main plot
- Export predictions: CSV/JSON with full provenance (model version, confidence scores, evidence)
- Batch processing: analyze multiple spectra sequentially
- Qt tests: `tests/test_functional_group_analysis.py`

**Phase 5: Hybrid Ensemble** (4 weeks)
- Implement `HybridFunctionalGroupPredictor` in `app/services/ml/hybrid_predictor.py`
- Combine rule-based and neural network predictions with tunable weights (default 40%/60%)
- Interpretability panel: show which method contributed to each prediction
- Comparison mode: side-by-side rule-based vs neural predictions
- User feedback collection: allow corrections to improve model via active learning
- Performance target: 92% precision, 88% recall
- Tests: Ensemble consistency, interpretability validation

### ML Dependencies (Optional)
Add to `requirements.txt` when implementing ML phases (mark as optional in comments):
```
# ML dependencies (optional, for functional group prediction)
rdkit>=2023.3.1              # Phase 2: Molecular structure parsing
tensorflow>=2.13.0           # Phase 3: Neural network (or pytorch>=2.0.0)
scikit-learn>=1.3.0          # Phase 2-3: Preprocessing, metrics
h5py>=3.9.0                  # Phase 2: Efficient dataset storage
```

### Design Documents
- Complete specification: `docs/specs/ml_functional_group_prediction.md`
- Architectural decision: `docs/brains/2025-10-25T0230-ir-ml-integration.md`
- Atlas coverage: Chapter 1 (§3.1a), Chapter 7 (§7a)
- User guide: `docs/user/reference_data.md` (IR Functional Groups section)
- Workplan: `docs/reviews/workplan.md` (IR Functional Groups and ML Integration Roadmap)

### Key Constraints
- **Canonical units**: IR data stored in cm⁻¹ (wavenumber), never mutated
- **Provenance-first**: All predictions recorded with method, confidence, evidence, model version
- **Offline-first**: Extended database works without ML; rule-based predictor works without neural network; neural predictor bundled for offline use
- **Immutable spectra**: Predictions are derived data, never modify original `Spectrum` objects
- **Explainability**: Every prediction must decompose into understandable components (peaks, patterns, rules, attention weights)
