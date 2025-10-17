# Atlas – Architectural Decisions

This log captures the architectural choices that currently govern Spectra's ingest pipeline, cache strategy, and remote services. It supplements the Master Prompt so future contributors can reconcile historical directives with the code that is now in production.

## Ingest pipeline

- `DataIngestService` registers CSV/TXT, FITS, and JCAMP-DX importers by default and dispatches files by extension, so new formats should plug in through `register_importer` rather than modifying the UI file pickers.【F:app/services/data_ingest_service.py†L15-L37】
- Every ingest normalises spectral axes through `UnitsService.to_canonical`, annotates the metadata with importer details, and emits a canonical `Spectrum` that keeps the original source path for provenance.【F:app/services/data_ingest_service.py†L38-L60】
- When a shared `LocalStore` is configured, the ingest service records each load into the cache, storing source-unit metadata and the checksum so subsequent sessions can reconcile reused files with their provenance bundle.【F:app/services/data_ingest_service.py†L61-L83】

## Cache strategy

- `LocalStore` resolves a platform-specific data directory (`%APPDATA%`, `~/Library/Application Support`, or `~/.local/share`) before persisting artefacts, which keeps cached spectra consistent across operating systems.【F:app/services/store.py†L20-L46】
- Cached entries merge metadata from repeated ingests, capture unit annotations, and stamp creation/update timestamps to maintain a single source of truth for each checksum.【F:app/services/store.py†L68-L120】
- Binary content is deduplicated by hashing the stored copy and placing it under `data/files/<sha256 prefix>`, preventing cache bloat when multiple manifests reference the same spectrum.【F:app/services/store.py†L121-L134】

## Remote services

- `RemoteDataService` exposes catalogues only when their dependencies are present (`requests` for NIST and `astroquery` for MAST), reporting actionable error messages when packages are missing.【F:app/services/remote_data_service.py†L94-L116】
- NIST searches translate legacy `text` queries into the `spectra` parameter and fall back to sensible identifiers, ensuring line-list downloads succeed even when API payloads are sparse.【F:app/services/remote_data_service.py†L167-L217】
- MAST requests default to calibrated spectroscopic products (`dataproduct_type="spectrum"`, `intentType="SCIENCE"`, `calib_level=[2, 3]`) and drop non-spectroscopic rows so the remote dialog stays focused on analysis-ready assets.【F:app/services/remote_data_service.py†L219-L279】
- Downloads reuse the cache when the same URI has already been fetched; otherwise the service routes through `requests` or `astroquery.Observations.download_file`, persists the payload via `LocalStore`, and records provider metadata so re-ingest flows honour provenance.【F:app/services/remote_data_service.py†L127-L164】【F:app/services/remote_data_service.py†L281-L320】
