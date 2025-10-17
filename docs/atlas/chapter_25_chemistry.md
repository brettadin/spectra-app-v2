# Chapter 25 — Chemistry

> **Purpose.** Provide the chemistry context that gives spectral features meaning: structure–property relationships, functional‑group signatures, speciation, equilibria, solid‑state motifs, solvation effects, and redox/coordination chemistry. This chapter connects chemical reasoning to the acquisition, calibration, and identification machinery defined in earlier chapters.
>
> **Scope.** Molecular and materials chemistry at campus scale: organics, inorganics, polymers, minerals, gases, solutions, and thin films. Emphasis on conditions that control spectra and on priors/constraints used by the identification engine (Ch. 7, 11, 15).
>
> **Path notice.** All file/folder names are **placeholders** resolved by the app’s path resolver at runtime. Do **not** hardcode. Tokens like `[SESSION_ID]`, `[DATASET_ID]`, `[MODALITY]`, `[YYYYMMDD]` are variables.

---

## 0. Chemical foundations that affect spectra

1. **Bonding and order.** Stretching frequencies scale with \(\omega \propto \sqrt{k/\mu}\) (force constant/effective mass). Greater bond order → higher \(k\) → higher \(\tilde{\nu}\) in IR/Raman.
2. **Substitution and conjugation.** Electron‑withdrawing groups and conjugation shift C=O, C=C, N=O bands; in UV–Vis, conjugation lowers \(E_g\) and red‑shifts \(\lambda_{\max}\).
3. **Symmetry.** Centrosymmetric molecules follow mutual exclusion (IR vs Raman active). Depolarization ratios and selection rules assist assignments (Ch. 23).
4. **Phase and crystallinity.** Polymorphs change lattice modes (Raman low‑frequency) and IR band splitting; amorphous vs crystalline gives broad vs sharp bands.
5. **Environment.** Solvent, pH, ionic strength, temperature, pressure, and hydrogen bonding alter positions, widths, and intensities; record in manifests.

---

## 1. Functional‑group anchors (indicative ranges)

> Ranges are **indicative**; use libraries (RRUFF, NIST, HITRAN) for exact values and uncertainties. Always report unit view and target FWHM (Ch. 5–6).

| Group/mode | IR (cm⁻¹) | Raman (cm⁻¹) | Notes |
|---|---:|---:|---|
| O–H stretch (H‑bonded) | 3200–3600 (broad) | weak | Broadens/reds‑shifts with stronger H‑bonding |
| N–H stretch | 3300–3500 | weak–mod | Amide A/B near 3300/3100 |
| C–H sp² | 3000–3100 | 3000–3100 | Aromatic C–H |
| C–H sp³ | 2850–2960 | 2850–2960 | Methyl/methylene |
| C=O (ketone/acid/amide) | 1630–1810 | weak | Conjugation and H‑bonding shift; amides split (I–III) |
| C≡N | 2210–2260 | weak | Strong IR, useful tag |
| C=C aromatic ring modes | 1500–1650 | 1580 (G), 1350 (D) | Graphitic signatures; I(D)/I(G) ratio |
| CO₃²⁻ (carbonate) | 1400–1500, 870–880 | 1085 (symmetric) | Polymorphs split lattice/low‑freq modes |
| SO₄²⁻ (sulfate) | 1100–1200 | 980–1010 | Tetrahedral symmetry patterns |
| Si–O (silicates) | 800–1200 | 400–1200 | Network polymerization reflected in band positions |

> Record assignments in `features.annotations[]` with source citations (Ch. 3 schema) and add confidence notes.

---

## 2. Speciation and equilibria (solutions and gases)

### 2.1 Acid/base: Henderson–Hasselbalch
\[
\mathrm{pH} = \mathrm{p}K_a + \log_{10}\frac{[\mathrm{A}^-]}{[\mathrm{HA}]}
\]
- Speciation controls IR/Raman bands (e.g., carboxylic acid vs carboxylate) and UV–Vis \(\lambda_{\max}\).
- Log pH, buffer, ionic strength; avoid CO₂ absorption in open systems.

### 2.2 Complexation and coordination
- Stepwise formation: \(\beta_n = \prod_i K_i\). Ligand field alters UV–Vis (d–d, LMCT) and Raman/IR (metal–ligand stretches).
- Record oxidation state, ligand set, geometry; note spin transitions with temperature.

### 2.3 Gas‑phase equilibria
- Partial pressures and temperature determine line strengths (Boltzmann) and broadening (Voigt). Reference cross‑sections from HITRAN/ExoMol with version pinning (Ch. 4).

### 2.4 Redox (Nernst)
\[
E = E^\circ - \frac{RT}{nF}\ln\frac{a_{\text{red}}}{a_{\text{ox}}}
\]
- Oxidation state changes shift UV–Vis; track dissolved O₂ and redox mediators when relevant.

---

## 3. Solid‑state chemistry and minerals

1. **Polymorphs and phase assemblages.** Unit cell and site symmetry produce distinct Raman lattice modes and IR band splitting; use XRD as validator when available.
2. **Substitutional chemistry.** Cation substitution shifts framework modes (e.g., Mg→Fe in carbonates/silicates). Keep stoichiometry priors consistent with atomic lines.
3. **Defects and disorder.** Broadening and band position shifts reflect strain; D‑band in carbon, Si phonon softening with defects.
4. **Hydration and hydroxylation.** OH bands characterize clays and hydrates; temperature/humidity control needed during acquisition.

---

## 4. Polymers and thin films

- **Backbone signatures.** PE, PP, PS, PMMA, PET have well‑known IR/Raman fingerprints; crystallinity changes band widths and intensities.
- **Conjugated polymers.** UV–Vis band edges shift with doping and chain length; Raman shows polaron/bipolaron modes under resonance.
- **Thin‑film optics.** Interference fringes in UV–Vis encode thickness; combine with Tauc for \(E_g\); log substrate and angle.

---

## 5. Sample preparation and contamination controls

1. **IR (ATR vs transmission).** ATR penetration depth depends on crystal and angle (Ch. 24 §4.3). Press uniformly; record crystal, angle, and pressure/turns.
2. **Raman.** Choose \(\lambda_0\) to avoid fluorescence; watch laser power and exposure; use standards (Si 520.7 cm⁻¹) pre/post.
3. **UV–Vis.** Match cuvette path length; blank properly; avoid stray light; check holmium lines.
4. **Gases.** Use sealed gas cell; log T, P; purge water/CO₂ for mid‑IR.
5. **Minerals/powders.** Grind consistently; avoid polymorph transformations from grinding/pressure; consider ATR pressure effects.
6. **Contamination sources.** Fingerprints (C–H), plasticizers (phthalates), solvents; record gloves/solvent and container types in manifests.

---

## 6. Chemical priors for identification (how chemistry constrains hypotheses)

- **Elemental balance.** Atomic lines set a hard gate on elements present/absent; molecular candidates must obey plausible stoichiometries.
- **Charge/phase consistency.** If solution pH > pK_a by 2 units, use deprotonated forms as higher‑prior candidates.
- **Environment.** Solvent polarity and ionic strength adjust expected shifts; priors include expected direction/magnitude.
- **Mixture parsimony.** Prefer minimal set of components explaining all strong features (penalize kitchen‑sink fits; Ch. 11).

**JSON prior stub** `priors/[DATASET_ID]/chemistry.json`:
```json
{
  "elements_present": ["Na", "K", "C", "O"],
  "pH": 8.4,
  "ionic_strength": 0.10,
  "phase": "solid|solution|gas",
  "expected_anions": ["CO3"],
  "exclusions": ["NO3"],
  "confidence": 0.8,
  "sources": ["NIST_ASD@2024", "RRUFF@v1", "lab-notes:[SESSION_ID]"]
}
```

---

## 7. Quantitation touchpoints

- **Beer–Lambert** for solutions; report \(\varepsilon(\lambda)\), path length, and linearity checks.
- **Cross‑sections** for gas absorption; integrate over line shape with HITRAN parameters.
- **Internal standards** for Raman (relative intensities) and IR (band area ratios); document uncertainty models.

---

## 8. Common chemistries and spectral cues (mini‑atlas)

- **Carbonates:** IR 1400–1500 and 870–880 cm⁻¹; Raman 1085 cm⁻¹; low‑freq lattice modes differentiate calcite/aragonite/vaterite.
- **Sulfates:** IR asymmetric S–O ~1100–1200 cm⁻¹; Raman symmetric near 980–1010 cm⁻¹; hydration water O–H bands.
- **Nitriles:** sharp IR 2210–2260 cm⁻¹; weak Raman.
- **Aromatics:** Raman G 1580 cm⁻¹, D 1350 cm⁻¹; UV–Vis \(\pi\to\pi^*\) bands; fluorescence depending on substituents.
- **Silicates:** broad IR 800–1200 cm⁻¹; Raman modes reflect Qⁿ network species; metal substitution shifts bands.

Each atlas entry in the app links to **checked library exemplars** with versioned citations.

---

## 9. Reporting discipline

- Cite assignments with source and confidence; avoid bare “fingerprint matches.”
- Always include environment (solvent, pH, T, P), instrument LSF, and calibration checks.
- Document any baseline models and masks that affect band areas/positions.

---

## 10. Worked mini‑examples

### 10.1 Carbonate vs bicarbonate in solution
- Adjust pH across pKₐ₂ of carbonic acid; track IR shift from 1700‑ish C=O (\(\mathrm{HCO}_3^-\) shoulder) to dominant 1415 cm⁻¹ carbonate. Record pH, buffer, and ionic strength.

### 10.2 Fe(II)/Fe(III) complex
- UV–Vis shows LMCT band change; Raman M–L stretch shifts with oxidation state. Use Nernst prior at measured pH and potentials.

### 10.3 Polymer identification
- Compare ATR‑IR of unknown film to library exemplars (PE/PP/PS/PET/PMMA). Use Raman to resolve ambiguous IR patterns (aromatic vs aliphatic).

---

## 11. Cross‑links

- Ch. 2 (clean acquisition), Ch. 3 (cross‑modal fusion schema), Ch. 4 (source registry), Ch. 5 (units/axes), Ch. 6 (calibration/LSF), Ch. 7 (identification logic), Ch. 8 (provenance), Ch. 11 (rubrics), Ch. 15 (consolidation), Ch. 23–24 (Spectroscopy & Physics), Ch. 27–28 (Astrochemistry & Physical chemistry).

---

## 12. Reference anchors (full citations in Ch. 32)

- Pavia et al., *Introduction to Spectroscopy* (functional groups and assignments).
- Silverstein & Webster, *Spectrometric Identification of Organic Compounds*.
- Cotton, *Advanced Inorganic Chemistry*; Lever, *Inorganic Electronic Spectroscopy* (ligand‑field).
- RRUFF (minerals), NIST Chemistry WebBook (organics), HITRAN/ExoMol (gases).
- IUPAC Gold Book for definitions; ACS style guide for citations.

> Chemistry provides the priors and constraints; physics and instrumentation provide the evidence. Keep both honest and your identifications will age well.

