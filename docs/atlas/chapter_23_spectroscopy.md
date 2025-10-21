# Chapter 23 — Spectroscopy

> **Purpose.** Present the physics that underpins the modalities in this framework so methods, calibrations, and scoring remain grounded in first principles. This is the reference for units, selection rules, line shapes, signal formation, noise, and the standard equations used elsewhere.
>
> **Scope.** Atomic emission/absorption, FTIR/ATR, Raman, UV–Vis, fluorescence, and basic astrophysical spectroscopy. Emphasis on campus‑available instruments and data processing consistent with Chapters 1–22.
>
> **Path notice.** All filenames and directories are **placeholders**. The app resolves tokens like `[SESSION_ID]`, `[DATASET_ID]`, `[MODALITY]`, `[INSTRUMENT_ID]`, `[YYYYMMDD]` at runtime. Do **not** hardcode paths.

---

## 0. Foundations

- **Spectral variables**
  - Wavelength \(\lambda\) (nm), frequency \(\nu\) (Hz), wavenumber \(\tilde{\nu}\) (cm⁻¹), photon energy \(E\) (eV).
  - Relationships: \(\nu = c/\lambda\); \(\tilde{\nu}=1/\lambda_{\text{cm}}\); \(E = h\nu = hc/\lambda\).
  - Raman shift \(\Delta\tilde{\nu} = |\tilde{\nu}_{\text{exc}} - \tilde{\nu}_{\text{scat}}|\) in cm⁻¹.
- **Spectral ranges (indicative)**: UV–Vis ~200–800 nm; near‑IR 0.8–2.5 µm; mid‑IR 2.5–25 µm (4000–400 cm⁻¹); Raman shifts typically 100–3500 cm⁻¹.
- **Medium**: “air” vs “vacuum” matters (dispersion); conversions per Ciddor/Edlén (see Ch. 5).
- **Conservation**: raw arrays are immutable; all transforms are **views** with provenance (Ch. 8).

---

## 1. Notation and constants (canonical)

- Constants pinned by CODATA version in manifests (Ch. 5): speed of light \(c\), Planck’s constant \(h\), Boltzmann \(k_B\), Avogadro \(N_A\).
- **Unit conversions**
  - \(E\,[\text{eV}] = 1240/\lambda\,[\text{nm}]\).
  - \(\tilde{\nu}\,[\text{cm}^{-1}] = 10^{7}/\lambda\,[\text{nm}]\).
  - Differential propagation: if \(y=f(x)\) with uncertainty \(\sigma_x\), then \(\sigma_y = |f'(x)|\,\sigma_x\). Store Jacobians for chained transforms.

---

## 2. Selection rules and what each modality sees

### 2.1 IR absorption (FTIR/ATR)
- **Rule:** mode must change the **dipole moment** (\(\Delta \mu \ne 0\)).
- **Fundamentals/overtones:** \(\Delta v = \pm1\) dominant; overtones/combination bands weaker.
- **Gas‑phase ro‑vibrational branches:** \(\Delta J = \pm1\) → P/R branches; Q‑branch allowed for some linear molecules.

### 2.2 Raman scattering
- **Rule:** mode must change **polarizability** (\(\Delta \alpha \ne 0\)).
- **Stokes vs anti‑Stokes ratio:**
  \[
  \frac{I_{\text{aS}}}{I_{\text{S}}} \approx \left(\frac{\nu_0 - \nu_v}{\nu_0 + \nu_v}\right)^4 \exp\!\left(-\frac{hc\,\nu_v}{k_B T}\right)
  \]
  Useful thermometer for surface temperature.
- **Resonance Raman:** electronic resonance amplifies specific modes; log excitation wavelength \(\lambda_0\).

### 2.3 UV–Vis absorption
- **Electronic transitions:** selection rules by spin and parity (Laporte); charge‑transfer often intense, d–d weaker.
- **Semiconductors:** bandgap from Tauc relation (see §5.4).

### 2.4 Atomic emission/absorption
- **Lines** from discrete electronic levels; intensities reflect population and transition probabilities; ionization balance depends on \(T\) and electron density.

### 2.5 Fluorescence
- **Quantum yield** \(\Phi = k_r/(k_r + k_{nr})\); **lifetime** \(\tau = 1/(k_r + k_{nr})\).
- **Stern–Volmer quenching:** \(I_0/I = 1 + K_{SV}[Q] = 1 + k_q\,\tau_0\,[Q]\).

---

## 3. Signal formation models

### 3.1 Beer–Lambert law (UV–Vis, mid‑IR in transmission)
\[
A(\lambda) = \log_{10}\!\frac{I_0}{I} = \varepsilon(\lambda)\,c\,\ell
\]
- Mixtures: \(A=\sum_j \varepsilon_j c_j \ell\) when non‑interacting.
- Stray light and baseline errors bias linearity; record checks and LOD/LOQ method (Ch. 2).

### 3.2 Raman intensity scaling
- Stokes intensity scales \(\propto (\nu_0 - \nu_v)^4 |\partial\alpha/\partial Q|^2\); fluorescence background must be modeled or masked.

### 3.3 Reflectance and Kubelka–Munk (diffuse)
\[
F(R_\infty) = \frac{(1 - R_\infty)^2}{2R_\infty}
\]
Maps reflectance to an absorption‑like quantity for powders/films (used with care; see Ch. 15).

### 3.4 Tauc plots (optical bandgaps)
For absorption coefficient \(\alpha\):
\[
(\alpha h\nu)^{1/m} = C(h\nu - E_g)
\]
with \(m=1/2\) direct allowed, \(m=2\) indirect allowed. Fit linear region; report window and assumptions.

---

## 4. Line shapes and broadening

### 4.1 Gaussian (Doppler) width
\[
\Delta \nu_D = \nu_0 \sqrt{\frac{8 k_B T \ln2}{m c^2}}
\]
### 4.2 Lorentzian (collisional) HWHM \(\gamma\)
- \(\gamma \propto P\) for pressure broadening; include species‑specific coefficients when available.
### 4.3 Voigt profile
- Convolution of Gaussian and Lorentzian. **Approximate FWHM:**
\[
w_V \approx 0.5346\,(2\gamma) + \sqrt{0.2166\,(2\gamma)^2 + w_G^2}
\]
- Convolve **templates** to the instrument LSF before matching; do not deconvolve noisy data blindly.

**Instrument LSF:** rectangular slits → sinc‑like ILS; gratings and interferometers differ. Store kernel and target FWHM (Ch. 6).

---

## 5. Instrument response, sampling, and resolution

- **Instrument response** (RSRF) converts counts to physical units (radiance/irradiance); derive from standards and store as a function of \(\lambda\).
- **Sampling/Nyquist:** ensure ≥2 points per FWHM. Report actual spectral bandwidth and sampling step.
- **Wavelength/shift solution:** map pixel/OPD to axis using lamps/polystyrene/Si; store RMS and withheld‑line checks (Ch. 6).

---

## 6. Noise, SNR, and artifacts

- **Noise sources:** photon (\(\sigma\sim\sqrt{N}\)), readout, dark, baseline drift, scattering, etalon fringes, cosmic rays (astro).
- **SNR estimates:** from line‑free windows; report method and window.
- **Common artifacts and mitigations**
  - **UV–Vis:** stray light → nonlinearity at high absorbance; check with cutoff filters.
  - **Raman:** fluorescence background; use longer \(\lambda_0\), time gating, or baseline models logged in provenance.
  - **FTIR:** water/CO₂ bands; purge and mask; apodization choices affect line shape.
  - **Astro:** telluric absorption; mask or correct using standards/models.

---

## 7. Polarization and orientation

- **Raman depolarization ratio** probes symmetry; polarized measurements help assign modes.
- **ATR contact/orientation** alters effective path length; ensure repeatable pressure and contact checks (Ch. 10).

---

## 8. Calibration references (campus‑friendly)

- **IR:** polystyrene film band positions; gas cells for CO₂/CO/H₂O.
- **Raman:** crystalline Si at 520.7 cm⁻¹ (temperature dependent at \(~0.022\,\text{cm}^{-1}/\text{K}\) scale).
- **UV–Vis:** holmium oxide glass/solution for band positions.
- **Atomic:** Hg/Ne/Xe/He lamps for wavelength calibration.
- **Astro:** CALSPEC standard stars for sensitivity; atmospheric emission lines for wavelength checks.

Store reference spectra and acceptance tolerances in `cal/` with validity windows (Ch. 6).

---

## 9. Equations cheat‑sheet (with safe defaults)

- **Conversions**: \(\text{FWHM}_G = 2\sqrt{2\ln2}\,\sigma\); \(\Delta v = c\,\Delta\lambda/\lambda\) for small Doppler shifts.
- **Barycentric correction:** apply to **templates**; compute using site/time and ephemeris source (Ch. 6).
- **Raman shift from wavelengths:**
  \[\Delta\tilde{\nu}\,[\text{cm}^{-1}] = 10^7\left(\frac{1}{\lambda_0\,[\text{nm}]} - \frac{1}{\lambda_s\,[\text{nm}]}\right)\]
- **Quenching:** \(I_0/I = 1 + K_{SV}[Q]\); dynamic vs static discrimination via lifetime.

---

## 10. Worked mini‑examples

### 10.1 Assigning carbonate groups (IR + Raman)
- IR: strong bands near 1415 and 871 cm⁻¹; Raman: symmetric stretch near 1085 cm⁻¹. Cross‑confirm per Ch. 3.

### 10.2 Bandgap from UV–Vis
- Build \((\alpha h\nu)^{1/2}\) plot; select linear region; extrapolate to \(E_g\). Report window and \(m\) choice per §3.4.

### 10.3 Gas‑phase temperature from line shapes
- Fit Voigt profiles; extract Gaussian width → infer \(T\) via Doppler formula (§4.1). Compare to pressure‑broadening expectations.

### 10.4 Stellar radial velocity
- Continuum‑normalize; cross‑correlate with template convolved to instrument LSF; locate CCF peak to get \(v_r\) (Ch. 15 astro example).

---

## 11. Data and metadata fields (must record)

- **Axis units** and **medium**; **instrument ID**; **RSRF** and **LSF** references; **environment** (\(T,P\)); **calibration artifacts**; **baseline model**; **masks**; **uncertainty method**.
- Store in `sessions/[SESSION_ID]/manifest.json` and per‑spectrum sidecars (Ch. 12), versioned and hashed (Ch. 8).

---

## 12. Cross‑links

- Ch. 1–2 (modalities and clean acquisition), Ch. 3 (fusion logic), Ch. 5 (units/axes and conversions), Ch. 6 (calibration & LSF), Ch. 7 (identification), Ch. 10 (workflows), Ch. 12 (formats), Ch. 15 (comparisons).

---

## 13. Reference anchors (full citations in Ch. 32)
- Skoog, Holler, and Crouch, *Principles of Instrumental Analysis*.
- Hollas, *Modern Spectroscopy*.
- Lakowicz, *Principles of Fluorescence Spectroscopy*.
- Demtröder, *Laser Spectroscopy*.
- Gray & Corbally, *Stellar Spectral Classification*.
- HITRAN, ExoMol, JPL/CDMS, NIST ASD, RRUFF, CALSPEC/MAST documentation.
- Ciddor/Edlén air–vacuum conversions; Voigt profile approximations (Humlíček/Whiting‑like formulas).

> Equations here are the canonical forms used by the app. If you change any math in code, update this chapter and the Docs module (Ch. 13) in the same commit.

