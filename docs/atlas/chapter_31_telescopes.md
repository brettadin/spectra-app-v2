# Chapter 31 — Telescopes
> **Purpose.** Specify campus‑scale telescope spectroscopy practices so data reach the app (Ch. 26) with correct units, frames, calibration artifacts, and provenance. Cover planning, acquisition, calibrations (bias/dark/flat/arc/standards), environmental logs, FITS metadata, and acceptance/QC.
>
> **Scope.** Small observatories (20–70 cm aperture) with slit or fiber‑fed grating spectrographs at low–mid resolution (R≈500–10,000). Targets: stars, emission‑line sources, asteroids/reflectance, bright nebulae. Archival tie‑ins (CALSPEC/MAST) included. Photometry is out of scope except where needed for flux standards.
>
> **Path notice.** Filenames and directories are **placeholders** resolved by the app’s path resolver at runtime. Tokens like `[SESSION_ID]`, `[INSTRUMENT_ID]`, `[YYYYMMDD]`, `[OBS_ID]`, `[SITE_ID]` are variables. Do **not** hardcode.

---

## 0. Observatory profile (minimum)

`observatories/[SITE_ID]/profile.json`:

```json
{
  "site_id": "campus_obs",
  "lat_deg": 42.376, "lon_deg": -71.116, "elev_m": 60,
  "time_standard": "UTC",
  "telescope": {"aperture_m": 0.4, "f_ratio": 8, "mount": "equatorial"},
  "spectrograph": {
    "mode": "slit|fiber",
    "resolving_power": {"R": 5000, "at_nm": 650},
    "slits_arcsec": [0.8, 1.0, 2.0],
    "orders": 1,
    "detector": {"type": "CCD", "binning": [1,1], "gain_e_per_ADU": 1.3, "read_noise_e": 4.5}
  },
  "extinction_curve_ref": "cal/astro/extinction_[SITE_ID]_[YYYY].csv"
}
```

Include dome/tube seeing notes, guiding camera model, and maximum track/guiding rate. Changing optics or detector parameters bumps profile version and invalidates LSF/RSRF until re‑verified (Ch. 26 §1–2).

---

## 1. Planning and scheduling

- **Target feasibility:** airmass < **[X\_MAX=2]**, altitude > **[ALT\_MIN=30°]** during exposure window; Moon separation and phase ≥ **[SEP\_MIN=45°]** if scattered light is a concern.
- **Exposure time estimate:** `texp = SNR_goal^2 * (Npix / throughput / flux)` with read noise and sky terms; store calculator inputs in `planning/[OBS_ID]_etc.json`.
- **Telluric strategy:** pick either masking windows (Ch. 26 §4) or a fast‑rotator hot star at similar airmass for division. Record choice.
- **Standards:** CALSPEC standard within **Δairmass ≤ 0.2** and **Δtime ≤ 2 h** for fluxing; arc/flat cadence every **[N\_exposures or minutes]**.

`planning/[OBS_ID]/plan.json`:

```json
{
  "targets": [{"name": "[TARGET]", "ra": "hh:mm:ss", "dec": "+dd:mm:ss", "priority": 1}],
  "windows": [{"start_utc": "[ISO]", "end_utc": "[ISO]"}],
  "snr_goal": 50,
  "telluric": {"mode": "mask|divide", "standard": "[STAR]"},
  "standards": {"flux": "[CALSPEC_ID]", "arc": "HgNe", "flat": "quartz"}
}
```

---

## 2. Calibration set per night (minimum viable)

1. **Bias**: ≥ 20 frames → master bias.
2. **Dark**: ≥ 10 per exposure time used (if required) → master dark.
3. **Flats**: dome/twilight/quartz; cover wavelength range; note slit/fiber and binning.
4. **Arcs**: Hg/Ne/Xe/He frames at each grating setting; before and after science to track drift.
5. **Flux standard**: one CALSPEC star observed like science (same slit/fiber, focus, binning).
6. **Telluric standard**: hot star at similar airmass if using division method.

Artifacts live under `sessions/[SESSION_ID]/cal/` with method cards (Ch. 26 §1–2; Ch. 8).

---

## 3. Acquisition SOP (slit or fiber)

### 3.1 Slit spectrograph

1. Focus telescope with a bright star; record FWHM seeing in arcsec.
2. Align target on slit with guide camera; ensure **parallactic angle** or use ADC to reduce differential refraction at high airmass.
3. Choose slit width ≥ seeing FWHM; log slit.
4. Acquire **science**: multiple sub‑exposures to reject cosmic rays; avoid saturation (peak < 50–70% full well).
5. Take arcs and flats bracketing the science exposure.

### 3.2 Fiber‑fed

1. Focus fiber input; verify far‑field illumination stability.
2. Center target in acquisition camera; monitor fiber injection.
3. Expose science and calibration as above.

**Safety:** no open laser pointers near optics; secure cables; respect dome interlocks.

---

## 4. Reduction outline (campus pipeline)

1. **Overscan/bias/dark** correction → variance model.
2. **Flat‑field** correction → pixel response and blaze removal (if applicable).
3. **Trace & extraction**: optimal 1D extraction with variance and mask arrays; record aperture width in pixels and arcsec.
4. **Wavelength solution**: fit polynomial or 2D model; store RMS and withheld‑line residuals; write `WCS` keywords (Ch. 26 §1, §8).
5. **Sky subtraction**: slit background subtraction or dedicated fiber; store sky model parameters.
6. **Flux calibration**: derive **RSRF(λ)** from CALSPEC, apply extinction correction k(λ); export both the RSRF and the calibrated spectrum (Ch. 26 §2).
7. **Telluric**: mask or divide; record airmass, model, and parameters.
8. **Barycentric context**: compute correction; store frame tags; do not shift raw data (Ch. 26 §3).

Transforms are logged in `ledger.jsonl` with parameter hashes (Ch. 8).

---

## 5. FITS headers and sidecars (must‑record)

- **Axis**: `CTYPE1=WAVE`, `CUNIT1=nm|Angstrom`, `CRVAL1`, `CRPIX1`, `CDELT1`.
- **Units**: `BUNIT='erg s-1 cm-2 nm-1'` or `'relative'` if unfluxed.
- **Frame**: `HIERARCH VFRAME='barycentric'`, `HIERARCH VBARY` (m/s), ephemeris ID.
- **Instrument**: slit width, grating, central wavelength, binning, gain, read noise.
- **Calibration refs**: arc solution ID, flat ID, `RSRF_ID`, extinction curve ID.
- **Provenance**: extraction aperture, polynomial degrees, masks.

Sidecar `sessions/[SESSION_ID]/headers/[FILE].json` mirrors key FITS cards for the app to validate (Ch. 12, 26 §8).

---

## 6. Quality metrics and acceptance

A spectrum is **fit for identification** when:

- **Wavelength RMS** ≤ spec and **withheld lines** residuals are unbiased.
- **LSF** measured from arcs/sky and valid during science frame; kernel or FWHM logged.
- **SNR** ≥ target in diagnostic windows.
- **RSRF** is applied or spectrum is marked **relative**; extinction curve version recorded.
- **Telluric** strategy recorded; deep bands masked if not corrected.

QC dashboard fields:

```json
{
  "rms_nm": 0.045,
  "lsf_fwhm_nm": 0.12,
  "snr_window": {"510-520nm": 65},
  "rsrf_id": "response_[YYYYMMDD]",
  "telluric": "mask|divide"
}
```

---

## 7. Reflectance spectroscopy (asteroids/comets)

- Observe a **solar‑analog** star closely matched in color and airmass.
- Compute relative reflectance: target / analog after extinction correction; smooth gently outside features.
- Convolve mineral lab templates to the measured LSF before comparison (Ch. 26 §10.3).
- Report wavelength scale, slope, and band centers with uncertainties.

---

## 8. Operations, weather, and logs

- **Weather limits:** wind, humidity, temperature thresholds; automatic safing when exceeded.
- **Timekeeping:** all timestamps in UTC with GPS‑synced clock. Log leap seconds via library version.
- **Observer log** `logs/[OBS_ID].md`: seeing, transparency, issues, instrument changes, calibrations done, noteworthy events.
- **Environment telemetry** `env/[OBS_ID].json`: temperature, pressure, humidity, wind; seeing estimate.

---

## 9. Training and roles

- **Level 1:** operate UI, acquire short exposures, run pipeline on fixtures.
- **Level 2:** plan observations, execute full calibration set, produce calibrated spectra and QC report.
- **Level 3:** maintain instrument, update extinction curves, validate RSRF/LSF, and mentor students.

Training checklists appear in Teaching Mode (Ch. 13) and export as PDFs for sign‑off.

---

## 10. Troubleshooting (symptom → cause → check)

- **Shifted lines** → wrong air/vacuum assumption; wrong arc solution; flexure → verify `MEDIUM`, re‑fit with arcs near in time.
- **Broad features** → poor focus, wide slit, seeing; convolve templates to measured LSF to validate.
- **Wavy continuum** → flat‑field or blaze residuals; re‑examine flats, correct blaze.
- **Residual sky lines** → background subtraction window too small; use larger background apertures or sky fibers.
- **Flux mismatch** → wrong slit losses; RSRF derived with different slit/seeing; mark as **relative** and document.

---

## 11. JSON stubs (portable)

**Observation bundle index** `sessions/[SESSION_ID]/obs_[OBS_ID]/index.json`:

```json
{
  "target": "[NAME]",
  "files": ["science_001.fits", "science_002.fits"],
  "cal": {"bias": "bias_master.fits", "dark": "dark_600s.fits", "flat": "flat_quartz.fits", "arc": "arc_HgNe.fits"},
  "standards": {"flux": "[CALSPEC_ID].fits", "telluric": "[STAR].fits"},
  "wavelength_solution": {"rms_nm": 0.05, "withheld": 0.06},
  "lsf": {"fwhm_nm": 0.12, "kernel": "voigt"},
  "rsrf_ref": "response_[YYYYMMDD].fits",
  "extinction_ref": "extinction_[SITE_ID]_[YYYY].csv"
}
```

**RSRF artifact** `sessions/[SESSION_ID]/cal/response_[YYYYMMDD].json`:

```json
{
  "standard": "[CALSPEC_ID]",
  "airmass_standard": 1.12,
  "k_lambda_ref": "extinction_[SITE_ID]_[YYYY].csv",
  "curve": [[350.0, 0.0021], [351.0, 0.0022]],
  "valid_start": "[ISO]", "valid_end": "[ISO]"
}
```

---

## 12. Cross‑links

- Ch. 12 (FITS/sidecars), Ch. 22 (UI), Ch. 26 (Astrophysics), Ch. 30 (Instrumentation), Ch. 8 (Provenance), Ch. 11 (Rubric & acceptance tiers).

---

## 13. Reference anchors (full citations in Ch. 32)

- CALSPEC standards; MAST archive guides; astropy time/coordinates/WCS and IAU SOFA ephemerides; site extinction curve methodology; slit losses and parallactic angle best practices; standard spectroscopic reduction references.

> Telescopes don’t get to be mysterious. Every exposure arrives with its frame, its LSF, and a paper trail. If something changed between the arc and the science, we either measured it or we don’t trust the result.

