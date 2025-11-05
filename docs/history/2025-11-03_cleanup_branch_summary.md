# Cleanup Branch Summary — 2025-11-03

Last verified: 2025-11-03 (local and UTC times noted in Knowledge Log)

This note summarizes the changes landed on Nov 2–3, 2025 during the cleanup and UI polish pass, with links to the relevant files and guides.

## Highlights

- Plot stability
  - Fixed x-axis reversal for cm⁻¹ (wavenumber) by reversing arrays post-conversion to keep x monotonic and prevent traces disappearing during pan/zoom.
  - File: `app/ui/plot_pane.py` (display mapping and update logic)

- Normalization and visibility controls
  - Global normalization (Max/Area) with NaN/Inf-robust scaling across all spectra; Y-scale transforms (Linear, signed Log10, Asinh) applied post-normalization.
  - Display-time calibration: FWHM blur and RV shift applied in nm-space prior to normalization (data remains unchanged).
  - Files: `app/ui/main_window.py`, `app/services/math_service.py`

- Reference overlays (NIST lines) usability
  - Bars rescale on zoom/normalization and draw behind spectra; anchor to y=0 when visible.
  - Distinct colours per pinned set using a dedicated overlay color iterator; double-click a pin to remove; “Show selected only” and “Clear Pins.”
  - Files: `app/ui/main_window.py`, `app/ui/reference_panel.py`

- Palette and dark-mode
  - Expanded palette (>20 colours) applied to datasets; separate iterator for overlays to avoid shifting dataset colours.
  - Improved dark-mode checked states (QToolButton/QCheckBox) for visibility.
  - Files: `app/ui/main_window.py`, `app/ui/styles.py`, `app/ui/palettes.py`

- Library and Docs
  - Library → Samples node lists bundled data; double-click to ingest.
  - Docs panel groups topics by category (User, Developer, History, Other) and renders Markdown when supported; index updated with a Cleanup Branch section.
  - Files: `app/ui/main_window.py`, `docs/INDEX.md`

## Documentation updated

- Patch notes: `docs/history/PATCH_NOTES.md` (entries for 2025-11-03, 2025-11-02)
- Plot tools guide: `docs/user/plot_tools.md` (Global/Y-scale/NaN & overlays)
- README and normalization verification: `README.md`, `NORMALIZATION_VERIFICATION.md`

## Where to start

- Cleanup master plan: `docs/dev/CLEANUP_MASTER_PLAN.md`
- Capability atlas (archived): `docs/app_capabilities.md`
- Repository inventory (archived): `docs/repo_inventory.md`
- Roadmap: `reports/roadmap.md`
- Docs index (updated): `docs/INDEX.md`

## Next steps

- Finish optional line-list caching for common elements.
- Evaluate replacing Line Shapes tab with a peak picker/fit or EW/FWHM tool.
- Continue consolidating older docs into the indexed structure and retire duplicates under `docs/history/archive/`.

## Logging expectations for future agents

- For every set of changes, update all three:
  - Patch Notes: add a dated bullet to `docs/history/PATCH_NOTES.md`.
  - Knowledge Log: add an entry to `docs/history/KNOWLEDGE_LOG.md` (use `docs/history/KNOWLEDGE_LOG_TEMPLATE.md`).
  - Daily Worklog: append to `docs/dev/worklog/YYYY-MM-DD.md` (use `docs/dev/worklog/TEMPLATE.md`).
- The PR template requires links to these; complete them before review.
