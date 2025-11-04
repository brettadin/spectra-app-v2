# Spectral Analysis Toolkit — Design and Plan (Nov 4, 2025)

This document captures the planned quality-of-life helpers and rigorous spectroscopy analysis features to layer onto the current plotting/normalization pipeline. It focuses on repeatable measurements, minimal UI friction, and provenance.

---

## Goals
- Rapid, precise interaction: read off exact coordinates; pick peaks with one click; jump to interesting points.
- Scientific measures that match spectroscopy practice: centroid, FWHM, equivalent width (EW), integrated flux/area.
- Robust comparisons: lab vs. standards vs. external references (e.g., NIST lines, functional groups), with alignment tools.
- Reproducible outputs: results copied/exported with sufficient metadata and parameters to reproduce runs.

## UI surfaces
- Status bar: live cursor coordinates (done), add optional pre-scale y readout and normalization/global indicators.
- Plot toolbar (compact actions):
  - Find local peak near cursor (planned)
  - Jump to global max (planned)
- Data Table dock:
  - Buttons: “Jump to max”, “Find peak near cursor”, “Copy selection” (planned)
  - Reflect current X unit and post-normalization values (done); optionally add a column for pre-Y-scale value when non-linear scale is active (planned)
- Measurement pane (new Inspector tab):
  - One-click peak measurements with centroid/FWHM/EW
  - Results table with per-measurement provenance (method, window, baseline, normalization state, units)
  - Export/Copy buttons

## Tiny contracts (APIs)
- Peak near cursor
  - Inputs: x_cursor (float, display units), active spectrum id (optional; default: first visible/selected), search window Δx (display units), prominence/min_distance (optional)
  - Outputs: peak_x_nm (float), peak_y (float, post-normalization), indices/window used, success flag
  - Errors: no visible data; empty window; NaN-only region; return success=False
- Jump to global max
  - Inputs: spectrum id (optional)
  - Outputs: x_nm at max(|y|), y value, index
- Measurement (centroid/FWHM/EW)
  - Inputs: window [x1, x2] (nm), baseline mode (flat/linear), normalization mode and factor (captured), y-scale (captured but not applied to metrics)
  - Outputs: centroid_nm, fwhm_nm, ew_nm, integrated_area, uncertainties (optional), flags

## Algorithms
- Peak finding: scipy.signal.find_peaks or minimal bespoke scan with windowed max/peak-shape heuristics. Guard with:
  - finite-only masking; drop NaNs/Infs
  - minimum sample count; enforce monotonic x (already in plotting via reversal for cm⁻¹)
- Centroid: weighted by intensity above baseline within window
- FWHM: interpolate half-maximum crossings for sub-sample accuracy
- Equivalent Width (EW): integrate (1 − y_norm) over window for transmittance/flux-normalized series; respect baseline selection

## Edge cases & safeguards
- Empty/NaN windows → no measurement
- Very noisy series → require prominence/min_distance
- Non-monotonic x (cm⁻¹ display) → operate in nm space (canonical) internally
- Non-linear Y-scale → compute metrics on pre-scale, post-normalization values only
- Global normalization on → record factor and mode; metrics based on the normalized array actually displayed

## Data shapes and units
- Canonical X: nm for all internal calculations; convert display→nm at the edges
- Y: use post-normalization arrays; carry raw/pre-scale Y for display only
- EW units: nm (or convertible to Å/µm for reporting); store nm internally

## Performance
- Operate on current downsample window where possible for responsiveness, but compute final metrics on the full-resolution arrays for accuracy when needed
- Keep find-peak O(window) with vectorized numpy when possible; avoid expensive global searches unless requested

## Provenance & export
- Record: spectrum id/name, timestamp, normalization/global flags, calibration params (FWHM, RV), window, baseline, algorithm parameters
- Export formats: CSV (rows=measurements), JSON (verbose with parameters) — copy-to-clipboard as a compact text block

## Implementation plan (phased)
1) QOL helpers (low risk)
   - Status bar: add scale and normalization badges; optional pre-scale y when non-linear scaling is active
   - Toolbar/Data Table: “Find peak near cursor”, “Jump to max” buttons with status readouts
2) Measurement pane
   - Create a dedicated Inspector tab with window selection from the current view or a drag-interaction on the plot
   - Implement centroid/FWHM/EW; copy/export results
3) Comparison tools
   - Pin measured features and overlay vertical markers with labels; compare to NIST lines or IR bands; compute offsets
4) Alignment utilities
   - Visual/assisted alignment: RV offset fitter (cross-correlation in nm), dispersion tweak; preview and accept

## References
- NIST ASD for atomic lines; IR functional groups references bundled under `app/data/reference/`
- Spectroscopy practice: Hearnshaw, “Astronomical Spectroscopy”; Draine, “Physics of the Interstellar and Intergalactic Medium” (emission/absorption line measures)
- SciPy signal processing: https://docs.scipy.org/doc/scipy/reference/signal.html#peak-finding

---

Status: Planning. Minimal UI hooks will be added alongside tests; metrics computed in nm-space with normalization-aware arrays.
