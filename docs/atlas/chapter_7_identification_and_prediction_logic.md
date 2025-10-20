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

