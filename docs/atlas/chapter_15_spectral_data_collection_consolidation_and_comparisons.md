# Chapter 15 — Spectral Data Collection, Consolidation, and Comparisons

> **Purpose.** Define how to plan, capture, organize, and compare spectra across instruments, sessions, and semesters so that conclusions are defensible and repeatable. This chapter stitches together acquisition (Ch. 2), unit/axis handling (Ch. 5), calibration/alignment (Ch. 6), fusion (Ch. 3 & 7), and provenance (Ch. 8) into a single, reproducible pipeline for building datasets and making comparisons that actually mean something.
>
> **Scope.** Campus instruments (atomic/UV–Vis, FTIR/ATR, Raman, fluorescence) plus optional astrophysical spectra and external libraries. Includes replicate strategy, batch effects, stitching, normalization views, similarity metrics, multi‑modal consolidation, mixture decomposition, and reporting.
>
> **Path notice.** All filenames and directories are **placeholders**. Resolve tokens like `[SESSION_ID]`, `[DATASET_ID]`, `[MODALITY]`, `[YYYYMMDD]` at runtime via the app’s path resolver. Do **not** hardcode paths.

---

## 0. Dataset design before you touch a button

1. **Define the comparison question.** Example: *Are these carbonate samples the same polymorph?* or *Did the thin‑film anneal change bandgap?* Write the question into the session manifest `notes` field.
2. **Choose modalities and resolutions.** Pick at least two complementary modalities when feasible (e.g., ATR‑IR + Raman). Pre‑select **target FWHM** for overlays (Ch. 6 §5) and unit views (Ch. 5).
3. **Replicate plan.** Minimum: 3 technical replicates per sample and modality; 2 independent days for inter‑day drift. Log replicates as `[DATASET_ID]_rep[01..]`.
4. **Controls.** Include positive material standards and blanks per run; standards become anchors for alignment checks.
5. **Randomization.** Randomize sample order to avoid drift trends masquerading as chemistry.

---

## 1. Collection plan and manifests

**Manifest skeleton** appended to `sessions/[SESSION_ID]/manifest.json`:
```json
{
  "dataset_goal": "Compare carbonate polymorph identity across prep methods",
  "replicate_policy": {"technical": 3, "inter_day": 2},
  "controls": ["polystyrene_IR", "Si_520.7_Raman", "holmium_UVVis"],
  "target_fwhm": {"ftir_cm-1": 4.0, "raman_cm-1": 6.0, "uvvis_nm": 0.5},
  "comparison_windows": {
    "ftir_cm-1": [[400, 800], [1300, 1600]],
    "raman_cm-1": [[100, 400], [1550, 1650]],
    "uvvis_nm": [[350, 800]]
  }
}
```

**Replicate labeling convention** (placeholder):
```
[SAMPLE_ID]_[MODALITY]_repXX_[YYYYMMDD]
```

---

## 2. Consolidation: turning many files into one coherent dataset

**Input bundles:** individual spectrum bundles with calibration artifacts and provenance (Ch. 6, 8).

**Consolidation product:** `datasets/[DATASET_ID]/consolidated.h5` containing:
- `spectra/` group with per‑sample, per‑modality canonical arrays and uncertainties.
- `views/` with **comparison views** aligned to common axis and **target FWHM** (views only; raw preserved).
- `tables/features.parquet` with extracted features (Ch. 3 schema).
- `meta/manifest_json` merged from sessions; conflicts resolved via rules below.

**Merge rules:**
1. **Units/axes** must match canonical per modality (Ch. 5). Reject on missing `unit` or `medium`.
2. **Resolution**: convolve high‑res down to `target_fwhm` for overlays; record kernel and windows (Ch. 6 §5).
3. **Velocity context** (astro): store barycentric and systemic velocities; perform comparisons in the **same frame**.
4. **Conflicts**: if two runs disagree on calibration RMS or response ID, prefer the newer artifact **only** when within validity window; else keep both with flags.

---

## 3. Stitching and normalization views

**Stitching** segmented spectra (echelle orders or range‑split scans):
1. Overlap regions must have ≥10× FWHM width.
2. Fit a smooth gain `g(λ)` in overlaps (low‑order spline). Apply to the higher‑noise segment.
3. Store a `stitch_map` object with nodes (λ, gain) and residuals.

**Normalization views** (do not overwrite source intensities):
- **Unit area/height** for template matching when absolute calibration is unknown.
- **Reflectance to Kubelka–Munk** for diffuse reflectance when comparing to absorption‑like libraries:
  \[
  F(R_∞) = \frac{(1-R_∞)^2}{2R_∞}
  \]
- **Baseline‑corrected** view using windows outside features (coefficients and masks recorded).

---

## 4. Similarity and difference metrics (1D, single modality)

Given two aligned, resolution‑matched spectra \(x\) and \(y\):

1. **Cosine similarity** (shape only):
\[
\mathrm{cos}(x,y) = \frac{\langle x, y \rangle}{\|x\|\,\|y\|}
\]
2. **Pearson correlation** (shape with mean centering): robust to gains; sensitive to baseline errors.
3. **Normalized cross‑correlation** with allowed shift window \(\Delta\) (astro, small Raman/IR offsets):
\[
\max_{|\delta|\le\Delta} \frac{\langle x, y_{\text{shifted}}(\delta) \rangle}{\|x\|\,\|y\|}
\]
4. **L2 residual norm** on masked windows: \(\|x-y\|_2\) with uncertainty weighting.
5. **Peak‑set Jaccard** for sparse features: \(J = |P_x \cap P_y|/|P_x \cup P_y|\) within tolerance windows.

**Guardrails:** never use DTW for physical spectra unless justified; it can invent non‑physical warps. Prefer cross‑correlation within physics‑allowed shifts.

---

## 5. Multi‑modal comparison score (dataset level)

Aggregate per‑modality similarities into a **comparison scorecard**:
\[
C_{\text{global}} = \sum_k w_k\, \phi_k(\text{sim}_k)
\]
- \(\text{sim}_k\) is the modality similarity (e.g., cosine or cross‑corr result).
- \(\phi_k\) maps similarity to a common 0–1 scale (e.g., identity for cosine; rescaled for residuals).
- Weights \(w_k\) reflect diagnostic power and QC (see Ch. 11 quality weights \(q_k\)).

**Scorecard JSON** (example):
```json
{
  "sample_A": "S01",
  "sample_B": "S02",
  "comparisons": {
    "ftir": {"method": "cosine", "window_cm-1": [1300,1600], "value": 0.93},
    "raman": {"method": "peak_jaccard", "tolerance_cm-1": 4.0, "value": 0.88},
    "uvvis": {"method": "pearson", "window_nm": [350,800], "value": 0.72}
  },
  "global": {"weights": {"ftir": 0.4, "raman": 0.4, "uvvis": 0.2}, "score": 0.86}
}
```

---

## 6. Mixture comparison and decomposition

When a sample may be a mixture of known components with templates \(T_j\), fit **non‑negative least squares** (NNLS) on aligned, convolved templates:
\[
\min_{a_j \ge 0} \; \| D - \sum_j a_j T_j \|_2^2 + \lambda \sum_j a_j
\]
- \(\lambda\) adds parsimony (L1) to avoid kitchen‑sink fits.
- For multi‑modal fits, solve per modality and reconcile coefficients via weighted consensus or a joint objective (stacked matrices with block weights).

Output a `mixture_model.json` with coefficients, residuals, masks, and diagnostics.

---

## 7. Batch effects and drift correction

- **Order effects:** visualize control spectra across time; regress out linear drift when scientifically appropriate; record correction model.
- **Inter‑day normalization:** use the response function ratio of standards between days to compute a gain correction curve; apply as a **view**.
- **Instrument swaps:** never splice datasets without matching LSF and axis solutions; if unavoidable, convolve to the coarsest LSF and flag the merge in the manifest.

---

## 8. Multivariate comparisons across many samples

1. **Feature matrix**: rows = samples, columns = features (e.g., peak intensities/positions) standardized to unit variance.
2. **PCA** for exploratory structure; **UMAP** for visualization with caution; always show loading plots to retain interpretability.
3. **Clustering**: hierarchical (Ward linkage) on cosine distance of normalized spectra or feature vectors; cut tree with cophenetic correlation sanity check.
4. **Outlier policy**: define robust thresholds (e.g., median absolute deviation on principal components) and inspect raw spectra before exclusion.

All projections store the random seed, algorithm parameters, and the exact input matrix hash.

---

## 9. Visualization patterns for comparisons

- **Overlay** at matched resolution with unit badges and masks visible.
- **Difference spectrum** \(x-y\) with uncertainty bands.
- **Ratio** \(x/y\) for transmittance/reflectance comparisons when physics warrants it.
- **Waterfall/stacked plots** for cohorts, aligned by a landmark feature.
- **Heatmaps** of similarity matrices with dendrograms; interactive tooltips show per‑pair scorecards.

Export figures with captions explaining unit views, resolution, masks, and libraries used.

---

## 10. Acceptance criteria for “good enough to compare”

A spectrum enters the consolidated dataset only if:
- Unit/medium flags present and consistent (Ch. 5).
- Calibration RMS within instrument spec (Ch. 6 §2); Si/polystyrene/lamps pass checks.
- LSF estimated and stored; target FWHM set for overlays.
- Baseline model and masks recorded; SNR ≥ modality‑specific threshold.
- Provenance bundle complete (Ch. 8). Otherwise quarantine.

---

## 11. Outputs and reports

- `datasets/[DATASET_ID]/consolidated.h5` with spectra, views, and metadata.
- `datasets/[DATASET_ID]/features.parquet` and `scorecards/*.json` for pairwise comparisons.
- `reports/[DATASET_ID]/comparison_[YYYYMMDD].pdf`: overview, QC table, similarity matrices, cluster plots, mixture models, and appendices with method parameters.
- `CHECKSUMS.txt` for all exported files.

---

## 12. Worked mini‑examples

### 12.1 Carbonates A vs B (IR+Raman)
- Convolve IR to 4 cm⁻¹ and Raman to 6 cm⁻¹; compare 1300–1600 cm⁻¹ and 100–400/1550–1650 cm⁻¹ windows.
- Peak‑set Jaccard 0.90 (IR) and 0.86 (Raman); global score 0.88 → likely same polymorph.

### 12.2 Thin‑film anneal (UV–Vis)
- Ratio pre/post spectra; Tauc fit shift from 2.85 to 2.95 eV; cosine similarity 0.96 overall but clear band‑edge shift.

### 12.3 Astro standard vs target
- Continuum‑normalize and cross‑correlate; peak CCF at +38 km s⁻¹; after correcting templates, key metal lines align; scorecard reports per‑order similarities.

---

## 13. Cross‑links

- Ch. 2 (clean acquisition), Ch. 5 (units/axes), Ch. 6 (calibration/LSF), Ch. 3 (fusion data model), Ch. 7 (scoring), Ch. 8 (provenance), Ch. 11 (rubrics).

---

## 14. Reference anchors (full cites in Ch. 32)
- **Savitzky–Golay** smoothing and derivative spectra (for visualization, not as ground truth).
- **Kubelka–Munk** function for diffuse reflectance comparisons.
- **PCA/UMAP** for multivariate analysis of spectral cohorts.
- **NNLS** and L1‑regularized mixture modeling.
- **Cross‑correlation** methods for spectral alignment and velocity estimation.

> **Note.** All transformations in this chapter create **views** only. Raw arrays remain immutable. All parameters, constants, windows, and kernels must be recorded in the provenance ledger and report appendices.

