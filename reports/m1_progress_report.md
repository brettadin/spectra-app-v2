# Milestone 1 Progress Report – Core Platform & Correctness

## Work Plan (Docs → Components → Tasks)
- **Architecture & UI shell** (`specs/architecture.md`, `specs/ui_contract.md`): establish PySide6 desktop shell with menu, data tabs, overlay and math controls; ensure responsive layout and keyboard-accessible actions.
- **Unit handling** (`specs/units_and_conversions.md`): implement canonical nm/A10 baseline in `UnitsService`, add conversion helpers, and enforce round-trip tests.
- **Data ingest** (`specs/system_design.md`, `specs/testing.md`): create pluggable ingest service with importer protocol, CSV importer, and metadata capture without mutating source values.
- **Provenance** (`specs/provenance_schema.md`): enhance manifest service to record sources, transforms, app/library versions, and timestamps.
- **Overlay & Math** (`specs/system_design.md`, `reports/feature_parity_matrix.md`): provide overlay engine returning derived views and math service for subtract/ratio with epsilon handling and trivial suppression.
- **Packaging** (`specs/packaging.md`): supply PyInstaller spec and Windows build instructions.
- **Testing & Samples** (`specs/testing.md`): extend pytest suite to cover conversions, ingest, overlay, math, and provenance; add sample spectra for regression coverage.

## Stack Decision & Rationale
- Selected **PySide6/Qt + Python** for UI and services. Aligns with architectural recommendation for native Windows desktop UX and keeps implementation in one language for maintainability. Qt widgets deliver responsive layout and strong accessibility support while remaining compatible with PyInstaller packaging (`specs/architecture.md`, `specs/packaging.md`).

## Assumptions & Open Questions
- Local time for patch logging matches container UTC; recorded identical ISO timestamp for local/UTC due to lack of timezone context.
- Windows-style path in prompt log is represented by repository-relative folder (`docs/history/past prompts/…`) because colon-prefixed drive paths are invalid inside the container.
- Overlay view currently renders tabular data rather than plots; assumes milestone scope emphasises service wiring and correctness over chart visualisation.
- Future ingest plugins (JCAMP, FITS) will follow the provided protocol but are out of scope for this milestone.

## Risks
- PySide6 binary size and dependency footprint could complicate final MSIX packaging; mitigate via PyInstaller spec tuning and optional UPX compression.
- Additional importer formats may need more metadata fields than the current `ImporterResult` dataclass captures.
- Math operations presently require aligned wavelength grids; interpolation service is deferred and may be required for heterogeneous datasets.

## Next Steps
- Implement plotting widget and richer overlay visualisation once correctness foundation stabilises.
- Add additional importers (JCAMP-DX, JSON manifest rehydration) and extend provenance manifests with transform replay data.
- Integrate knowledge-log automation and CI packaging as described in architecture/system design documents.

## Patch Prompt Log Reference
- `docs/history/past prompts/2025-10-14T070029_local-patch-v1.0.0_user-prompt.txt`
