# RUNNER PROMPT — autonomous improve/fix/add loop (safe & test-first)

**Repo:** `C:\Code\spectra-app-beta`
**Start here:** Read and follow `docs\history\MASTER PROMPT.md` as the product spec + acceptance criteria.

## 0) Mode: Continuous Improvement (CI Loop)

Operate in repeating mini-cycles:

1. **PLAN (RFC):** From `MASTER PROMPT.md` + current backlog, draft `docs\reviews\workplan.md` (checkbox list). For any non-trivial change, create `docs\rfc\RFC-YYYYMMDD-bN.md` with:

   * Problem, context, constraints
   * Proposed change (UI/UX/data/algorithms)
   * Tests you’ll add
   * Risk & rollback plan
   * Acceptance Criteria (bullet list)

2. **BRANCH:** `improve/YYMMDD-bN-shortname`.

3. **IMPLEMENT (small commits):** Keep UI contract, provenance, and performance budgets intact. Add code + tests together.

4. **TEST & CI:** Run `pytest -q`. Fix failures. CI must be green on PR.

5. **DOCS:** Update:

   * `docs/history/PATCH_NOTES.md` (what/why)
   * `docs/brains.md` (AI notes for future agents)
   * User docs under `docs/user/` if behavior changed
   * Dev docs under `docs/dev/` (APIs, pipelines)

6. **PR & MERGE:** Open PR with:

   * Link to RFC and checklists
   * “What changed / How verified / Screenshots if UI”
   * “Follow-ups” section
     Merge only when CI is green and Acceptance Criteria met.

7. **NEXT:** Append 3–5 proposed next improvements to `docs\reviews\backlog.md` with value/cost—pick the top 1–2 for the next cycle.

---

## 1) Keep Tests & CI loud

Ensure these exist (add if missing):

**`.github/workflows/ci.yml`**

```yaml
name: CI
on: [push, pull_request]
jobs:
  test:
    strategy:
      fail-fast: false
      matrix: { os: [ubuntu-latest, windows-latest], python-version: ['3.10','3.11'] }
    runs-on: ${{ matrix.os }}
    env: { QT_QPA_PLATFORM: offscreen, PIP_DISABLE_PIP_VERSION_CHECK: 1 }
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: ${{ matrix.python-version }} }
      - name: Install deps
        run: |
          python -m pip install --upgrade pip
          python -m pip install -r requirements.txt
          python -m pip install pytest pytest-cov mypy ruff
      - name: Lint & type check
        run: |
          ruff check app tests
          mypy app --ignore-missing-imports
      - name: Tests
        run: pytest -q --maxfail=1 --disable-warnings --cov=app --cov-report=term-missing
```

**`pytest.ini`**

```ini
[pytest]
addopts = -q
filterwarnings = ignore::DeprecationWarning
markers = gui
```

**Minimal test set (expand each cycle):**

* `tests/test_units_roundtrip.py` — nm/Å/µm/cm⁻¹ idempotent
* `tests/test_ingest_csv.py` — headers, units, metadata preserved
* `tests/test_ingest_fits.py` — 1D FITS path, units to nm
* `tests/test_ingest_jcamp.py` — JCAMP-DX basics
* `tests/test_differential.py` — A−B, A/B ε-guard, trivial zero suppression
* `tests/test_duplicate_guard.py` — stable labels, ledger rules
* `tests/test_provenance_manifest.py` — export includes version/units/transforms
* `tests/test_plot_perf_stub.py` — LOD cap respected (no GUI)

---

## 2) Self-Proposing Improvements (what to look for each cycle)

When planning an RFC, scan for and propose the **highest-leverage** changes that **won’t** break users:

**A. Ingest & Formats**

* Solidify CSV/TXT, FITS(1D), JCAMP-DX; add small fixtures.
* Optional next: NetCDF/HDF5 adapters behind **feature flags** (`FEATURE_NETCDF`).
* Robust header skipping, unit hints, irregular grid handling.

**B. Remote Fetchers (modular, cached)**

* NIST line lists (atomic/IR): local cache + citation bundle.
* MAST/JWST spectra: normalized metadata (obsid, instrument, wave units).
* ESO/SDSS adapters optional behind flags.
* **No live network in CI**: use mocked fixtures.

**C. Math & Analysis**

* Baseline/continuum removal, smoothing (SG), peak find/fit (Gauss/Voigt).
* Redshift/velocity offset slider, line overlays (with legend hygiene).
* Differential tools stable: ε-guard/mask, “add anyway” on trivial zero.

**D. Plot Performance & UX**

* Downsample/peak-envelope LOD (≤120k pts per trace).
* No per-curve antialias; avoid area fills for big arrays.
* Crosshair readout, unit toggle (idempotent), legend truncation + tooltip.
* Non-blocking autoscale; bulk updates when ingesting multiple traces.

**E. Provenance & Credits**

* Every transform recorded; exports include PNG/CSV + manifest JSON.
* Inline credits: source, authors, year, DOI/URL, instrument, range.

**F. Desktop Ergonomics**

* Preferences (data dir, theme, default units).
* Local data store under `%APPDATA%\SpectraApp\data` (Windows) with index JSON (SHA-256, units, provenance).
* Safe migrations with deprecation notes.

**G. Quality Gates**

* Increase coverage threshold gradually.
* Add ruff + mypy rules over time; fix highest-signal warnings first.
* UI contract test: verify required widgets/actions exist.

---

## 3) Guardrails (don’t break users)

* **Feature flags** for new/experimental features; default OFF until tested.
* **Migrations**: log schema bumps; docs on rollback.
* **Performance budgets**: keep UI responsive with 1M-point traces.
* **Data idempotency**: store canonical nm; never overwrite raw arrays.
* **Accessibility**: keyboard shortcuts, clear labels, dark/light themes.

---

## 4) Docs that evolve with the code

* `docs/user/` — Quickstart, File Types, Units & Conversions, Plot/Toolbar, Math Tools, Exports & Credits, FAQ.
* `docs/dev/` — Ingestion pipeline, Fetcher contracts, Provenance schema, Performance notes, UI contract JSON, How to add a new plugin/provider.
* `docs/edu/` — Spectroscopy primers (absorption/emission, units), stellar/planetary spectra basics, line identification, redshift, references (NIST/MAST/JWST/specutils/specviz).
* Update `docs/history/PATCH_NOTES.md` + `docs/brains.md` every batch.

---

## 5) Definition of Done (each batch)

* CI green on Windows + Ubuntu.
* New/changed features covered by tests & docs.
* UI contract intact; plot remains responsive; no regressions.
* Provenance & credits show correctly in UI and exports.
* Workplan/rfc checkboxes ticked; backlog updated with next 3–5 items.

---

## 6) Kickoff now

1. Read `docs\history\MASTER PROMPT.md`.
2. Create `docs\reviews\workplan.md` + (if needed) `docs\rfc\RFC-YYYYMMDD-b1.md`.
3. Branch `improve/YYMMDD-b1-kickoff`.
4. Implement the smallest shippable batch (ingest tests + provenance polish + one UX fix), open PR, iterate until green.
5. Repeat the CI Loop.
