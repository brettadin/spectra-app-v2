# Chapter 26 — Astrophysics

> **Purpose.** Provide a campus‑practical guide to acquiring, calibrating, and interpreting **astronomical spectra** so they align with the app’s physics, units, and provenance rules. Focus on radial velocity, flux calibration, telluric handling, template matching, and reporting with reproducible metadata.
>
> **Scope.** Low‑ to mid‑resolution spectrographs on small telescopes, archival spectra (e.g., CALSPEC/MAST), and synthetic libraries. Targets include stars, emission‑line objects, Solar System bodies, and reflectance spectra. Assumes Chapters 5–8 (units, calibration, provenance) and Chapter 12 (FITS format) are followed.
>
> **Path notice.** All filenames and directories are **placeholders**. Resolve tokens like `[SESSION_ID]`, `[DATASET_ID]`, `[MODALITY]`, `[INSTRUMENT_ID]`, `[YYYYMMDD]` at runtime via the path resolver. Do **not** hardcode.

---

## 0. Instruments, resolution, and axis honesty

- **Spectral resolution** \(R = \lambda/\Delta\lambda\): record nominal and measured values. Measure the **instrument line spread function (LSF)** per run using arc/sky lines; store kernel and FWHM (Ch. 6).
- **Axis/WCS** in FITS headers: `CTYPE1='WAVE'|'FREQ'|'VELO-LSR'`, `CUNIT1='Angstrom|nm|Hz|m/s'`, `CRVAL1`, `CRPIX1`, `CDELT1`. Prefer **vacuum wavelengths**; when air wavelengths are provided, convert with the chosen model (Ch. 5) and record the model name.
- **Sampling**: \(\ge\)2 points per FWHM; warn when under‑sampled. Never upsample for evidence; convolve templates down to the measured LSF.

---

## 1. Calibration overview (observing night → science spectrum)

1. **Bias/dark/flat** frames → master corrections with medians and outlier rejection. Record exposure times, temperatures, and CCD readout modes.
2. **Wavelength solution** from arc lamps (Hg/Ne/Xe/He) or sky emission; report RMS and withheld‑line residuals. Store the solution coefficients and validity window.
3. **Trace & extraction**: optimal extraction for 1D spectra; save variance array (per‑pixel uncertainties) and a **mask** for cosmic rays and bad pixels.
4. **Flux calibration** using a spectrophotometric standard (CALSPEC): derive **response function** RSRF(\(\lambda\)) and apply to the target (see §2).
5. **Telluric handling** (O₂, H₂O): mask and/or correct using standards or a model; record airmass and method.
6. **Barycentric context**: compute barycentric correction for the time, site, and target; store frame and ephemeris reference (§3). Do **not** shift raw data; shift **templates** for matching.

All steps are captured in the transform ledger (Ch. 8) with parameters and hashes of inputs.

---

## 2. Flux calibration and response

For a standard star with known flux \(F_{\text{std}}(\lambda)\) and observed counts \(C_{\text{std}}(\lambda)\) at airmass \(X_{\text{std}}\):
\[
\mathrm{RSRF}(\lambda)
= \frac{F_{\text{std}}(\lambda)\,10^{+0.4\,k(\lambda)\,X_{\text{std}}}}{C_{\text{std}}(\lambda)/t_{\text{std}}}
\]
Apply to the target with counts \(C_{\text{obj}}\), exposure time \(t_{\text{obj}}\), and airmass \(X_{\text{obj}}\):
\[
F_{\text{obj}}(\lambda)
= \mathrm{RSRF}(\lambda)\,\frac{C_{\text{obj}}(\lambda)}{t_{\text{obj}}}\,10^{-0.4\,k(\lambda)\,X_{\text{obj}}}
\]
- \(k(\lambda)\) is the site extinction curve (site‑specific; versioned). If only **relative fluxing** is feasible, normalize continua consistently and mark result as **relative**.
- Record RSRF as a function with validity window (hours) and seeing/slit notes; changing slit or clouds invalidate transfer.

**Artifacts** (placeholders):
```
sessions/[SESSION_ID]/cal/response_rsr f_[YYYYMMDD].fits
sessions/[SESSION_ID]/cal/extinction_curve_[SITE]_[YYYY].csv
```

---

## 3. Velocities and frames

- **Observed Doppler shift** (non‑relativistic): \(v_r \approx c\,(\lambda_{\text{obs}}/\lambda_0 - 1)\). Use the exact relativistic formula when needed.
- **Barycentric correction** \(v_{\text{bary}}\): compute from site coordinates, time (UTC), and target RA/Dec with a standard ephemeris. Store frame tags: `frame: topocentric|heliocentric|barycentric|LSR` and the ephemeris/version used.
- **Policy:** keep raw wavelengths in their native frame; shift **templates** by \(v_{\text{bary}}\) and trial velocities during cross‑correlation. Report final velocities in the chosen frame with uncertainty from CCF width.

**Context JSON** (placeholder):
```json
{
  "astro_frame": {
    "native": "topocentric",
    "comparison": "barycentric",
    "v_bary_mps": 23456.7,
    "ephemeris": "[EPHEMERIS_ID]@[VERSION]",
    "site": {"lat": 42.0, "lon": -71.0, "elev_m": 100}
  }
}
```

---

## 4. Telluric absorption and sky emission

- **Tellurics**: O₂ A‑band (~760.5 nm), O₂ B‑band (~688 nm), broad H₂O bands. Strategy hierarchy:
  1) **Mask** regions for identification;
  2) **Divide** by a fast‑rotator standard at similar airmass;
  3) **Model** with a radiative‑transfer tool using site meteorology.
- **Sky emission**: subtract with off‑object fibers/slits when available; otherwise fit and subtract background.
- Always record the method and parameters; never claim detections inside uncorrected deep telluric bands.

---

## 5. Templates and libraries

- **Stellar**: empirical (CALSPEC, Pickles) and synthetic (PHOENIX/Kurucz). Convolve to LSF and adjust metallicity, \(T_{\text{eff}}\), \(\log g\) priors if known.
- **Atomic/molecular**: NIST ASD for atomic lines; CH, CN, TiO, CaH, and other bands from evaluated molecular lists; interstellar **DIBs** catalogs as optional overlays.
- **Solar/asteroid reflectance**: use solar analog stars and divide target by analog to obtain relative reflectance; record analog ID and offsets.

All **source IDs** are pinned as `source_id@version` and cached with checksums (Ch. 4).

---

## 6. Matching and radial velocity by cross‑correlation

- **Continuum normalize** the science spectrum and template over selected windows; log masks and polynomial degree.
- **Convolve** template to the measured LSF; resample **template** on the science grid if needed.
- **Cross‑correlation function (CCF)** over trial velocities \(v\):
\[
\mathrm{CCF}(v) = \frac{\langle D, T_v \rangle}{\|D\|\,\|T_v\|}
\]
where \(T_v\) is the velocity‑shifted template. The peak gives \(v_r\) with uncertainty from the peak width; report the window and number of lines contributing.

- For emission‑line objects, fit centroids of individual lines with the LSF model and average; reject lines inside telluric masks.

---

## 7. Quality control and acceptance

A spectrum is **fit for identification** when:
- Wavelength RMS \(\le\) instrument spec; baseline residuals show no large‑scale systematics.
- RSRF exists and is valid for the observation; or the analysis is flagged as **relative** with justification.
- Barycentric context is recorded; telluric strategy and masks are attached.
- SNR in key windows \(\ge\) course/project threshold.

QC tables are exported with per‑order/per‑segment metrics for echelle or segmented data.

---

## 8. FITS layout and metadata (minimum)

- **HDU0**: flux array in physical units or relative units; `BUNIT` records the unit.
- **HDU1**: `UNCERTAINTY` or variance array; **HDU2**: `MASK` array.
- **Header cards** (indicative):
```
SIMPLE  = T
BITPIX  = -64
NAXIS   = 1
NAXIS1  = N
CTYPE1  = 'WAVE    '
CUNIT1  = 'nm      '
CRVAL1  = 500.0
CRPIX1  = 1
CDELT1  = 0.05
BUNIT   = 'erg s-1 cm-2 nm-1'
HIERARCH LSF_FWHM = 0.2           / nm at 500 nm
HIERARCH MEDIUM   = 'vacuum'
HIERARCH RSRF_ID  = 'response_rsr f_[YYYYMMDD]'
HIERARCH VFRAME   = 'barycentric'
HIERARCH VBARY    = 23456.7       / m/s
```
- Include provenance keywords: extraction method, bias/dark/flat IDs, arc solution ID, extinction curve ID, standard star ID.

---

## 9. Reporting and evidence

- **Plots**: continuum‑normalized overlays, CCF curves with peak and uncertainty, line‑by‑line residuals at matched LSF.
- **Tables**: identified lines with rest wavelengths, observed positions, inferred velocities, and masks.
- **Provenance**: standard star, extinction curve, ephemeris, LSF kernel, wavelength solution RMS, telluric strategy, and any masked windows.

All exports include `CHECKSUMS.txt` and a method card (Ch. 8, 14).

---

## 10. Worked mini‑examples

### 10.1 Stellar radial velocity (R≈5000)
- Extract 1D spectrum; measure LSF from arc lines (FWHM 0.12 nm at 600 nm).
- Barycentric correction +12.3 km s⁻¹; convolve PHOENIX template to LSF; compute CCF over ±300 km s⁻¹.
- Peak at +38.2 ± 1.5 km s⁻¹; velocity reported in barycentric frame. Evidence graph links Balmer and metal lines that drove the peak.

### 10.2 Emission‑line galaxy (low‑res)
- Fit [O II], Hβ, [O III], Hα centroids; exclude chunks inside O₂ A/B.
- Compute redshift from line set; compare to cross‑correlation against galaxy templates.
- Report z, line fluxes, and SNR with masks and windows.

### 10.3 Asteroid reflectance spectrum
- Observe target and solar‑analog star; ratio target/analog after airmass correction → relative reflectance.
- Identify broad silicate bands around 1 µm; compare to laboratory mineral templates convolved to instrument LSF.

---

## 11. Cross‑links

- Ch. 5 (units/air–vacuum conversion), Ch. 6 (LSF and response), Ch. 7 (identification scoring), Ch. 8 (provenance), Ch. 12 (FITS), Ch. 15 (comparisons), Ch. 23–24 (Spectroscopy/Physics).

---

## 12. Reference anchors (full citations in Ch. 32)

- **CALSPEC** spectrophotometric standards and documentation.
- **MAST** archive usage guidelines for spectra.
- **Astropy** (time, coordinates, WCS, barycentric correction) and **IAU SOFA** ephemerides.
- **PHOENIX** or **Kurucz** stellar atmosphere libraries; **Pickles** empirical library.
- **NIST ASD** (atomic lines); molecular band references (CH, CN, TiO); **DIBs** catalogs.
- **Atmospheric extinction** curves (site‑specific) and **telluric** correction tools.

> **Note.** Velocity frames and flux units must be explicit in headers and UI. Barycentric corrections are applied to **templates**, not raw data, to preserve reproducibility. All correction models and versions belong in the manifest and report footers.

