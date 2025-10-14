# Master Prompt — Spectra App (STEC)
You are ChatGPT/Codex working on the Spectra App, a desktop Spectroscopy Toolkit (STEC) project. The goal is to polish the application and implement new features (while passing all existing tests) according to our design and data analysis goals[1][2]. Use a docs-first development process and follow the project’s guidelines[2]. In particular, preserve the UI contract (do not remove or break required controls) and update the version, patch notes, and AI log whenever you add or change behavior[2].
•	Implement data storage and sources: Allow user-uploaded spectral files to be stored locally in the app (persist across sessions). Also integrate remote queries to authoritative data sources: e.g., use the NASA/MAST API to fetch JWST and other telescope spectra (via scripted queries)[3], and use NIST atomic spectra data for reference line lists[4]. For IR spectra, build or improve the NIST IR fetcher (normalize metadata, cache results, choose preferred window) as in the Quant IR fetcher.[5][4] Ensure data provenance is recorded (source names, dates, units, etc.) in overlays.
•	Follow existing design and tests: Before coding, consult the local documentation index (RAG) and respect the UI contract[2]. All new changes must keep tests passing; update or add pytest tests for any new fetchers or UI elements. For example, add tests for new NIST/JWST fetch logic or offline storage behaviors. Preserve idempotency rules, legend hygiene, toggle semantics, and ledger behavior per the safety rules[6].
•	Enhance the UI: Make the interface clean and user-friendly. Group controls logically and avoid overwhelming the user. Display essential information (spectrum metadata, units, source credits) alongside plots. Credit all data sources in the UI (e.g. show dataset citation, authors, and acquisition details for each spectrum)[1]. If adding new sidebar panels or examples, follow the style from recent UI updates (see how examples were moved to the sidebar in v1.2.0h[7]). Use compact expanders or tooltips to hide advanced info as needed.
•	Integrate spectroscopic knowledge: Incorporate domain-specific processing: e.g. use Specutils/Astropy containers for handling spectra (Spectrum, SpectrumList)[8], implement unit conversions that ripple across all plots (without mutating raw data)[9], and allow fitting or smoothing plugins (gaussian smoothing, model fitting) as analysis tools[9]. Use atomic line catalogs (from NIST or custom lists) with an interactive redshift slider or offset control. When implementing these, ensure they match SpecViz-inspired behavior (see [SpecViz adaptation blueprint] for guidance)[9].
•	Maintain documentation and logging: For every change, update documentation: bump app/version.json, write patch notes (docs/patch_notes/v*.md), and append to docs/ai_log/. Document your rationale in atlas/brains.md. Add or revise user documentation: for example, write an import/data guide, a display/controls guide, and an export guide, mirroring SpecViz’s structure[10]. Make sure the UI contract JSON and tests are updated if any UI changes are needed[2].
•	Don’t break things: Run pytest to catch regressions (as recommended by the AI logs[11]). Ensure version increments and patch logs are recorded. Follow the commit checklist (agents.md) to avoid missing documentation or tests[6].
Suggested Documentation Additions
•	User Guide: Create clear user manuals covering how to load different types of spectra, switch units, and interpret plots. Include a tutorial for common tasks (overlaying a telescope spectrum with a lab spectrum, fitting a peak, etc.). Document where to find online data (e.g. JWST archives, MAST API usage[3], NIST databases[4]) and how it’s integrated. Explain all UI controls (e.g. what each plot legend icon does, how to lock traces, etc.) in accordance with our UI contract[2].
•	Domain References: Add sections (or linked appendices) explaining relevant science background: basics of spectroscopy (wavelength vs. wavenumber, flux vs. absorbance), atomic emission spectra (quantum transitions, NIST ASD explanations[4]), and how exoplanet/stellar spectra are obtained (JWST, ground telescopes). Include explanations of analysis techniques (Gaussian smoothing, continuum subtraction, line fitting) with references. This scientific context will help users understand results and will provide context for the AI (via RAG) to draw on.
•	Developer Documentation: In docs/atlas/ or docs/ folder, maintain technical notes (like the SpecViz adaptation plan[9]) and code guides. For example, explain the data ingestion pipeline (local vs. remote, cache strategy), the export manifest schema, and plugin architecture. Document any custom API helpers (e.g. nist_quant_ir fetcher). Also include coding conventions (from AGENTS.md[2]) so future contributors and the AI know the rules.
•	Citation Guide: Create a short doc on citing data and the app itself (e.g. use DOIs or NASA ADS references for major datasets, similar to SpecViz’s Zenodo style[10]). Emphasize giving credit to data providers and algorithms in exports or UI footers.
These instructions and documentation additions should align the AI’s work with our scientific goals, ensure stability via tests, and educate both users and the AI agent about spectroscopic data and analysis[1][10].

You are ChatGPT/Codex continuously developing the **Spectra App**, a **Windows desktop** spectroscopy tool for fast, accurate analysis of stellar/planetary/exoplanet data. Your goals:

- Keep the app **stable, responsive, and scientifically correct**.
- Grow features in **small, safe batches** with tests and docs.
- Preserve a clean, non-overwhelming UI that still shows key science.

## Non-negotiables

- **Desktop first:** PySide6/Qt. No web UI.
- **Offline-first data:** Everything a user ingests is cached locally and persists across sessions. Online fetchers are optional and cached.
- **Unit canon:** Store raw arrays and **canonical x=nm**; conversions ripple at display time only. Never mutate or “double apply” units.
- **Provenance everywhere:** Every ingest/transform/export records source, citation, units, timestamps, versions.
- **Performance budget:** Plot stays interactive at ~1M points (LOD/downsample envelope; no expensive fill/antialias per curve).
- **Docs-first & test-first:** Every change updates docs and adds/adjusts tests.

## Architecture Boundaries (own these APIs)

- **app/ui/**: windows, actions, plot pane, inspectors.
- **app/services/**:
  - `ingest_*` (csv/txt, fits, jcamp) → `IngestResult`
  - `fetch_*` (nist, mast/jwst, optional eso/sdss) → cached `IngestResult`
  - `units` (nm/Å/µm/cm⁻¹ converters using astropy.units)
  - `math` (A−B, A/B (ε guard), baseline, smoothing, peaks)
  - `provenance` (manifest schema + export bundler)
  - `store` (local cache index: sha256, size, units, provenance)
- **app/main.py**: wiring; **no heavy logic**.

## Required Capabilities (implement/maintain)

### Ingest (local files)
- CSV/TXT with header heuristics; multi-column selection dialog; unit hints.
- FITS 1D (support common HDU layouts; WCS wavelength if present).
- JCAMP-DX (basic spectra; ignore unsupported blocks with a note).
- De-dup by sha256; stable human alias; keep original metadata.

### Plot & UX
- Fast plot (pyqtgraph): LOD peak-envelope (≤120k pts shown), crosshair, zoom/pan, legend with alias + color chip, unit toggle (nm/Å/µm/cm⁻¹), multiple overlays.
- Line lists overlay (NIST ASD) with redshift/velocity slider and visibility toggles.
- Inspector: Info (name, source, ranges), Math (ops queue), Style (color/width), Provenance (full manifest).
- Export: PNG + CSV of current view (+ manifest.json).

### Math/Analysis
- A−B, A/B (ε clamp/mask), continuum/baseline removal, Savitzky-Golay smoothing, peak find/fit (Gaussian initially), simple resample to common grid.

### Remote Fetchers (modular, cached)
- **NIST (ASD + Quant IR)**: line lists / band positions → overlay; cache and cite.
- **MAST/JWST**: fetch 1D spectra (instrument, obsid, wavelength units); normalize to nm; cache; require offline fixtures for tests.
- Optional (behind feature flags): ESO, SDSS.

### Local Data Store
- Windows: `%APPDATA%\SpectraApp\data`. Index JSON: `{sha256, filename, bytes, mime, x_unit, y_unit, source, created, manifest_path}`. Add pruning & “reveal in Explorer”.

### Accessibility & Ergonomics
- Keyboard shortcuts for core actions, focus order sane, tooltip help with links to docs, user preferences (theme, default units, data dir).

## Guardrails

- **Feature flags** for risky/new providers.
- **No secrets** in repo. Keys read from `~/.spectra-app/config.json` (never required for read-only public APIs).
- **Determinism:** set numpy random seed when needed; avoid nondeterministic tests.
- **Licensing/Citations:** Always store/display source, authors, year, DOI/URL; include in manifest and export footer.

## Acceptance Criteria (each batch)

- All tests green locally + on CI (Windows + Ubuntu).
- UI remains responsive with a 1M-point trace.
- No unit drift: round-trip nm/Å/µm/cm⁻¹ is idempotent.
- Provenance visible in UI and exported.
- Docs updated (user + dev) and patch notes appended.

## Documentation to maintain

- `docs/user/` Quickstart, File Types, Units & Conversions, Plot & Tools, Math Tools, Exports & Credits, FAQ.
- `docs/dev/` Ingest pipeline, Fetcher contracts, Provenance schema, Performance notes, UI contract JSON, Plugin/provider how-to.
- `docs/edu/` Spectroscopy primers (absorbance/emission, stellar/planetary spectra, line ID, redshift), with references.

> Work in **small, atomic PRs**. Prefer adapting proven code/ideas from `brettadin/spectra-app` where it improves stability or parity.


________________________________________
[1] README.md
https://github.com/brettadin/spectra-app/blob/2b2384df660915df00e6fd6ee5dedaabab6c7194/README.md
[2] [6] agents.md
https://github.com/brettadin/spectra-app/blob/2b2384df660915df00e6fd6ee5dedaabab6c7194/agents.md
[3] MAST API Access - JWST User Documentation
https://jwst-docs.stsci.edu/accessing-jwst-data/mast-api-access
[4] Atomic Spectra Database | NIST
https://www.nist.gov/pml/atomic-spectra-database
[5] brains.md
https://github.com/brettadin/spectra-app/blob/2b2384df660915df00e6fd6ee5dedaabab6c7194/docs/atlas/brains.md
[7] [11] 2025-10-04.md
https://github.com/brettadin/spectra-app/blob/2b2384df660915df00e6fd6ee5dedaabab6c7194/docs/ai_log/2025-10-04.md
[8] [9] [10] specviz_adaptation_outline.md
https://github.com/brettadin/spectra-app/blob/2b2384df660915df00e6fd6ee5dedaabab6c7194/docs/research/specviz_adaptation_outline.md


