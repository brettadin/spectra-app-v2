# Chapter 9 — App Features This Workflow Expects

> **Purpose.** Specify the product features the Spectra App must implement so the scientific workflow defined in Chapters 1–8 is practical, consistent, and teachable. Features cover acquisition ingest, calibration management, multi‑modal visualization, identification, reporting, provenance, and pedagogy.
>
> **Scope.** Campus instruments (atomic/UV–Vis, FTIR/ATR, Raman, fluorescence), external datasets (Chapter 4), and astrophysical spectra. Includes UI/UX principles, APIs, storage, performance, and testing.
>
> **Path notice.** All filenames and directories are **placeholders**. The app must resolve tokens like `[SESSION_ID]`, `[DATASET_ID]`, `[MODALITY]`, `[INSTRUMENT_ID]`, `[YYYYMMDD]` at runtime. Do **not** hardcode paths.

---

## 1. Product principles (non‑negotiable)
1. **Deterministic science.** Same inputs → same outputs. Randomized steps pin and record a seed.
2. **Raw is sacred.** Raw data are immutable (Chapter 6). All processing occurs in derived views with full provenance (Chapter 8).
3. **Unit‑safe by design.** Canonical axes per modality (Chapter 5). No chained conversions.
4. **Resolution‑aware.** Always respect and display instrument LSF/FWHM; harmonize to common resolution for overlays.
5. **Explainable decisions.** Every identification shows per‑feature contributions and uncertainties (Chapter 7).
6. **Education mode.** Every advanced action can display a short “why this matters” card with links to the docs and sources.

---

## 2. Feature map (modules)

### 2.1 Ingest Manager
- **What it does:** Validates and imports session bundles from instruments and archives (Chapter 2, 4).
- **Key functions:**
  - Vendor parser routing (file sniffing), unit detection, medium flag (air/vacuum) enforcement.
  - Manifest validator (Chapter 8 schema); refuses ingest on missing units/medium.
  - Hash calculation (SHA‑256) and quarantine for mismatches.
  - Optional de‑identification of operator names per policy.
- **Outputs:** Standardized bundle under `sessions/[SESSION_ID]/...` plus validation report.

### 2.2 Calibration Manager
- **What it does:** Tracks and applies calibration artifacts and their validity windows (Chapter 6).
- **Key functions:** artifact registry, lamp/Si/polystyrene dashboards, response functions, extinction curves, velocity frames.
- **UI:** plots of wavelength RMS over time, FWHM vs λ, response stability; amber warnings when artifacts are used outside validity.

### 2.3 Spectral Viewer (multi‑pane)
- **What it does:** Visualizes spectra from multiple modalities concurrently.
- **Key functions:**
  - Per‑pane unit toggles (λ nm, \(\tilde{\nu}\) cm⁻¹, eV, THz), synchronized cursor read‑outs.
  - Resolution harmonizer: convolve higher‑res views down to target FWHM with banner noting the target.
  - Overlay manager with masks for tellurics/solvent bands.
  - Feature annotations with uncertainties, hover to reveal fit residuals and provenance.

### 2.4 Feature Extraction & Fitting
- **What it does:** Peak picking, baseline modeling, fits (Gaussian/Lorentzian/Voigt/sinc‑apodized), band area integration.
- **Key functions:** auto and manual masks; reproducible parameter storage; batch processing; SNR/FWHM metrics (Chapter 2 §7).

### 2.5 Fusion & Identification
- **What it does:** Implements Chapter 7 scoring and Bayesian fusion across modalities.
- **Key functions:** priors panel (elements, environment, trust tiers), modality weights, top‑N hypotheses with confidence tiers and alternatives.
- **UI:** “Evidence graph” panel linking features to hypotheses and priors, click‑through to libraries.

### 2.6 External Source Registry & Cache
- **What it does:** Exposes adapters to authoritative sources (Chapter 4) with version pinning and licensing notes.
- **Key functions:** source browser, download with etag/checksum, version selection, side‑by‑side library versions.

### 2.7 Report Builder
- **What it does:** Generates human‑readable and machine‑readable exports (Chapter 8 §9–10).
- **Key functions:**
  - Auto‑populate top‑N identifications, overlays, metrics, transform ledger, and bibliography.
  - Export zip: CSV/TXT + HDF5/Parquet bundle + `manifest.json` + `CHECKSUMS.txt` + PDF.

### 2.8 Teaching Mode (Curriculum tools)
- **What it does:** Embeds guided labs and quizzes; toggles “explain math” for Beer–Lambert, Raman shift, Doppler, etc.
- **Key functions:** sandbox datasets, step‑through calibration demos, auto‑graded checkpoints, badge for “clean run” completion.

---

## 3. APIs and extensibility

### 3.1 Adapter interface (new file formats/sources)
```python
class Adapter(Protocol):
    def sniff(self, path: str) -> bool: ...
    def load(self, path: str, *, options: dict | None = None) -> DatasetBundle: ...
```
- **Contract:** return canonical axis, units, uncertainties, and a provenance block with `source_id@version`.
- **Registration:** entry‑points or plugin registry file `adapters/plugins.json` (placeholder path).

### 3.2 Identification hook
```python
def identify(sample_bundle, context, *, priors=None, config=None) -> list[Hypothesis]:
    """Implements Chapter 7; deterministic given fixed inputs."""
```
- **Outputs:** ranked hypotheses with evidence graphs and explanations.

### 3.3 Model cards and ML plug‑ins
- **Model card JSON:** `{name, version, hash, training_set_id, metrics, license, citation}`.
- **Predict API:** `predict(features: ndarray, meta: dict) -> dict` with deterministic seed and calibration curve for probabilities.

### 3.4 Scripting boundaries
- Sandboxed execution environment with no network access; read‑only access to session bundles; write via approved API that logs transforms.

---

## 4. UI/UX guidelines
1. **Unit badges everywhere.** Axis labels show units; tooltips show synchronized nm/cm⁻¹/eV values (Chapter 5).
2. **LSF banner.** If an overlay uses convolved views, display the target FWHM prominently.
3. **Visible provenance.** A status bar icon opens the transform ledger; clicking any step highlights the view where it applies.
4. **Honest defaults.** Smoothing off by default; baseline models visible and editable; raw view one click away.
5. **Accessibility.** Keyboard navigation for all controls; colorblind‑safe palettes; readable fonts; focus outlines.
6. **Guardrails.** Uploads without units/medium are blocked with a precise error and a link to Chapter 5.

---

## 5. Data storage and formats
- **Internal bundles:** HDF5 or Parquet with groups for `raw`, `processed`, `meta`, `provenance`, `lsf`, `masks` (see Chapter 4 §9, Chapter 8 §9).
- **Sidecars:** `manifest.json` per session; JSON sidecars for vendor‑opaque files.
- **Graphs:** evidence and lineage graphs as JSON with node/edge lists (Chapters 3 and 8).
- **Caches:** `cache/sources/[PROVIDER]/[VERSION]/[DATASET_ID]/...` with checksums.

---

## 6. Performance and robustness
- **Rendering:** virtualized plotting for large arrays; downsampling on the fly with quality flags.
- **Computation:** vectorized operations; FFT‑based convolutions; cache transformed views keyed by content hash.
- **Faults:** failure‑tolerant ingest (retry/backoff), offline mode using cached libraries, red banners for stale caches.

---

## 7. Security and privacy
- **Roles:** student/TA/PI; role gates access to editing methods and deleting sessions.
- **PII:** store operator initials only (policy‑dependent). No grades/IDs in manifests.
- **Licensing:** registry enforces usage terms per source; blocked actions when redistribution is restricted.

---

## 8. Testing and QA
- **Unit tests:** unit conversions, Raman error propagation, wavelength solution, response function, LSF convolution (Chapters 5–6).
- **Integration tests:** ingest a full session; verify provenance ledger completeness and determinism.
- **Benchmark suite:** top‑k identification accuracy and calibration of probabilities on the gold set (Chapter 7 §10).
- **UI snapshot tests:** ensure unit badges, LSF banners, and provenance icons render in all states.

---

## 9. Onboarding and pedagogy
- **Quick‑start tours:** interactive walkthrough of a clean acquisition and identification.
- **Doc links:** context‑sensitive links from UI panels to the relevant chapter sections.
- **Demo datasets:** ship with curated standards (Si, polystyrene, Hg/Ne/Xe, quinine sulfate, CALSPEC star) with full manifests.

---

## 10. Future upgrades
- Collaborative annotations with versioned comments tied to the evidence graph.
- Spectral‑imaging support (2D/3D cubes) with spectral ROI extraction.
- Active‑learning loop that proposes the next most informative measurement.
- W3C PROV export and DOI minting for campus datasets (see Chapter 8 §15).
- Mobile capture companion for photos of instrument setups linked to sessions.

---

## 11. Cross‑links
- Ch. 1–2: modality background and acquisition SOPs.
- Ch. 3: evidence graph and cross‑modal fusion expectations.
- Ch. 4: source registry and ingestion adapters.
- Ch. 5: units and conversions (unit badges, toggles).
- Ch. 6: calibration artifacts and LSF handling.
- Ch. 7: identification engine and scoring outputs.
- Ch. 8: provenance, manifests, and exports.
- Ch. 11: scoring rubric thresholds displayed in reports.

---

## 12. References (selected standards & docs)
- **JSON Schema** — https://json-schema.org/specification.html
- **HDF5** (The HDF Group) — https://portal.hdfgroup.org/display/HDF5/HDF5
- **Apache Parquet** — https://parquet.apache.org/documentation/latest/
- **W3C PROV** — https://www.w3.org/TR/prov-overview/
- **FITS/WCS** (IAU/IVOA, via NASA/GSFC) — https://fits.gsfc.nasa.gov/ and https://fits.gsfc.nasa.gov/fits_wcs.html
- **Astropy WCS/Spectra** — https://docs.astropy.org/en/stable/wcs/ and https://docs.astropy.org/en/stable/visualization/

> **Note.** Replace access dates and versions in final reports. All links above are anchors; actual use must capture exact version/commit IDs in manifests.

