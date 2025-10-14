# Workplan — Batch 1 (2025-10-14)

- [x] Seed tiny fixtures for tests (`tests/data/mini.*`).
- [x] Lock in unit round-trip behavior (`tests/test_units_roundtrip.py`).
- [x] Implement local store service and cache index tests.
- [x] Ensure provenance export emits manifest bundle.
- [x] Guard plot performance with LOD cap test.
- [x] Update user and developer documentation (importing + ingest pipeline).
- [x] Run lint/type/test suite locally; confirm CI configuration.
- [ ] Smoke-check app launch, CSV/FITS ingest, unit toggle, export manifest.

## Batch 1 QA Log

- 2025-10-14: ✅ `ruff check app tests`
- 2025-10-14: ✅ `mypy app --ignore-missing-imports`
- 2025-10-14: ✅ `pytest -q --maxfail=1 --disable-warnings`
- 2025-10-15: ✅ `pip install -r requirements.txt`
- 2025-10-15: ✅ `ruff check app tests`
- 2025-10-15: ✅ `mypy app --ignore-missing-imports`
- 2025-10-15: ⚠️ `pytest -q --maxfail=1 --disable-warnings --cov=app --cov-report=term-missing` (fails: coverage plugin unavailable in test harness)
- 2025-10-15: ✅ `pytest -q --maxfail=1 --disable-warnings`
