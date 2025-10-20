# Chapter 2 — How to Gather the Spectra Cleanly (Campus Edition)

> **Purpose.** Provide practical, campus-realistic standard operating procedures (SOPs) and quality gates so that spectra acquired with different instruments are clean, comparable, and reproducible across semesters and personnel.
>
> **Scope.** Optical spectroscopy commonly available on college campuses: atomic emission/absorption, FTIR/ATR (including gas cells), Raman, UV–Vis, and fluorescence/phosphorescence. Optional notes for diffuse reflectance (DRUV) and long-path gas cells. Telescope/observatory retrieval is covered in Chapter 4 (Data sources).
>
> **Path notice.** File and folder names are **placeholders**. All paths must be resolved via the application’s path resolver at runtime. Do **not** hardcode. Tokens like `[SESSION_ID]`, `[INSTRUMENT_ID]`, `[MODALITY]`, `[YYYYMMDD]` are variables.

---

## 0. First principles for clean data
1. **Idempotence.** Store raw signals once. All processing (baseline, smoothing, apodization, convolve/deconvolve) is re-computable and logged in `transforms_applied`.
2. **Canonical axes.** Enforce canonical axis per modality (see Chapter 1): IR in cm⁻¹, Raman in cm⁻¹ shift, UV–Vis/atomic in nm. Conversions are re-derived from canonical, never chained.
3. **Resolution honesty.** Record FWHM or LSF; for overlays convolve higher resolution down. Never sharpen without explicit logging and justification.
4. **QC every session.** Each acquisition session produces a `cal/` bundle and a `manifest.json` with instrument/environment metadata and references used.

---

## 1. Universal SOP (applies to every instrument)

### 1.1 Session initialization
- Allocate a unique `[SESSION_ID]` (e.g., `2025-10-17T20-03-11Z_labA`).
- Create the session layout:
```
sessions/[SESSION_ID]/[MODALITY]/raw/
sessions/[SESSION_ID]/[MODALITY]/processed/
sessions/[SESSION_ID]/cal/
sessions/[SESSION_ID]/manifest.json
```
- Capture **operator**, **course/lab**, **instrument roster** `[INSTRUMENT_ID]`, firmware, and a photo of the setup if permitted.

### 1.2 Labels and sample custody
- Assign `[SAMPLE_ID]` and **stickers**/labels to cuvettes/cells. Record preparation steps, concentrations, matrices, and storage conditions.
- Keep a paper or digital bench sheet that mirrors all fields the app expects.

### 1.3 Environment and safety
- Record room temperature and humidity; annotate purge status for IR; note flame gases and flows for emission; confirm laser interlocks for Raman.
- Follow PPE and hazard sheets. For high-power lasers or flames, log the safety checklist pass/fail in the manifest.

### 1.4 Calibration set
- Plan the calibration files you will collect (lamp/Si/polystyrene/background/blank). Place all outputs under `cal/` with names like `cal_[YYYYMMDD]_[type].*`.

### 1.5 Replicates and blanks
- Minimum: **1 blank + 3 replicates** per sample condition unless demo-only. Replicates separated in time detect drift.

### 1.6 Export discipline
- Export **vendor-native raw** when possible and a **lossless interchange** (CSV/TXT, JCAMP-DX, FITS) plus the **manifest**. No lossy formats.

---

## 2. Atomic emission and absorption (elemental)

### 2.1 Equipment
- Discharge or hollow-cathode lamps, fiber-coupled spectrometer.
- For AAS: burner head or graphite furnace, gas controls, hollow-cathode lamps, autosampler (optional).

### 2.2 Daily QC
- **Wavelength check:** Hg/Ne/Xe lamp; verify key lines are within instrument spec.
- **Dark/stray-light capture** with shutter closed or source off.

### 2.3 Emission acquisition SOP
1. Warm up lamp and spectrometer per manufacturer.
2. Record slit width, grating, integration time, averages.
3. Acquire **dark** → **lamp calibration** → **sample emission**.
4. Save to:
```
sessions/[SESSION_ID]/atomic/raw/[SAMPLE_ID]_emission_[rep].csv
sessions/[SESSION_ID]/cal/lamp_[HgNeXe]_[YYYYMMDD].csv
```
5. Note suspected self-absorption; reduce source intensity if necessary.

### 2.4 AAS SOP (if available)
1. Prepare **blank** and **standards** (≥5 points) plus QC check standards.
2. Record flame gas mix and flows; align lamp, set current and wavelength.
3. Run calibration, capture calibration curve and residuals.
4. Analyze unknowns; bracket with QC check standards.
5. Save to `processed/` a copy of the calibration model and stats (slope, intercept, R², LOD/LOQ method noted).

### 2.5 Acceptance criteria
- Wavelength error ≤ instrument spec (e.g., ≤ 0.2 nm typical for entry spectrometers).
- AAS calibration linearity R² ≥ 0.995 across the working range.

---

## 3. FTIR / ATR / Gas cells (molecular IR)

### 3.1 Equipment
- FTIR bench with ATR accessory (diamond/Ge/ZnSe), purge or desiccant, polystyrene film, long-path gas cell (optional) with pressure/vacuum gauge.

### 3.2 Daily QC
- **Background** spectrum captured after purge stabilization.
- **Polystyrene film** check; record observed peak positions vs certificate.

### 3.3 ATR SOP
1. Clean crystal; record **crystal type** and **pressure setting**.
2. Acquire **background**; store under `cal/background_[YYYYMMDD].*`.
3. Place sample, apply consistent pressure, acquire at chosen resolution (e.g., 4 cm⁻¹) and scans (e.g., 32–64).
4. Export **interferogram** and **processed** spectrum; log apodization, zero-filling, baseline model.

### 3.4 Gas-cell SOP
1. Evacuate the cell; log residual pressure.
2. Fill to target pressure; record **path length**, **pressure**, **temperature**.
3. Acquire series at multiple pressures for line shape studies.

### 3.5 Acceptance criteria
- Polystyrene peaks within stated spec; water/CO₂ residuals minimized or documented.
- Interferogram SNR sufficient (define SNR metric, see §7.1).

---

## 4. Raman spectroscopy

### 4.1 Equipment
- Raman microscope or portable Raman; 532/633/785 nm lasers; notch/edge filters; objectives (10×, 50×); power meter; Si wafer.

### 4.2 Daily QC
- **Silicon reference** at 520.7 cm⁻¹; measure **exact** laser wavelength if available.

### 4.3 SOP
1. Choose laser to balance Raman cross-section and fluorescence.
2. Set **power at sample** conservatively; verify with power meter.
3. Focus; minimize exposure to avoid heating; enable cosmic-ray removal.
4. Acquire sample and **Si reference**.
5. Export wavelength-based spectrum; app computes **Raman shift** using logged λ₀.

### 4.4 Acceptance criteria
- Si peak position within tolerance; sample shows no burning or drift between accumulations.

---

## 5. UV–Vis absorption (liquids, films)

### 5.1 Equipment
- Single/double-beam spectrophotometer; matched cuvettes; holmium filter (optional); integrating sphere for diffuse reflectance.

### 5.2 SOP
1. Prepare blank (solvent) and sample; record **path length**, **solvent**, **pH**, **temperature**.
2. Run **baseline** with blank; verify flatness.
3. Acquire sample at appropriate concentration to maintain linear range (A ~ 0.1–1.0 typical).
4. Export transmittance and absorbance, plus baseline file.

### 5.3 Acceptance criteria
- Stray-light check passed; linear Beer–Lambert behavior for calibration runs.

---

## 6. Fluorescence / Phosphorescence

### 6.1 Equipment
- Fluorimeter or spectrometer + excitation source; emission/excitation slits; filters; geometry adapters; standards (e.g., quinine sulfate).

### 6.2 SOP
1. Record **excitation wavelength** and **emission slit**; choose geometry (right-angle or front-face for turbid samples).
2. Acquire **excitation** and **emission** spectra; store correction files for instrument response.
3. For lifetimes, log TCSPC settings or phase-modulation parameters.

### 6.3 Acceptance criteria
- Emission correction applied; photobleaching assessed by repeated scans.

---

## 7. Quantitative quality metrics

### 7.1 Signal-to-noise ratio (SNR)
- Define SNR as \( \mathrm{SNR} = \mu_{signal} / \sigma_{baseline} \) using a flat baseline window; report window indices.

### 7.2 Resolution (FWHM)
- Fit isolated line/peak; store FWHM and model (Gaussian/Lorentzian/Voigt). Keep fit residuals.

### 7.3 Wavelength/wavenumber accuracy
- Report ∆λ or ∆(cm⁻¹) against references (lamp lines, polystyrene, Si). Store both absolute error and drift across session.

### 7.4 Baseline drift
- Compute linear/quadratic drift across blank; store coefficient and p-value; flag if above threshold.

### 7.5 Replicate precision
- Compute RSD across replicates at each wavelength bin or integrated band area; flag if RSD exceeds method threshold.

---

## 8. Controls and checks
- **Blanks:** solvent/air for UV–Vis/IR, dark for emission.
- **Standards:** polystyrene (IR), Si (Raman), holmium (UV–Vis), lamp (atomic), quinine sulfate (fluorescence).
- **Spikes/Recoveries:** AAS/UV–Vis quant work; document recovery % and uncertainty.
- **Duplicates:** at least one per session; analyze variance.

---

## 9. Method files (JSON templates)

**Atomic emission**
```
{
  "modality": "atomic_emission",
  "slit_nm": 25,
  "integration_ms": 50,
  "averages": 10,
  "lamp": "Ne",
  "calibration_files": ["cal/lamp_Ne_[YYYYMMDD].csv"],
  "notes": "Adjust slit to avoid saturation"
}
```

**AAS**
```
{
  "modality": "aas",
  "element": "Cu",
  "wavelength_nm": 324.8,
  "flame": {"fuel": "acetylene", "oxidant": "air", "flows": "vendor_units"},
  "standards_mg_per_L": [0, 0.1, 0.2, 0.5, 1.0],
  "calibration_model": "linear",
  "qc_check": 0.35
}
```

**FTIR-ATR**
```
{
  "modality": "ftir_atr",
  "apodization": "Happ-Genzel",
  "resolution_cm-1": 4,
  "scans": 32,
  "purge": "dry_air",
  "background_file": "cal/background_[YYYYMMDD].spa",
  "atr_crystal": "diamond",
  "pressure_setting": "medium"
}
```

**Raman**
```
{
  "modality": "raman",
  "laser_nm_exact": 785.02,
  "objective": "50x",
  "power_mw_at_sample": 5.0,
  "exposure_s": 2.0,
  "accumulations": 5,
  "cosmic_ray_removal": true,
  "calibration": {"reference": "Si_520.7", "file": "cal/raman/[SESSION_ID]_Si.json"}
}
```

**UV–Vis**
```
{
  "modality": "uvvis",
  "path_length_cm": 1.000,
  "solvent": "water",
  "pH": 7.0,
  "slit_bw_nm": 1.0,
  "scan_rate_nm_per_min": 120,
  "baseline_mode": "double-beam"
}
```

**Fluorescence**
```
{
  "modality": "fluorescence",
  "excitation_nm": 350,
  "em_slit_nm": 5,
  "integration_s": 0.5,
  "geometry": "right-angle",
  "correction_file": "cal/fluor_correction_[YYYYMMDD].csv"
}
```

---

## 10. Naming conventions and manifest structure
- Filenames: `[SAMPLE_ID]_[MODALITY]_[rep|timepoint].ext` with an accompanying JSON sidecar containing the metadata for that file if vendor format is opaque.
- `manifest.json` schema fields (minimum):
  - `session_id`, `operator`, `course`, `instrument_meta`, `environment_meta`, `method_file`, `calibration_files`, `transforms_applied`, `lsf_or_resolution`, `axis_canonical`, `references`.
- The app validates presence/format of required fields before accepting an upload.

---

## 11. Common pitfalls and remedies
- **Axis mismatch (nm vs µm vs cm⁻¹):** enforce canonical axis and display unit badges in UI; block uploads lacking unit info.
- **Over-smoothing:** show warning if smoothing kernel exceeds peak FWHM/2; always keep raw.
- **Stray light (UV–Vis):** verify with cutoff filters or saturated absorbance tests; report in manifest.
- **Fluorescence baseline (Raman):** prefer baseline modeling with residual inspection; log the model and parameters.
- **Water/CO₂ in FTIR:** purge adequately or subtract reference; record strategy.

---

## 12. Safety snapshots (non-exhaustive)
- **Lasers:** wear rated eyewear; log laser class; interlocks engaged.
- **Flames/oxidizers:** verify gas lines and flashback arrestors; keep extinguishers accessible.
- **Vacuum/gas cells:** do not exceed rated pressure; check seals; log pressure history.

---

## 13. Printable checklists (tear-off)

### 13.1 Pre-run
- [ ] Session ID created and folders initialized
- [ ] Instrument warm-up complete
- [ ] Calibration plan written (lamp/Si/polystyrene/blank)
- [ ] Sample IDs labeled and logged
- [ ] Safety checks passed

### 13.2 During run
- [ ] Dark/blank taken
- [ ] Calibration files saved to `cal/`
- [ ] Replicates acquired (≥3)
- [ ] Environment recorded (T, humidity, purge/gas flows)

### 13.3 Post-run
- [ ] Export raw + processed + manifest
- [ ] Review QC metrics (SNR, FWHM, wavelength accuracy)
- [ ] Backup to lab share or repository via app ingest

---

## 14. Future upgrades and ideas
- Automated **method wizards** per instrument that pre-populate JSON from vendor files.
- On-instrument **QR codes** for `[INSTRUMENT_ID]` to auto-fill metadata.
- Live **QC dashboard** that trends wavelength accuracy and FWHM across semesters.
- Plug-in for **epsilon-stabilized division** and masking for small denominators in spectral math operations.
- Auto-prompt for **convolution-to-common-resolution** when overlaying mismatched datasets.

---

## 15. Reference anchors (for course notes and SOPs)
- NIST polystyrene film certificate; silicon Raman reference notes; standard instrument manuals and course texts for Beer–Lambert, ATR penetration depth, Raman selection rules, fluorescence correction practices.

> **Cross-links.** See Chapter 1 (Modalities) for theory/background; Chapter 5 for unit/axis rules; Chapter 6 for calibration math; Chapter 8 for provenance; Chapter 11 for scoring; Chapter 14–16 for app and AI workflows.

