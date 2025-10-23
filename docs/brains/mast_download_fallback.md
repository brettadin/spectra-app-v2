# MAST download fallback — astroquery → direct HTTP

Purpose: Ensure robust downloads from MAST when the astroquery path stalls or returns empty files.

Context
- Primary path: `RemoteDataService._fetch_via_mast` uses `astroquery.mast.Observations.download_file` to a temp directory, then copies to a persistent temp file.
- Problem: Rare stalls / 0% progress or zero-byte files were observed in some environments.

Fallback
- If the copied file is empty (size <= 0), switch to direct HTTP using the public MAST Download API:
  `GET https://mast.stsci.edu/api/v0.1/Download/file?uri=mast:...`
- Stream with a timeout and chunked writes to a temp file; infer a reasonable suffix; return that path.

Files & functions
- `app/services/remote_data_service.py`
  - `_fetch_via_mast(record)` — primary astroquery path with temp-dir isolation
  - `_fetch_via_mast_direct(mast_uri)` — fallback via HTTP

How to test
- Choose a `mast:` product URI from search results.
- Simulate failure by forcing the astroquery branch to create an empty file and confirm the fallback retrieves a non-empty file.
- Ensure LocalStore records the file and ingest succeeds.

See also
- `remote_data_pipeline.md`
- `ingest_service_bytes.md`

Change log
- 2025-10-22: Added fallback to direct API with timeouts and streaming write, plus persistent temp copy and cleanup.
