# Chapter 5 — Unifying Axes and Units in the App

> **Purpose.** Specify iron‑clad, testable rules for spectral axes and unit handling so every dataset in the application is interoperable. Provide formulas, tolerances, APIs, and QA checks that prevent cumulative errors and axis chaos.
>
> **Scope.** Optical spectroscopy used in this project: atomic/UV–Vis (wavelength, energy), IR (wavenumber), Raman (Raman shift), fluorescence (excitation/emission), with optional astrophysical frequency/velocity frames. Includes conversions among nm, µm, cm⁻¹, eV, THz, and vacuum↔air wavelength handling.
>
> **Path notice.** File and folder names are **placeholders**. Resolve at runtime using the app’s path resolver. Tokens like `[SESSION_ID]`, `[MODALITY]`, `[DATASET_ID]` are variables.

---

## 0. Canonical axis per modality (contract)

| Modality | Canonical axis | Allowed views | Notes |
|---|---|---|---|
| Atomic, UV–Vis | Wavelength **λ** in **nm** | cm⁻¹, µm, eV, THz | Vacuum wavelengths preferred; allow air wavelengths with explicit flag and conversion (see §3). |
| IR (FTIR/ATR/gas) | Wavenumber **\(\tilde{\nu}\)** in **cm⁻¹** | µm, nm, THz | Increasing axis left→right (low to high cm⁻¹) is recommended for data arrays; UI may flip for convention. |
| Raman | Raman shift **Δ\(\tilde{\nu}\)** in **cm⁻¹** | Emission wavelength nm | Must use **exact** laser wavelength λ₀ (nm) logged per acquisition. |
| Fluorescence | Emission λ in **nm** (plus Excitation λ in nm) | cm⁻¹, eV | Report Stokes shift in nm and cm⁻¹. |
| Astrophysical | Wavelength **nm** or Frequency **Hz** (per header) | Velocity frames (km s⁻¹) | Respect FITS/WCS spectral conventions; do not modify raw headers, only create views. |

**Rule C‑1 (Idempotence).** The canonical array is stored once. Any view is a computed, non‑persisted transform. No chained conversions.

**Rule C‑2 (Monotonicity).** Stored canonical axes must be strictly monotone. If an instrument outputs descending axes, store a view for rendering but preserve a monotone data array.

---

## 1. Fundamental relations and exact constants

Let **c** be the speed of light and **h** Planck’s constant (use CODATA‑pinned values in code; store version in manifest).

- Wavenumber (vacuum): \(\tilde{\nu} = 1/\lambda_{\mu m}\) in cm⁻¹ when λ is in cm.
- Frequency: \(\nu = c/\lambda\).
- Photon energy: \(E = h\,c/\lambda = h\,\nu\) with preferred view \(E\,[\mathrm{eV}] = \tfrac{hc}{e}\,\tfrac{1}{\lambda}\).
- Handy factor: \(E\,[\mathrm{eV}] \approx 1239.841984\,\mathrm{eV\,nm}/\lambda\,[\mathrm{nm}]\). Store the exact factor used and its source.

**Raman shift (exact)** using emitted wavelength λₛ and excitation λ₀ (both in nm):
\[
\Delta\tilde{\nu}\;[\mathrm{cm}^{-1}] = 10^{7}\!\left(\frac{1}{\lambda_0}\; - \;\frac{1}{\lambda_s}\right)
\]

**Error propagation** (1σ) for Raman shift if λ₀ has uncertainty σ₀ and λₛ has σₛ:
\[
\sigma_{\Delta\tilde{\nu}}^2 = \left(10^{7}\,\frac{1}{\lambda_0^2}\,\sigma_0\right)^2 + \left(10^{7}\,\frac{1}{\lambda_s^2}\,\sigma_s\right)^2
\]

---

## 2. Unit conversions (formulas and guards)

### 2.1 Wavelength ↔ wavenumber
- \(\tilde{\nu}\,[\mathrm{cm}^{-1}] = 10^{7}/\lambda\,[\mathrm{nm}]\)
- \(\lambda\,[\mathrm{nm}] = 10^{7}/\tilde{\nu}\,[\mathrm{cm}^{-1}]\)

### 2.2 Wavelength ↔ energy (eV)
- \(E\,[\mathrm{eV}] = 1239.841984\,/\,\lambda\,[\mathrm{nm}]\)
- \(\lambda\,[\mathrm{nm}] = 1239.841984\,/\,E\,[\mathrm{eV}]\)

### 2.3 Wavelength ↔ frequency
- \(\nu\,[\mathrm{THz}] = 299.792458\,/\,\lambda\,[\mathrm{\mu m}]\)
- \(\lambda\,[\mathrm{\mu m}] = 299.792458\,/\,\nu\,[\mathrm{THz}]\)

**Guard G‑1 (Precision).** Use float64 for axes. When converting, compute from canonical, never from a previously converted view.

**Guard G‑2 (Labeling).** Every array/view carries an explicit `unit` field. UI shows a unit badge on axes and in legends.

---

## 3. Vacuum vs air wavelengths (atomic/UV–Vis)

Many historical line lists are in **air wavelengths**. Modern practice prefers **vacuum**. Provide conversions using a standard refractive index of dry air at defined conditions.

- **Air to vacuum:** \(\lambda_{vac} = n_{air}\,\lambda_{air}\)
- **Vacuum to air:** \(\lambda_{air} = \lambda_{vac}/n_{air}\)

Use a recognized dispersion relation (Edlén‑type or Ciddor) parameterized by pressure, temperature, CO₂ fraction, and humidity. Store the chosen model name and parameters in the manifest for every conversion.

**Guard G‑3.** Never silently assume air or vacuum. Require an explicit flag in the dataset (`wavelength_medium: "vacuum"|"air"`) and log any conversion with the full parameter set.

---

## 4. Raman specifics

1. Always store λ₀ (exact excitation wavelength) measured or factory‑specified; prefer measured if available.
2. Compute Raman shift from λ₀ and the **detector‑space** peak position λₛ; do not back‑convert from a previously computed shift.
3. Display both **Raman shift** and **emission wavelength** views in the UI with synchronized cursors.
4. Record whether anti‑Stokes region is captured; mark temperature estimates if intensity ratios are used.

---

## 5. Fluorescence specifics

- Store excitation and emission spectra in separate tracks with their own units and corrections.
- **Stokes shift:** report both in nm and cm⁻¹ using the Raman‑style relation with λ₀=λ_ex and λₛ=λ_em,peak.

---

## 6. Axis direction and resampling policy

- **Storage:** canonical arrays are strictly monotone and uniformly typed (float64).
- **Rendering:** views may be reversed for convention (e.g., IR high→low cm⁻¹); this is cosmetic only.
- **Resampling:** if a comparison requires common sampling, create a **view** with interpolation; record method (`linear|cubic|fft`) and parameters. Never overwrite source sampling.

---

## 7. API surface (pseudocode) — conversions and views

```python
class AxisView(Enum):
    CANONICAL = "canonical"
    WAVENUMBER_CM1 = "cm-1"
    WAVELENGTH_NM = "nm"
    WAVELENGTH_UM = "um"
    ENERGY_EV = "eV"
    FREQUENCY_THz = "THz"

class Spectrum:
    axis: np.ndarray  # canonical
    unit: str         # e.g., "nm", "cm-1"
    meta: dict        # instrument, medium, lambda0, etc.

    def as_view(self, target: AxisView, *, medium: str|None=None,
                air_model: AirIndexModel|None=None) -> View:
        """Return non-persistent transformed view. No chaining."""
        # 1) validate canonical
        # 2) convert with exact formulas/constants
        # 3) attach view metadata: {source_unit, target_unit, method, constants_version}
        ...
```

**Validation hooks**
- Reject if `unit` missing.
- Warn if air/vacuum mismatch without `medium`.
- Cache results keyed by (source hash, target, parameters) to avoid drift across calls.

---

## 8. UI/UX rules

- Unit badges on plots (e.g., **λ [nm]**, **\(\tilde{\nu}\) [cm⁻¹]**, **E [eV]**); hover tooltip shows the other representations at the cursor.
- A single **Units** control toggles views per panel. Toggling does not modify underlying data.
- “Copy value” copies all synchronized forms at the cursor, e.g., `λ=532.000 nm | \(\tilde{\nu}\)=18797.3 cm⁻¹ | E=2.329 eV`.
- If views are convolved to a common resolution for overlay, show a banner: `Displayed at FWHM = 6.0 cm⁻¹`.

---

## 9. Numeric tolerances and matching windows

Set tolerances relative to local instrument resolution.

- **Position tolerance**: \(\pm 2\,\sigma_{inst}\) default unless library uncertainty dominates.
- **Raman shift tolerance**: combine λ₀ and λₛ uncertainties via §1 error propagation, then inflate by instrument resolution.
- **Air/vacuum conversion uncertainty**: propagate from n_air model parameters.

All tolerances are recorded in the `transforms_applied` or `matching_params` sections of manifests and reports.

---

## 10. Quality assurance and tests

### 10.1 Round‑trip tests (must pass)
- nm → cm⁻¹ → nm returns to within **relative error ≤ 1e‑12** for synthetic arrays in float64.
- nm → eV → nm within 1e‑12 using the pinned constants.
- Raman λ space → shift space → λ space recovers peaks within **0.1 cm⁻¹** at 500–2000 cm⁻¹ typical regions.

### 10.2 Property‑based tests
- Monotone canonical arrays produce monotone views (except intentional reversals for display).
- No unitless arrays accepted; uploads missing units are rejected with a clear error.

### 10.3 Fixtures
- Include fixtures for: Hg/Ne/Xe lamp lines (nm), polystyrene peaks (cm⁻¹), Si Raman 520.7 cm⁻¹, holmium filter features (nm).

---

## 11. Examples (worked small)

### 11.1 500.0 nm conversions
- \(\tilde{\nu} = 10^{7}/500.0 = 20000.0\,\mathrm{cm}^{-1}\)
- \(E \approx 1239.841984/500.0 = 2.479684\,\mathrm{eV}\)
- \(\nu = c/\lambda \approx 5.99585\times10^{14}\,\mathrm{Hz}\)

### 11.2 Raman with λ₀ = 785.02 nm, peak at λₛ = 830.00 nm
- \(\Delta\tilde{\nu} = 10^{7}(1/785.02 - 1/830.00) \approx 695.7\,\mathrm{cm}^{-1}\)

> Verify these with the app’s unit inspector; store constants and last verification date in the session manifest.

---

## 12. Manifest fields (axis/units section)

```json
{
  "axis_units": {
    "canonical": "cm-1|nm|eV|THz",
    "medium": "vacuum|air",
    "air_model": {"name": "Ciddor96|Edlen66", "params": {"P_Pa": 101325, "T_K": 293.15, "xCO2": 0.0004, "RH": 0.0}},
    "constants": {"c": "CODATA-20xx", "h": "CODATA-20xx"},
    "raman": {"lambda0_nm": 785.02, "lambda0_unc_nm": 0.02}
  }
}
```

---

## 13. Common pitfalls and explicit mitigations

- **Mixing air and vacuum wavelengths.** Mitigation: require `medium` field; red banner if absent; conversion recorded with model and parameters.
- **Chained conversions causing drift.** Mitigation: always compute from canonical; unit tests enforce round‑trip bounds.
- **Axis flipped silently.** Mitigation: data arrays remain monotone; UI flip is cosmetic and labeled.
- **Raman with nominal λ₀.** Mitigation: store measured λ₀ when possible; otherwise mark nominal and increase uncertainty.
- **Over‑rounded tick labels.** Mitigation: keep high precision in data; round labels only; tooltips show full precision.

---

## 14. Cross‑links

- Chapter 1 for modality definitions; Chapter 2 for acquisition SOPs that collect λ₀ and mediums; Chapter 3 for cross‑modal fusion that depends on matched axes; Chapter 6 for resolution/LSF details; Chapter 8 for provenance fields that store constants and conversions.

---

## 15. References (anchor list)
- IUPAC Gold Book entries for spectral quantities and Beer–Lambert law.
- CODATA recommended values for physical constants.
- Standard air refractive index formulations (Edlén‑type; Ciddor’s 1996 parameterization).
- FITS/WCS spectral axis conventions for astrophysical data (WAVE/FREQ/VRAD).

