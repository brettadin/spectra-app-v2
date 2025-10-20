# Chapter 10 — Campus Workflows That Actually Work

> **Purpose.** Package realistic, repeatable lab and observatory workflows that produce clean, comparable spectra across semesters, and feed directly into identification/prediction (Ch. 7). Each workflow includes goals, inputs, step‑by‑step SOPs, QC gates, outputs, success metrics, and upgrade notes.
>
> **Scope.** Campus‑available instruments: atomic emission/AAS, FTIR/ATR (incl. gas cells), Raman, UV–Vis, fluorescence; optional telescope/archival spectra.
>
> **Path notice.** All paths are **placeholders** to be resolved at runtime by the app’s path resolver. Tokens like `[SESSION_ID]`, `[DATASET_ID]`, `[INSTRUMENT_ID]`, `[YYYYMMDD]` are variables and must **not** be hardcoded.

---

## 0. Shared conventions
- Canonical axes per modality (Ch. 5).
- Resolution/LSF captured and respected (Ch. 6).
- Full provenance bundle for every run (Ch. 8).
- Teaching variant in each workflow that reduces steps but preserves scientific integrity.

---

## 1) Gas‑phase IR/Raman Library Build (CO₂, CO, CH₄, H₂O, N₂O…)
**Goal.** Build a campus reference set for common gases at multiple pressures/temperatures with alignment to evaluated line lists.

**Inputs.** FTIR with purge; long‑path gas cell (or short path if that’s what you’ve got); optional Raman with gas cell; standards (cylinders or generated vapors); pressure/temperature readouts.

**SOP.**
1. Initialize `[SESSION_ID]`; verify purge; capture **background** and **polystyrene** check.
2. For each gas **species** × **pressure set**: evacuate, fill to target, acquire FTIR at ≥2 resolutions (e.g., 4 and 0.5 cm⁻¹ if available); log `[PRESSURE_TORR]`, `[TEMP_K]`, `[PATH_LENGTH_CM]`.
3. Optional Raman: excite at 532/785 nm; log exact λ₀; acquire low‑frequency modes if hardware allows.
4. Export interferograms and processed spectra; bind HITRAN/HITEMP metadata in manifest.

**QC gates.** Polystyrene within spec; pressure trace monotone; SNR threshold met; no unlogged baseline smoothing.

**Outputs.** `sessions/[SESSION_ID]/ftir/raw|processed/*`, `raman/*`, `manifest.json`; derived cross‑sections at instrument resolution; alignment notes.

**Success metrics.** Line‑center residuals vs line list within tolerance; consistent Voigt widths vs P,T; reproducible Raman shifts.

**Upgrades.** Temperature‑controlled cell; implement automated synthesis of synthetic spectra from line parameters for didactic overlays.

---

## 2) Mineral Set: Raman + ATR‑IR + Diffuse UV–Vis
**Goal.** Build a mineral atlas for teaching and identification benchmarks.

**Inputs.** Known mineral specimens; Raman microscope/portable; FTIR‑ATR; UV–Vis with integrating sphere for diffuse reflectance.

**SOP.**
1. Assign `[SAMPLE_ID]` per specimen; photo and note provenance.
2. Raman: capture Si reference, then sample at ≥2 laser wavelengths if fluorescence is an issue; record power and objective.
3. ATR‑IR: clean crystal; collect background; acquire at 4 cm⁻¹; repeat for contact repeatability.
4. UV–Vis DRS: measure white reference; measure sample; compute reflectance and approximate bandgap where relevant.

**QC gates.** Raman Si at 520.7 cm⁻¹ within tolerance; ATR reproducibility across touches; reflectance >0 and ≤1 with flat white reference.

**Outputs.** Per‑specimen bundle with Raman, IR, and DRS; cross‑links to external library IDs.

**Success metrics.** Library matches top‑1 or top‑3 across modalities; polymorphs distinguished by low‑freq Raman/IR.

**Upgrades.** Add micro‑Raman mapping; micro‑ATR on polished sections; texture/strain mapping overlays.

---

## 3) Calibration Lamp Atlas (Hg/Ne/Xe/He + metal halide)
**Goal.** Create a campus atlas for wavelength calibration and teaching atomic structure.

**Inputs.** Discharge lamps; fiber spectrometer; stable mount; manufacturer line sheets.

**SOP.**
1. Warm up lamp and spectrometer; acquire dark.
2. Acquire emission at multiple slit widths and integration times.
3. Fit wavelength solution; store residuals and withheld‑line checks; tag **air vs vacuum**.

**QC gates.** RMS wavelength residual ≤ instrument spec; no saturated peaks; instrument drift trended across sessions.

**Outputs.** Cal curves `cal/wavelength/*.json`, annotated line spectra, plot overlays.

**Success metrics.** Reusable calibration curve per lamp with documented drift; improved student identification speed.

**Upgrades.** Add intensity calibration with calibrated source; add Stark/pressure broadening demos.

---

## 4) UV–Vis Quant Kit (Beer–Lambert) — metal complex or dye
**Goal.** Quantify a solute via absorbance and validate linearity and detection limits.

**Inputs.** UV–Vis spectrophotometer; standards; matched cuvettes; solvent/blank.

**SOP.**
1. Prepare ≥5‑point standard series and blanks; record path length and cuvette ID.
2. Baseline with solvent; scan standards then unknowns, randomized order.
3. Fit calibration curve; compute LOD/LOQ using standard deviation of blank and slope; store method.

**QC gates.** Linear range R² ≥ 0.995; residuals structureless; stray‑light check passed.

**Outputs.** Calibration model file + stats; absorbance spectra; method JSON.

**Success metrics.** Recovery 95–105% on spike; inter‑day slope variation within threshold.

**Upgrades.** Automatic orthogonal distance regression; temperature‑dependent ε tracking.

---

## 5) Fluorescence Environment Probe (Stokes shift & quenching)
**Goal.** Demonstrate environment sensitivity using a standard fluorophore and quenchers.

**Inputs.** Fluorimeter; quinine sulfate or fluorescein; quenchers (e.g., KI); buffer series; correction file for instrument response.

**SOP.**
1. Record excitation λ and slit widths; acquire emission spectra across conditions; correct for instrument response.
2. If doing quenching, produce Stern–Volmer plot; store fit and uncertainty.

**QC gates.** No inner‑filter artifacts (check absorbance ≤0.1–0.2 at excitation); stable lamp output; reproducible Stokes shift.

**Outputs.** Excitation/emission scans; corrected emission; fit parameters and plots.

**Success metrics.** Linear Stern–Volmer region; consistent quantum‑yield proxy across replicates.

**Upgrades.** Time‑resolved measurements; oxygen‑quenching demo with deoxygenation steps logged.

---

## 6) Semiconductor Thin Films: Bandgap + Structure
**Goal.** Estimate optical bandgap and assess crystallinity.

**Inputs.** UV–Vis with integrating sphere or transmission setup; Raman; optional XRD as validator.

**SOP.**
1. Acquire transmission/reflectance; compute absorption coefficient and Tauc plot (store model choice: direct/indirect).
2. Raman: collect spectra to assess phonon modes and disorder (D/G/2D for carbons; LO/TO modes for III–V/oxide systems).

**QC gates.** Clear linear Tauc region; Raman peak positions within known ranges; LSF matched for overlays.

**Outputs.** Bandgap estimate with confidence; Raman assignment notes; overlays.

**Success metrics.** Bandgap within literature range for reference films; Raman indicators match expected phase.

**Upgrades.** Ellipsometry import; temperature‑dependent Raman for phase transitions.

---

## 7) Polymer/Organic Identification: IR + Raman
**Goal.** Identify common polymers/organics via complementary vibrational spectra.

**Inputs.** ATR‑IR; Raman with 532/785 nm options; polymer standards set.

**SOP.**
1. ATR: acquire with consistent pressure; note carbonyl and backbone bands.
2. Raman: select laser to minimize fluorescence; collect with exact λ₀ logged.
3. Cross‑match against internal library; confirm with diagnostic pairings (e.g., IR C=O with Raman symmetric stretches).

**QC gates.** ATR reproducibility; Raman baseline documented; Si check passed.

**Outputs.** Paired IR/Raman with feature tables; top‑N identifications.

**Success metrics.** Correct ID for standards; robustness to fluorescence via laser choice.

**Upgrades.** Add mapping and crystallinity metrics; build teaching “unknowns” set.

---

## 8) Observatory Tie‑In: Standards + Science Target
**Goal.** Produce an absolute‑calibrated spectrum and identify atomic/molecular features.

**Inputs.** Campus telescope + spectrograph (or archival spectra); standard star list; atmospheric extinction curve or derive per session.

**SOP.**
1. Record site/time; acquire standard star(s) and target; capture calibration frames as applicable.
2. Reduce data; derive sensitivity function using standards; correct science target; document barycentric correction.
3. Identify Balmer/He lines; cross‑correlate molecular templates convolved to instrument LSF.

**QC gates.** Sensitivity function smooth and stable; residuals vs standard minimal; wavelength solution verified with sky lines or lamps.

**Outputs.** Flux‑calibrated spectra with uncertainties; velocity context; identification report.

**Success metrics.** Radial velocity consistent with catalog within tolerance; features matched at expected strengths.

**Upgrades.** Telluric correction from standard or model; multi‑order echelle stitching; IFU integration when available.

---

## 9) Environmental Monitoring (Optional): Open/Long‑Path IR/UV
**Goal.** Track ambient gases or vapors using open‑path or long‑path cells.

**Inputs.** FTIR with path to outdoor intake or enclosed long path; optional UV–Vis DOAS if available.

**SOP.**
1. Acquire periodic backgrounds; log meteorological context; collect spectra on schedule.
2. Fit target species using convolved library cross‑sections; report concentrations with uncertainty.

**QC gates.** Stability of reference channel; quality masks for saturated humidity bands.

**Outputs.** Time series of concentrations; spectral residuals; QC flags.

**Success metrics.** Consistent retrievals during known events (e.g., lab releases); agreement with handheld sensors if available.

**Upgrades.** Automated alert thresholds; meteorology integration.

---

## 10) “Mystery Sample” Cross‑Modal Practicum
**Goal.** End‑to‑end unknown identification using at least two modalities.

**Inputs.** Curated unknowns that require cross‑modal reasoning (e.g., carbonate vs bicarbonate; graphitic vs amorphous carbon; dye mixtures).

**SOP.**
1. Randomly assign unknown; acquire per Ch. 2 SOPs with calibration artifacts.
2. Extract features; run identification (Ch. 7) with explicit priors toggled on/off to demonstrate effect.
3. Produce a report with evidence graph and alternatives; submit bundle for scoring.

**QC gates.** All manifests complete; calibration artifacts attached; unit/axis flags present.

**Outputs.** Full bundle + report PDF; graded rubric (Ch. 11) with feedback.

**Success metrics.** Two‑modality corroboration for top hypothesis; clean provenance; reproducible results by another team.

**Upgrades.** Adaptive next‑measurement suggestion; peer‑review mode where teams critique each other’s evidence graphs.

---

## Data layout reminder (for all workflows)
```
sessions/[SESSION_ID]/[MODALITY]/raw/*
sessions/[SESSION_ID]/[MODALITY]/processed/*
sessions/[SESSION_ID]/cal/*
sessions/[SESSION_ID]/manifest.json
reports/[SESSION_ID]/[DATASET_ID]/report_[YYYYMMDD].pdf
```

---

## Instructor/TA quick checks
- Unit/medium flags present; canonical axes correct.
- Wavelength RMS and LSF FWHM in range for instrument.
- Backgrounds current; baselines logged and reproducible.
- Versioned references (line lists, libraries) recorded.

---

## Cross‑links
- Ch. 1–2 for modality theory and SOPs.
- Ch. 3 for fusion logic and evidence graphs.
- Ch. 4 for external sources and adapters.
- Ch. 5 for axis/units.
- Ch. 6 for calibration/LSF and response.
- Ch. 7 for identification.
- Ch. 8 for provenance.
- Ch. 11 for scoring rubric.

---

## Future upgrades
- Automated “method wizard” that generates method JSONs from a natural‑language plan.
- Classroom mode: one‑click creation of a **Mystery Sample** assignment with rubric and autograder hooks.
- Spectral‑imaging extensions and spatial ROIs.
- Library version comparator to show what changes across updates (e.g., HITRAN2020 → HITRAN2024).

