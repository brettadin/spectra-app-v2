# Chapter 24 — Physics

> **Purpose.** Supply the physical principles that our spectroscopy workflows rely on so that acquisition, calibration, identification, and reporting (Ch. 1–23) stay grounded in first‑principles reasoning rather than folklore.
>
> **Scope.** Quantum states and transitions, intensities and populations, line shapes and broadening, light–matter interaction, optics of sampling (ATR, reflectance), radiometry, detector noise, and sampling/resolution. Formulas and variables match notation used elsewhere (Ch. 5–7, 12).
>
> **Path notice.** Any filenames and directories mentioned are **placeholders** resolved at runtime by the app’s path resolver (Ch. 14). Tokens like `[SESSION_ID]`, `[DATASET_ID]`, `[YYYYMMDD]` must **not** be hardcoded.

---

## 0. Constants, notation, and units (canonical)

- **Constants** (pin versions in manifests; see Ch. 5): speed of light \(c\), Planck’s constant \(h\), reduced Planck \(\hbar\), Boltzmann \(k_B\), Avogadro \(N_A\), elementary charge \(e\), vacuum permittivity \(\varepsilon_0\).
- **Variables**: wavelength \(\lambda\) (nm), frequency \(\nu\) (Hz), wavenumber \(\tilde{\nu}\) (cm⁻¹), energy \(E\) (eV), temperature \(T\) (K).
- **Relations**: \(\nu=c/\lambda\), \(E=h\nu=hc/\lambda\), \(\tilde{\nu}=1/\lambda_{\text{cm}}\), small‑shift Doppler \(\Delta v/c \approx \Delta\lambda/\lambda\).
- **Medium**: “air” vs “vacuum” flags required; conversions via Ciddor/Edlén (Ch. 5).

---

## 1. Quantum states and transition probabilities

### 1.1 Eigenstates and selection rules
- **Eigenproblem**: \(\hat H\lvert n\rangle = E_n\lvert n\rangle\). Transitions occur when the perturbation couples states.
- **Time‑dependent perturbation** (electric dipole): matrix element \(\mu_{fi} = \langle f\lvert \hat{\mu} \rvert i\rangle\).
- **Selection rules** (typical cases):
  - **IR (vibrational)**: \(\Delta\mu\ne 0\) along the normal mode; fundamental \(\Delta v=\pm1\) dominant.
  - **Raman**: \(\Delta\alpha\ne 0\) (polarizability change). Depolarization ratio reports symmetry.
  - **Electronic (UV–Vis)**: spin‑allowed; Laporte parity rule in centrosymmetric systems; vibronic coupling relaxes rules.
  - **Rotational**: \(\Delta J=\pm1\) for rovibrational P/R branches; Q‑branch mode‑dependent.

### 1.2 Intensities from Fermi’s Golden Rule
For angular frequency \(\omega\):
\[
W_{i\to f} \propto \big|\langle f\lvert\hat{V}(\omega)\rvert i\rangle\big|^2\,g(\omega)
\]
with density of final states \(g(\omega)\). In practice this reduces to dipole (IR/UV–Vis) or polarizability (Raman) moments times line‑shape factors.

### 1.3 Einstein coefficients and oscillator strength
- **Einstein A/B** relate spontaneous/stimulated processes. Absorption cross‑section \(\sigma(\nu)\) connects to oscillator strength \(f\): \(\int \sigma(\nu)\,d\nu \propto f\).
- **Fluorescence quantum yield**: \(\Phi = k_r/(k_r+k_{nr})\); lifetime \(\tau = 1/(k_r+k_{nr})\).

---

## 2. Populations and temperature dependence

- **Boltzmann distribution** for level populations: \(N_j/N = g_j\,\exp(-E_j/k_BT)/Z\) with partition function \(Z=\sum_j g_j\,e^{-E_j/k_BT}\).
- **Vibrational/rotational** population factors control overtone/branch intensities.
- **Raman Stokes/anti‑Stokes** ratio thermometer:
\[
\frac{I_{\text{aS}}}{I_{\text{S}}} \approx \left(\frac{\nu_0-\nu_v}{\nu_0+\nu_v}\right)^4 \exp\!\left( -\frac{hc\,\nu_v}{k_B T} \right)
\]

---

## 3. Line shapes and broadening mechanisms

### 3.1 Natural, Doppler, collisional
- **Natural** (lifetime) width: Lorentzian with HWHM \(\gamma_n = 1/(4\pi\tau)\).
- **Doppler** (thermal) Gaussian FWHM:
\[
\Delta \nu_D = \nu_0\sqrt{\frac{8k_B T\ln 2}{mc^2}}
\]
- **Collisional (pressure)**: Lorentzian width \(\gamma_c \propto P\) with species‑specific coefficients.

### 3.2 Voigt profile and instrument convolution
- **Voigt** is the convolution of Gaussian and Lorentzian. Empirical FWHM approximation:
\[
w_V \approx 0.5346\,(2\gamma) + \sqrt{0.2166\,(2\gamma)^2 + w_G^2}
\]
- **Instrument line spread function (LSF)** must be convolved with library templates before comparison (Ch. 6). We **never** deconvolve to set ground truth; deconvolution is for diagnostics only.

---

## 4. Light–matter in bulk samples

### 4.1 Beer–Lambert law (transmission)
\[
A(\lambda) = \log_{10}\!\frac{I_0}{I} = \varepsilon(\lambda)\,c\,\ell
\]
Mixtures: \(A = \sum_j \varepsilon_j c_j \ell\) if non‑interacting; record limitations and stray‑light checks (Ch. 2, 15).

### 4.2 Diffuse reflectance and Kubelka–Munk
For optically thick samples:
\[
F(R_\infty) = \frac{(1-R_\infty)^2}{2R_\infty}
\]
Used to approximate absorption‑like behavior from reflectance; report when used and assumptions (Ch. 15).

### 4.3 ATR effective path length (penetration depth)
For incident angle \(\theta\) and indices \(n_1,n_2\) with evanescent field:
\[
\delta_p = \frac{\lambda}{2\pi n_1\sqrt{\sin^2\theta - (n_2/n_1)^2}}
\]
Record crystal type, \(\theta\), and contact pressure; changes in \(\delta_p\) affect relative band intensities.

### 4.4 Tauc analysis for semiconductors
\[
(\alpha h\nu)^{1/m} = C(h\nu - E_g),\quad m=\tfrac{1}{2}\;\text{(direct)},\; m=2\;\text{(indirect)}
\]
Fit the **linear region** only; store window and model choice (Ch. 15).

---

## 5. Scattering and Raman specifics

- **Polarizability tensor** \(\boldsymbol{\alpha}\): intensity \(I\propto |\mathbf{e}_s^T\,\boldsymbol{\alpha}\,\mathbf{e}_i|^2\) with incident/scattered polarizations \(\mathbf{e}_{i,s}\).
- **Resonance Raman**: pre‑resonant enhancement near electronic transitions; log \(\lambda_0\) precisely and treat fluorescence background carefully.
- **Depolarization ratio** \(\rho = I_\perp/I_\parallel\) informs mode symmetry; requires polarization‑controlled setup.

---

## 6. Radiometry and frames (astro and lab)

- **Irradiance** \(E_\lambda\) (W m⁻² nm⁻¹), **radiance** \(L_\lambda\) (W m⁻² sr⁻¹ nm⁻¹), **photon flux** (photons s⁻¹ m⁻² nm⁻¹). Record which you use.
- **Response** (RSRF): converts counts to physical units; derived from standards (Ch. 6). Store as function of \(\lambda\) with validity window.
- **Velocity frames**: apply barycentric correction; compare spectra in the **same** frame. Cross‑correlate templates after LSF convolution (Ch. 15 astro).

---

## 7. Detector physics and noise

- **Shot noise** \(\sigma \approx \sqrt{N}\), **read noise** (electronics), **dark current**, **1/f** components.
- **SNR** measured in line‑free windows; report method and window bounds.
- **Dynamic range** and **linearity**: verify with standards (e.g., holmium, neutral density filters). Avoid saturation; store integration time and slit widths.

---

## 8. Sampling, resolution, and aliasing

- **Sampling**: step size \(\Delta x\) must satisfy ≥2–3 points per FWHM to resolve line shapes.
- **Apodization** in FTIR: trade resolution for sidelobe suppression; record function and effective resolution.
- **Convolution policy**: always convolve high resolution down to low for overlays; never upsample as evidence (Ch. 6, 15).

---

## 9. Fields, perturbations, and environments

- **Zeeman/Stark** effects split lines; if fields present, record field strengths and geometry in manifests.
- **Matrix/solvent shifts**: dielectric environment changes electronic and vibrational energies; store solvent/pH/ionic strength.
- **Temperature/pressure**: control and log; affects populations and line shapes (Ch. 2, 6).

---

## 10. Kinetics and photophysics

- **Rate equations** for excited states: \(dN^*/dt = k_{abs}N - (k_r + k_{nr})N^*\).
- **Quenching** (Stern–Volmer): \(I_0/I = 1 + K_{SV}[Q]\); **time‑resolved** separates dynamic vs static quenching.
- **Energy transfer** (FRET) qualitative note: \(R_0\) depends on overlap integral and orientation; not default campus capability but appears in literature comparisons.

---

## 11. Group theory at a glance (assignments)

- **Character tables** predict IR/Raman activity; centrosymmetric molecules obey mutual exclusion (IR vs Raman active).
- Use **depolarization** and **polarization selection** in Raman to assign mode symmetries.

---

## 12. What to record every time (physics fields in manifests)

- Axis units and **medium**; instrument ID; **RSRF** and **LSF** references with validity; temperature/pressure; ATR geometry if used; baseline model; masks; uncertainty method; calibration artifacts used (polystyrene, Si, lamps, standard stars). See Ch. 8 for manifest schema.

---

## 13. Worked mini‑examples

- **Gas temperature from Doppler width**: fit Gaussian width to an isolated line, use §3.1 to solve for \(T\); compare to pressure‑broadening expectation.
- **ATR penetration depth change**: compute \(\delta_p\) for ZnSe vs diamond crystals; explain intensity ratios across bands.
- **Raman anti‑Stokes check**: estimate \(T\) from \(I_{aS}/I_S\) on a mode at 1000 cm⁻¹ with \(\lambda_0=785\) nm.
- **Stellar radial velocity**: cross‑correlate a template convolved to the instrument LSF, find CCF peak, convert to \(v_r\), and include barycentric frame.

---

## 14. Cross‑links

- Ch. 5 (units/axes), Ch. 6 (calibration, LSF, response), Ch. 7 (identification logic), Ch. 12 (formats), Ch. 15 (comparisons), Ch. 23 (Spectroscopy specifics), Ch. 32 (Sources).

---

## 15. Reference anchors (full citations in Ch. 32)

- Core texts: Skoog/Holler/Crouch; Hollas; Demtröder; Lakowicz; Gray & Corbally.
- HITRAN/ExoMol/JPL/CDMS for line data; NIST ASD for atomic; CALSPEC/MAST for standards.
- Ciddor/Edlén refractive index of air; Voigt profile approximations (Humlíček/Whiting‑style); Kubelka–Munk theory; ATR penetration depth derivations.

> **Rule of engagement.** If code changes any physics or definitions here, update this chapter and the Docs module (Ch. 13) in the **same commit** that changes the implementation.

