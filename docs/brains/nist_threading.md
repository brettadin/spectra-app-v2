# NIST threading & UI safety

Purpose: Document the threading model for NIST line searches and how UI updates are kept on the main thread.

Key points
- Worker emits signals; UI slots run in the GUI thread.
- Avoid `thread.wait()` in signal handlers. Use `QTimer.singleShot(0, ...)` to schedule cleanup.
- Generate NIST CSV locally from fetched line data; connect results directly to ingest.

Files
- `app/ui/remote_data_dialog.py` — search/download workers with non-blocking cleanup
- `app/main.py` — NIST slots and dispatch; menu wiring

Symptoms fixed
- `QThread::wait: Thread tried to wait on itself` warning on close
- Occasional crash when switching filters during selection updates

See also
- `remote_data_pipeline.md`
- `mast_download_fallback.md`

Change log
- 2025-10-22: Moved cleanup to timers; added selection bounds checks; improved error surfacing.
