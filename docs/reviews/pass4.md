# Pass 4 — Data & Provenance Cohesion (2025-10-17T00:30:00Z)

Concentrates on reproducibility, manifests, and store coherence.

## Unified Manifest & Store
- Adopt a single manifest schema (v1.2.0) with explicit `applied_steps`,
  uncertainty descriptors, view state, and cross-links to cache entries.
- Ensure LocalStore uses content-addressed paths, exposes manifest references,
  and links out to the Knowledge Log and Library view.

## Export & Replay
- Export bundles must include canonical CSVs, original uploads, manifests,
  provenance log, and view-state JSON capable of replaying the UI.
- Add round-trip tests that regenerate `view.png` within an RMSE threshold.

## Library & History Cohesion
- Library actions: inspect metadata, open manifests/logs, re-export current view.
- History dock should hyperlink to Knowledge Log entries and Library records.

## CI & Tooling
- `.github/workflows/provenance.yml` validates manifests and runs targeted pytest
  suites (`roundtrip`, `ui_contract`). Keep it green; quarantine flaky tests with
  an issue + follow-up task in the workplan.

## Documentation
- Update provenance guides, developer notes, and user exporting docs.
- Capture cohesive flow diagrams in `docs/brains/` when store/export pipelines
  evolve.

## References
- `specs/provenance_schema.json`
- `docs/user/importing.md`
- `docs/user/reference_data.md`
- `docs/history/PATCH_NOTES.md`
