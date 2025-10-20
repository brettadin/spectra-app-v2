# Chapter 17 — Goals and Outcomes

> **Purpose.** Define precise scientific, educational, and engineering goals for this project, with measurable outcomes, milestones, and acceptance criteria. Align day‑to‑day work with the long‑term research report and pedagogy.
>
> **Scope.** Campus spectroscopy across modalities (atomic/UV–Vis, FTIR/ATR, Raman, fluorescence) and astrophysical spectra; application development, data curation, ML assists, documentation, and teaching deployments.
>
> **Path notice.** Filenames and directories below are **placeholders** to be resolved at runtime by the app’s path resolver. Tokens `[SESSION_ID]`, `[DATASET_ID]`, `[MODALITY]`, `[YYYYMMDD]`, `[MODEL_ID]` etc. **must not** be hardcoded.

---

## 0. North‑star objectives (what success looks like)

1. **Scientific:** cross‑modal identifications with documented confidence tiers, reproducible by independent agents/semesters using the same inputs.
2. **Educational:** students complete an end‑to‑end workflow (acquire → calibrate → identify → report) with correct unit handling and provenance.
3. **Engineering:** the app runs deterministically offline, with unit‑safe transforms and full provenance (Ch. 5, 8), on standard campus machines.
4. **Community & Openness:** data and methods export cleanly with citations and licenses; selected datasets published to an institutional repository with DOIs.

---

## 1. Measurable outcomes (S.M.A.R.T.)

### 1.1 Identification accuracy & calibration
- **Top‑1 identification accuracy (benchmarks):** ≥ **[TARGET 0.85–0.95]** across modalities combined (Ch. 7, 11).
- **Reliability (Brier/ECE):** ECE ≤ **[TARGET 0.05]** for G(M) confidence scores (Ch. 11 §7).
- **Wavelength/shift RMS vs standards:** within **instrument spec** and ≤ **[TARGET]** per modality (Ch. 6 tests).

### 1.2 Reproducibility & determinism
- **Bit‑wise reproducible runs:** 100% on benchmark sessions with pinned seeds and versions (Ch. 8 §11).
- **Manifest completeness rate:** ≥ **[TARGET 0.98]** sessions with all required fields present.

### 1.3 Education & usability
- **Onboarding time:** novice completes Ch. 2 SOP + Ch. 7 identification + export under **[TARGET 90 min]**.
- **Quiz mastery:** ≥ **[TARGET 85%]** average on unit/axes and calibration quizzes (Ch. 13).
- **Lab rubric pass rate:** ≥ **[TARGET 90%]** of teams meet Tier B or better (Ch. 11 §8).

### 1.4 Performance
- **Render latency:** spectral pans/zooms ≤ **[TARGET 60 ms]** for N ≤ 1e6 points (virtualized rendering).
- **Cross‑correlation runtime:** ≤ **[TARGET 3 s]** per template on typical laptop CPU for N ≤ 1e5, with LSF convolution cached.

> **Note.** Fill TARGET placeholders during pilot; store in `benchmarks/[DATE]/targets.json` and cite in reports.

---

## 2. Milestones and timeline (indicative)

### Phase R0 — Foundations (Weeks 0–4)
- Chapter 1–6 SOPs & unit tests green.
- Ingest Manager and calibration artifacts live (Ch. 9 §2).
- Dataset: “Calibration Lamp Atlas” v1 (Ch. 10 §3).

### Phase R1 — Identification Loop (Weeks 5–8)
- Evidence graph & fusion (Ch. 3, 7) produce ranked hypotheses with rubric tables (Ch. 11).
- Teaching Mode v1; two guided labs (Raman Si; FTIR+ATR basics) (Ch. 13).

### Phase R2 — Consolidation & Reports (Weeks 9–12)
- Consolidated dataset build (Ch. 15) with comparison scorecards.
- Report Builder generates export bundles with DOIs for campus datasets (optional) (Ch. 8 §15).

### Phase R3 — ML Assists (Weeks 13–16)
- Taggers and template suggesters integrated with model cards (Ch. 16). Offline retraining pipeline documented.

Each phase ends with a **go/no‑go checklist** referencing chapter acceptance tests.

---

## 3. Acceptance criteria (per chapter)

- **Ch. 2:** All SOP checklists pass; backgrounds and reference checks within tolerance.
- **Ch. 5:** Unit toggles and conversions pass round‑trip tests; Raman shift math validated on fixtures.
- **Ch. 6:** LSF/FWHM and wavelength solutions recorded with RMS and residual plots; response functions stable across day.
- **Ch. 7:** Identification returns deterministic ranked hypotheses; per‑feature evidence visible.
- **Ch. 8:** Transform ledger complete; bundle digests verified; environment lockfile present.
- **Ch. 9:** UI shows unit badges, LSF banners, provenance icon; Ingest Manager blocks unitless data.
- **Ch. 11:** Rubric thresholds and weights versioned; reliability curves included.
- **Ch. 12:** File saves/load round‑trip (CSV+JSON ↔ HDF5 ↔ Parquet tables) with hashes unchanged.
- **Ch. 13:** Lessons compile; quizzes auto‑grade; report templates render.
- **Ch. 15–16:** Consolidated comparisons reproducible; ML predictions calibrated and explained.

---

## 4. Datasets and coverage goals

- **Calibration set:** Hg/Ne/Xe/He lamps, polystyrene (IR), Si 520.7 (Raman), holmium filter (UV–Vis), CALSPEC star.
- **Mineral set:** ≥ **[N=50]** specimens across silicates, carbonates, oxides with IR+Raman.
- **Gas set:** CO₂, CO, CH₄, H₂O, N₂O at **[≥3]** pressures × **[≥2]** temperatures with FTIR (± Raman).
- **Thin film set:** **[N=20]** films with UV–Vis bandgaps and Raman phase markers.

Coverage tables live at `datasets/catalog.json` with checksums and licensing.

---

## 5. Risk register and mitigations

| Risk | Impact | Likelihood | Mitigation |
|---|---|---|---|
| Missing units/medium flags | Blocks ingest or corrupts comparisons | Medium | Hard block in Ingest Manager; Chapter 5 enforcement; training |
| Calibration drift mid‑semester | Identification accuracy degrades | Medium | Scheduled checks (Si/polystyrene/lamps); drift dashboards; segmented solutions |
| Library version changes | Non‑reproducible results | Medium | Pin `source_id@version`; cache with checksums; side‑by‑side comparison tool (Ch. 4) |
| Student data quality variance | Noisy training/benchmarks | High | Gold‑standard bench set; quarantine rules; Teaching Mode guardrails |
| Over‑confident ML | Misleading suggestions | Medium | Probability calibration required; Tier gates (Ch. 11); human‑in‑the‑loop review |
| Storage sprawl | Hard to find and verify data | Medium | Content‑addressable layout; manifests; exports with `CHECKSUMS.txt` |

---

## 6. Governance, reviews, and reporting

- **Weekly** triage: ingest errors, calibration drifts, rubric exceptions.
- **Bi‑weekly** review: benchmark accuracy, ECE, performance metrics; doc drift checks.
- **End‑phase** gate: run determinism and benchmark suites; publish release notes and updated docs bundle.
- **Public artifacts:** `reports/[DATE]/release_notes.md`, `benchmarks/[DATE]/summary.json`, and `docs/releases/[SEMVER]/`.

---

## 7. Roles and responsibilities (RACI)

| Task | Student | TA | PI/Faculty | App Maintainer |
|---|---|---|---|---|
| Acquisition & manifests | R | A/C | I | I |
| Calibration & QC | R | A | C | I |
| Identification & reporting | R | A | C | I |
| Source registry & licensing | I | C | A | R |
| Rubric tuning & benchmarks | C | R | A | R |
| Docs & Teaching Mode | R | A | C | C |
| ML model curation | I | C | A | R |

R = Responsible, A = Accountable, C = Consulted, I = Informed.

---

## 8. Deliverables checklist (by phase)

- **R0:** Ingest Manager; unit conversion tests; calibration artifacts; minimal datasets.
- **R1:** Identification engine; evidence graph; rubric v1; two guided labs.
- **R2:** Consolidation pipeline; report builder; dataset DOIs (optional).
- **R3:** ML assists with model cards; offline retraining scripts; improved Teaching Mode.

Each deliverable links to a test or lesson proving it works.

---

## 9. Budget & resource sketch (indicative, campus‑scale)

- **Consumables:** cuvettes, ATR crystals maintenance, gas cylinders, polystyrene films, standards `[BUDGET_PLACEHOLDER]`.
- **Instrument time:** allocation per course `[HOURS_PLACEHOLDER]` with booking calendar.
- **Compute:** lab workstations; optional server `[SPECS_PLACEHOLDER]` for class deployments.
- **Storage:** external drives or departmental NAS; backups weekly with checksum audits.

> Replace placeholders with department‑approved numbers; record in `admin/budget_[YYYY].json`.

---

## 10. Evaluation methods

- **Technical:** run benchmark suite; compare accuracy, reliability, performance to targets; publish `benchmarks/[DATE]` bundle.
- **Pedagogical:** pre/post tests; rubric grades; survey on confidence with units/calibration/provenance.
- **Operational:** ingest error rate; manifest completeness; time‑to‑report.

All evaluations export to `reports/evaluations_[YYYYMM].zip` with anonymized aggregates.

---

## 11. Exit criteria and expansion gates

- **Exit:** All R3 deliverables complete; targets met or justified; docs up to date; Sources (Ch. 32) compiled.
- **Expansion gates:** spectral imaging support, live instrument bridges, federated learning pilots (Ch. 14–16 future upgrades) approved by PI after risk review.

---

## 12. Cross‑links

- Ch. 2 (SOPs), Ch. 5 (units), Ch. 6 (calibration), Ch. 7 (identification), Ch. 8 (provenance), Ch. 9 (features), Ch. 11 (rubrics), Ch. 12 (formats), Ch. 13 (learning), Ch. 15–16 (consolidation & AI).

---

## 13. Reference anchors (full citations in Ch. 32)

- Evaluation and assessment in STEM labs; reliability and probability calibration literature; open‑science best practices; format standards (HDF5, Parquet, FITS, JCAMP‑DX); IUPAC/ACS style.

> **Reminder.** Replace every placeholder with department‑approved values before final report submission; record access dates, DOIs, and versions in Chapter 32 (Sources).

