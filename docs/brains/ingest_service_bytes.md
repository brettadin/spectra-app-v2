# In-memory ingest — `DataIngestService.ingest_bytes`

Purpose: Enable direct ingestion of spectra from byte buffers without requiring a user-managed file save, while preserving LocalStore provenance.

Interface
- `ingest_bytes(content: bytes, suggested_name: str | None = None, extension: str | None = None) -> List[Spectrum]`
- Resolves the file type via `extension` or `suggested_name` suffix, writes to a temp file with that suffix, and delegates to `ingest(Path)`.

Why
- Supports “Quick Plot” experiences from remote sources (MAST/NIST/Exo.MAST) and programmatic ingestion in tests or agents.

Behavior
- Uses existing importers (CSV/FITS/JCAMP), unit normalization, and LocalStore recording.
- Temp file is removed after ingest; LocalStore copy persists as the canonical cache.

How to extend/test
- Add `RemoteDataService.fetch_bytes(record)` that returns `(bytes, suggested_name)` and call `ingest_bytes`.
- Unit-test: craft small CSV/JCAMP bytes and assert spectra are returned with expected units and metadata.

See also
- `remote_data_pipeline.md`
- `mast_download_fallback.md`

Change log
- 2025-10-22: Initial introduction of `ingest_bytes` with suffix inference and temp-file delegation.
