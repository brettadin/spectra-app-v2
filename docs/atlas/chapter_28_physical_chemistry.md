# Chapter 28 — Physical Chemistry

> **Purpose.** Ground the spectroscopy workflows in thermodynamics, kinetics, and statistical mechanics so that observed spectral changes map to defensible thermodynamic and kinetic quantities with units, uncertainties, and provenance.
>
> **Scope.** Equilibria, activities, partition functions, temperature/pressure effects, reaction rates, adsorption, phase behavior, transport, and how these propagate into IR/Raman/UV–Vis/fluorescence and astro use‑cases. Equations and symbols match earlier chapters (Ch. 5–7, 12, 23–27).
>
> **Path notice.** Filenames and directories below are **placeholders** resolved at runtime by the app’s path resolver. Tokens like `[SESSION_ID]`, `[DATASET_ID]`, `[YYYYMMDD]`, `[MODEL_ID]` are variables. Do **not** hardcode.

---

## 0. Thermodynamics: state functions, activities, equilibria

- **Gibbs energy**: \(\Delta G = \Delta H - T\,\Delta S\). Reaction spontaneity at constant \(T,p\): \(\Delta G<0\).
- **Chemical potential** of species \(i\): \(\mu_i = \mu_i^\circ + RT\ln a_i\), with activity \(a_i = \gamma_i x_i\) (solutions) or \(a_i = p_i/p^\circ\) (gases). Record **activity model** and ionic strength when used.
- **Equilibrium constant**: \(\Delta G^\circ = -RT\ln K\). Use **activities**, not bare concentrations, when ionic strength is non‑negligible.
- **van’t Hoff** (temperature dependence):
  \[
  \frac{d\ln K}{dT} = \frac{\Delta H^\circ}{RT^2}\quad \Rightarrow \quad \ln K = -\frac{\Delta H^\circ}{R}\frac{1}{T} + \frac{\Delta S^\circ}{R}
  \]
  Fit \(\ln K\) vs \(1/T\) linearly; report fit window and heteroscedastic errors.
- **Activity coefficients** (electrolytes): Debye–Hückel (dilute), Davies (moderate), Pitzer (high I). Pin chosen model and parameters in manifests.

**Thermo context sidecar** `sessions/[SESSION_ID]/thermo_context.json` (example):
```json
{
  "T_K": 298.15,
  "p_Pa": 101325,
  "ionic_strength": 0.10,
  "activity_model": {"name": "Davies", "params": {"A": 0.51}},
  "standard_state": {"solvent": "water", "p0_Pa": 101325},
  "notes": "Buffered at pH 7.0 with phosphate; CO2 minimized"
}
```

---

## 1. Statistical mechanics link: populations and intensities

- **Partition function** \(q\) per molecule; total \(Q = q^N/N!\). Populations: \(N_j/N = g_j e^{-E_j/k_BT}/Z\).
- **Spectral consequence**: relative line intensities follow Boltzmann factors and transition moments. Examples: rotational envelopes (temperature), Stokes/anti‑Stokes Raman ratio (Ch. 23 §2.2):
  \[
  \frac{I_{\text{aS}}}{I_{\text{S}}} \approx \left(\frac{\nu_0-\nu_v}{\nu_0+\nu_v}\right)^4 e^{-hc\nu_v/k_BT}
  \]
- **Isotopic substitution**: vibrational frequency scales approximately as \(\tilde\nu \propto \sqrt{k/\mu}\). Use to assign modes or diagnose mixtures.

---

## 2. Kinetics: rate laws and extraction from spectra

- **General rate law**: for \(A\to P\), \(d[A]/dt = -k[A]^n\). Integrated forms used for fits:
  - First‑order: \(\ln([A]_t/[A]_0) = -kt\)
  - Pseudo‑first order: keep excess reagent constant; fit as first‑order in the limiting species.
  - Second‑order (simple): \(1/[A]_t - 1/[A]_0 = kt\)
- **Arrhenius**: \(k(T) = A\,e^{-E_a/RT}\); **Eyring/transition‑state**: \(k = (k_BT/h)\,e^{\Delta S^\ddagger/R} e^{-\Delta H^\ddagger/RT}\).
- **From spectra**: convert an observable \(y(t)\) (absorbance, band area, ratio) to species concentration via calibration or stoichiometric relations. Fit globally across multiple bands to improve robustness.
- **Mechanisms**: consecutive (A→B→C), parallel, reversible; fit microkinetic ODEs when needed with confidence intervals.

**Kinetics fit sidecar** `sessions/[SESSION_ID]/kinetics_fit.json` (example):
```json
{
  "model": "first_order",
  "observable": "IR C=O area",
  "mapping": {"A": "area_to_conc:calib_id"},
  "T_K": [298.15, 308.15, 318.15],
  "k_s-1": [0.012, 0.027, 0.051],
  "arrhenius": {"Ea_kJ_per_mol": 52.1, "lnA": 23.4},
  "uncertainty": {"method": "bootstrap", "n": 2000}
}
```

---

## 3. Phase behavior and thermophysical effects

- **Clapeyron**: \(dP/dT = \Delta S/\Delta V\). **Clausius–Clapeyron** (vapor pressure): \(\ln P = -\Delta H_{vap}/(RT) + C\).
- **Solutions**: Raoult’s law (ideal), Henry’s law (dilute solute). Deviations captured by activity coefficients.
- **Spectral signatures**: phase transitions sharpen/split bands; ATR effective path depth changes with refractive index (Ch. 24 §4.3).

---

## 4. Electrolytes, pH, and buffers

- **Henderson–Hasselbalch**: \(\mathrm{pH} = \mathrm{p}K_a + \log([A^-]/[HA])\). Apparent \(pK_a\) depends on ionic strength; record buffer composition.
- **Ionic strength**: \(I = \tfrac{1}{2}\sum_i c_i z_i^2\). Debye–Hückel (dilute): \(\log \gamma_i = -A z_i^2 \sqrt{I}/(1+Ba_i\sqrt{I})\).
- **Spectral link**: acid/base forms have distinct IR/Raman features and UV–Vis \(\lambda_{max}\). Use speciation to set priors (Ch. 25 §2).

---

## 5. Adsorption, surfaces, and thin films

- **Langmuir isotherm**: coverage \(\theta = KC/(1+KC)\) or with pressure \(P\). Competitive adsorption extends to multiple species.
- **Kinetics on surfaces**: Langmuir–Hinshelwood vs Eley–Rideal; use IR band areas at the surface or SERS intensities as proxies for \(\theta\).
- **Thin‑film optics**: interference fringes encode thickness; combine with Tauc for \(E_g\); log substrate, angle, and refractive indices.

**Adsorption fit stub** `sessions/[SESSION_ID]/adsorption_fit.json`:
```json
{
  "model": "Langmuir",
  "temperatures_K": [298.15],
  "concentrations_M": [0.01, 0.02, 0.05, 0.10],
  "theta_from": "IR band area normalized",
  "K_M-1": 1200,
  "CI": {"95%": [900, 1600]}
}
```

---

## 6. Transport and time resolution

- **Diffusion** (Fick): \(\partial c/\partial t = D\,\partial^2 c/\partial x^2\). Mixing and flow set observed time constants; record cell geometry, flow rate, and path length.
- **Heat transfer** affects temperature during long acquisitions; log stabilization time and temperature drift.

---

## 7. Uncertainty propagation and fitting discipline

- **Propagation**: if \(y=f(\mathbf{x})\) with covariance \(\mathbf{\Sigma}_x\), then \(\Sigma_y \approx J\,\Sigma_x\,J^T\) with Jacobian \(J\). Report confidence intervals on \(K\), \(k\), \(\Delta H^\circ\), \(E_a\).
- **Regression honesty**: weighted least squares with uncertainty per point; check residuals for structure; include parameter covariances in sidecars.
- **Model comparison**: use AIC/BIC for mechanism choice; report \(\Delta\)AIC in reports (Ch. 7, 11).

---

## 8. Mapping spectra to thermodynamic/kinetic quantities

- **Equilibrium from absorbance** (two‑species example): if \(A = \varepsilon_{HA} \ell [HA] + \varepsilon_{A^-} \ell [A^-]\) and \(C_{tot}=[HA]+[A^-]\), solve for \([A^-]\), then \(K_a = [H^+][A^-]/[HA]\). Propagate uncertainties from \(\varepsilon\) and baseline.
- **Raman/IR band ratios** as proxies for \(\theta\) or conversion when band strengths are known; ensure linearity within range.
- **Astro rotational temperature**: Boltzmann plot of \(\ln(N_u/g_u)\) vs \(E_u/k\) using line integrals (Ch. 27 §3.2).

---

## 9. Acceptance criteria and QC

A dataset supports physical‑chemistry inference when:
- Temperature, pressure, and composition metadata exist with methods (thermometer, barometer, pH meter model/calibration).
- Activity model and ionic strength are recorded for electrolyte systems.
- Baseline and band‑area extraction methods are logged; SNR meets thresholds in diagnostic regions.
- For kinetics, timebase and synchronization to acquisition are recorded; dead‑time characterized.

---

## 10. Worked mini‑examples

### 10.1 van’t Hoff from dimerization (IR)
- Benzoic acid in CCl₄: measure monomer C=O and dimer H‑bond bands at several \(T\). Compute \(K\) from band areas using known \(\varepsilon\); fit \(\ln K\) vs \(1/T\) → \(\Delta H^\circ, \Delta S^\circ\). Record activity model (ideality assumed) and windows.

### 10.2 Arrhenius from ester hydrolysis (IR or UV–Vis)
- Track ester C=O decrease and acid C=O increase or a chromophore in UV–Vis. Pseudo‑first order with water/acid in excess. Extract \(k(T)\) and fit Arrhenius and Eyring parameters.

### 10.3 Langmuir adsorption by ATR‑IR
- Dose analyte solutions over a functionalized surface. Convert band area to \(\theta\) via calibration; fit isotherm; at multiple \(T\), extract adsorption \(\Delta H^\circ\) from van’t Hoff on \(K(T)\).

### 10.4 Rotational temperature from emission
- Use relative intensities of rotational lines to compute \(T_{rot}\) via Boltzmann plot; compare with expected \(T\) from cell or sky conditions.

---

## 11. Data structures (schemas)

**thermo_context.json**
```json
{
  "schema_version": "1.0.0",
  "T_K": 298.15,
  "p_Pa": 101325,
  "solution": {"solvent": "H2O", "ionic_strength": 0.10, "buffer": "phosphate", "pH": 7.00},
  "activity_model": {"name": "Debye-Huckel", "params": {"A": 0.51, "B": 0.33}},
  "standards": ["thermometer:[ID]", "pH_meter:[ID]"],
  "uncertainties": {"T_K": 0.1, "p_Pa": 50}
}
```

**kinetics_fit.json**
```json
{
  "schema_version": "1.0.0",
  "model": "A->P|A<->B|A->B->C",
  "parameters": {"k1_s-1": 0.012, "k-1_s-1": 0.001},
  "temperature_K": 298.15,
  "mapping": {"observable": "IR:C=O_area", "calibration_id": "[ID]"},
  "fit": {"method": "WLS", "covariance": [[...],[...]]},
  "diagnostics": {"AIC": 123.4, "BIC": 130.1, "residual_normality_p": 0.41}
}
```

---

## 12. Cross‑links

- Ch. 5 (units/axes), Ch. 6 (LSF/response), Ch. 7 (identification and priors), Ch. 8 (provenance), Ch. 12 (formats), Ch. 13 (Docs), Ch. 15 (comparisons), Ch. 23–27 (Spectroscopy/Physics/Astro/Astrochemistry), Ch. 11 (rubric and confidence tiers).

---

## 13. Reference anchors (full citations in Ch. 32)

- Atkins & de Paula, *Physical Chemistry* (thermo/kinetics/stat mech).
- McQuarrie & Simon, *Physical Chemistry: A Molecular Approach* (partition functions, spectroscopy links).
- Laidler, Meiser & Sanctuary, *Physical Chemistry* (kinetics, Arrhenius/Eyring).
- IUPAC Gold Book (definitions); CODATA constants.
- NIST Chemistry WebBook (thermochemical data), JANAF tables.
- Debye–Hückel/Davies/Pitzer primary references for activity coefficients.

> Physical chemistry sits between spectra and inference: convert pixels to physics to chemistry, with units and uncertainty or it doesn’t count.

