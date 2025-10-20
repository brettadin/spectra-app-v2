# Chapter 20 — Fun Additions

> **Purpose.** Collect delight‑creating, morale‑preserving features that make the spectroscopy workflow engaging without compromising rigor. Every item here is strictly optional, opt‑in, and sandboxed away from raw data or scoring logic.
>
> **Scope.** UI niceties, sonification/visual toys, classroom games, onboarding aids, and export flourishes that sit on top of the core workflow (Ch. 1–19) and respect units (Ch. 5), calibration (Ch. 6), provenance (Ch. 8), and determinism.
>
> **Path notice.** All filenames and directories below are **placeholders** resolved by the app’s path resolver at runtime. Tokens like `[SESSION_ID]`, `[DATASET_ID]`, `[MODALITY]`, `[YYYYMMDD]` must **not** be hardcoded. These features write only to **views** and **metadata**; raw arrays remain immutable.

---

## 0. Non‑negotiable guardrails
1. **No science harm.** Fun features never alter raw data or rubric results (Ch. 11). Any derived play view is labeled and excluded from identification.
2. **Opt‑in only.** Default off in research mode; available in Teaching Mode (Ch. 13) or via per‑user settings.
3. **Accessible by design.** Colorblind‑safe palettes, keyboard control, captions for audio/animations.
4. **Deterministic.** If a feature affects a saved artifact (e.g., a sticker on a report), it is versioned and captured in provenance (Ch. 8).

---

## 1. Visual polish and play
- **Theme switcher:** light/dark/high‑contrast themes; lab‑friendly “no glare” palette.
- **Plot skins (non‑scientific):** alternate but unit‑honest render styles (grid/no‑grid, subtle tick marks). Saved as shareable JSON `plot_profiles/*.json`.
- **Waterfall & curtain overlays:** flip between overlay, waterfall, and a draggable **wipe slider** to compare two spectra at matched FWHM (Ch. 6 §5).
- **Spectral highlight glow:** animated halos around features in the evidence graph when hovered (Ch. 3), with a toggle to minimize distraction.
- **Timeline bar:** tiny **sparklines** for SNR, wavelength RMS, and FWHM drift across a session.

---

## 2. Sonification (ear candy, not evidence)
- **Pitch‑by‑axis mapper:** map axis to pitch/time and intensity to amplitude; export `.wav` with a JSON sidecar describing mapping and units.
- **Event tones:** optional chimes for QC passes (e.g., Si 520.7 cm⁻¹ within tolerance) with lab‑safe volume caps.
- **Rule:** sonifications are **never** used for scoring or identification; they exist only as learning aids.

---

## 3. Live mini‑calculators
- **Raman shift & uncertainty**: interactive calculator tied to λ₀ with propagation (Ch. 5), copy‑to‑report snippet.
- **Beer–Lambert helpers**: dilution math, LOD/LOQ cheat sheet with the chosen formula and reference (Ch. 2, 5).
- **Tauc assistant**: click two points to fit a provisional bandgap line; strictly a preview, not a stored result.

---

## 4. Classroom games (Teaching Mode)
- **Mystery Sample Arcade**: timed drills that spawn synthetic noisy spectra from known templates. Scoring uses the **rubric simulator** so students see how G(M) changes (Ch. 11).
- **Feature‑tag microtasks**: quick peak tagging with hints; accepted tags flow into the feedback queue (Ch. 16 §7), all with reviewer approval before they influence training.
- **Calibration Bingo**: checklist tiles for “Dark captured,” “Polystyrene match,” “Si 520.7 OK.” Completing a row unlocks a **Clean Run** badge.

> Badges live only in teaching exports; never embedded in research reports by default.

---

## 5. Stickers and stamps (harmless flourishes)
- **Unit badge stickers**: small SVG glyphs (nm, cm⁻¹, eV) that summarize the unit view used in a figure (Ch. 5).
- **“Matched FWHM” stamp**: subtle banner declaring the target resolution used for overlays (Ch. 6). Auto‑adds when the harmonizer is active.
- **Provenance footer**: a tasteful footer line with app build, rubric ID, library versions count. Toggle on/off for teaching PDFs (Ch. 8, 11).

---

## 6. AR‑lite camera helpers (if device has a camera)
- **ATR contact overlay**: outline crystal and show pressure/coverage hints using simple edge detection; store only a thumbnail with a toggle; no faces saved.
- **Cuvette sanity**: glare/scratch detector for UV–Vis cuvettes; suggests rotating or cleaning.

> All camera features are **offline**, local‑only, and excluded from research exports unless explicitly included.

---

## 7. Gentle gamification (opt‑in)
- **Badges** (teaching mode):
  - *Clean Run*: all QC gates passed, no unlogged transforms.
  - *Calibration Hawk*: wavelength RMS within top decile for course cohort.
  - *Provenance Purist*: manifest complete, zero warnings.
- **Leaderboards** are disabled by default; if enabled for a class, they show **process** metrics only (never grades), anonymized.

---

## 8. Quality‑of‑life extras
- **Keyboard palette**: single‑key shortcuts for axis toggle, mask brush, FWHM harmonizer.
- **One‑click “Open evidence”**: jumps from a report table row to the exact evidence graph node (Ch. 3, 7).
- **“Why this matters” popovers**: short context blurbs with references that link into the Docs module (Ch. 13).
- **Session scrapbook**: optional `notes.md` saved alongside manifests; supports fenced code blocks for quick calculations.

---

## 9. Exports worth keeping
- **Gallery sheet**: contact‑sheet PNG/SVG with small multiples for a cohort of spectra at matched FWHM.
- **Parameter bookmark**: JSON file that re‑opens the Spectral Viewer to the same zoom, masks, and overlays.
- **Poster mode**: big‑font, high‑contrast figure exporter with unit badges and stamps pre‑arranged.

---

## 10. Easter eggs (responsible ones)
- **Polystyrene Party**: when the polystyrene check hits within tight tolerance, the viewer borders glow for 1 second. Can be disabled globally.
- **Si 520.7 confetti**: a single burst of 10 triangles on pass; zero opacity after 0.7 s. Off by default in research mode.

---

## 11. Settings and policy
- **Profile JSON**: `profiles/[USER]/fun_settings.json` stores toggles; captured in provenance only if a fun feature affects an export.
- **Class policy switch**: instructors can force‑disable any fun feature for assessment sessions.

---

## 12. Future ideas
- **Spectral‑to‑color palette designer** that maps diagnostic bands to brand‑safe colors for figures (with CVD‑safe presets).
- **Haptic taps** on trackpads for QC passes (hardware‑dependent).
- **AR laser‑spot finder** for Raman alignment using a neutral density preview.

---

## 13. Cross‑links
- Ch. 3 (evidence graph hover highlights), Ch. 5 (unit badges), Ch. 6 (FWHM harmonizer), Ch. 8 (provenance of exports), Ch. 11 (rubric simulator), Ch. 13 (Teaching Mode), Ch. 15 (comparison visualizations).

> **Reminder.** Fun stays fun only if it’s honest. These features must never fabricate or “prettify” scientific results. The unit badges, FWHM stamps, and provenance footers double as subtle pedagogy while keeping everything defensible.

