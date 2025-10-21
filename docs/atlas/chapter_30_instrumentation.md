# Chapter 30 — Instrumentation

> **Purpose.** Specify campus‑scale spectroscopy hardware, required accessories, calibration artifacts, metadata, and acceptance/QC procedures so measurements feed the workflow (Ch. 1–29) without ambiguity.
>
> **Scope.** FTIR/ATR, Raman microscope/spectrometer, UV–Vis spectrophotometer, steady‑state fluorescence, and a fiber‑fed grating spectrograph for atomic/continuum work. Astrophysical instruments are in Ch. 31. Non‑optical validators (XRD, MS, NMR) are referenced for cross‑checks only.
>
> **Path notice.** All file/folder names are **placeholders** resolved at runtime by the app’s path resolver. Tokens like `[SESSION_ID]`, `[INSTRUMENT_ID]`, `[DATASET_ID]`, `[YYYYMMDD]` must **not** be hardcoded.

---

## 0. Instrument inventory and minimum viable configs

| Modality         | Core instrument                              | Typical range                | Native resolution (indicative) | Notes                                                               |
| ---------------- | -------------------------------------------- | ---------------------------- | ------------------------------ | ------------------------------------------------------------------- |
| FTIR (bench)     | FTIR with ATR + transmission cell            | 4000–400 cm⁻¹                | 0.5–4 cm⁻¹ (selectable)        | Beamsplitter/detector selection documented; purge optional          |
| Raman            | Dispersive Raman microscope (532/633/785 nm) | 100–3500 cm⁻¹ shift          | 1–6 cm⁻¹ FWHM                  | Interchangeable gratings; notch/edge filters; objective list        |
| UV–Vis           | Double‑beam or diode‑array spectrophotometer | 200–1100 nm                  | 0.5–5 nm SBW                   | Cuvette paths 1–10 mm; integrate sphere/DRS optional                |
| Fluorescence     | Steady‑state fluorimeter                     | 230–700 nm ex, 250–900 nm em | 1–5 nm bandpass                | Excitation/emission correction files; front‑face accessory optional |
| Atomic/continuum | Fiber‑fed grating spectrometer               | 350–900 nm                   | R≈500–5000                     | Mercury/Ne/Xe/He lamps for wavelength checks                        |

> **Accessories required.** ATR crystals (diamond/ZnSe), gas cell (IR), polystyrene film, Si wafer, holmium filter/glass, neutral density filters, alignment target, calibration lamps (Hg/Ne/Xe/He), temperature/pressure readouts, Raman calibration tile.

---

## 1. Calibration artifacts (campus‑obtainable)

| Artifact                         | Modality            | Purpose                                          | Stored as                                         |
| -------------------------------- | ------------------- | ------------------------------------------------ | ------------------------------------------------- |
| **Polystyrene film**             | FTIR                | Band position reference; acceptance test         | `cal/ftir/polystyrene_[YYYY].json` + raw spectrum |
| **Si (520.7 cm⁻¹)**              | Raman               | Shift reference; laser λ₀ and spectrograph drift | `cal/raman/si520_[YYYYMMDD].json`                 |
| **Holmium glass/solution**       | UV–Vis              | Wavelength accuracy; stray light sanity          | `cal/uvvis/holmium_[YYYY].json`                   |
| **Hg/Ne/Xe/He lamp**             | Atomic/Raman/UV–Vis | Wavelength solution and LSF kernel by line fits  | `cal/atomic/arc_[YYYYMMDD].json`                  |
| **Fluorescence correction file** | Fluorimeter         | Ex/Em spectral correction (instrument response)  | `cal/fluor/corr_[INSTRUMENT_ID]_[YYYY].json`      |
| **White reflectance standard**   | UV–Vis DRS          | Baseline/reference for integrating sphere        | `cal/uvvis_drs/white_ref_[YYYYMMDD].json`         |

Each artifact record stores: acquisition file refs, environment (T, humidity), instrument state, fit results (centers, FWHM), and validity window.

---

## 2. Instrument manifest (minimum metadata)

`instruments/[INSTRUMENT_ID]/profile.json` (example):

```json
{
  "instrument_id": "raman:RM-785-01",
  "modality": "raman",
  "make_model": "[MAKE] [MODEL]",
  "detector": {"type": "CCD", "cooling": "-60C"},
  "lasers_nm": [532, 633, 785],
  "gratings_gmm": [600, 1200],
  "objectives": ["10x", "50x", "100x"],
  "native_fwhm_cm-1": {"785": 3.2},
  "lsf_kernel_ref": "cal/raman/lsf_[YYYYMMDD].json",
  "response_ref": null,
  "safety": {"laser_class": 3, "interlocks": true}
}
```

> The manifest is versioned; changes to optics or detectors bump `profile.json` and invalidate cached LSF/response unless re‑verified.

---

## 3. LSF characterization (all modalities)

**Goal.** Derive a wavelength‑dependent **instrument line spread function** (LSF) or per‑band FWHM for honest resolution matching (Ch. 6).

### 3.1 Procedure (generic)

1. Acquire narrow‑line spectra (arc lamps for UV–Vis/atomic; Si or neon line leaks for Raman; polystyrene for FTIR band proxies).
2. Fit peaks with Gaussian/Lorentzian/Voigt; record **center**, **FWHM**, **shape**, **uncertainty**.
3. Fit a smooth model of FWHM vs axis value; export kernel parameters or a lookup table.

**Artifact** `cal/[MODALITY]/lsf_[YYYYMMDD].json`:

```json
{
  "model": "voigt",
  "params": [{"axis": 520.7, "fwhm": 3.2, "gamma": 1.1, "sigma": 2.7}],
  "valid_start": "[ISO-8601]",
  "valid_end": "[ISO-8601]",
  "fits": [{"line_id": "Si520", "center": 520.69, "fwhm": 3.20, "shape": "voigt", "r2": 0.998}]
}
```

**Acceptance.** LSF drift ≤ predefined threshold across a session; else flag and re‑characterize.

---

## 4. Wavelength/shift calibration and accuracy

- **FTIR**: run polystyrene check at session start/end; acceptable band deviations ≤ 0.5–1.0 cm⁻¹ depending on resolution. Log apodization.
- **Raman**: measure Si 520.7 cm⁻¹ and optional Ne lines for scale; infer λ₀ each run; target shift accuracy ≤ 1 cm⁻¹. Store laser temp if available.
- **UV–Vis**: holmium peaks within ≤ 0.2–0.5 nm; verify stray light with cutoff filters.
- **Atomic/continuum**: arc lines fit RMS ≤ instrument spec; report withheld‑line residuals.

All calibration runs are captured in `sessions/[SESSION_ID]/cal/` with ledger entries (Ch. 8).

---

## 5. Response/sensitivity characterization

- **Fluorescence**: excitation/emission correction using certified lamps or secondary standards; store curves and validity.
- **UV–Vis DRS**: white reference and black trap; report reflectance scale uncertainty.
- **Astro instruments**: see Ch. 31 (RSRF from CALSPEC).

Response files are referenced in manifests and enforced by the Ingest Manager when absolute intensities are claimed.

---

## 6. Environment telemetry and controls

- **Temperature/pressure/humidity** recorded per session when relevant (gas cells, FTIR purge, Raman drift).
- **Laser power and integration time** logged; avoid saturation; document auto‑exposure settings.
- **ATR contact**: pressure/turns recorded; optional AR‑assist overlay (Ch. 20 §6).

`env/telemetry_[SESSION_ID].json`:

```json
{"T_K": 298.1, "p_Pa": 101325, "RH_percent": 35, "laser_mW": 3.0}
```

---

## 7. Standard operating procedures (SOP) outlines

### 7.1 FTIR (ATR)

1. Inspect crystal; clean; capture **background**.
2. Place sample; apply uniform pressure; record **turns/force**.
3. Acquire 32–128 scans; choose apodization; save raw + parameters.
4. Run **polystyrene** check pre/post; log deviations.

### 7.2 Raman

1. Choose λ₀ to minimize fluorescence; verify power on a **cal tile**.
2. Focus; set grating; acquire Si 520.7; update shift solution.
3. Acquire sample; check for burning; use mapping if needed.
4. Record neon check post‑run for drift.

### 7.3 UV–Vis

1. Warm up; baseline with blank; verify holmium peaks.
2. Check **stray light**; choose slit bandwidth; avoid saturation.
3. Acquire sample; record path length; run replicate scans.

### 7.4 Fluorescence

1. Warm up; load **excitation/emission correction**.
2. Optimize slit widths; check inner‑filter effects by dilution series.
3. Record spectra; validate with quinine sulfate or other standard.

---

## 8. QC dashboards and acceptance gates

- **Wavelength RMS** vs reference below threshold; badges: green/amber/red with exact numbers.
- **LSF drift** within window; banner indicates target FWHM in overlays (Ch. 22).
- **SNR** in diagnostic windows exceeds target.
- **Response validity** within its time window; otherwise mark spectra **relative**.

Failures block identification unless overridden with a reason in the ledger (Ch. 11 penalties apply).

---

## 9. Safety and maintenance

- **Raman lasers**: interlocks engaged; eyewear labeled by wavelength; beam paths enclosed.
- **FTIR**: moving parts and IR sources are hot; let cool before servicing.
- **UV–Vis/Fluor**: avoid solvent vapors near optics; manage waste.
- **Maintenance**: scheduled checks for desiccant, purges, lamp hours, detector cooldown. Log service in `instruments/[INSTRUMENT_ID]/service.log`.

---

## 10. Booking, training, and roles

- **Booking** via departmental calendar; instrument lockouts for maintenance windows.
- **Training tiers**: Level 1 (view/export), Level 2 (acquire/calibrate), Level 3 (trainer). App enforces tier for risky actions.
- **Checklists**: printable `sops/[MODALITY]_checklist.md` and in‑app walkthroughs (Ch. 13 Teaching Mode).

---

## 11. Exported calibration bundle

Export a **calibration bundle** per quarter/semester:

```
exports/cal/[INSTRUMENT_ID]/[YYYYMM]_bundle.zip
  ├─ polystyrene_*.json + spectra
  ├─ si520_*.json + spectra
  ├─ holmium_*.json + spectra
  ├─ arc_*.json + spectra
  ├─ lsf_*.json
  ├─ response_*.json
  └─ CHECKSUMS.txt
```

Include method card and environment summaries; artifacts have validity windows.

---

## 12. Acceptance tests (per modality)

- **FTIR/ATR**: polystyrene bands within tolerance; replicate overlay repeatability; purge status recorded.
- **Raman**: Si 520.7 cm⁻¹ within tolerance; neon residuals low; map reproducibility across spots.
- **UV–Vis**: holmium peak positions within tolerance; stray‑light test passed; bandpass labeled.
- **Fluorescence**: correction applied; quinine sulfate reference within intensity window after correction.
- **Atomic/continuum**: arc RMS good; LSF kernel stable across range segments.

Tests auto‑generate a **calibration report** with plots and badges.

---

## 13. JSON stubs (portable)

**Calibration run record**

```json
{
  "cal_id": "cal:[UUID]",
  "instrument_id": "uvvis:UV-01",
  "artifact": "holmium",
  "files": ["sessions/[SESSION_ID]/cal/holmium_[TS].csv"],
  "results": {"peaks_nm": [361.5, 416.0], "rms_nm": 0.18},
  "valid_start": "[ISO-8601]",
  "valid_end": "[ISO-8601]"
}
```

**Session manifest (instrument block)**

```json
{
  "instrument": {
    "id": "ftir:FT-01",
    "lsf_ref": "cal/ftir/lsf_[YYYYMMDD].json",
    "response_ref": null,
    "wavelength_solution_ref": "cal/ftir/polystyrene_[YYYY].json",
    "notes": "apod=Happ-Genzel, res=2 cm^-1"
  }
}
```

---

## 14. Troubleshooting (symptoms → causes → checks)

- **Peaks shifted** → wrong medium (air/vacuum), drift, wrong λ₀ → check unit badge, run reference.
- **Broader than expected** → focus/slit/apodization; convolve templates vs measured LSF to confirm.
- **Structured baseline** → fluorescence (Raman), water/CO₂ (FTIR), lamp drift (UV–Vis) → adjust λ₀ or purge/mask.
- **Inconsistent repeats** → sample heterogeneity, ATR contact, cuvette orientation → re‑prep and document.

---

## 15. Cross‑links

- Ch. 2 (SOPs), Ch. 5 (units), Ch. 6 (LSF/response), Ch. 7 (identification), Ch. 8 (provenance), Ch. 10 (workflows), Ch. 12 (formats), Ch. 15 (comparisons), Ch. 22 (UI), Ch. 31 (Telescopes).

---

## 16. Reference anchors (full citations in Ch. 32)

- Instrumentation texts and standards (FTIR apodization, Raman shift calibration, UV–Vis holmium standards, fluorescence correction practices).
- Vendor‑agnostic best practices for spectral resolution, slit/LSF characterization, and reference materials.

> Instruments are citizens of the provenance system. If the optics change and the LSF/response aren’t re‑verified, the app will refuse to pretend the data are the same.

