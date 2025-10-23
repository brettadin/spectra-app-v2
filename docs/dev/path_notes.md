# Path notes (where things live)

- Remote Data UI: `app/ui/remote_data_dialog.py`
  - Workers: `_SearchWorker`, `_DownloadWorker`
  - Filtering, preview, link rendering; non-blocking cleanup
- Remote catalogue service: `app/services/remote_data_service.py`
  - Search providers (MAST, ExoSystems, NIST)
  - Downloads (MAST via astroquery + HTTP fallback; NIST CSV generation)
- Ingest pipeline: `app/services/data_ingest_service.py`
  - Importers registry and `ingest(path)`, `ingest_bytes(content, ...)`
- Importers: `app/services/importers/*.py`
  - CSV, FITS, JCAMP; heuristics and error messages
- Units normalization: `app/services/units_service.py`
- Local cache: `app/services/store.py`
  - Stored files under `%APPDATA%/SpectraApp/data/files/<sha prefix>/`
  - `index.json` contains source, units, and timestamps
- Main window: `app/main.py`
  - Wires menu actions, plotting, overlays, provenance export
