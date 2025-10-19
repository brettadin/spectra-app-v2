# Chapter 22 — Good UI Design

> **Purpose.** Specify a clear, honest, and accessible UI that makes rigorous spectroscopy workflows easier instead of cuter. The interface must surface units, resolution, provenance, and uncertainty at all times without making users suffer.
>
> **Scope.** Spectral Viewer, Ingest Manager, Calibration Manager, Evidence Graph, Source Registry, Consolidator, Report Builder, and Teaching Mode. Applies to desktop first, with responsive patterns for small laptops.
>
> **Path notice.** Any filenames or directories shown are **placeholders**. The app resolves tokens like `[SESSION_ID]`, `[DATASET_ID]`, `[MODALITY]`, `[YYYYMMDD]` at runtime. Do **not** hardcode paths.

---

## 0. Non‑negotiable design principles
1. **Truth over pretty.** Visuals never lie: unit badges, LSF banners, mask shading, and uncertainty ribbons are visible by default.
2. **Deterministic interactions.** Every user action is reversible and logged (Ch. 8). No silent smoothing, no surprise resampling.
3. **Progressive disclosure.** Simple defaults first; advanced controls are one click away with a clear “why this matters” link (Ch. 13).
4. **Consistent language.** Same term, same behavior, everywhere. “Harmonize to FWHM” means the exact same thing in every panel.
5. **Keyboard‑first.** All critical tasks are accessible via shortcuts and focusable controls; mouse is optional, not mandatory.
6. **Accessible by design.** WCAG 2.2 AA minimum: color‑safe palettes, contrast ≥ 4.5:1, alt‑text, captioned videos (Ch. 21 §8).
7. **Performance‑aware.** Virtualized plots, lazy data fetch, no spinner purgatory. Always show an informative skeleton state.
8. **Context is king.** Tooltips show triple‑unit readouts, FWHM at cursor, and local SNR; status bar shows provenance and rubric version.

---

## 1. Information architecture

### 1.1 Top‑level navigation
- **Acquire/Import** → Ingest Manager
- **Calibrate** → Calibration Manager
- **Visualize** → Spectral Viewer (multi‑pane)
- **Identify** → Evidence Graph + Rubric Tables
- **Datasets** → Consolidator + Scorecards
- **Sources** → Registry & Cache
- **Reports** → Report Builder
- **Teach** → Teaching Mode hub

### 1.2 Panel layout (desktop)
- Left sidebar: dataset/session tree with search and quick filters.
- Primary canvas: plot or table.
- Right inspector: context details (units, LSF, masks, parameters) + actionable controls.
- Bottom status bar: app build, rubric ID, library versions count, current axis mode.

---

## 2. Visual language

### 2.1 Typography
- Sans for UI (11–13 px base, 14–16 px for data tables). Mono for numbers in tables and readouts to prevent jitter.

### 2.2 Color semantics
- **Data palette**: neutral hues; separate **status palette** for warnings/success to avoid confusing color with meaning.
- Masks shaded with 20–30% alpha. Uncertainty ribbons at 40–60% alpha, no neon.

### 2.3 Iconography
- Unit badge icons (nm, cm⁻¹, eV), LSF kernel glyphs (Gaussian, Lorentzian, Voigt), provenance ledger glyph.
- All icons have text labels on hover; no mystery hieroglyphics.

### 2.4 Grids and ticks
- Light grid optional, off by default. Ticks on both axes with sensible density; thousands separators never used (Ch. 12 §12).

---

## 3. Plotting & interaction principles

1. **Synchronized cursors.** Hover anywhere to see nm, cm⁻¹, eV simultaneously with conversions from Ch. 5.
2. **Resolution honesty.** If overlays are convolved, a **LSF banner** displays the target FWHM and kernel (Ch. 6 §5).
3. **Brush to mask.** Drag to create a mask region; inspector shows reason and notes; masks persist in provenance.
4. **Snap‑to‑peak.** Hold a modifier key to snap to nearest detected feature; shows center ± uncertainty and FWHM.
5. **Linked inspector.** Selecting a row in the feature table highlights the exact region, and the Evidence Graph node pulses (Ch. 3).
6. **Pan/zoom:** scroll or keys; double‑tap to zoom to a band; shift+scroll to adjust y‑scale only. Provide reset.
7. **Uncertainty ribbons:** toggle on/off; defaults on for research mode.
8. **Tooltips that matter:** include axis units, intensity unit, uncertainty, mask state, local SNR, and the view stack (baseline, normalization, convolution).

---

## 4. States: empty, loading, error, stale

- **Empty:** explain what belongs here and provide a single primary action.
- **Loading:** skeleton plots with axis units and estimated point count.
- **Error:** human‑readable message with remediation and a “view ledger” link.
- **Stale cache:** amber banner with “refresh libraries” action and last‑checked timestamp.

All states log to provenance when relevant to exports (Ch. 8).

---

## 5. Forms and validation

- Units and medium are **required**; missing → hard stop (Ch. 5).
- Instant feedback with inline math previews (e.g., Raman λ₀ → shift ± σ).
- File pickers display detected format and adapter; unsupported files explain why and link to the Source Registry (Ch. 4).

---

## 6. Accessibility specifics (WCAG 2.2 AA)

- Keyboard map visible via `?` or `Ctrl+/`.
- Focus outlines always visible; skip links to main canvas and tables.
- All charts have data table equivalents and downloadable CSV (Ch. 12 §3).
- Colorblind‑safe presets (deuteranopia/protanopia/tritanopia), switchable at runtime.

---

## 7. Responsive behavior

- Collapsible sidebars; inspector becomes a drawer.
- Critical readouts (unit badges, LSF banner, provenance icon) never hidden; move to status bar if needed.
- Plot simplifies ticks and hides secondary adornments at narrow widths; preserve data fidelity.

---

## 8. Core components (contracts)

### 8.1 UnitBadge
```ts
<UnitBadge axis="nm|cm^-1|eV" medium="air|vacuum" onToggleAxis={...} />
```
- Always present near axes; toggling emits an event that updates synchronized cursors.

### 8.2 LsfBanner
```ts
<LsfBanner kernel="gaussian|lorentzian|voigt" fwhm={number} unit="nm|cm^-1" />
```
- Appears when any overlay is convolved; includes a link to the calibration artifact used.

### 8.3 EvidenceGraphPanel
```ts
<EvidenceGraphPanel graphRef="graphs/[SESSION_ID]/[DATASET_ID]/evidence.json" onSelectNode={...} />
```
- Shows feature→hypothesis edges; weights, priors, and library citations accessible via sidebar.

### 8.4 RubricTable
```ts
<RubricTable scores={...} thresholdsRef="rubrics/[YYYYMMDD]/rubric.json" />
```
- Displays per‑modality scores, quality weights, priors, global score, and tier assignment (Ch. 11).

### 8.5 CalibrationTimeline
```ts
<CalibrationTimeline artifacts={array} onOpenArtifact={...} />
```
- Plots wavelength RMS, response stability, and FWHM over time; warns on validity window violations (Ch. 6 §7).

### 8.6 SourceRegistryTable
```ts
<SourceRegistryTable sources={...} onSync={...} />
```
- Shows `source_id@version`, license, DOI/URL, cache status; supports side‑by‑side compare (Ch. 4).

### 8.7 ReportBuilder
```ts
<ReportBuilder sessionRef="sessions/[SESSION_ID]" datasetRef="datasets/[DATASET_ID]" />
```
- Composes PDF + bundle with manifest, ledger, evidence graph, and figures (Ch. 8, 12).

---

## 9. Microcopy: words that earn their keep

- **Buttons:** “Harmonize to FWHM,” “Add Mask,” “Open Evidence,” “Export Bundle,” “Validate Units,” “Attach Calibration.”
- **Errors:** “Missing unit/medium. Choose axis units (nm/cm⁻¹/eV) and medium (air/vacuum). See Chapter 5.”
- **Warnings:** “You’re viewing a **convolved** overlay at 6.0 cm⁻¹. Raw data remain unchanged.”

Tone: concise, direct, never cutesy.

---

## 10. Keyboard map (defaults)
- `1/2/3` switch unit axis (nm/cm⁻¹/eV)
- `M` add mask brush; `Shift+M` remove
- `H` harmonize to target FWHM
- `E` open Evidence Graph; `R` open Rubric
- `G` toggle grid; `U` toggle uncertainty ribbon
- `Ctrl+K` command palette; `?` help

All shortcuts are remappable in settings and recorded if they affect exports.

---

## 11. Theming and print/export

- **Themes:** light, dark, high‑contrast; chosen theme saved in profile JSON and optionally stamped in report footer.
- **Print:** vector SVGs at 300 DPI equivalent; large fonts; unit badges and LSF banners included by default; provenance footer optional (Ch. 20 §5).

---

## 12. QA checklist for UI releases

- Unit badges appear on all plots and in all themes.
- LSF banner triggers exactly when overlays are convolved and shows correct kernel/FWHM.
- Evidence Graph panel opens from all relevant links and highlights nodes from table clicks.
- Keyboard navigation covers 100% of critical paths (ingest → view → identify → export).
- Error states and empty states are informative and link to docs.

---

## 13. Anti‑patterns to avoid

- Hiding units to “reduce clutter.”
- Auto‑smoothing or baseline correction on load.
- Collapsing provenance behind multiple clicks.
- Rainbow color maps for quantitative data; non‑color‑safe palettes.
- Exporting bitmaps without the underlying data.

---

## 14. Cross‑links
- Ch. 5 (units/axes), Ch. 6 (LSF), Ch. 3 (evidence graph model), Ch. 7 (identification outputs), Ch. 8 (provenance), Ch. 9 (feature expectations), Ch. 12 (formats), Ch. 13 (Docs), Ch. 20–21 (fun + useful additions).

---

## 15. Reference anchors (full citations in Ch. 32)
- WCAG 2.2 guidelines for accessibility.
- Nielsen–Norman heuristics for usability.
- Tufte & Munzner for visualization honesty and density.
- Color‑vision deficiency resources and contrast standards.
- ISO/IEC usability standards for software ergonomics.

> The UI is there to make physics and provenance obvious, not to cosplay a spaceship dashboard. If a design choice risks unit confusion or hides resolution, it’s wrong. End of sermon.

