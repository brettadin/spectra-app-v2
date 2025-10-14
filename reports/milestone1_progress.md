# Milestone 1 Progress Report – Core Platform & Correctness

## Work Plan Mapping

| Documentation Source | Components Implemented | Tasks Completed |
| --- | --- | --- |
| `specs/architecture.md`, `specs/system_design.md` | Service layer foundation (UnitsService, DataIngestService, OverlayService, MathService, ProvenanceService) | Built immutable `Spectrum` model, canonical unit conversions, pluggable ingest registry, overlay manager and math operations with suppression logging. |
| `specs/units_and_conversions.md` | Units/Conversions Service & tests | Implemented nm/µm/Å/cm⁻¹ wavelength conversions, transmittance/absorbance/α handling and round-trip pytest coverage. |
| `specs/provenance_schema.md`, `specs/testing.md` | Provenance manifest creation & persistence | Added manifest builder including checksums, operations log and JSON writer, plus unit tests for manifest integrity. |
| `specs/system_design.md`, `specs/ui_contract.md` | PySide6 shell (Data, Compare, Provenance tabs) | Created responsive Qt UI wiring ingest, overlay, math and provenance services, with chart overlays and keyboard-accessible controls. |
| `specs/packaging.md` | Windows packaging assets | Authored PyInstaller spec and Windows build guide capturing dependency locks and smoke test expectations. |

## Key Decisions & Rationales

- **Stack**: Adopted PySide6/Qt with numpy-powered services, matching the recommended architecture for native Windows UX and leveraging existing template code for low-cost deployment.
- **Canonical units**: Chose nm and base-10 absorbance as internal baselines to guarantee idempotent conversions and align with scientific conventions outlined in the units specification.
- **Data ingestion**: Implemented importer protocol with contextual metadata, keeping parsers pluggable and non-destructive per data handling requirements.
- **Math engine**: Resampled spectra on demand and suppressed trivial results with explicit logging to avoid silent mutations while providing deterministic operations.
- **Packaging**: Standardised on PyInstaller with a reusable spec so Windows builds can be reproduced without additional tooling costs.

## Assumptions & Open Questions

- **Packaging execution**: Cross-compiling Windows binaries inside this Linux environment is out of scope; the spec and instructions are provided for a native Windows run (assumption logged for follow-up).
- **Additional formats**: CSV importer covers the milestone needs; JCAMP-DX and FITS plugins remain future tasks per plugin guide.
- **Knowledge log integration**: Deferred until later milestones because current scope prioritises core services and tests.

## Risks & Mitigations

- **Large PySide6 dependency footprint**: Mitigated by documenting Windows build steps and pinning versions in `requirements.txt`.
- **Future importer complexity**: Protocol and metadata structures were designed to accept richer context (e.g., path length) to reduce refactoring risk.
- **UI scalability**: Chart widget currently targets moderate datasets; plan to profile performance before loading very large spectra.

## Next Steps

1. Add JCAMP-DX and FITS import plugins with corresponding tests and sample datasets.
2. Implement knowledge log service and integrate history tab wiring.
3. Extend math service with normalised difference, smoothing and resampling configuration options.
4. Begin functional group prediction stubs per ML service specification.

## Patch-Prompt Record

Verbatim request stored at: `docs/history/past prompts/2025-10-14T065106_local-patch-milestone1_user-prompt.txt`.
