# Patch Notes

This document summarizes notable user-facing changes. It appears in the in-app Docs tab (F1) so you can review updates without leaving the app.

## 0.1.0 — 2025-11-02

Highlights
- Data dock cleanup: a new toolbar in Datasets adds quick removal actions
  - Remove Selected (Del)
  - Clear All (Ctrl+Shift+C, with confirmation)
- Remote Data moved to the Inspector: use Ctrl+Shift+R to open the tab; providers and background execution unchanged
- History panel UX: add filter field and a small toolbar (Refresh, Copy, Export)
  - Hidden by default (View → History) to keep the workspace focused
- Shortcuts (kept minimal and logical)
  - F1: View Documentation
  - Ctrl+Shift+R: Show Remote Data tab
  - Ctrl+Shift+A: Reset Plot
  - Del: Remove selected datasets
  - Ctrl+Shift+C: Clear all datasets (confirmation)
  - Ctrl+L: Focus dataset filter
  - Ctrl+Shift+H: Show History dock
  - Ctrl+M: Switch to Merge/Average tab
- Calibration scaffold: added a light service for view-time resolution matching and RV/frame adjustments; UI dock to follow

Notes
- The History dock focuses on high-level log entries (import/export/remote/search summaries and knowledge entries). Routine ingest bookkeeping remains in the Library and provenance manifests.
- Remote Data still supports MAST/ExoSystems and curated Solar System archives. NIST spectral lines live under Inspector → Reference.

See also
- Quickstart: getting started, unit toggles, and export
- Remote Data: panel workflow and provider tips
- Plot Tools: legend, normalization, and dataset removal toolbar
