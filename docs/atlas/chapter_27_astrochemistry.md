# Chapter 27 — Astrochemistry

> **Purpose.** Connect laboratory spectroscopy, molecular physics, and astronomical observations to build chemically credible identifications of interstellar/planetary molecules and solids. Define how to compute column densities, excitation temperatures, and mixture compositions from spectra while preserving unit honesty, resolution matching, and provenance.
>
> **Scope.** Ice and refractory solids in the IR; gas‑phase rotational/ro‑vibrational spectra from cm–µm; PAH features; comet/asteroid reflectance. Uses laboratory band strengths and line catalogs (CDMS/JPL/HITRAN/ExoMol) with telescope or archive data (CALSPEC/MAST and ground‑based). Assumes Chapters 5–8 (units, calibration, provenance), 12 (FITS), 15 (comparisons), 23–26 (Spectroscopy/Physics/Astrophysics).
>
> **Path notice.** Filenames and directories are **placeholders**. Resolve tokens like `[SESSION_ID]`, `[DATASET_ID]`, `[MODALITY]`, `[YYYYMMDD]`, `[SOURCE_ID]` at runtime via the path resolver. Do **not** hardcode.

---

## 0. Vocabulary and units (canonical)
- **Wavelength** (µm, nm), **wavenumber** (cm⁻¹), **frequency** (GHz), **velocity** (km s⁻¹), **flux density** (Jy), **brightness temperature** \(T_B\) (K), **optical depth** \(\tau\) (unitless).
- **Frames:** native (topocentric) vs barycentric/LSR; report chosen frame and keep raw in native (Ch. 26).
- **Resolution:** convolve templates to the instrument **LSF**; never deconvolve as evidence (Ch. 6).

---

## 1. Chemical inventory by spectral class

### 1.1 Ices and solids (mid‑IR)
Typical bands (indicative, convolved to instrument LSF):
- H₂O ice: 3.05 µm (O–H stretch), 6.0 µm (H–O–H bend), 13 µm libration.
- CO: 4.67 µm; CO₂: 4.26 µm; CH₃OH: 3.53 µm; NH₃: 2.96 µm.
- Silicate dust: 9.7 µm and 18 µm Si–O features; composition controls profile.
- PAHs: 3.3, 6.2, 7.7, 8.6, 11.2–11.3 µm aromatic bands.

### 1.2 Gas‑phase (radio/mm/sub‑mm/IR)
- **Rotational lines**: CO, ¹³CO, C¹⁸O, HCN, HCO⁺, CS, NH₃; selection rules \(\Delta J = \pm 1\) for linear rotors.
- **Rovibrational**: CO, HCN, CH₄, H₂O in near/mid‑IR; require air↔vacuum care (Ch. 5).

### 1.3 Reflectance (planets, comets, asteroids)
- Broad silicate and hydrated mineral bands; compare to laboratory mineral templates convolved to the instrument LSF (Ch. 26 §10.3).

> Use authoritative libraries with pinned versions: **CDMS/JPL** (rotational), **HITRAN/ExoMol** (rovibrational), **Ames PAH IR** database (aromatics), **RRUFF** (solids), **CALSPEC/MAST** (standards/archives).

---

## 2. From optical depth to column density (ices)

For an absorption band with integrated optical depth:
\[
N = \frac{1}{A}\int_{\tilde{\nu}_1}^{\tilde{\nu}_2} \tau(\tilde{\nu})\,d\tilde{\nu}
\]
- \(N\): column density (molecules cm⁻²)
- \(A\): band strength (cm molecule⁻¹), **from laboratory data with citation and version**
- Integration bounds must be stated; continuum model and masks recorded in provenance.

**Band‑strength registry stub** `sources/band_strengths/[SOURCE_ID].json`:
```json
{
  "species": "CO2",
  "band_center_cm-1": 2340,
  "window_cm-1": [2300, 2380],
  "A_cm_per_molecule": 1.1e-17,
  "reference": "[DOI]",
  "source_id": "lab:CO2_ice_A@v1",
  "uncertainty": 0.1
}
```
Store temperature, mixture, and morphology (amorphous/crystalline) since \(A\) and profiles can vary.

---

## 3. Rotational lines: excitation and column density

### 3.1 Optically thin LTE estimate
For a transition \(u\to l\):
\[
N_{\mathrm{tot}} = \frac{8\pi k \nu^2}{h c^3 A_{ul}}\,\frac{Q(T_{\mathrm{ex}})}{g_u}\,\exp\!\left(\frac{E_u}{k T_{\mathrm{ex}}}\right) \int T_B\,dv
\]
- \(A_{ul}\): Einstein coefficient; \(Q\): partition function; \(g_u\): upper‑state degeneracy; \(E_u\) in K or J (be explicit); \(\int T_B dv\) in K km s⁻¹.
- Pull \(A_{ul}, E_u, g_u, Q(T)\) from **CDMS/JPL** with `source_id@version`. Units must be tracked.

### 3.2 Rotational diagram (Boltzmann plot)
Plot \(\ln(N_u/g_u)\) vs \(E_u/k\); slope gives \(-1/T_{\mathrm{rot}}\); intercept yields \(\ln(N_{\mathrm{tot}}/Q)\). Correct for optical depth and beam filling if known.

### 3.3 Non‑LTE note
If densities are below critical or radiative trapping is important, use a non‑LTE solver (e.g., **RADEX/LVG**) offline. Record model and collision rates version in the manifest.

**Line‑catalog reference stub** `sources/lines/[SPECIES]_CDMS_[VER].json`:
```json
{
  "species": "CO",
  "transition": "J=1-0",
  "nu_GHz": 115.271,
  "A_ul": 7.203e-8,
  "E_u_K": 5.53,
  "g_u": 3,
  "Q_ref": "Q(T) table ref",
  "catalog": "CDMS@2024"
}
```

---

## 4. PAHs and large molecules

- Use **Ames PAH IR** templates; fit 3.3, 6.2, 7.7, 8.6, 11.2 µm complexes with blended profiles (Drude/Voigt).
- Record charge state and size proxies if inferred (ionized PAHs shift band positions and relative intensities).
- Treat continuum carefully; store polynomial/spline order and windows.

---

## 5. Mixtures, isotopologues, and chemistry

- **Isotopologues/isotopes**: ¹³CO, C¹⁸O, H¹³CN… lines shift and have different intensities; use for optical‑depth diagnostics.
- **Mixtures**: NNLS across templates for multi‑component ices or blended lines; penalize excessive components (Ch. 15 §6).
- **Chemistry context**: reaction pathways on grains (CO → H₂CO → CH₃OH), photolysis/thermal processing tracks seen in profile changes; record environment (UV field, temperature cycles).

---

## 6. Workflow: lab ↔ telescope ↔ app

1. **Lab spectra**: measure ices/solids at known T and mixture; derive band strengths and profiles. Save as `sources/band_strengths/*.json` with DOIs.
2. **Archive/telescope**: ingest FITS; verify axis units and frame; attach RSRF and LSF (Ch. 26 §1–2). Mask tellurics.
3. **Template preparation**: convolve lab/theory templates to instrument LSF; resample **template** to data grid; apply barycentric/LSR shifts to templates.
4. **Identification**: use cross‑correlation for dense bands; peak‑set likelihood for sparse bands; Bayesian fusion across species with priors (Ch. 7).
5. **Quantitation**: integrate \(\tau(\tilde{\nu})\) for ices; use \(\int T_B dv\) and catalog parameters for rotational lines; report propagation of uncertainties.
6. **Reporting**: evidence graph links each identification to specific bands/lines, templates, and sources with versions.

---

## 7. Quality control and acceptance

A spectrum is **fit for astrochemical inference** when:
- **Axis/units/frames** are explicit; air↔vacuum conversions and velocity frames recorded (Ch. 5, 26).
- **LSF/RSRF** are known or analysis is explicitly marked relative; telluric masks present.
- **SNR** exceeds modality thresholds in key windows; continuum model recorded.
- **Library IDs** are pinned (`source_id@version`) and checksummed.

Failure modes: mis‑framed velocities, un‑convolved templates, unit drift (µm vs cm⁻¹), continuum misfits.

---

## 8. JSON outputs

**Ice band result**
```json
{
  "result_id": "ice:[UUID]",
  "species": "CO2",
  "band_center_um": 4.26,
  "N_cm-2": 1.8e17,
  "A_source": "lab:CO2_ice_A@v1",
  "integration_cm-1": [2300, 2380],
  "tau_area_cm-1": 0.0023,
  "uncertainty": {"stat": 0.1, "sys": 0.2},
  "provenance": {"lsf": "lsf_id", "continuum": "poly_deg2", "mask": "mask_id"}
}
```

**Rotational line result**
```json
{
  "result_id": "rot:[UUID]",
  "species": "CO",
  "transition": "J=1-0",
  "int_TB_dv_K_kms": 12.3,
  "Tex_K": 12.0,
  "N_cm-2": 2.4e16,
  "catalog": "CDMS@2024",
  "A_ul": 7.203e-8,
  "Eu_K": 5.53,
  "gu": 3,
  "Q_T": 45.1,
  "frame": "LSR",
  "provenance": {"lsf": "lsf_id", "baseline": "poly_deg1", "window_kms": [-50, 50]}
}
```

---

## 9. Visualization patterns

- **Continuum‑subtracted overlays** of PAH/ice bands with uncertainty ribbons; show integration windows and masks.
- **Velocity‑stacked plots** of rotational lines with a shared \(v\) axis; mark systemic velocity and isotopologue positions.
- **Rotational diagrams** with fit lines and confidence bands; table links back to line entries.

---

## 10. Cross‑links

- Ch. 4 (source registry), Ch. 5 (units/air–vacuum), Ch. 6 (LSF/response), Ch. 7 (fusion/priors), Ch. 8 (provenance), Ch. 12 (FITS/sidecars), Ch. 15 (mixtures), Ch. 26 (Astrophysics).

---

## 11. Reference anchors (full citations in Ch. 32)
- **CDMS** and **JPL** spectral line catalogs.
- **HITRAN** and **ExoMol** for rovibrational data.
- **Ames PAH IR** spectral database.
- **LAMDA** collisional data; **RADEX** for non‑LTE modeling.
- **Boogert, Gerakines & Whittet (2015)** ice reviews; **Tielens, *Physics and Chemistry of the ISM***.
- **NIST ASD** for atomic references; **RRUFF** for mineral solids.

> Astrochemistry merges lab constants and sky spectra. If you don’t pin versions and record frames/resolution, the chemistry will lie to you. This chapter gives the math and the paper trail so it can’t.

