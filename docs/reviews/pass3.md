# Pass 3 — Calibration & Identification Blueprint (2025-10-17T00:20:00Z)

Defines the roadmap for calibration fidelity and explainable identification.

## Calibration Track
- Build `CalibrationService` handling kernels, frames, RV shifts, and σ
  propagation.
- Surface calibration controls in a dedicated dock with live banners and trace
  badges.
- Extend provenance schema with ordered `applied_steps` describing kernels,
  frames, reference frames, and uncertainty updates.
- Tests: FWHM tolerance, no sharpening, RV deltas, air↔vacuum idempotence,
  uncertainty propagation on dense arrays.

## Identification Track
- Implement peak extraction, line matching, similarity scoring, and explainable
  composite scores.
- UI: Identification dock with catalogue chooser, bandpass filters, RV grid,
  score cards, and plot-linked highlights.
- Provenance: Manifest block containing catalogue hash/version, weights,
  component scores, best-fit RV, and seed values.
- Tests: Deterministic peak lists, jitter tolerance, cross-correlation RV,
  component weight sanity.

## Documentation
- Update user identification guide, developer notes, and knowledge log entries.
- Capture architecture rationale in `docs/brains/` when major choices are made.

## References
- `docs/specs/provenance_schema.json`
- `docs/atlas/0_index_stec_master_canvas_index_numbered.md`
- `docs/user/reference_data.md`
