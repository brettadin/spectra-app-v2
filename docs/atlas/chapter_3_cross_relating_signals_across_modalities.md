# Chapter 3 — Cross‑Relating Signals Across Modalities

> **Purpose.** Define how to combine information from different spectroscopy modalities (atomic emission/absorption, FTIR/ATR, Raman, UV–Vis, fluorescence, and optional non‑optical validators) into coherent hypotheses about composition and environment. Provide data structures, scoring, and workflows so multiple agents and semesters produce comparable, auditable results.
>
> **Scope.** Campus‑available instruments and credible external datasets (e.g., NIST ASD, HITRAN, RRUFF, CALSPEC/MAST). Astrophysical data are included at the level of instrument response, radial velocity, and template matching.
>
> **Path notice.** File and folder names are **placeholders**. All paths must be resolved by the application’s path resolver at runtime. Tokens like `[SESSION_ID]`, `[DATASET_ID]`, `[MODALITY]`, `[YYYYMMDD]` are variables.

---

## 1. Fusion philosophy and invariants

1. **Keep each spectrum native.** Maintain canonical axes per modality (see Chapter 1). Harmonize only for comparison (temporary views), never by overwriting source data.
2. **Preserve resolution honestly.** Store and use each instrument’s LSF/FWHM. Convolve higher resolution down to the lower one before cross‑correlation.
3. **Provenance everywhere.** Every transform used for fusion (continuum normalization, baseline, convolution, Doppler/radial‑velocity correction) is logged in `transforms_applied` with parameters.
4. **Explainable scoring.** Identification outputs must enumerate which features from which modalities contributed what weight, with uncertainties.

---

## 2. Canonical feature schema

All modalities reduce to **features** (lines/bands/edges) + **context** (continuum, instrument, environment). Store features in a shared schema so downstream logic is modality‑agnostic.

```json
{
  "feature_id": "[AUTO_UUID]",
  "modality": "ftir|raman|uvvis|atomic|fluorescence",
  "axis": {
    "unit": "cm^-1|nm|eV",
    "canonical": true,
    "center": 1580.3,
    "center_unc": 0.8,
    "fwhm": 18.5,
    "fwhm_unc": 2.0
  },
  "intensity": {
    "value": 1.00,
    "unit": "relative|absorbance|counts|a.u.",
    "unc": 0.05
  },
  "shape": "gaussian|lorentzian|voigt|unknown",
  "annotations": ["C=C stretch", "G-band"],
  "evidence": {
    "peak_picker": {"algo": "local-maxima", "params": {"prominence": 0.01}},
    "fit": {"algo": "voigt-fit", "r2": 0.992}
  },
  "links": {
    "spectrum_ref": "sessions/[SESSION_ID]/[MODALITY]/processed/[FILENAME]",
    "library_refs": ["RRUFF:ID", "HITRAN:species:line_id", "NIST_ASD:transition_id"]
  }
}
```

**Continuum/context** objects capture baseline models, normalization constants, radial‑velocity shifts, and applied convolutions with full parameters.

---

## 3. Cross‑modal mapping: what constrains what

| Source modality | What it constrains | How it gates other searches |
|---|---|---|
| **Atomic (emission/absorption)** | Elemental presence; ionization states; plasma conditions from line ratios and broadening | Reduces molecular candidate space to those consistent with detected elements and plausible stoichiometries |
| **FTIR/ATR (IR)** | Functional groups, bond orders; gas‑phase rotational envelopes → temperature | Filters Raman/UV–Vis expectations; narrows isomers by diagnostic bands |
| **Raman** | Symmetry‑sensitive modes, carbon ordering, lattice/strain | Complements IR; rules in/out centrosymmetric motifs and polymorphs |
| **UV–Vis** | Electronic transitions; bandgaps; ligand‑field and conjugation signatures | Discriminates oxidation states, conjugation length, semiconductor phases |
| **Fluorescence** | Microenvironment; trace aromatic species; lifetimes | Confirms UV–Vis assignments; indicates quenching media and impurities |
| **Non‑optical (MS/XRD/NMR)** | Molecular mass, crystal phase, local bonding | Acts as validator or prior in Bayesian scoring |

---

## 4. Environmental and instrumental parameters

To reconcile modalities, estimate and propagate shared parameters:

- **Temperature \(T\)** from IR rotational envelopes or atomic line ratios; enters partition functions and expected band intensities.
- **Pressure/path length** for gas‑phase IR; influences line shapes (Lorentz vs Doppler vs Voigt) and HITRAN cross‑section use.
- **Matrix/solvent** for UV–Vis/fluorescence; shifts and broadening recorded as environment metadata.
- **Radial velocity** \(v_r\) for astrophysical spectra; barycentric correction stored; shifts applied to templates, not to raw data.
- **Instrument response** (throughput vs wavelength) and **LSF** per dataset; used to convolve library templates for apples‑to‑apples matching.

---

## 5. Harmonization workflow (without destroying data)

1. **Axis alignment.** Convert comparison views to common units (e.g., IR cm⁻¹, Raman shifts already in cm⁻¹, UV–Vis nm). Never resample destructively; use interpolated views.
2. **Resolution match.** Convolve higher‑resolution spectrum with target LSF to match the lower‑resolution partner. Store `convolution:{kernel, fwhm, method}` in the view metadata.
3. **Continuum normalization.** For UV–Vis/astro continua, fit low‑order polynomials or splines outside features; store model coefficients and window masks.
4. **Velocity/offset.** Apply barycentric and radial‑velocity corrections to **templates**; log applied shifts.
5. **Intensity scale.** If absolute calibration exists (irradiance, cross‑sections), use it; else, scale to unit area/height per defined rule, with flags.

---

## 6. Matching and scoring

### 6.1 Deterministic peak‑set matching

For a candidate species/template \(M\), expected feature centers \(\mu_i\) are compared to observed features \(x_j\). Use a tolerance that scales with local resolution \(\sigma_{\text{inst}}\).

- **Position likelihood per feature** (Gaussian model):
\[
\mathcal{L}_i = \exp\Big(-\tfrac{1}{2}\big(\tfrac{x_j - \mu_i}{\sigma_i}\big)^2\Big), \quad \sigma_i^2 = \sigma_{\text{inst}}^2 + \sigma_{\text{lib}}^2
\]

- **Composite match score** for modality \(k\):
\[
S_k(M) = \sum_{i\in k} w_i \log \mathcal{L}_i - \alpha\,\mathrm{FP}_k - \beta\,\mathrm{FN}_k
\]
where FP and FN penalize extra/missing bands, and \(w_i\) weights by diagnostic power.

### 6.2 Template cross‑correlation

For dense bands (e.g., astro molecular templates, vibrational manifolds):
\[
C(M) = \max_{\Delta,\gamma}\; \frac{\langle T_M(\Delta,\gamma) * R,\; D\rangle}{\|T_M(\Delta,\gamma)\|\,\|D\|}
\]
with template \(T_M\) convolved to instrument LSF and shifted/broadened by \((\Delta,\gamma)\); data \(D\) is continuum‑normalized.

### 6.3 Bayesian fusion across modalities

Treat modality scores as likelihood terms; include priors from elemental constraints:
\[
\log P(M\mid \mathbf{D}) = \log P(M) + \sum_k \lambda_k\, S_k(M) - \mathrm{penalties}
\]
- \(P(M)\) encodes priors (e.g., elemental presence, stoichiometry, environment).
- \(\lambda_k\) weights per modality; tuned using validation sets.

### 6.4 Confidence and alternatives

Report **top‑N hypotheses** with \(\Delta\)AIC/BIC‑like separations and per‑modality contributions. Always provide **nearest alternatives** and what new data would resolve ambiguity (e.g., a specific Raman line or UV–Vis band edge).

---

## 7. Evidence graph data model

Represent inferences as a graph to keep decisions auditable.

```json
{
  "graph_id": "[AUTO_UUID]",
  "nodes": [
    {"id": "feat:raman:1580", "type": "feature", "label": "Raman 1580 cm^-1", "source": "raman"},
    {"id": "feat:ftir:1060", "type": "feature", "label": "IR 1060 cm^-1", "source": "ftir"},
    {"id": "hyp:carbonate", "type": "hypothesis", "label": "Carbonate present"},
    {"id": "env:T", "type": "parameter", "label": "T=298 K ± 3"}
  ],
  "edges": [
    {"from": "feat:ftir:1060", "to": "hyp:carbonate", "relation": "supports", "weight": 0.7},
    {"from": "feat:raman:1580", "to": "hyp:carbonate", "relation": "supports", "weight": 0.4},
    {"from": "env:T", "to": "hyp:carbonate", "relation": "conditions", "weight": 0.2}
  ],
  "justification": {
    "libraries": ["HITRAN", "RRUFF"],
    "transforms": ["continuum_poly_deg2", "lsf_convolution_fwhm=6.0"]
  }
}
```

The UI should allow clicking a hypothesis to reveal its supporting features, templates, and parameter assumptions.

---

## 8. Worked mini‑examples (illustrative)

### 8.1 Gas‑phase CO₂ vs CO in FTIR + Raman
- **FTIR:** bands near 2350 cm⁻¹ (CO₂ asymmetric stretch) with pressure‑dependent line shape; weak or absent 2143 cm⁻¹ (CO) region.
- **Raman:** 1388 cm⁻¹ (CO₂ symmetric stretch) strong in Raman but IR‑inactive; CO Raman weak.
- **Fusion:** IR detects 2350 cm⁻¹, Raman confirms 1388 cm⁻¹; Bayesian prior gates out CO‑only hypothesis.

### 8.2 Alkali carbonate mineral
- **Atomic emission:** Na, K lines present.
- **IR:** strong 1400–1500 cm⁻¹ carbonate bands; **Raman** lattice modes differentiate polymorphs.
- **UV–Vis:** largely featureless; supports inorganic salt conclusion.

### 8.3 Carbon material (graphitic vs amorphous)
- **Raman:** D ~1350 cm⁻¹, G ~1580 cm⁻¹, 2D ~2700 cm⁻¹ ratios inform ordering.
- **IR:** weak; **UV–Vis:** featureless tail. Cross‑modal consensus favors sp²‑rich graphite‑like phase.

### 8.4 Astrophysical H and He with molecular overlays
- **Atomic:** Balmer series positions set velocity reference; **UV–Vis/continuum** normalized.
- **Molecular templates (e.g., CH, CN) convolved** to instrument LSF and shifted by radial velocity; cross‑correlation returns best \(v_r\) and presence scores. Priors enforce stellar type consistency.

---

## 9. Conflict resolution and uncertainty

- **Disagreement across modalities** triggers a **conflict report** listing mismatched features, suspected causes (resolution, baseline, fluorescence, matrix effects), and recommended next measurements.
- **Uncertainty propagation**: per‑feature \(\sigma\) feeds into match tolerances; report composite confidence intervals on scores.
- **Missing‑data robustness**: if a modality is absent, renormalize weights and explicitly mark assumptions.

---

## 10. Output objects

### 10.1 Hypothesis object
```json
{
  "hypothesis_id": "hyp:carbonate_sodium",
  "label": "Sodium carbonate present",
  "priors": {"elements": ["Na", "C", "O"], "env": {"phase": "solid"}},
  "scores": {
    "ftir": 18.2,
    "raman": 11.5,
    "uvvis": 0.3,
    "atomic": 6.8,
    "total_log_posterior": 31.4
  },
  "alternatives": ["hyp:bicarbonate", "hyp:sulfate"],
  "required_followups": ["raman_low_freq_100-300_cm-1", "ftir_2_cm-1_resolution"],
  "evidence_graph_ref": "graphs/[SESSION_ID]/[DATASET_ID]/carbonate_graph.json"
}
```

### 10.2 Report block (auto‑generated)
- Summary paragraph
- Table of supporting features with uncertainties
- Plots: per‑modality overlays at matched resolution
- Provenance: library versions, instrument settings, transforms

---

## 11. Validation strategy

1. **Internal controls:** known standards per modality (Si, polystyrene, Hg/Ne/Xe, quinine sulfate).
2. **Cross‑lab reproducibility:** repeat acquisition in another session/instrument; compare scores and selected features.
3. **Blind samples:** hide composition; measure fusion accuracy and calibration drift in weights \(\lambda_k\).
4. **Astro sanity checks:** verify radial velocity and line identifications against CALSPEC/standard stars.

---

## 12. Reference anchors (general)
- NIST Atomic Spectra Database (ASD) — authoritative atomic lines/levels.
- HITRAN — high‑resolution molecular absorption data for gases.
- RRUFF — integrated Raman/XRD/chemistry for minerals.
- CALSPEC/MAST — spectrophotometric standard stars and space‑based spectra.
- Core texts: Skoog/Holler/Crouch; Hollas; Lakowicz; Gray & Corbally for stellar classification.

> **Cross‑links.** See Chapter 5 for unit/axis rules, Chapter 6 for calibration/LSF math, Chapter 7 for the full identification engine, Chapter 8 for provenance fields, and Chapter 11 for scoring thresholds and confidence tiers.

