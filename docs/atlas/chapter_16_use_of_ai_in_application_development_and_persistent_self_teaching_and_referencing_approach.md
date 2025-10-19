# Chapter 16 — Use of AI in Application Development and Persistent, Self‑Teaching and Referencing Approach

### FROM HUMAN DEV. ###
*** NOTE THAT NOT ALL DESCRIPTIONS OF AI APPLICATIONS ARE CORRECTLY DESCRIBED HERE. 
*** THIS FILE NEEDS MANUAL CHECKING/REVISIONS. 
*** AS THE AI MODEL DOES NOT PERFORM MANY OF THE CLAIMED CAPABILITIES. 
*** AI WAS USED IN THE CODING OF THIS PROGRAM, DATA SOURCING, DOCUMENT CONSTRUCTION AND UPKEEP, GITHUB PULL REQUESTS. 
*** NO AI IS USED IN THE ACTUAL PROGRAM ITSELF. UNLESS IT IS IMPLEMENTED AT A LATER DATE AND ITS INCLUSION IS SPECIFIED CLEARLY. ***
*** ANY USE OF AI IN THIS CODE, IS DONE IN THE FORM OF MAKING THE CODEX AGENTS SELF REFERENCE/REVISE/LEARN FROM PROVIDED DOCUMENTION. 
*** AI WILL READ ALL DOCUMENTS WRITTEN BY PAST AGENTS IN THE DESIGNATED AREAS
*** AI WILL WRITE DOCUMENTATION/TASKS/FINDINGS/SUGGESTIONS/PROGRESS AS IT WORKS IN CONSISTENT FORMATS AND WAYS, SUCH THAT IT CAN BE REFERENCED BY FUTURE DEVELOPER
*** AI WILL KNOW TO FOLLOW CONSISTENT, LOGICAL, REPRODUCABLE PATHS AND THOUGHT PROCESSES.
*** AI WILL KNOW TO REFER TO REFERENCE MATERIALS, CONSULTING THEM IN FULL, AND CREDITING SOURCES USED. WHERE THEY ARE USED. AND CORRECTLY CITE THEM, AND PROPERLY DOCUMENT THEM IN OUR REFERENCE MATERIAL DOCUMENTATIONS.
*** AI WILL KNOW TO UPDATE NEWLY ACQUIRED REFERENCES AND SOURCES AND CORRECTLY CITING THEM, AND PROPERLY DOCUMENT THEM IN OUR REFERENCE MATERIAL DOCUMENTATIONS.



> **Purpose.** Define how artificial intelligence (AI/ML) supports the Spectra App without undermining scientific rigor. Specify the feedback loops that let the system improve through use while preserving determinism, provenance, and reproducibility.
>
> **Scope.** Model types (classifiers, regressors, anomaly detectors), training data management, inference APIs, human‑in‑the‑loop labeling, uncertainty calibration, continual learning via **offline** updates, and knowledge capture from reports to keep documentation synchronized with practice.
>
> **Path notice.** Filenames and directories are **placeholders**. The app resolves tokens like `[SESSION_ID]`, `[DATASET_ID]`, `[YYYYMMDD]`, `[MODEL_ID]` at runtime. Do **not** hardcode.

---

## 0. Design tenets (non‑negotiable)
1. **Science first.** Physics‑based rules and evaluated libraries remain primary (Ch. 4–7). ML assists; it does not overrule ground truth without justification.
2. **Deterministic inference.** Given fixed inputs and model versions, outputs are bit‑wise reproducible (seed pinned; versions logged) (Ch. 8).
3. **Explainable by default.** Every prediction exposes features, contributions, and uncertainties (e.g., SHAP) suitable for reports.
4. **Human‑in‑the‑loop.** User corrections are first‑class data, captured with provenance and used in **offline** retraining only after review.
5. **Data minimization.** No PII in training sets; spectra content never leaves local storage unless explicitly exported.

---

## 1. What AI does here (and what it doesn’t)

### 1.1 Supported tasks
- **Multi‑label tagging** of functional groups (IR/Raman).
- **Template suggestion** and **shortlist ranking** for identification (Ch. 7), used to prioritize scoring.
- **Regression**: bandgap from UV–Vis; temperature proxies from rotational envelopes; fluorescence quenching constants.
- **Anomaly detection**: flag spectra that violate calibration, unit, or feature expectations; surface outliers in cohorts (Ch. 15).

### 1.2 Anti‑tasks (forbidden)
- Silent unit conversions or smoothing.
- Auto‑modifying calibration constants.
- Training on raw student data without explicit opt‑in and provenance capture.

---

## 2. Data sources for training (curated only)

- **Authoritative libraries**: NIST ASD (atomic), HITRAN/ExoMol/JPL/CDMS (molecular), RRUFF (minerals), CALSPEC/stellar libraries (astro) (Ch. 4). Use evaluated uncertainties as labels or weights.
- **Campus gold standards**: sessions measured under Chapter 2 SOPs with clean QC, frozen as `benchmarks/[DATE]/` (Ch. 7 §10; Ch. 15 §11).
- **User feedback log**: corrected identifications and labeled features stored as `feedback/[YYYYMMDD]/labels.parquet` with checksums.

**Prohibition:** exclude quarantined or unit‑ambiguous spectra.

---

## 3. Model registry and cards

Every model has a **model card** and a content‑addressed artifact in `models/[MODEL_ID]/`:
```json
{
  "model_id": "ml:raman_groups:v1.2.0",
  "task": "multi_label_classification",
  "architecture": "gradient_boosting",
  "training_set_id": "benchmarks/2025-09-01/raman_groups",
  "hash": "sha256:...",
  "metrics": {"micro_f1": 0.91, "macro_f1": 0.88, "ece": 0.03},
  "calibration": {"method": "isotonic", "ece": 0.03},
  "explainability": {"method": "shap", "sparsity": 15},
  "license": "[LICENSE]",
  "citation": "[ADD DOI]",
  "created": "[ISO-8601]"
}
```
Model cards are embedded in reports when predictions are used.

---

## 4. Inference API (deterministic)

```python
def predict(task: str, features: np.ndarray | dict, meta: dict,
            *, model_id: str, seed: int = 1729) -> dict:
    """Return predictions with uncertainties and explanations.
    - task: one of {"tagging","template_suggest","regression","anomaly"}
    - features: engineered features or spectral segments (see §5)
    - meta: modality, units, instrument, LSF, etc.
    - model_id: pinned model card id
    - seed: for any stochastic components (fixed default)
    Returns: {pred, prob|interval, explain, provenance}
    """
```
**Outputs include**: prediction, confidence/probability or interval, explanation objects (e.g., SHAP values or prototype matches), and full provenance (model card, features hash, constants version).

---

## 5. Feature engineering contracts

- **IR/Raman**: peak positions, widths, intensities; windowed spectral descriptors (spectral contrast, derivatives); baseline metrics; laser λ₀ for Raman.
- **UV–Vis**: band edge metrics (Tauc slope and intercept), area ratios, baseline tilt.
- **Astro**: cross‑correlation peaks, template indices, CCF width, velocity frame.
- **Global QC**: SNR estimates, wavelength RMS, LSF FWHM, masks coverage.

Feature schemas are versioned under `schemas/features/[DATE].json` and referenced by models.

---

## 6. Continual learning loop (offline only)

1. **Collect** feedback and new gold‑standard sessions with clean QC.
2. **Curate** via review queue; remove conflicts; harmonize units/resolution (Ch. 5–6).
3. **Train** candidate models with cross‑validation and probability calibration.
4. **Validate** on a held‑out campus benchmark; stress‑test with synthetic drifts (resolution, noise, axis offsets).
5. **Compare** to incumbent via pre‑registered metrics; require non‑inferiority on safety checks (false positives on conflicting modalities).
6. **Publish** new model with updated model card; keep old versions available; app prompts for upgrade with changelog.

**Storage:** Datasets tracked with checksums; training scripts saved with environment lockfiles. No opaque notebooks as the only record.

---

## 7. Human‑in‑the‑loop labeling

- **Evidence‑first UI:** users assign or correct labels from the **evidence graph** (Ch. 3) to avoid contextless clicks.
- **Inter‑rater checks:** require two reviewers for new class additions; compute Cohen’s κ; flag low agreement.
- **Active learning:** sampler surfaces spectra where the model is uncertain or modalities conflict most.

Labels include class ontology, rationale, and links to features and external sources.

---

## 8. Uncertainty and probability calibration

- **Classification:** Platt scaling or isotonic regression; report Expected Calibration Error (ECE) in model cards.
- **Regression:** empirical prediction intervals from residuals or conformal prediction.
- **Anomaly scores:** convert to calibrated probabilities via extreme‑value theory or isotonic mapping; keep thresholds in rubric config (Ch. 11).

All calibration artifacts are saved under `models/[MODEL_ID]/calibration/` with hashes.

---

## 9. Explainability and audit

- **Global**: feature importance distributions; prototype exemplars; class‑wise error analysis.
- **Local**: SHAP/attribution vectors per prediction; top contributing peaks/bands with units and uncertainties.
- **Report embedding**: compact explanation panels with links back to raw spectra and transforms (Ch. 8).

**Guardrails:** cap explanation verbosity; never hide conflicts between modalities.

---

## 10. Knowledge base and self‑referencing

- **Doc sync**: when a new model, rubric, or SOP ships, a doc PR is auto‑generated to update Chapter references (Ch. 13). Builds are deterministic and versioned.
- **Method cards**: each exported report generates a structured **method card** with parameters, QC, and key decisions; cards feed searchable knowledge for future sessions.
- **Query layer**: agents can query past reports by feature patterns (e.g., “Raman 1085 ± 2 cm⁻¹ + IR 1415 cm⁻¹ carbonate”) to retrieve precedent.
- **Teaching feedback**: quiz results map to weak concepts; the app suggests targeted lessons.

All KB items are content‑addressed; citations carry DOIs/versions.

---

## 11. Safety, bias, and ethics

- **Bias audits**: check class imbalance, instrument bias (one lab section dominating training), and modality coverage. Mitigate via stratified sampling and cost weights.
- **Adversarial sanity**: inject non‑physical spectra (unit flips, impossible negative transmittance) to ensure models fail closed with clear errors.
- **Licensing**: training only on data permitted by source terms (Ch. 4 §7). Respect opt‑out flags in campus data.
- **Privacy**: no PII; per‑session anonymization option for teaching data exports.

---

## 12. Failure modes and mitigations

- **Spurious correlations**: prefer physics‑aware features; enforce rule checks before trusting ML suggestions.
- **Drift**: monitor performance by semester; if ECE or accuracy drifts, roll back or trigger retraining.
- **Over‑confidence**: calibrated probabilities required; low‑confidence predictions are labeled **provisional** and must not auto‑populate reports.

---

## 13. Integration with identification engine (Ch. 7)

- ML provides priors and candidate orderings; the physics‑based scorer retains final say.
- **API bridge:** `ml.suggest_candidates()` returns templates with priors; `identify()` consumes them alongside rule‑based priors.
- **Learning from decisions:** accepted identifications and rejected alternatives are logged for offline retraining.

---

## 14. Minimal JSON stubs

**Feedback label**
```json
{
  "label_id": "lbl:[UUID]",
  "spectrum_ref": "sessions/[SESSION_ID]/[MODALITY]/processed/[FILE]",
  "task": "functional_group",
  "classes": ["carbonate","hydroxyl"],
  "evidence_graph_ref": "graphs/[SESSION_ID]/[DATASET_ID]/evidence.json",
  "annotator": {"role": "ta|pi", "id": "[ANON]"},
  "created": "[ISO-8601]"
}
```

**Prediction output**
```json
{
  "pred_id": "pred:[UUID]",
  "model_id": "ml:raman_groups:v1.2.0",
  "input_hash": "sha256:...",
  "pred": {"carbonate": 0.82, "sulfate": 0.11, "nitrile": 0.02},
  "explain": {"top_features": ["1085_cm-1","1415_cm-1"]},
  "calibrated": true,
  "created": "[ISO-8601]"
}
```

---

## 15. Evaluation protocol (ship with app)

- **Metrics**: accuracy/top‑k for tagging; MAE for regression; AUROC/PR for anomaly detection; ECE/Brier for calibration.
- **Splits**: stratify by instrument and semester to avoid leakage; group by sample, not scan.
- **Stress tests**: resolution and unit flips; Gaussian noise; baseline drifts; partial occlusion of diagnostic regions.
- **Repro pack**: `benchmarks/[DATE]/eval_[YYYYMMDD].zip` with predictions, confusion matrices, reliability curves, code version, and lockfiles.

---

## 16. Future upgrades

- **Physics‑informed models** that embed selection rules and line‑shape priors.
- **Joint spectral‑spatial models** for imaging datasets.
- **Program synthesis** for method recommendations using constraints from Chapters 2, 5, and 6.
- **Federated learning** across campuses with differential privacy where policy permits.

---

## 17. Reference anchors (full citations in Ch. 32)
- **Model cards** and **Datasheets for Datasets** for documentation best practices.
- **Probability calibration** (Platt, isotonic) and **conformal prediction**.
- **Explainability** (SHAP) for feature attribution.
- **Active learning** and semi‑supervised learning references.
- **DVC/MLflow‑style** experiment tracking for reproducible ML.

> **Cross‑links.** Ch. 3 (evidence graph), Ch. 4 (sources), Ch. 5 (units), Ch. 6 (calibration/LSF), Ch. 7 (identification), Ch. 8 (provenance), Ch. 11 (rubrics), Ch. 13 (docs), Ch. 15 (comparisons).

