# Chapter 1 — Modalities, Instruments, and What They Tell You

> **Purpose.** Define the spectroscopy modalities we will use across campus-grade instruments, the physical information they encode, and the acquisition/calibration practices required so that heterogeneous data can be compared, merged, and reasoned over in the Spectra App.
>
> **Scope.** Elemental and molecular spectroscopy with optical methods: atomic emission/absorption, FTIR/ATR, Raman, UV–Vis absorption, and fluorescence/phosphorescence. We also note optional ground-truth modalities (MS/XRD/NMR) as priors or validators.
>
> **Path notice.** File and folder names in this document are **placeholders**. All paths must be resolved by the application’s path resolver at runtime. Do not hardcode. When you see tokens like `[SESSION_ID]`, `[MODALITY]`, `[INSTRUMENT_ID]`, or `[YYYYMMDD]`, treat them as variables.

---

## 1. Shared data model and invariants

### 1.1 Canonical spectral axes
- **Atomic / UV–Vis:** canonical axis is wavelength \(\lambda\) in **nm**. Provide derived energy **eV** and wavenumber **cm⁻¹** as views.
- **Infrared (FTIR/ATR):** canonical axis is wavenumber \(\tilde{\nu}\) in **cm⁻¹**. Provide micrometre view (\(\mu m\)) as a convenience.
- **Raman:** canonical axis is **Raman shift** \(\Delta\tilde{\nu}\) in **cm⁻¹** relative to the **exact** excitation wavelength \(\lambda_0\) (nm):
  \[
  \Delta\tilde{\nu}\;[\mathrm{cm}^{-1}] = 10^{7}\!\left(\frac{1}{\lambda_0(\mathrm{nm})} - \frac{1}{\lambda_s(\mathrm{nm})}\right)
  \]
- **Fluorescence/phosphorescence:** store both **excitation** and **emission** axes in **nm**; report Stokes shift in **nm** and **cm⁻¹**.

**Rule:** conversions must always re-derive from the canonical axis, never apply chained transforms. Store the canonical arrays exactly once per spectrum.

### 1.2 Resolution and instrument function
- Preserve the **instrument line-shape** (ILS/LSF) or effective resolution (e.g., FWHM) as metadata. For comparisons, convolve higher-resolution spectra down to the lower-resolution reference. Never overwrite the original.

### 1.3 Provenance bundle per spectrum
Each acquisition persists a **bundle**:
```
{ raw, processed, calibration, instrument_meta, environment_meta, transforms_applied }
```
Include version pins (library/line-list versions, app build), and citations used for identification.

---

## 2. Atomic emission and absorption (elemental identification)

### 2.1 What this modality tells you
- **Emission (lamps, flames, plasmas):** discrete lines that fingerprint elements; relative line ratios encode plasma conditions.
- **AAS (atomic absorption):** quantitative elemental analysis via Beer–Lambert law for ground-state atoms in a flame or graphite furnace.

### 2.2 Typical campus instruments
- Hollow-cathode or discharge **calibration lamps** coupled to a fiber spectrometer.
- **Flame emission** rigs or multi-element plasma sources (where available).
- **AAS** instruments (flame or electrothermal) for quantitation.

### 2.3 Core relations
- **Beer–Lambert (AAS):** \(A = \varepsilon c \ell\) where \(A\) is absorbance (unitless), \(\varepsilon\) molar absorptivity, \(c\) molarity, \(\ell\) path length (cm).
- **Doppler width (sanity check):** \(\Delta\tilde{\nu}_D \propto \tilde{\nu}\sqrt{T/M}\) for gas-phase lines.

### 2.4 Minimal acquisition protocol (emission)
1. Warm up source and spectrometer; record `[START_TIME]`, `[ROOM_TEMP]`.
2. Capture **dark** and **lamp** references; store under `sessions/[SESSION_ID]/cal/`.
3. Acquire emission with logged slit width, integration, averaging.
4. Export raw spectrum and wavelength calibration curve; bind in the manifest.

### 2.5 Minimal acquisition protocol (AAS)
1. Define standards and blanks; record flame gas composition and flow.
2. Run calibration set → linear fit; store coefficients + QC stats.
3. Analyze unknowns with bracketing checks and spikes where applicable.

### 2.6 Common pitfalls
- **Self-absorption** and **ionization interferences** in flames.
- Misassigning lines at low resolution; always cross-check with authoritative line lists.

### 2.7 Calibration anchors
- Hg/Ne/Xe lamp lines for wavelength scale (daily).

---

## 3. Molecular infrared (FTIR, ATR, gas cells)

### 3.1 What this modality tells you
- **Functional groups** and bonding motifs from vibrational fundamentals/overtones.
- **Gas-phase** rovibrational envelopes encode temperature and pressure.

### 3.1a Comprehensive Functional Group Coverage (2025-10-25 Update)

The application now provides an **extended IR functional groups database** with 50+ groups organized into 8 chemical families, enabling detailed molecular identification from IR/FTIR spectra:

**1. Hydroxyl Groups (6 variants)**
- O-H free (alcohols, 3650-3600 cm⁻¹): Sharp, concentration-dependent
- O-H hydrogen-bonded (alcohols, 3550-3200 cm⁻¹): Broad, dominant in condensed phase
- O-H phenolic (3650-3200 cm⁻¹): Intermediate sharpness, red-shifted from aliphatic
- O-H carboxylic (3300-2500 cm⁻¹): Very broad, overlaps with C-H, diagnostic with C=O at 1710 cm⁻¹
- Primary/secondary alcohols distinguished by C-O stretch position and coupling patterns

**2. Carbonyl Groups (7 variants)**
- Ketones (1750-1680 cm⁻¹): Strong, sharp; position varies with conjugation/ring strain
- Aldehydes (1740-1720 cm⁻¹): Characteristic C-H aldehyde doublet at 2830, 2720 cm⁻¹
- Esters (1750-1735 cm⁻¹): Often coupled with strong C-O stretch at 1300-1000 cm⁻¹
- Carboxylic acids (1725-1700 cm⁻¹): Paired with broad O-H; dimers common in condensed phase
- Amides (1690-1650 cm⁻¹): Amide I/II bands, position sensitive to H-bonding
- Anhydrides (1850-1800, 1790-1740 cm⁻¹): Characteristic doublet from symmetric/asymmetric C=O stretch
- Acid chlorides (1815-1785 cm⁻¹): Higher frequency than other carbonyls due to Cl electronegativity

**3. Amine Groups (4 variants)**
- Primary amines (NH₂): Doublet at 3500-3300 cm⁻¹ + N-H bend at 1650-1580 cm⁻¹
- Secondary amines (NH): Single N-H stretch at 3350-3310 cm⁻¹, often weak
- Tertiary amines (N): No N-H stretch, identified by C-N stretch + context
- N-H wagging/twisting modes provide additional diagnostic information

**4. Aromatic Groups (4 variants)**
- C-H aromatic stretch (3100-3000 cm⁻¹): Multiple bands, weaker than aliphatic C-H
- C=C aromatic stretch (1600-1585, 1500-1400 cm⁻¹): Ring breathing modes
- C-H out-of-plane bending (900-690 cm⁻¹): Substitution pattern fingerprint (mono/ortho/meta/para)
- Overtone/combination bands (2000-1650 cm⁻¹): Weak but characteristic patterns

**5. Aliphatic Groups (5 variants)**
- C-H sp³ stretch (2970-2850 cm⁻¹): Strong, methyl/methylene distinction via position
- C-H sp² stretch (3095-3075 cm⁻¹): Alkenes, higher frequency than sp³
- C-H sp stretch (3333-3267 cm⁻¹): Alkynes, sharp and distinctive
- C=C alkene (1680-1620 cm⁻¹): Position varies with substitution; often weak in symmetric alkenes
- C≡C alkyne (2260-2100 cm⁻¹): Sharp, medium intensity; absent if internal symmetric alkyne

**6. Nitrogen Groups (3 variants)**
- Nitriles (C≡N, 2260-2210 cm⁻¹): Sharp, medium-strong; conjugation lowers frequency
- Nitro compounds (NO₂): Characteristic doublet at 1560-1540 + 1385-1345 cm⁻¹ (~150 cm⁻¹ separation)
- Azo compounds (N=N, 1630-1575 cm⁻¹): Often weak; aromatic azo compounds more visible

**7. Sulfur Groups (4 variants)**
- Thiols (S-H, 2600-2550 cm⁻¹): Weaker than O-H, sharp, distinctive frequency
- Sulfoxides (S=O, 1070-1030 cm⁻¹): Strong, asymmetric stretch
- Sulfones (SO₂, 1350-1300 + 1160-1120 cm⁻¹): Doublet from symmetric + asymmetric stretch
- Disulfides (S-S, 500-400 cm⁻¹): Weak, low frequency, requires far-IR or Raman confirmation

**8. Halogen Groups (4 variants)**
- C-F (1400-1000 cm⁻¹): Very strong, multiple bands; exact position varies with substitution
- C-Cl (800-600 cm⁻¹): Medium-strong, decreases in frequency with halogen mass
- C-Br (690-515 cm⁻¹): Weaker than C-Cl, overlaps with fingerprint region
- C-I (600-500 cm⁻¹): Weak, far-IR region, often better characterized by Raman

**Database Structure** (`app/data/reference/ir_functional_groups_extended.json`):
- Wavenumber ranges: minimum, maximum, characteristic peak
- Intensity descriptors: strong, medium, weak, variable
- Vibrational modes: stretch (ν), bend (δ), rock (ρ), wag (ω), twist (τ)
- Chemical classes: alcohols, ketones, aromatics, etc.
- Related groups: functional groups that commonly co-occur (e.g., COOH has both C=O and O-H)
- Diagnostic value (1-5 scale): reliability for identification
- Notes: interference patterns, concentration effects, matrix dependencies

**Usage in Application**:
- Reference tab → IR Functional Groups: Browse all 50+ groups with wavenumber ranges
- Filter/search by name, wavenumber, or chemical class
- Preview overlays on inspector plot; click "Show on plot" to overlay on main spectrum
- Auto-detection via `ReferenceLibrary.ir_groups` (falls back to basic 8-group database if extended version unavailable)

**Future ML Integration** (see Chapter 7, §7a):
- Phase 1 (4 weeks): Automated peak detection with rule-based functional group matching
- Phase 2-3 (14 weeks): Neural network training on ~52K labeled IR spectra (NIST + SDBS)
- Phase 4 (4 weeks): UI integration with confidence scores and evidence display
- Phase 5 (4 weeks): Hybrid ensemble combining rule-based and ML predictions

**Provenance**: Compiled from NIST Chemistry WebBook, Pavia et al. (2015), Silverstein et al. (2015), and SDBS (AIST Japan). All groups validated against authoritative spectroscopy references.

### 3.2 Typical campus instruments
- FTIR bench (ATR accessory for solids/liquids). Optional: long-path **gas cell** for gases and vapors.

### 3.3 Core relations
- **ATR penetration depth (qualitative dependence):** \(d_p \propto \frac{\lambda}{n_1\sqrt{\sin^2\theta - (n_2/n_1)^2}}\). Use exact form in methods when indices and angle are logged.
- FT processing: interferogram → spectrum via FFT with apodization; log window and resolution (e.g., 2 or 4 cm⁻¹).

### 3.4 Minimal acquisition protocol
1. Log ATR crystal, pressure setting, apodization, resolution, scans, purge status.
2. Background with clean crystal; save `background_[YYYYMMDD].*` in `cal/`.
3. Acquire sample; for gas cells record `[PATH_LENGTH_CM]`, `[PRESSURE_TORR]`, `[TEMP_K]`.
4. Export **interferogram** + **processed** spectrum, with every transform recorded.

### 3.5 Calibration anchors
- **Polystyrene film** wavenumber checks; periodic background updates.

### 3.6 Common pitfalls
- Water/CO₂ contamination, variable ATR contact, unlogged baseline or smoothing.

---

## 4. Raman spectroscopy (complement to IR)

### 4.1 What this modality tells you
- Modes driven by **polarizability** changes (often IR-inactive). Sensitive to symmetry, crystallinity, strain, carbon ordering.

### 4.2 Typical campus instruments
- Raman microscope or portable Raman with 532/633/785 nm lasers; notch/edge filters; objectives.

### 4.3 Core relations
- **Raman shift** definition (see §1.1) using **exact** \(\lambda_0\).
- Relative intensity scales roughly as \(I \propto 1/\lambda^4\) (shorter \(\lambda\) increases Raman signal but may increase fluorescence).

### 4.4 Minimal acquisition protocol
1. Log `[LASER_WAVELENGTH_NM_EXACT]`, `[POWER_MW_AT_SAMPLE]`, `[OBJECTIVE]`, `[EXPOSURE_S]`, `[ACCUMULATIONS]`.
2. Capture **Si 520.7 cm⁻¹** reference; store in `cal/raman/`.
3. Acquire sample; export **wavelength** spectrum; convert to **cm⁻¹** using \(\lambda_0\) in the app.

### 4.5 Common pitfalls
- Fluorescence baseline, sample heating, using nominal instead of **measured** \(\lambda_0\).

---

## 5. UV–Vis absorption (electronic transitions, quantitation)

### 5.1 What this modality tells you
- Electronic transitions; ligand-field and conjugation trends; **quantitation** via Beer–Lambert when assumptions hold.

### 5.2 Typical campus instruments
- Single- or double-beam spectrophotometer; integrating sphere for diffuse reflectance (solids/films).

### 5.3 Core relations
- **Beer–Lambert:** \(A = \varepsilon c \ell\). Track **path length**, **slit bandwidth**, **scan rate**, and **baseline**.

### 5.4 Minimal acquisition protocol
1. Baseline with matched cuvette and solvent; record `[PATH_LENGTH_CM]`, `[SOLVENT]`, `[pH]`, `[TEMP_K]`, `[SLIT_BW_NM]`.
2. Choose concentration to avoid stray-light saturation; acquire spectrum.
3. Export transmittance and absorbance with metadata.

### 5.5 Common pitfalls
- Stray light at high absorbance, inner-filter effects, solvent cutoff ignored.

---

## 6. Fluorescence and phosphorescence (trace detection, environment)

### 6.1 What this modality tells you
- Emission after electronic excitation; **Stokes shift** separates excitation/emission; lifetimes report on environment and intersystem crossing.

### 6.2 Typical campus instruments
- Steady-state fluorimeter; optionally time-resolved modules; or spectrometer + excitation source with filters.

### 6.3 Core relations
- **Stokes shift:** \(\Delta\lambda = \lambda_{\mathrm{em,peak}} - \lambda_{\mathrm{ex,peak}}\). Also report in cm⁻¹.
- **Jablonski diagram** logic for allowed processes (absorption, ISC, internal conversion, emission).

### 6.4 Minimal acquisition protocol
1. Log `[EXCITATION_NM]`, `[EMISSION_SLIT_NM]`, `[INT_TIME_S]`, and geometry (right-angle vs front-face).
2. Acquire excitation and emission scans; export both and the instrument-response correction files.
3. For lifetimes: log TCSPC/phase-mod parameters and model used.

### 6.5 Common pitfalls
- Photobleaching, quenching by oxygen/halides, spectral bleedthrough if filters are mismatched.

---

## 7. Optional validators and priors (non-optical)
- **Mass spectrometry (MS):** elemental/isotopic composition, molecular mass and fragments.
- **X-ray diffraction (XRD):** crystalline phase identification, lattice constants.
- **NMR:** local bonding environment and connectivity in solution/solids.

Use these to **validate** optical assignments or to constrain search spaces in identification workflows. Store links in the provenance manifest rather than merging axes.

---

## 8. Metadata schema (to be captured for every run)

| Category | Required fields (examples) |
|---|---|
| Instrument | `[INSTRUMENT_ID]`, make/model, serial, firmware, detector, resolution or LSF, slit/laser specs |
| Acquisition | operator, date/time, method file, integration/exposure, accumulations, averaging, scan rate |
| Sample | `[SAMPLE_ID]`, preparation, concentration, matrix, temperature, pressure, cuvette/path length |
| Calibration | reference materials, files, coefficients; exact laser wavelength (Raman); lamp IDs (atomic) |
| Environment | purge status, humidity, ambient T, flame gases and flows, gas-cell pressure |
| Transforms | background subtraction, baseline model, apodization, smoothing, cosmic-ray removal, convolve/deconvolve |
| References | DOIs/URLs and versions of line lists and libraries used |

**Export bundle layout (placeholders):**
```
sessions/[SESSION_ID]/[MODALITY]/raw/*
sessions/[SESSION_ID]/[MODALITY]/processed/*
sessions/[SESSION_ID]/cal/*
sessions/[SESSION_ID]/manifest.json
```

---

## 9. Quality gates and competency checks
- **Atomic:** identify ≥5 lamp lines within tolerance at stated resolution; if AAS, linear calibration with R² ≥ 0.995 over the working range.
- **FTIR:** polystyrene film peaks within instrument spec; background refreshed per lab SOP; apodization logged.
- **Raman:** Si line at **520.7 cm⁻¹** within tolerance; uses **exact** \(\lambda_0\). Fluorescence baseline handling recorded.
- **UV–Vis:** Beer–Lambert linearity over chosen range; stray-light test documented.
- **Fluorescence:** emission correction applied; Stokes shift reported and justified.

---

## 10. Common failure modes and mitigations
- **Axis confusion:** mixing nm, µm, and cm⁻¹. Mitigation: enforce canonical axis per modality and explicit unit badges in UI.
- **Over-smoothing:** loss of spectral detail. Mitigation: store raw and processed; show transform provenance.
- **Resolution mismatch:** misleading overlays. Mitigation: convolve down to common FWHM before comparison.
- **Hidden preprocessing:** vendor software auto-fixes. Mitigation: disable autos unless documented; record all transforms.

---

## 11. Example method templates (copy as JSON into method files)

**Raman (785 nm) template**
```
{
  "modality": "raman",
  "laser_nm_exact": 785.02,
  "objective": "50x, NA 0.75",
  "power_mw_at_sample": 5.0,
  "exposure_s": 2.0,
  "accumulations": 5,
  "cosmic_ray_removal": true,
  "calibration": {"reference": "Si_520.7", "file": "cal/raman/[SESSION_ID]_Si.json"}
}
```

**FTIR (ATR) template**
```
{
  "modality": "ftir_atr",
  "apodization": "Happ-Genzel",
  "resolution_cm-1": 4,
  "scans": 32,
  "purge": "dry air",
  "background_file": "cal/background/[YYYYMMDD].ibw",
  "atr_crystal": "diamond",
  "pressure_setting": "medium"
}
```

**UV–Vis template**
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

---

## 12. Cross-modality synopsis (why we keep all of them)
- **Element → molecule bridge:** atomic lines constrain elemental availability; IR/Raman constrain bonding motifs; UV–Vis constrains conjugation/ligand-field/bandgaps; fluorescence exposes microenvironment and trace species.
- **Environment inference:** rotational envelopes (FTIR gas) and line broadening (atomic) give temperature/pressure priors used by identification logic.

---

## 13. Symbols and notation (quick reference)
- \(\lambda\) wavelength (nm unless stated) • \(\tilde{\nu}\) wavenumber (cm⁻¹) • \(\Delta\tilde{\nu}\) Raman shift (cm⁻¹)
- \(A\) absorbance • \(\varepsilon\) molar absorptivity • \(c\) concentration (M) • \(\ell\) path length (cm)
- FWHM full width at half maximum • LSF/ILS instrument line-shape

---

## 14. References and sources (stable anchors)
1. **NIST Atomic Spectra Database (ASD)** — Kramida, A. et al., NIST ASD (accessed YYYY‑MM‑DD). https://physics.nist.gov/asd
2. **HITRAN** — Gordon, I. E. et al., "The HITRAN2020 molecular spectroscopic database," *JQSRT* 277 (2022) 107949. https://hitran.org
3. **RRUFF Project** — Lafuente, B. et al., in *Highlights in Mineralogical Crystallography* (2015), and database https://rruff.info
4. **Lakowicz, J. R.** *Principles of Fluorescence Spectroscopy*, 3rd ed., Springer (2006).
5. **Skoog, Holler, Crouch.** *Principles of Instrumental Analysis*, 7th ed., Cengage (2017).
6. **Hollas, J. M.** *Modern Spectroscopy*, 4th ed., Wiley (2004).
7. **IUPAC Gold Book** — entries for Beer–Lambert law and related photometric terms. https://goldbook.iupac.org
8. **NIST SRM 1921b Polystyrene Film** — wavenumber calibration reference material, NIST SRM documentation.
9. **Silicon Raman reference** — 520.7 cm⁻¹ line for calibration; see manufacturer application notes and standard practice in Raman metrology.

> **Note on citations.** URLs/DOIs are provided as canonical anchors. Final export should include exact access dates and versions. Where multiple acceptable references exist (e.g., FT apodization theory), prefer peer‑reviewed sources or official standards.

---

## 15. Forward links
- Chapter 2: **How to gather the spectra cleanly (campus edition)** will elaborate SOPs and checklists.
- Chapter 5: **Unifying axes and units** formalizes conversions and idempotent transforms.
- Chapter 7: **Identification and prediction logic** encodes the priors derived here into scoring and ML assists.

---

### Appendix A — Quick calibration checklist (printable)
- Atomic: lamp lines verified; dark/stray-light captured.
- FTIR: background up to date; polystyrene check within spec.
- Raman: Si 520.7 validated; \(\lambda_0\) measured; power limited to avoid heating.
- UV–Vis: baseline OK; slit bandwidth recorded; concentration within linear range.
- Fluorescence: filter set documented; emission correction applied; photobleaching checked.

