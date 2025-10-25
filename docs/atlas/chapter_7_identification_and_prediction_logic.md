# Chapter 7 — Identification and Prediction Logic

> **Purpose.** Specify a transparent, testable identification and prediction engine that ingests calibrated spectra from multiple modalities (atomic emission/absorption, FTIR/ATR, Raman, UV–Vis, fluorescence, and optional non‑optical validators), generates candidate hypotheses, scores them with explainable metrics, fuses evidence under explicit priors, and produces auditable reports.
>
> **Scope.** Campus instruments and curated external libraries; detection, classification, and regression tasks (e.g., functional‑group tagging, bandgap estimation). Supports astrophysical use cases (radial velocity, template matching) and lab samples (solutions, solids, gas cells).
>
> **Path notice.** File and folder names are **placeholders**. All paths must be resolved via the application’s path resolver at runtime. Tokens like `[SESSION_ID]`, `[DATASET_ID]`, `[MODALITY]`, `[YYYYMMDD]` are variables; do not hardcode.

---

## 1. Design principles

1. **Deterministic by default.** Given the same inputs and configuration, results are bit‑wise reproducible. Randomized routines fix `seed` and record it.
2. **Explainable first.** Every score decomposes into per‑feature, per‑modality contributions with uncertainties.
3. **Raw preserved.** Only views are transformed; raw data remain immutable (see Chapter 6).
4. **Priors explicit.** Elemental presence, stoichiometry, environment, and source reliability feed into priors that are visible and editable.
5. **Graceful missingness.** Absent modalities re‑weight the fusion but never silently zero out evidence.

---

## 2. Inputs and context

- **Spectrum bundles** from Chapter 6 with: calibrated axis, response‑corrected intensity, LSF/Resolution, uncertainties.
- **Extracted features** (peaks/bands/edges) with centers, FWHM, intensities, and covariance (see Chapter 3 schema).
- **Priors**: elemental detections (atomic), plausible stoichiometries, temperature/pressure, solvent/matrix, trust tiers for libraries (Chapter 4).
- **Templates**: line lists and spectral templates (atomic, molecular, minerals, astro) with versioned provenance.

---

## 3. Candidate generation

1. **Atomic‑gated shortlist**: map detected elements to allowed molecular families (e.g., presence of Na and CO₃²⁻ hints alkali carbonates) using a simple ruleset table.
2. **Band dictionary hit**: rough matching of diagnostic IR/Raman regions to candidate groups/isomers.
3. **Context filters**: temperature/pressure windows, solvent presence, expected phase (solid/gas/solution), astrophysical class.
4. **User constraints** (optional): whitelist/blacklist, known sample prep.

The candidate set `𝓒` proceeds to modality‑level scoring.

---

## 4. Per‑modality scoring

Let observed features be \(\{x_j\}\) and template/library expectations for candidate \(M\) be \(\{\mu_i\}\) with uncertainties.

### 4.1 Sparse features (lines/bands)

- **Position likelihood (Gaussian)**
\[
\mathcal{L}_i = \exp\!\left[-\tfrac{1}{2}\Big(\tfrac{x_j-\mu_i}{\sigma_i}\Big)^2\right], \quad \sigma_i^2 = \sigma_{\text{inst}}^2 + \sigma_{\text{lib}}^2
\]
- **Intensity consistency (optional)** using a robust loss comparing observed vs expected relative intensities; down‑weight when absolute calibration is unavailable.
- **Penalty terms** for extra peaks not explained by \(M\) (FP) and expected peaks missing (FN), scaled by diagnostic weights \(w_i\).

**Per‑modality score**
\[
S_k(M) = \sum_{i\in k} w_i \log \mathcal{L}_i \; - \; \alpha_k\,\mathrm{FP}_k \; - \; \beta_k\,\mathrm{FN}_k
\]

### 4.2 Dense templates (cross‑correlation)

For continua or dense bands (astro molecules, mineral lattices), compute normalized cross‑correlation with the template convolved to the instrument LSF and adjusted for shift/broadening parameters \((\Delta,\gamma)\):
\[
C_k(M)=\max_{\Delta,\gamma}\; \frac{\langle \tilde{T}_M(\Delta,\gamma),\; D_k\rangle}{\|\tilde{T}_M(\Delta,\gamma)\|\,\|D_k\|}
\]
Convert \(C_k\) to a log‑likelihood via Fisher transform or empirically calibrated mapping.

### 4.3 Raman specifics

- Use **exact λ₀** for Raman shift (Chapter 5). Propagate \(\sigma_{\Delta\tilde{\nu}}\) from λ₀ and λₛ uncertainties.
- Apply fluorescence baseline correction masks; record baseline model in the evidence object.

### 4.4 UV–Vis specifics

- For quant work, score linearity of Beer–Lambert calibration for target species. For solids/films, derive bandgap (Tauc) and compare to candidate ranges.

### 4.5 Fluorescence specifics

- Score Stokes shift, emission maxima, and quenching behavior against candidate fluorophores or microenvironments.

---

## 5. Priors and reliability weights

- **Elemental prior** \(P_0(M)\): compatible with detected elements and plausible stoichiometries.
- **Environment prior**: temperature/pressure/solvent constraints.
- **Source reliability weights** \(\rho_s\): trust tier of libraries (Chapter 4) and measurement quality (SNR, calibration RMS). These scale \(w_i\) and the per‑modality \(\lambda_k\).

Priors are explicit objects in the manifest, each with rationale and provenance.

---

## 6. Evidence fusion

Combine per‑modality scores with weights \(\lambda_k\) to produce a log‑posterior (up to a constant):
\[
\log P(M\mid \mathbf{D}) = \log P_0(M) + \sum_k \lambda_k\, S_k(M) - \Gamma(M)
\]
where \(\Gamma(M)\) includes complexity penalties (e.g., for adding too many components) and rule‑based penalties (e.g., environmental contradictions).

**Confidence tiers**
- **High**: posterior gap to alternative \(\Delta\ge\tau_H\) and minimum evidence in ≥2 modalities.
- **Moderate**: \(\tau_M \le \Delta < \tau_H\) or strong single‑modality evidence with no contradictions.
- **Low/Provisional**: otherwise; report additional data likely to disambiguate.

Thresholds \(\tau_H, \tau_M\) are set via validation (see §10) and recorded with versioning.

---

## 7. Machine‑learning assists (optional but encouraged)

### 7.1 Tasks
- **IR/Raman functional‑group tagging** (multi‑label classification).
- **Bandgap estimation** from UV–Vis (regression).
- **Anomaly discovery** for unknowns (unsupervised/one‑class methods).
- **Astro template selection** and spectral type suggestion.

### 7.2 Training data hygiene
- Curate labels from authoritative sources; split by **sample** not by scan to avoid leakage.
- Use cross‑validation with stratification by class and instrument.
- Calibrate probabilities (Platt or isotonic). Track calibration error.

### 7.3 Model choices
- Start with transparent models (logistic/gradient boosting) for tagging; add 1D CNNs only when justified.
- Always ship **feature importance/SHAP** for explainability. Store model hash, training set ID, and metrics.

### 7.4 Human‑in‑the‑loop
- User corrections update a **feedback log**; periodically retrain with review. Keep an audit trail of label provenance.

---

## 7a. IR Functional Group Identification — Hybrid Approach (Implementation in Progress)

The application implements a **three-tier hybrid system** for automated IR functional group identification, combining comprehensive reference databases, rule-based analysis, and neural network predictions.

### 7a.1 Extended IR Functional Groups Database

**Status**: ✅ Implemented (`app/data/reference/ir_functional_groups_extended.json`)

The reference library contains **50+ functional groups** organized into 8 chemical families:

1. **Hydroxyl groups** (6 variants): O-H free, hydrogen-bonded, phenolic, carboxylic, primary/secondary alcohols
2. **Carbonyl groups** (7 variants): ketone, aldehyde, ester, carboxylic acid, amide, anhydride, acid chloride
3. **Amine groups** (4 variants): primary (NH₂), secondary (NH), tertiary (N), N-H stretch/bend patterns
4. **Aromatic groups** (4 variants): C-H aromatic stretch, C=C stretch/bending, substitution patterns
5. **Aliphatic groups** (5 variants): sp³/sp²/sp C-H systems, C=C alkene, C≡C alkyne
6. **Nitrogen groups** (3 variants): nitrile (C≡N), nitro (doublet at 1550/1350 cm⁻¹), azo (N=N)
7. **Sulfur groups** (4 variants): thiol (S-H), sulfoxide (S=O), sulfone (SO₂), disulfide (S-S)
8. **Halogen groups** (4 variants): C-F, C-Cl, C-Br, C-I

Each group record includes:
- **Wavenumber ranges**: minimum, maximum, characteristic peak (cm⁻¹)
- **Intensity descriptors**: strong, medium, weak, variable
- **Vibrational modes**: stretch, bend, rock, wag, twist, symmetric/asymmetric
- **Chemical classes**: alcohols, ketones, aromatic, etc.
- **Related groups**: functional groups that commonly co-occur
- **Diagnostic value** (1-5 scale): reliability for identification
- **Notes**: interference patterns, concentration effects, matrix dependencies

**Usage**: `ReferenceLibrary.ir_functional_groups()` automatically loads extended database when available, falling back to basic 8-group database for backward compatibility.

**Provenance**: Compiled from NIST Chemistry WebBook, Pavia et al. (2015) *Introduction to Spectroscopy*, Silverstein et al. (2015) *Spectrometric Identification of Organic Compounds*, and SDBS (AIST Japan) database.

### 7a.2 Enhanced Rule-Based Analyzer (Phase 1 — Planned, 4 weeks)

**Peak Detection Pipeline**:
1. Convert spectrum to canonical wavenumber (cm⁻¹) if needed via `UnitsService`
2. Apply `scipy.signal.find_peaks` with prominence and width filtering
3. Match detected peaks to functional group database ranges
4. Score matches using Gaussian likelihood (position accuracy)
5. Apply contextual rules for group interactions
6. Rank predictions by confidence score

**Contextual Rules** (examples):
- Broad O-H (2500-3300 cm⁻¹) + sharp C=O (1710 cm⁻¹) → **Carboxylic acid** (high confidence)
- Doublet at 3400 + 3300 cm⁻¹ + N-H bend at 1600 cm⁻¹ → **Primary amine** (moderate confidence)
- C-H aromatic (3030 cm⁻¹) + C=C (1600, 1500 cm⁻¹) → **Aromatic ring** (high confidence)
- Nitro doublet (1550 + 1350 cm⁻¹) with ~150 cm⁻¹ separation → **Nitro group** (high confidence)

**Confidence Scoring**:
\[
\text{Confidence}_i = w_{\text{pos}} \cdot \mathcal{L}_{\text{pos}} + w_{\text{int}} \cdot \mathcal{L}_{\text{int}} + w_{\text{context}} \cdot N_{\text{correlated}}
\]
where:
- \(\mathcal{L}_{\text{pos}}\) = position likelihood (Gaussian with instrument + library uncertainties)
- \(\mathcal{L}_{\text{int}}\) = intensity consistency (observed vs expected relative intensity)
- \(N_{\text{correlated}}\) = number of correlated peaks present (e.g., C=O with O-H for COOH)

**Performance Target**: 80% precision, 70% recall, <100ms latency per spectrum.

### 7a.3 Neural Network Predictor (Phases 2-3 — Planned, 14 weeks)

**Data Collection** (Phase 2 — 6 weeks):
- **NIST Chemistry WebBook**: ~18,000 IR spectra with molecular structures (SMILES/InChI)
- **SDBS (AIST Japan)**: ~34,000 IR spectra with chemical annotations
- **Label Generation**: Use RDKit `Fragments` module to parse structures into functional group presence/absence
- **Preprocessing**: Baseline correction, normalization, resampling to 4000-400 cm⁻¹ at 2 cm⁻¹ resolution (1800 points)
- **Augmentation**: Baseline shifts, noise injection (realistic instrument noise), spectral shifting (±5 cm⁻¹), intensity scaling
- **Storage**: HDF5 or Parquet for efficient batch loading during training

**Model Architecture** (Phase 3 — 8 weeks):
```
Input Layer: (1800,) — IR spectrum resampled to fixed grid
↓
Conv1D(64, kernel=11) + ReLU + MaxPool(2)
↓
Conv1D(128, kernel=7) + ReLU + MaxPool(2)
↓
Multi-Head Self-Attention (4 heads) — Focus on diagnostic regions
↓
Global Average Pooling
↓
Dense(256) + ReLU + Dropout(0.3)
↓
Dense(50+) + Sigmoid — Multi-label classification (independent probabilities)
```

**Training Strategy**:
- Loss: Binary cross-entropy with class weights for imbalanced groups
- Optimizer: Adam with learning rate scheduling
- Validation: 5-fold cross-validation on training set (80% data)
- Holdout test: 20% of data never seen during training or validation
- Early stopping on validation loss to prevent overfitting
- Model checkpointing to save best weights

**Interpretability**:
- Attention weights show which spectral regions influenced each prediction
- SHAP values decompose predictions into per-wavenumber contributions
- Gradient-weighted class activation mapping (Grad-CAM) highlights diagnostic peaks

**Performance Target**: 90% precision, 85% recall, <500ms GPU / <2s CPU latency.

### 7a.4 Hybrid Ensemble (Phase 5 — Planned, 4 weeks)

**Combination Strategy**:
\[
P_{\text{ensemble}}(\text{group}) = w_{\text{rules}} \cdot P_{\text{rules}}(\text{group}) + w_{\text{nn}} \cdot P_{\text{nn}}(\text{group})
\]

**Default Weights**: 40% rule-based, 60% neural network (tunable per session based on user feedback)

**Fallback Logic**:
- If neural network unavailable → 100% rule-based
- If rule-based detects high confidence → boost rule weight to 60%
- If both methods disagree → flag for manual review, show both predictions

**Interpretability Features**:
- Show which method contributed to each prediction (color-coded: blue=rules, green=NN, purple=ensemble)
- Display supporting evidence from both approaches side-by-side
- Attention map overlay on spectrum showing neural focus regions
- Peak list showing rule-based matches

**Performance Target**: 92% precision, 88% recall.

### 7a.5 Implementation Status and References

**Current State** (as of 2025-10-25):
- ✅ Extended IR database (50+ groups) implemented and integrated
- ✅ Auto-detection in `ReferenceLibrary.ir_groups` property
- ✅ Comprehensive metadata with provenance tracking
- 📋 Phase 1 (rule-based) design complete, implementation pending
- 📋 Phases 2-5 (ML) design documented in `docs/specs/ml_functional_group_prediction.md`

**Documentation**:
- Complete specification: `docs/specs/ml_functional_group_prediction.md`
- Architectural decision: `docs/brains/2025-10-25T0230-ir-ml-integration.md`
- Implementation summary: `IR_EXPANSION_SUMMARY.md`
- User guide updates pending Phase 1 implementation

**Dependencies**:
- Current: `scipy >= 1.11.0` (peak detection)
- Future ML phases: `rdkit`, `tensorflow` or `pytorch`, `scikit-learn`, `h5py` (all optional)

**Testing Strategy**:
- Phase 1: Unit tests on synthetic spectra, integration tests on known compounds (benzoic acid, acetone, ethanol)
- Phase 3: Hold-out test set (20%), 5-fold cross-validation, adversarial testing (noisy baselines, overlapping bands)
- Phase 5: Ensemble consistency, interpretability validation, user acceptance testing

**Research References**:
- FG-BERT (idrugLab): Transformer-based functional group prediction from SMILES
- FTIR Neural Networks (aaditagarwal): Direct spectral pattern learning
- RDKit: Molecular structure parsing for training label generation

> **Cross-links**: See `docs/specs/ml_functional_group_prediction.md` for complete technical specification, `app/data/reference/ir_functional_groups_extended.json` for database schema, and `docs/brains/2025-10-25T0230-ir-ml-integration.md` for architectural rationale. User interface design and workflow integration pending Phase 4 implementation.

---

## 8. Conflict handling and follow‑up design

- Generate a **conflict report** when modalities disagree beyond tolerance: list discordant features, suspected causes (resolution mismatch, baseline, fluorescence, matrix), and recommended follow‑ups (e.g., higher‑resolution IR, low‑freq Raman, different solvent).
- Provide an **active‑inference** suggestion: the single next measurement with the highest expected information gain.

---

## 9. Outputs and schemas

### 9.1 Hypothesis object (ranked)
```json
{
  "hypothesis_id": "hyp:[AUTO_UUID]",
  "label": "[Human-readable name]",
  "components": ["species_or_phase_ids"],
  "priors": {"elements": ["Na","K"], "env": {"T_K": 298, "phase": "solid"}},
  "scores": {"ftir": 18.2, "raman": 11.5, "uvvis": 0.3, "atomic": 6.8, "ml": 2.1},
  "weights": {"ftir": 1.0, "raman": 0.9, "uvvis": 0.4, "atomic": 0.8, "ml": 0.3},
  "log_posterior": 31.4,
  "confidence_tier": "high|moderate|low",
  "alternatives": ["hyp:alt1","hyp:alt2"],
  "required_followups": ["raman_low_freq_100-300_cm-1","ftir_2_cm-1"],
  "evidence_graph_ref": "graphs/[SESSION_ID]/[DATASET_ID]/[ID].json",
  "provenance": {"libraries": ["NIST_ASD@vX","HITRAN@2020","RRUFF@YYYYMM"], "models": ["XGBoost@hash"], "app_build": "[SEMVER]"}
}
```

### 9.2 Detection object (per feature)
```json
{
  "feature_ref": "feat:[UUID]",
  "assignments": [{"candidate": "M:carbonate", "score": 4.1, "delta_ppm": 7.2}],
  "uncertainty": {"center": 0.5, "fwhm": 0.8},
  "notes": "Overlaps with sulfate; flagged for higher resolution"
}
```

### 9.3 Report block (auto‑generated)
- Executive summary and top‑N table with \(\Delta\) to alternatives.
- Per‑modality overlays at matched resolution with annotated features.
- Score decomposition heatmaps and SHAP plots (if ML used).
- Full provenance: library versions, instrument settings, transforms, constants.

---

## 10. Validation and benchmarking

1. **Gold standards:** measure a panel of known samples across modalities; freeze as the **benchmark set** with checksums.
2. **Metrics:** identification accuracy, top‑k accuracy, calibration curves (reliability), detection precision/recall, ROC/PR for binary tags.
3. **Weight tuning:** optimize \(\lambda_k\) and penalty parameters via cross‑validation on the benchmark set.
4. **Stress tests:** simulate resolution mismatches, baseline drifts, and SNR drops; ensure graceful degradation.
5. **Astro checks:** verify radial velocity, template matches, and telluric handling on standard stars.

All benchmark results are exported to a `benchmarks/` folder with versioned reports.

---

## 11. Edge cases and mitigations

- **Isomer ambiguity:** escalate to low‑frequency Raman or NMR prior when bands coincide.
- **Baseline/fluorescence contamination:** increase penalties on intensity terms; rely more on position likelihoods.
- **Overlapping species mixtures:** allow multi‑component hypotheses with L1 penalty to discourage over‑fitting.
- **Resolution mismatch:** re‑compute comparisons at the coarsest FWHM; reject if post‑convolution mismatch persists.
- **Astro tellurics/continuum:** mask telluric regions; use standard‑star derived response/continuum models.

---

## 12. API surface (pseudocode)

```python
def identify(sample_bundle, context, *, priors=None, config=None) -> List[Hypothesis]:
    """Return ranked hypotheses with explanations.
    - sample_bundle: calibrated spectra + features (all modalities available)
    - context: environment, instrument, library registry entries
    - priors: optional user-specified constraints
    - config: thresholds, weights, seeds, matching windows
    Deterministic given fixed inputs.
    """
```

Additional helpers:
- `add_prior(elements=..., env=..., reliability=...)` → updates prior object with provenance.
- `set_weights({modality: λ_k})` → records in manifest and report.
- `explain(hypothesis)` → returns per‑feature contribution table and plots.

---

## 13. Future upgrades

- **Active learning**: choose next measurement to maximize information gain.
- **Semi‑supervised discovery**: cluster unknowns; propose new classes with human review.
- **Joint spectral‑spatial**: extend to spectral imaging cubes.
- **Physics‑informed nets**: embed selection rules/line‑shape physics inside ML models.
- **Uncertainty calibration**: Bayesian neural nets or deep ensembles where warranted.

---

## 14. References (anchor list)
- Core instrumentation texts (instrumental analysis; modern spectroscopy; fluorescence fundamentals).
- Statistical learning references (probabilistic modelling, model selection, calibration of classifiers).
- Authoritative line/band libraries and archives enumerated in Chapter 4 (atomic, molecular, mineral, astro).

> **Cross‑links.** See Chapter 3 for feature schema and evidence graph; Chapter 5 for axes/units; Chapter 6 for calibration artifacts; Chapter 8 for full provenance fields; Chapter 11 for the scoring rubric thresholds used in reporting.

