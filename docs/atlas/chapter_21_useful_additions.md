# Chapter 21 — Useful Additions

> **Purpose.** List the non‑flashy, actually useful tools that save hours, prevent mistakes, and make the rest of this framework bearable in real labs and classrooms.
>
> **Scope.** Utilities, validators, converters, debuggers, small calculators, batch helpers, interop bridges, and accessibility features that wrap around the core acquisition→calibration→identification workflow (Ch. 2, 6, 7, 9, 11, 12, 15).
>
> **Path notice.** All filenames and directories below are **placeholders** and must be resolved at runtime via the app’s path resolver. Do **not** hardcode. Tokens like `[SESSION_ID]`, `[DATASET_ID]`, `[MODALITY]`, `[YYYYMMDD]`, `[INSTRUMENT_ID]` are variables.

---

## 0. Guiding rules
1. **No silent side‑effects.** Utilities operate on **views** or separate exports; raw data remain immutable (Ch. 8).
2. **Unit‑first.** Every helper displays and validates units/medium; refuses ambiguous inputs (Ch. 5).
3. **Deterministic.** Same inputs → same outputs; seeds logged when randomness exists.
4. **Explain‑on‑hover.** Every button has a rationale and a link into Docs (Ch. 13).

---

## 1. Validators and sanity checks

### 1.1 Unit & medium sentinel
- **What:** Quick validator that inspects a spectrum/bundle and confirms axis units, medium (air/vacuum), and canonicality.
- **UI:** Badge row: `λ nm | vacuum | canonical ✓`.
- **Output:** JSON report `validators/unit_report_[YYYYMMDD].json` with pass/fail and remediation hints.

### 1.2 Wavelength/shift RMS guard
- **What:** Computes RMS error vs. lamp/polystyrene/Si references; flags beyond tolerance.
- **Output fields:** `{rms, tol, pass, lsf_fwhm_at_ref}` stored in `qc/`.

### 1.3 LSF honesty check
- **What:** Compares declared FWHM to empirical FWHM from narrow lines; warns on drift.

### 1.4 Response function checker
- **What:** Plots sensitivity vs time; raises amber when using response outside validity window (Ch. 6 §7).

### 1.5 Evidence graph lint
- **What:** Ensures every hypothesis has at least one supporting feature per contributing modality and cites library versions (Ch. 3).
- **Output:** `lint/evidence_[DATASET_ID].json` with missing edges and stale citations.

---

## 2. Calculators and micro‑tools

- **Raman shift & error**: λ₀ ± δλ → Δ\(\tilde{\nu}\) with uncertainty propagation; copyable snippet for reports (Ch. 5).
- **Air↔vacuum conversion**: Ciddor/Edlén with parameter panel; UI shows equation and inputs (Ch. 5).
- **Beer–Lambert helper**: ε from slope, LOD/LOQ from blank σ; prints the exact formula used and reference.
- **Tauc assistant**: preview fit and energy window selection; outputs the window used but stores result only when run via the main pipeline.
- **Velocity frames**: convert observed wavelengths to barycentric and LSR frames; records ephemeris source (Ch. 6).

All calculators export `calc/[NAME]_[YYYYMMDD].json` for provenance if the values are embedded in a report.

---

## 3. Batch helpers

### 3.1 Batch feature extraction
- **CLI:** `spectra batch-fit --glob sessions/[SESSION_ID]/**/processed/*.csv --model voigt --window 100:1800`
- **Behavior:** Uses saved defaults; writes per‑file `features.parquet` and a manifest delta.

### 3.2 Batch axis/LSF harmonizer (views only)
- **CLI:** `spectra harmonize --dataset [DATASET_ID] --target-fwhm 6.0cm-1 --out views/`
- **Behavior:** Produces comparison views at the specified FWHM with masks captured.

### 3.3 Batch report exporter
- **CLI:** `spectra report --dataset [DATASET_ID] --rubric rubrics/[YYYYMMDD]/rubric.json --out exports/[...]`
- **Behavior:** Renders PDF + data bundle with `CHECKSUMS.txt` (Ch. 8 §9).

---

## 4. Interop bridges

- **JCAMP importer** with dialect normalizer; rejects missing units; maps to canonical schema (Ch. 12 §4).
- **FITS reader** honoring WCS for spectral axis; warns on missing `BUNIT` (Ch. 12 §7).
- **CSV+sidecar** exporter for teaching; pretty tables plus JSON sidecar (Ch. 12 §3).
- **Parquet line‑list loader** for HITRAN‑style tables with dictionary encoding (Ch. 12 §6).

**Policy:** every bridge is versioned as an **adapter** in the source registry (Ch. 4) with tests and example fixtures.

---

## 5. Visualization toolbelt

- **Overlay manager** with synchronized cursors and unit badges; explicit FWHM banner when convolved (Ch. 6).
- **Difference/ratio plots** with uncertainty bands and mask shading.
- **Peak‑table cross‑linking**: click a row to highlight that region in the plot and the evidence graph node (Ch. 3).
- **Heatmaps** for similarity matrices with dendrogram thumbnails; tooltips show pairwise scorecards (Ch. 15).

Exports include SVGs with embedded metadata and captions.

---

## 6. Dataset ops and comparators

- **Consolidator UI**: assembles `datasets/[DATASET_ID]/consolidated.h5` from session bundles (Ch. 15 §2).
- **Version diff**: compares `source_id@version` pairs; shows changed lines/bands and uncertainties.
- **Rubric diff**: highlights deltas in component weights, modality weights, and thresholds between rubric versions (Ch. 11 §5).

---

## 7. Troubleshooting and forensic aids

- **Transform ledger viewer**: timeline of steps with parameters; jump‑to‑plot at any step (Ch. 8 §3).
- **Residual inspector**: plots fit residuals, baseline models, and bad regions; exports a “why this failed” snippet.
- **Noise estimator**: robust σ from baseline windows; stamps SNR into the manifest.
- **Drift dashboard**: graphs wavelength RMS, response stability, and FWHM vs time per instrument.

---

## 8. Accessibility & inclusion (non‑optional, actually useful)

- **Keyboard‑first** controls for all frequent actions; discoverable shortcuts list.
- **Color‑safe presets** and high‑contrast mode.
- **Alt‑text** required for all exported figures; auto‑generated first draft editable in the Report Builder.
- **Captioned mini‑videos** for Teaching Mode demos (Ch. 13).

---

## 9. Admin & housekeeping utilities

- **Cache manager**: shows which libraries/models occupy space; safe eviction by `source_id@version`.
- **License auditor**: flags datasets not permitted for redistribution; exports a license appendix (Ch. 4 §7).
- **Checksum auditor**: walks `sessions/` and `datasets/` to verify hashes; writes a summary.
- **Lockfile capture**: one‑click export of environment lockfiles with session bundles (Ch. 8 §6).

---

## 10. Security/privacy guards

- **Offline mode** hard switch; blocks networked adapters unless explicitly whitelisted (Ch. 14 §9).
- **PII scrubber** for manifests used in teaching exports (operator initials only, if policy requires).
- **Sandbox runner** for notebook snippets: no network, read‑only session access, transforms logged (Ch. 14 §6).

---

## 11. JSON stubs (portable configs)

**Validator policy** `configs/validator_policy.json`:
```json
{
  "unit_required": true,
  "medium_required": true,
  "rms_tol_nm": {"uvvis": 0.2},
  "rms_tol_cm-1": {"ftir": 0.5, "raman": 1.0},
  "snr_min": {"uvvis": 50, "ftir": 30, "raman": 20}
}
```

**Plot profile** `plot_profiles/minimal.json`:
```json
{
  "grid": false,
  "tick_density": "compact",
  "font_size": 12,
  "show_masks": true,
  "unit_badges": true
}
```

---

## 12. Acceptance tests (ship with app)

- Unit/medium sentinel rejects unitless files; helpful error text links to Ch. 5.
- Wavelength RMS guard fails when lamp lines are perturbed beyond tolerance; UI shows red badge.
- Evidence graph lint fails when a hypothesis lacks supporting features or citations.
- Batch helpers run deterministically on fixtures; outputs match checksums.

---

## 13. Cross‑links

- Ch. 3 (evidence graph), Ch. 4 (source registry & adapters), Ch. 5 (unit/medium enforcement), Ch. 6 (LSF/response), Ch. 8 (provenance), Ch. 9 (feature map), Ch. 11 (rubric), Ch. 12 (formats), Ch. 13 (Docs/Teaching), Ch. 15 (consolidation).

---

## 14. Future upgrades

- **Template differ**: visual diff of library templates before/after convolution to the local LSF.
- **QC recommender**: suggests the single next check with highest expected value given the current failures.
- **Report explainer**: generates a plain‑language appendix explaining each rubric term used, with citations.

> These are the unsexy features that prevent 90% of avoidable pain. Keep them boring, reliable, and versioned.

