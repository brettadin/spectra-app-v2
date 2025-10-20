# Chapter 6 — Calibration and Alignment Pipeline

> **Purpose.** Establish a rigorous, instrument‑agnostic pipeline to calibrate, correct, and align spectra so that cross‑instrument and cross‑modality comparisons are numerically valid and reproducible.
>
> **Scope.** Grating/fiber spectrometers (atomic/UV–Vis), FTIR/ATR (including gas cells), Raman microscopes/portables, fluorimeters, and astrophysical spectra from archives. Includes wavelength/wavenumber/shift calibration, background and response correction, resolution/LSF estimation, velocity frames, and uncertainty propagation.
>
> **Path notice.** All paths below are **placeholders** resolved at runtime by the app’s path resolver. Tokens like `[SESSION_ID]`, `[INSTRUMENT_ID]`, `[MODALITY]`, `[YYYYMMDD]` are variables. Do not hardcode.

---

## 0. Pipeline philosophy and invariants

1. **Raw is sacred.** Store raw detector space once. Every correction produces a new **view** with a provenance record; the raw never changes.
2. **Small, explicit steps.** Each transform is single‑purpose, parameterized, and recorded in `transforms_applied` with versioned code identifiers.
3. **Axis honesty.** Calibrate the axis once per session, attach uncertainties, and never silently re‑fit mid‑run.
4. **Resolution preserved.** Estimate the instrument LSF/FWHM; for comparisons, **convolve high‑res down** to the lowest common resolution.
5. **Uncertainty through everything.** Propagate uncertainties for additive and multiplicative operations and for convolutions.

---

## 1. Calibration objects (what we create and reuse)

Each session yields a set of reusable calibration artifacts saved under `sessions/[SESSION_ID]/cal/`:

- **Dark/offset model**: detector bias vs exposure/temperature.
- **Nonlinearity model** (if applicable): counts correction curve with validity range.
- **Wavelength/wavenumber/shift solution**: mapping from pixel/time/OPD to physical axis with RMS residuals.
- **Instrument response** (relative spectral response function, RSRF): converts counts→relative flux or corrects spectral tilt.
- **Instrument line‑shape (LSF) kernel**: Gaussian/Lorentzian/Voigt or measured kernel; FWHM as function of wavelength.
- **Throughput/flat field** (if available): pixel‑to‑pixel sensitivity.
- **Velocity frame context**: observatory/site vector and barycentric correction function (astro use).

Each artifact is a small JSON+array bundle: `{name, parameters, units, validity, checksums, created_at, code_version}` with a sidecar data file (CSV/NPY/HDF5).

---

## 2. Wavelength / wavenumber / Raman‑shift calibration

### 2.1 Grating/fiber spectrometers (atomic/UV–Vis)
- **Inputs:** pixel index `x`, lamp line list (Hg/Ne/Xe/He), measured line centers `x_i`.
- **Model:** polynomial or low‑order spline mapping `λ(x) = a0 + a1 x + a2 x^2 + ...`. Prefer the lowest order that passes residual tests.
- **Fit strategy:** robust fit with outlier rejection (RANSAC or sigma‑clipping). Save residuals and **RMS_λ**.
- **Checks:** compare derived λ for withheld lines; air/vacuum tag recorded (see Chapter 5); store temperature/pressure if air conversions are used.

### 2.2 FTIR (interferometer)
- **Axis source:** internal reference laser defines the OPD scale. The manufacturer’s scale is primary; we **verify** with a polystyrene film and log offsets.
- **Metadata:** apodization window, zero filling, phase correction method (e.g., Mertz); store as part of the processed view.

### 2.3 Raman
- **Primary reference:** silicon at **520.7 cm⁻¹**. Measure the **exact** laser wavelength `λ₀` (nm) or record nominal with uncertainty.
- **Mapping:** detector pixel → emission λₛ → Raman shift `Δν̃` via `Δν̃ = 10^7 (1/λ₀ − 1/λₛ)`.
- **Checks:** verify secondary lines (e.g., neon) if available; store `σ(Δν̃)` from `σ(λ₀), σ(λₛ)` (see Chapter 5 error propagation).

---

## 3. Backgrounds, stray light, and baseline

1. **Dark/offset subtraction:** build a dark model per exposure time/temperature bin; subtract before any non‑linear steps.
2. **Stray light correction (UV–Vis/grating):** optional de‑scattering model using high‑absorbance cutoff filters; store method and residuals.
3. **Background (FTIR/ATR):** background spectrum acquired post‑purge; ensure temporal proximity; subtract or ratio depending on mode; record apodization consistency.
4. **Fluorescence/continuum baselines:** model with low‑order polynomials/splines outside masked features; save coefficients and windows.
5. **Cosmic ray removal (Raman):** median combine accumulations or apply spike detection; store algorithm and masks.

---

## 4. Instrument response (relative flux) and absolute calibration

### 4.1 Relative spectral response function (RSRF)
- **Goal:** remove instrument throughput tilt to compare to libraries.
- **Method:** measure a standard (e.g., white reference for reflectance, CALSPEC star for astro) with known spectrum `S_ref(λ)`; compute response `R(λ) = C(λ)/S_ref(λ)` where `C(λ)` are counts.
- **Use:** corrected spectrum `S_corr(λ) = C(λ)/R(λ)`.
- **Storage:** `response_[YYYYMMDD].json` with wavelength grid, uncertainties, and provenance of the reference.

### 4.2 UV–Vis specifics
- **Transmittance/Absorbance:** `T = I/I0`, `A = −log10 T`. Track path length and cuvette; for concentration work, store calibration curve and residuals.

### 4.3 Astrophysical absolute flux
- **Extinction:** derive atmospheric extinction curve from standards per night and airmass `X`; correct `C(λ)`.
- **Sensitivity function:** fit a smooth function `S(λ)` mapping corrected counts to physical flux `F(λ)`. Store function, polynomial degree/spline knots, and standard star IDs.

---

## 5. Resolution and line‑spread function (LSF)

1. **Estimation:** fit unresolved lines with Gaussian/Lorentzian/Voigt; record **FWHM(λ)** and kernel shape. For FTIR, the nominal ILS is sinc‑like; log effective apodized FWHM.
2. **Use in overlays:** when comparing datasets, compute the **target FWHM** (the coarsest among them). Convolve higher‑res spectra using the stored kernel to the target.
3. **Deconvolution caution:** only allowed for visualization or specific analyses; mark outputs clearly; never use deconvolved data as matching input unless explicitly flagged experimental.

---

## 6. Velocity frames and Doppler context (astro)

1. **Barycentric correction:** compute Earth–barycenter velocity at observation time/site; store `v_bary` and method/library version.
2. **Radial‑velocity estimation:** cross‑correlate continuum‑normalized data with convolved templates; the CCF peak yields `v_r`. Save CCF, peak width, and uncertainty.
3. **Application rule:** apply shifts to **templates** during matching, not to the raw science spectrum; report final `v_sys = v_r + v_bary` in the manifest.

---

## 7. Uncertainty propagation (sketches)

- **Additive corrections (dark subtraction):** `σ_out^2 = σ_in^2 + σ_dark^2`.
- **Multiplicative corrections (response division):** `(σ_out / S_out)^2 = (σ_in / C)^2 + (σ_R / R)^2`.
- **Convolution with normalized kernel `K`:** `σ_out^2 = K^2 * σ_in^2` (discrete convolution of variances).
- **Peak fits:** store parameter covariance from the fitter; propagate to center/FWHM/intensity uncertainties for matching tolerances.

All uncertainty models must be recorded in the report block for reproducibility.

---

## 8. Alignment for cross‑comparison (endgame)

1. **Choose target axis and resolution:** select a canonical axis per modality (Chapter 5) and the coarsest FWHM among spectra.
2. **Create comparison views:** interpolate to a common grid only for visualization/matching; never replace source sampling. Record interpolation method.
3. **Continuum normalization:** outside of features, use spline/polynomial windows agreed per modality; save masks.
4. **Quality gates:** reject overlays if wavelength RMS exceeds threshold or if LSF mismatch > 10% after convolution.

---

## 9. Output artifacts and report blocks

Every processed spectrum gains:
- `axis_solution`: coefficients, RMS, withheld‑line residuals, medium (air/vacuum), and model.
- `response_applied`: response ID, reference used, fit residuals.
- `lsf`: kernel name, FWHM(λ), estimation method.
- `velocity_context` (astro): `v_bary`, `v_r`, library versions.
- `uncertainty_model`: per‑wavelength uncertainties and how they were derived.

The **session report** includes trend plots of wavelength RMS, FWHM vs λ, and response stability across time.

---

## 10. Failure modes and mitigations

- **Calibration drift mid‑session:** insert periodic checks (lamp/polystyrene/Si) and apply segmented solutions; record breakpoints.
- **Saturation/clipping:** flag and discard saturated regions; reduce exposure or slit.
- **Etalon/fringes:** detect via Fourier domain; apply notch filtering; record affected ranges.
- **Order stitching (echelle/segmented spectrometers):** fit overlapping regions with smooth gains; store stitch map and residuals.
- **Purge instability (FTIR):** monitor H₂O/CO₂ bands; auto‑prompt to refresh background when drift exceeds threshold.

---

## 11. Minimal test suite (must ship with app)

1. **Wavelength solution test:** synthetic line set with known polynomial; recover coefficients within tolerance; RMS below spec.
2. **FTIR verification:** simulated interferogram → apodize → FFT; check that polystyrene synthetic peaks land correctly.
3. **Raman conversion test:** λ space → shift space round‑trip within 0.1 cm⁻¹.
4. **Response function test:** apply known tilt; recover RSRF and flatten within 1% RMS.
5. **LSF convolution test:** high‑res synthetic line convolved to target; FWHM matches within 2%.
6. **Velocity pipeline test:** inject known `v_r`; CCF recovers within stated uncertainty.

---

## 12. JSON method stubs (examples)

**Grating spectrometer wavelength calibration**
```json
{
  "modality": "atomic_uvvis",
  "calibration": {
    "lines": "cal/lamp_Ne_[YYYYMMDD].csv",
    "model": "poly",
    "order": 3,
    "fit": {"clip_sigma": 3.0, "min_lines": 8}
  },
  "dark": {"enabled": true, "model": "per_exposure"},
  "response": {"enabled": true, "standard": "holmium_filter", "smoothing": "spline_k3"},
  "lsf": {"estimate": true, "kernel": "gaussian"}
}
```

**FTIR session**
```json
{
  "modality": "ftir",
  "background": {"file": "cal/background_[YYYYMMDD].spa", "apodization": "Happ-Genzel"},
  "verification": {"ref": "polystyrene", "tolerance_cm-1": 0.5},
  "processing": {"resolution_cm-1": 4, "scans": 64, "phase": "Mertz", "zerofill": 2},
  "lsf": {"type": "sinc_apodized", "fwhm_cm-1": 4.2}
}
```

**Raman session**
```json
{
  "modality": "raman",
  "lambda0_nm": 785.02,
  "references": ["Si_520.7"],
  "cosmic_rays": {"method": "median_of_accumulations"},
  "baseline": {"model": "poly", "order": 2, "mask": "auto"},
  "lsf": {"estimate": true, "kernel": "voigt"}
}
```

**Astro spectrum alignment**
```json
{
  "modality": "astro_uvvis",
  "extinction": {"airmass": 1.3, "curve_id": "site_X_2025-10-17"},
  "sensitivity": {"standard": "CALSPEC_BD+17_4708", "fit": "spline_k3"},
  "velocity": {"barycentric": true, "template": "G2V_highres", "ccf_window_nm": [480, 540]}
}
```

---

## 13. Cross‑links

- Chapter 2 for acquisition SOPs that generate calibration files.
- Chapter 5 for axis and unit conventions used here.
- Chapter 7 for how calibrated spectra feed the identification engine.
- Chapter 8 for storing all provenance and calibration artifacts in manifests.

---

## 14. Reference cues (to be filled with exact editions/DOIs in Sources chapter)
- Instrument manuals for your specific models (wavelength fitting and dark/linearity procedures).
- Standard practice for FTIR processing (apodization, phase correction, zero‑filling), polystyrene verification.
- Raman calibration using Si 520.7 cm⁻¹ and laser wavelength logging.
- Photometric/astro spectroscopic calibration workflows (extinction and sensitivity functions).

