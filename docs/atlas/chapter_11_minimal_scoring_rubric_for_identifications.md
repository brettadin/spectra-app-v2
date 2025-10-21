# Chapter 11 — Minimal Scoring Rubric for Identifications

> **Purpose.** Define a transparent, compact, and testable scoring rubric for spectral identifications that any agent can apply and reproduce. The rubric converts features from one or more modalities into normalized scores, fuses them under explicit priors, and assigns confidence tiers with auditable thresholds.
>
> **Scope.** Atomic emission/absorption, FTIR/ATR, Raman, UV–Vis, fluorescence, plus optional validators (MS/XRD/NMR) as priors or penalties. Usable in both research and teaching modes.
>
> **Path notice.** Filenames and locations below are **placeholders** resolved by the app’s path resolver at runtime. Tokens such as `[SESSION_ID]`, `[DATASET_ID]`, `[MODALITY]`, `[YYYYMMDD]` must **not** be hardcoded.

---

## 0. Definitions

- **Candidate (M):** a hypothesized species/phase/mixture to be tested.
- **Feature:** a detected line/band/edge with center, FWHM, intensity, and uncertainties (see Ch. 3 schema).
- **Library set (L):** expected features for M from authoritative sources (Ch. 4) at the comparison resolution.
- **Instrument quality (q_k):** a modality‑specific quality weight derived from calibration/QC metrics (Ch. 2 & 6).
- **Modality weight (λ_k):** configuration weight per modality (Ch. 7), versioned in the manifest.

---

## 1. Per‑modality scoring S_k(M)

Each modality k contributes a **bounded** score S_k ∈ [0, 1] constructed from four components:

1. **Position agreement** (centers vs library):
   \[
   s_{pos} = \frac{1}{N_m}\sum_{i=1}^{N_m} \exp\!\Big[-\tfrac{1}{2}\Big(\tfrac{\Delta_i}{\sigma_i}\Big)^2\Big] \quad\text{with}\quad \sigma_i^2 = \sigma_{inst}^2+\sigma_{lib}^2
   \]
   where N_m is number of **matched** features, \(\Delta_i = x_i - \mu_i\).

2. **Coverage** (expected features observed):
   \[
   s_{cov} = \frac{N_m}{\max(1, N_{exp})}
   \]

3. **Parsimony penalties** (missing/extra):
   \[
   s_{pen} = 1 - \alpha\,\frac{\mathrm{FN}}{\max(1,N_{exp})} - \beta\,\frac{\mathrm{FP}}{\max(1,N_{obs})}
   \]

4. **Relative intensity consistency** (optional when absolute calibration is weak): use rank correlation or normalized chi‑square on **relative** intensities.
   - **Spearman option:** \( s_{int} = (\rho_{s}+1)/2 \in [0,1] \)
   - **Robust chi‑square option:** \( s_{int} = \exp\big(-\tfrac{1}{2}\chi_r^2\big) \)

Combine with modality‑specific component weights **w** that sum to 1:
\[
S_k = w_{pos}\,s_{pos} + w_{cov}\,s_{cov} + w_{pen}\,s_{pen} + w_{int}\,s_{int}
\]

**Default component weights (tune per course/lab):**
- Atomic: w = {pos 0.45, cov 0.25, pen 0.20, int 0.10}
- FTIR: w = {pos 0.35, cov 0.30, pen 0.20, int 0.15}
- Raman: w = {pos 0.40, cov 0.25, pen 0.20, int 0.15}
- UV–Vis: w = {pos 0.30, cov 0.30, pen 0.20, int 0.20}
- Fluorescence: w = {pos 0.25, cov 0.30, pen 0.20, int 0.25}

> **Note.** These are **placeholders** and must be tuned against the benchmark set (see §7). Store tuned values in `rubrics/[YYYYMMDD]/weights.json`.

---

## 2. Instrument quality weight q_k ∈ [0.3, 1.0]

Quality gates scale a modality’s contribution using objective QC metrics captured in the session manifest:

\[
q_k = \mathrm{clip}\Big(1 - a\,\frac{\mathrm{RMS}_{\lambda}}{\tau_{\lambda}} - b\,\frac{\Delta\mathrm{FWHM}}{\tau_{\mathrm{FWHM}}} - c\,\frac{1}{\mathrm{SNR}/\tau_{\mathrm{SNR}}},\;0.3,\;1.0\Big)
\]

- \(\mathrm{RMS}_{\lambda}\): wavelength (or shift) calibration RMS.
- \(\Delta\mathrm{FWHM}\): absolute deviation from expected LSF FWHM at comparison wavelength.
- SNR: signal‑to‑noise ratio in a baseline window.
- a, b, c, and thresholds \(\tau\) are modality‑specific and recorded in the rubric config.

**Rationale:** even “clean‑looking” spectra with poor calibration should not dominate the fusion.

---

## 3. Fusion into a global score

The global score is a prior‑weighted, quality‑weighted combination of per‑modality scores:
\[
G(M) = \sigma\!\left( \log P_0(M) + \sum_k \lambda_k\, q_k\, f(S_k) - \Gamma(M) \right)
\]
- \(P_0(M)\): prior from elemental constraints, environment, and source trust tiers (Ch. 7), expressed in log‑space.
- \(f(S_k)\): link function mapping [0,1] → log‑likelihood units. **Default:** \(f(S)=\log\tfrac{\epsilon+S}{\epsilon+1-S}\) with small \(\epsilon\approx 10^{-6}\).
- \(\Gamma(M)\): parsimony penalty (e.g., L1 on number of components or parameters in a mixture model).
- \(\sigma\): logistic squashing to keep G(M) in (0,1) for report readability; raw log‑posterior also stored.

**Configuration:** modality weights \(\lambda_k\) are in `rubrics/[DATE]/fusion.json` and version‑pinned in reports.

---

## 4. Confidence tiers and acceptance rules

Let \(M_1\) be the top candidate and \(M_2\) the runner‑up.

- **Tier A (High):**
  - \(G(M_1) \ge \theta_A\),
  - Gap \(\Delta = G(M_1) - G(M_2) \ge \delta_A\), and
  - Evidence from **≥2 modalities** with \(S_k \ge s_{min}\) for each.
- **Tier B (Moderate):** \(G(M_1) \ge \theta_B\) and either \(\Delta \ge \delta_B\) **or** one modality extremely strong \(S_k \ge s_{strong}\) with no cross‑modal contradictions.
- **Tier C (Provisional):** Otherwise; report nearest alternatives and recommend follow‑ups.

**Default thresholds (to be tuned):**
```
{
  "theta_A": 0.85, "delta_A": 0.15, "s_min": 0.55,
  "theta_B": 0.70, "delta_B": 0.08, "s_strong": 0.80
}
```

**Single‑modality exception:** if only one modality is available, allow Tier A only when: (i) that modality has unique, high‑diagnostic features (e.g., multiple unblended atomic lines with correct ratios), and (ii) SNR and calibration exceed stricter gates. Record the exception in the report.

---

## 5. Rubric JSON (portable, versioned)

**File** (placeholder): `rubrics/[YYYYMMDD]/rubric.json`
```json
{
  "component_weights": {
    "atomic": {"pos": 0.45, "cov": 0.25, "pen": 0.20, "int": 0.10},
    "ftir":   {"pos": 0.35, "cov": 0.30, "pen": 0.20, "int": 0.15},
    "raman":  {"pos": 0.40, "cov": 0.25, "pen": 0.20, "int": 0.15},
    "uvvis":  {"pos": 0.30, "cov": 0.30, "pen": 0.20, "int": 0.20},
    "fluor":  {"pos": 0.25, "cov": 0.30, "pen": 0.20, "int": 0.25}
  },
  "quality": {
    "a": {"atomic": 0.5, "ftir": 0.4, "raman": 0.5, "uvvis": 0.5, "fluor": 0.3},
    "b": {"atomic": 0.3, "ftir": 0.3, "raman": 0.3, "uvvis": 0.2, "fluor": 0.2},
    "c": {"atomic": 0.2, "ftir": 0.3, "raman": 0.2, "uvvis": 0.3, "fluor": 0.5},
    "tau_lambda": {"atomic": 0.2, "ftir": 0.5, "raman": 1.0, "uvvis": 0.3, "fluor": 0.5},
    "tau_fwhm": {"atomic": 0.3, "ftir": 0.5, "raman": 6.0, "uvvis": 0.5, "fluor": 0.8},
    "tau_snr": {"atomic": 50, "ftir": 30, "raman": 20, "uvvis": 50, "fluor": 30}
  },
  "fusion": {"lambda": {"atomic": 0.9, "ftir": 1.0, "raman": 0.9, "uvvis": 0.6, "fluor": 0.5}, "epsilon": 1e-6},
  "tiers": {"theta_A": 0.85, "delta_A": 0.15, "s_min": 0.55, "theta_B": 0.70, "delta_B": 0.08, "s_strong": 0.80},
  "penalty": {"L1_components": 0.05}
}
```
> Numbers are **illustrative** defaults. Tune using §7 and store tuned configs under a dated folder.

---

## 6. Report requirements

Every identification report must include a **Rubric Table** per candidate containing:

- Per‑modality: S_k, component scores (s_pos, s_cov, s_pen, s_int), q_k, λ_k, N_exp, N_m, FP, FN, calibration RMS, SNR, target FWHM.
- Global: prior log weight, penalty \(\Gamma\), raw log‑posterior, squashed G(M), confidence tier, \(\Delta\) to runner‑up.
- Alternatives: top‑3 with \(\Delta\) and the single most informative follow‑up measurement.

---

## 7. Validation & tuning protocol

1. **Benchmark set:** curated standards measured across modalities with ground truth (Ch. 7 §10). Freeze as `benchmarks/[DATE]/` with checksums.
2. **Grid search or Bayesian optimization** over component weights, λ_k, and tier thresholds to maximize **top‑1 accuracy** and **calibration** (Brier score) with k‑fold CV.
3. **Reliability curves:** plot predicted G(M) vs empirical accuracy; adjust link function temperature if over/under‑confident.
4. **Stress testing:** inject controlled errors (resolution mismatch, wavelength offsets, SNR drops) and verify graceful degradation.
5. **Lock‑in:** commit tuned rubric as a versioned artifact; update app defaults and documentation references.

---

## 8. Teaching mode rubric (grading)

For classroom “Mystery Sample” exercises (Ch. 10 §10), grade on:

- **Process (40%)**: complete manifests, proper calibration use, clean transforms ledger.
- **Evidence (40%)**: correct feature extraction, justified matches, correct use of priors.
- **Communication (20%)**: clear report, correct units, proper citations.

**Auto‑checks:** unit badges present, two‑modality corroboration if available, rubric table fields non‑empty, confidence tier rules satisfied.

---

## 9. Edge cases and exceptions

- **Mixtures:** allow multi‑component hypotheses with an L1 penalty; coverage and penalties computed per component then aggregated.
- **Isomers/near‑degenerates:** favor modalities with discriminatory power (low‑frequency Raman, ligand‑field UV–Vis) by increasing λ_k for the relevant modality in the tuned rubric.
- **Astrophysical templates:** require velocity consistency and mask tellurics; add a template‑fit quality term to s_pos via CCF peak width.

---

## 10. Cross‑links

- Ch. 3: feature schema and evidence graph.
- Ch. 5: units/axes (matching windows use σ_inst from here).
- Ch. 6: calibration and q_k derivation.
- Ch. 7: priors, penalties, and fusion logic.
- Ch. 8: provenance fields for storing rubric configs and results.
- Ch. 10: workflows feeding the rubric.

---

## 11. Reference anchors (add full citations in Ch. 32)

- Instrumental analysis and spectroscopy texts (Skoog/Holler/Crouch; Hollas; Lakowicz) for physical basis of features and uncertainties.
- Statistical learning and model calibration sources for scoring, likelihood links, and reliability curves.
- Authoritative data sources for libraries (Ch. 4) that define the expected features and uncertainties.

