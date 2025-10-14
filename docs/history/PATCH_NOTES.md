# Patch Notes

## 2025-10-14

- Added an automated smoke workflow test that instantiates the preview shell, ingests CSV/FITS data, exercises unit toggles, and exports a provenance bundle.
- Centralised the reusable FITS fixture under `tests/conftest.py` to support regression suites.
- Documented the new smoke validation loop for developers and provided a matching user checklist.
