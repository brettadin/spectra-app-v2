# Chapter 18 — Future Goals

> **Purpose.** Lay out the concrete next steps and stretch targets for the spectroscopy program and app: scientific expansions, instrumentation upgrades, software capabilities, data practices, and teaching deployments.
>
> **Scope.** Campus instruments (atomic/UV–Vis, FTIR/ATR, Raman, fluorescence), astrophysical tie‑ins, cross‑campus collaborations, and the application stack. Plans span near‑term (0–12 months), mid‑term (12–36 months), and moonshots (36–60+ months).
>
> **Path notice.** Filenames and directories are **placeholders** and resolved by the app’s path resolver at runtime. Tokens like `[SESSION_ID]`, `[DATASET_ID]`, `[MODALITY]`, `[YYYYMMDD]`, `[MODEL_ID]` must **not** be hardcoded.

---

## 0. North‑star themes
1. **Trustworthy cross‑modal identification at scale.** Larger, cleaner reference sets with known uncertainties; reproducible scoring (Ch. 11) and transparent provenance (Ch. 8).
2. **Teaching that sticks.** Self‑paced labs, auto‑graded checkpoints, and consistent reporting (Ch. 13) across semesters.
3. **Open, citable datasets.** Campus‑curated spectra with DOIs and exact methods (Ch. 8 §15) for reuse and benchmarking.
4. **Physics‑aware ML.** Assistance that respects units, resolution, and selection rules (Ch. 16), with fully calibrated probabilities.

---

## 1. Near‑term goals (0–12 months)

### 1.1 Scientific
- **Gas library v1** (FTIR ± Raman): CO₂, CO, CH₄, H₂O, N₂O at ≥3 pressures × ≥2 temperatures with Voigt fits and cross‑section overlays.
- **Mineral atlas v1**: ≥50 specimens with paired Raman/ATR‑IR and links to external library IDs.
- **Thin‑film bandgaps v1**: 20 films with UV–Vis Tauc fits plus Raman phase checks.

### 1.2 Instrumentation & SOPs
- **LSF characterization kit** for each instrument; store kernels with validity windows (Ch. 6).
- **Raman λ₀ measurement fixture** to reduce shift uncertainty; log λ₀ per session (Ch. 5 §4).

### 1.3 Application
- **Evidence graph UI** end‑to‑end (Ch. 3) with click‑through to features and provenance.
- **Report Builder v1** with rubric table and alternative hypotheses (Ch. 11).
- **Library registry dashboard** with version pinning and license notes (Ch. 4).

### 1.4 Education
- **Two guided labs** finalized: Raman Si check + ATR basics (Ch. 13).
- **Mystery Sample practicum** release (Ch. 10 §10) with auto‑grading hooks.

**Exit criteria:** benchmark top‑1 ≥ [TARGET], ECE ≤ [TARGET], manifest completeness ≥ 0.98; two classes run the full workflow.

---

## 2. Mid‑term goals (12–36 months)

### 2.1 Scientific expansions
- **Volatile organics & solvents** panel in IR/Raman with temperature‑dependent shifts and band shapes.
- **Coordination compounds** set (UV–Vis ligand‑field + Raman): map oxidation‑state signatures.
- **Environmental monitoring pilot**: open/long‑path FTIR time series with retrievals for campus air.

### 2.2 Instrumentation upgrades
- **Low‑frequency Raman module** (down to ~50 cm⁻¹) for polymorph discrimination.
- **Temperature‑controlled gas cell** for line‑shape validation and didactic kinetics.
- **Integrating sphere** or DRS accessory standardization for UV–Vis reflectance.

### 2.3 Application capabilities
- **Spectral‑imaging beta**: 2D/3D cubes with ROI extraction and per‑pixel identification views.
- **Template workshop**: convolve external libraries to local LSF on demand; compare versions side‑by‑side.
- **Active‑inference helper**: propose the next measurement to maximize information gain (Ch. 7 §13).

### 2.4 ML and analytics
- **Physics‑aware taggers** for IR/Raman functional groups with calibrated probabilities and SHAP explanations (Ch. 16 §7–8).
- **Mixture NNLS pipeline** with parsimony and cross‑modal reconciliation (Ch. 15 §6).

**Exit criteria:** new datasets published with DOIs; spectral‑imaging MVP used in one course; taggers reach macro‑F1 ≥ [TARGET].

---

## 3. Moonshots (36–60+ months)

- **Federated campus consortium**: shared rubric, schemas, and DOI’d datasets; privacy‑preserving model sharing (Ch. 16 §16).
- **Live instrument bridges**: vendor‑agnostic capture of manifests and calibration artifacts in real time (Ch. 14 §15).
- **Physics‑informed networks** embedding selection rules and line shapes; uncertainty‑aware identification with priors from Chapter 7.
- **Spectral‑spatial discovery**: joint modeling of cubes to map composition across microstructures or astronomical fields.

**Evidence of success:** cross‑site reproducibility on blind datasets; published comparisons showing portability of our pipeline.

---

## 4. Research questions to drive upgrades

1. **How much resolution do we really need?** Quantify identification gains vs FWHM and SNR across modalities.
2. **What’s the minimal cross‑modal set** for confident identification of polymers, minerals, or thin films?
3. **How to best calibrate probabilities** so G(M) tracks empirical accuracy across semesters and instruments? (Ch. 11, 16)
4. **When do baseline models bias identification?** Compare penalties vs explicit continuum models per modality.
5. **How portable are calibrations** across instruments and days? Model drift and propose segmented solutions.

Each question maps to a semester‑sized project with datasets, analysis notebooks, and a short paper.

---

## 5. Roadmap tables

### 5.1 Features (indicative)
| Feature | Owner | Effort | Risk | Dep | Target |
|---|---|---:|:---:|---|---|
| Evidence graph UI | App | M | L | Ch. 3 | R0 |
| Report Builder v1 | App | M | L | Ch. 11 | R0 |
| Library registry dashboard | App | S | L | Ch. 4 | R0 |
| Active‑inference helper | App/ML | M | M | Ch. 7,16 | R2 |
| Spectral‑imaging beta | App | L | M | Ch. 14 | R2 |
| Template workshop | App | M | L | Ch. 4,6 | R2 |
| Live instrument bridges | App | L | H | Ch. 14 | R3 |

Effort: S/M/L ~ weeks/months/semester. Risk: L/M/H (technical + schedule). Dep: primary chapter dependencies.

### 5.2 Datasets
| Dataset | Size | QC Gates | Release |
|---|---:|---|---|
| Gas v1 | ~100 spectra | Polystyrene check, pressure/temperature logs | R0 |
| Mineral atlas v1 | ~150 spectra | Si 520.7 cm⁻¹, ATR reproducibility | R1 |
| Thin films v1 | ~60 spectra | Tauc linearity, Raman phase markers | R1 |
| Environmental FTIR pilot | ~1e4 time points | humidity masks, response stability | R2 |

---

## 6. Governance, ethics, and openness

- **Licensing & attribution**: registry enforces source terms; export packages include full citations (Ch. 4, 8, 32).
- **PII & privacy**: minimal operator metadata; anonymized teaching exports (Ch. 8 §12).
- **Reproducibility**: determinism tests as release gates (Ch. 14 §7).
- **Transparency**: public method cards for DOI’d datasets; W3C PROV export planned (Ch. 8 §15).

---

## 7. Risks and mitigations (forward‑looking)

| Risk | Mitigation |
|---|---|
| Library version drift alters results | Pin `source_id@version`, keep multiple versions in cache; side‑by‑side comparator (Ch. 4) |
| Over‑reliance on ML suggestions | Keep physics‑first scoring; require calibrated probabilities; human‑in‑the‑loop edits logged (Ch. 16) |
| Lab turnover | Teaching Mode and docs bundle ensure continuity; benchmark datasets anchor rubrics (Ch. 13, 15) |
| Storage growth | Content‑addressable storage; periodic dedup; checksum audits (Ch. 8, 12) |

---

## 8. Budget and resources (placeholders)

- **Consumables**: standards, cuvettes, ATR crystals maintenance `[BUDGET_PLACEHOLDER]`.
- **Instrumentation**: low‑freq Raman module, temp‑controlled gas cell `[BUDGET_PLACEHOLDER]`.
- **Compute/Storage**: workstation + NAS `[BUDGET_PLACEHOLDER]`.
- **Student support**: graders, doc editors `[BUDGET_PLACEHOLDER]`.

Record finalized numbers in `admin/budget_[YYYY].json`.

---

## 9. Cross‑links
- Ch. 2 (SOPs), Ch. 3 (fusion), Ch. 4 (source registry), Ch. 5 (units), Ch. 6 (calibration), Ch. 7 (identification), Ch. 8 (provenance), Ch. 9 (features), Ch. 10 (workflows), Ch. 11 (rubrics), Ch. 12 (formats), Ch. 13 (learning), Ch. 15–16 (consolidation & AI), Ch. 32 (Sources).

---

## 10. References (anchor list; full citations in Ch. 32)
- Best practices in open spectral data curation and DOI minting.
- Probability calibration and reliability diagrams (classification/regression).
- Physics‑informed ML and uncertainty quantification literature.
- Standards: HDF5, Parquet, FITS/WCS, JCAMP‑DX; IUPAC Gold Book; CODATA constants.

> Replace placeholder targets and budgets with department‑approved values during the pilot; record exact versions/access dates of sources in Chapter 32 (Sources).

