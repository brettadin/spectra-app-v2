# Workplan — Batch 1 (2025-10-14)

- [x] Seed tiny fixtures for tests (`tests/data/mini.*`).
- [x] Lock in unit round-trip behavior (`tests/test_units_roundtrip.py`).
- [x] Implement local store service and cache index tests.
- [x] Ensure provenance export emits manifest bundle.
- [x] Guard plot performance with LOD cap test.
- [x] Update user and developer documentation (importing + ingest pipeline).
- [x] Run lint/type/test suite locally; confirm CI configuration.
- [x] Smoke-check app launch, CSV/FITS ingest, unit toggle, export manifest (automated in tests/test_smoke_workflow.py).

## Batch 1 QA Log

- 2025-10-14: ✅ `ruff check app tests`
- 2025-10-14: ✅ `mypy app --ignore-missing-imports`
- 2025-10-14: ✅ `pytest -q --maxfail=1 --disable-warnings`
- 2025-10-14: ✅ `pip install -r requirements.txt`
- 2025-10-14: ✅ `ruff check app tests`
- 2025-10-14: ✅ `mypy app --ignore-missing-imports`
- 2025-10-14: ⚠️ `pytest -q --maxfail=1 --disable-warnings --cov=app --cov-report=term-missing` (fails: coverage plugin unavailable in test harness)
- 2025-10-14: ✅ `pytest -q --maxfail=1 --disable-warnings`

# Workplan — Batch 2 (2025-10-14)

- [x] Close out Batch 1 smoke-check (launch app, ingest CSV/FITS, toggle units, export manifest).
- [x] Capture current state of CI gates (ruff, mypy, pytest) on the latest branch.
- [x] Inventory pending documentation deltas required before next feature work. (See `docs/reviews/doc_inventory_2025-10-14.md`.)

## Batch 2 QA Log

- 2025-10-14: ✅ `ruff check app tests`
- 2025-10-14: ✅ `mypy app --ignore-missing-imports`
- 2025-10-14: ❌ `pytest -q --maxfail=1 --disable-warnings --cov=app --cov-report=term-missing` (fails: pytest-cov plugin missing)
- 2025-10-14: ✅ `pytest -q --maxfail=1 --disable-warnings`

# Workplan — Batch 3 (2025-10-14)

- [x] Draft user quickstart walkthrough covering launch → ingest → unit toggle → export.
- [x] Author units & conversions reference with idempotency callouts (`docs/user/units_reference.md`).
- [ ] Document plot interaction tools and LOD expectations.
- [ ] Expand importing guide with provenance export appendix.

## Batch 3 QA Log

- 2025-10-14: ✅ `pytest -q`
