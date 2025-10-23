# Remote Data Pipeline — search → select → download → ingest → plot

Purpose: Describe how the Remote Data feature searches catalogues, renders results, downloads files, ingests spectra, and plots them, including failure handling.

Components
- UI: `app/ui/remote_data_dialog.py`
- Service: `app/services/remote_data_service.py`
- Ingest: `app/services/data_ingest_service.py`
- Store: `app/services/store.py`

Flow
1) Search
   - Provider: MAST, ExoSystems (MAST+Exoplanet Archive), NIST
   - Worker `_SearchWorker` streams results; UI updates are non-blocking
2) Filter/Preview
   - User filters (All/Spectra/Images/Other); preview shows metadata and citations
3) Download & Import
   - Worker `_DownloadWorker` downloads via `RemoteDataService.download`
   - Non-spectral files (images/logs/etc.) are skipped with a clear message
4) Ingest
   - `DataIngestService.ingest(path)` resolves an importer (CSV/FITS/JCAMP) and normalizes units via `UnitsService`
   - `LocalStore.record()` persists the source and updates an index entry
5) Plot
   - Main window adds the resulting `Spectrum` objects to `OverlayService` and refreshes the plot

Reliability and Fallbacks
- Threading: cleanup via `QTimer.singleShot` to avoid blocking waits
- MAST: downloads to an isolated temp dir; persistent temp copy used for ingest
- MAST fallback: if astroquery returns an empty file, fallback to direct HTTP: `https://mast.stsci.edu/api/v0.1/Download/file?uri=mast:...`
- NIST: CSV generated locally from line results; cached via a pseudo-URI for uniqueness

See also
- `mast_download_fallback.md` (empty-file handling and direct HTTP path)
- `ingest_service_bytes.md` (in-memory ingest for streaming/quick plot)
- `nist_threading.md` (main-thread UI updates, signal wiring)

Change log
- 2025-10-22: Added filters, selection guards, and non-blocking worker cleanup; reworked MAST temp handling and fallback; non-spectral skip; improved status messages.
