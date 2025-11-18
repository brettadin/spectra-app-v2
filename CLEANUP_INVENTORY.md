# Repository Cleanup Inventory & Mapping
**Branch**: `clean-up-v2`  
**Date**: 2025-11-12

## 📋 Root-Level Files Requiring Action

### ✅ Keep (Essential)
- `.gitattributes`, `.gitignore`, `.github/` — Git configuration
- `README.md` — Primary documentation entry
- `requirements.txt`, `environment.yml`, `pyproject.toml` — Dependencies
- `RunSpectraApp.cmd`, `RunSpectraApp_Conda.cmd` — Launch scripts
- `sitecustomize.py` — Bootstrap numpy installer
- `pyrightconfig.json` — Type checking config
- `AGENTS.md`, `START_HERE.md`, `CONTRIBUTING.md`, `SECURITY.md` — Core docs
- `actual clean up.md` — This cleanup plan (temporary working doc)

### 🔄 Move to docs/
**Root planning docs → docs/reviews/ or docs/history/**

| Current Location | Target | Reason |
|-----------------|--------|--------|
| `goals.txt` | `docs/reviews/goals.md` | Active planning doc; convert to MD |
| `HOUSEKEEPING_PLAN.md` | Merge into `docs/reviews/cleanup_consolidation_plan.md` | Superseded by this cleanup |
| `IMPLEMENTATION_SUMMARY.md` | `docs/history/implementation_summary.md` | Historical recap |
| `IR_EXPANSION_SUMMARY.md` | `docs/history/ir_expansion_summary.md` | Historical recap |
| `NORMALIZATION_VERIFICATION.md` | `docs/dev/normalization_verification.md` | Developer QA doc |
| `AUDIT_REPORT.md` | `docs/history/audit_report_2025-11-04.md` | Historical snapshot |

### 🗑️ Delete (Obsolete)
| File | Reason |
|------|--------|
| `patch.patch` | Abandoned patch file; superseded by git history |
| `test_history.md` | Unclear purpose; likely superseded by proper tests |
| `__pycache__/` (root) | Python cache; should be in .gitignore |

### 🧪 Move to tests/
**Root test files → tests/**

| Current | Target | Purpose |
|---------|--------|---------|
| `test_exoplanet_manual.py` | `tests/manual/test_exoplanet_manual.py` | Manual integration test |
| `test_global_normalization.py` | `tests/manual/test_global_normalization.py` | Manual test |
| `test_math_operations.py` | `tests/manual/test_math_operations.py` | Manual test |
| `test_modis_logic.py` | `tests/manual/test_modis_logic.py` | Manual test |
| `test_normalization_debug.py` | `tests/manual/test_normalization_debug.py` | Debug/manual test |
| `test_qt_simple.py` | `tests/manual/test_qt_simple.py` | Simple Qt test |
| `test_spex_manual.py` | `tests/manual/test_spex_manual.py` | Manual test |

**Note**: These appear to be manual/integration tests rather than automated unit tests, so placing in `tests/manual/` subdirectory.

---

## 📂 Directory Consolidation

### Phase 2: Storage Reorganization

**downloads/ → storage/cache/**
- **Current**: `downloads/` with subdirs `files/`, `_cache/`, `_incoming/`, `index.json`
- **Target**: `storage/cache/` (preserve structure)
- **Purpose**: Cached remote downloads from MAST/NIST
- **Code Impact**: 
  - Path alias already exists: `storage://cache` in `app/utils/path_alias.py`
  - Update `LocalStore` default path in `app/services/store.py`
  - Update `RemoteDataService` references
  - Update `LineListCache` references
- **Docs Impact**: Update `docs/user/remote_data.md`, `docs/user/importing.md`

**exports/ → storage/exports/**
- **Current**: `exports/` with various exported manifests/CSVs/PNGs
- **Target**: `storage/exports/` (preserve structure)
- **Purpose**: User-generated export bundles
- **Code Impact**:
  - Add `storage://exports` alias to path_alias.py
  - Update default export location in `ProvenanceService`
  - Update file dialog defaults in main_window.py
- **Docs Impact**: Update `docs/user/plot_tools.md` export section

### Phase 3: Tests & Samples

**samples/ large datasets → storage/curated/**
- **Current**: `samples/` has multiple subdirs with test fixtures and demo data
- **Keep in samples/**: 
  - `README.md`
  - `sample_spectrum.csv`, `sample_transmittance.csv`, `sample_manifest.json`
  - `test_fixtures/` (small files for unit tests)
- **Move to storage/curated/**:
  - `calibration_standards/` (if large)
  - `exoplanets/` (if large)
  - `fits data/` (if large)
  - `laboratory/` (if large)
  - `solar_system/` (large manifests/spectra)
- **Code Impact**: Update test imports if needed
- **Docs Impact**: Update `docs/user/quickstart.md`, `README.md`

### Phase 4: Documentation Taxonomy

**specs/ → docs/specs/**
- **Current**: Root-level `specs/` directory
- **Target**: Merge into existing `docs/specs/`
- **Files**: `architecture.md`, `packaging.md`, `plugin_dev_guide.md`, `provenance_schema.md`, `system_design.md`, `testing.md`, `ui_contract.md`, `units_and_conversions.md`
- **Action**: Check for duplicates with `docs/specs/` then merge or consolidate
- **Impact**: Update all cross-references in docs

**reports/ → docs/**
- **Current**: `reports/` with historical progress, audits, feature matrices
- **Target**: Distribute based on content type

| Current File | Target Location | Type |
|--------------|----------------|------|
| `AUDIT_REPORT.md` | `docs/history/audit_report_2025-11-04.md` | Historical |
| `state_of_repo_2025-11-04.md` | `docs/history/state_of_repo_2025-11-04.md` | Historical |
| `bugs_and_issues.md` | `docs/reviews/bugs_and_issues.md` | Active tracking |
| `risk_register.md` | `docs/reviews/risk_register.md` | Active tracking |
| `roadmap.md` | `docs/reviews/roadmap.md` | Planning |
| `developer_notes.md` | `docs/dev/developer_notes_archive.md` | Dev reference |
| `feature_parity_*.md`, `m1_*.md`, `milestone1_progress.md` | `docs/history/milestones/` | Historical milestones |
| `naming_and_logs.md` | `docs/dev/naming_and_logs.md` | Dev guidance |
| `repo_audit.md` | `docs/history/repo_audit.md` | Historical |
| `logs/` subdirectory | `docs/history/logs/` or delete if redundant | Archive |
| `runtime.log` | Delete (runtime artifact) | Temporary |

---

## 🔧 Code References to Update

### Files referencing old paths:
1. **app/services/store.py** — `LocalStore` default base_dir
2. **app/services/remote_data_service.py** — Download cache location
3. **app/services/line_list_cache.py** — NIST cache location
4. **app/ui/main_window.py** — Export dialog defaults, download directory
5. **tests/** — Various test fixtures and paths
6. **docs/** — User guides mentioning downloads/exports

### Path Alias Updates Needed:
- ✅ `storage://cache` already exists
- ➕ Add `storage://exports`
- ➕ Add `storage://curated` (optional, for future)

---

## 📝 Documentation Updates Required

### Primary Docs:
- `docs/INDEX.md` — Update all paths/structure
- `docs/user/importing.md` — Cache location references
- `docs/user/remote_data.md` — Download location
- `docs/user/plot_tools.md` — Export location
- `docs/user/quickstart.md` — Sample data locations
- `README.md` — Getting started paths

### Dev Docs:
- `docs/dev/reference_build.md` — Data paths
- `docs/developer_notes.md` — If it references old structure
- `AGENTS.md` — Path conventions
- `START_HERE.md` — Directory overview

### Add Redirect Stubs:
- `docs/specs/MOVED.md` → "Content merged into docs/specs/"
- `reports/MOVED.md` → "Content distributed to docs/history/ and docs/reviews/"

---

## ✅ Verification Checklist

After each phase:
- [ ] Run `pytest -q --maxfail=1`
- [ ] Run headless smoke: `$env:QT_QPA_PLATFORM="offscreen"; pytest -q tests/test_smoke_workflow.py`
- [ ] Manual launch: `python -m app.main`
- [ ] Test Light/Dark theme switch
- [ ] Test import from samples
- [ ] Test remote data fetch (if applicable)
- [ ] Test export manifest
- [ ] Verify no broken doc links
- [ ] Update PATCH_NOTES.md with timestamp
- [ ] Update knowledge log if significant

---

## 🎯 Execution Order

1. **Phase 2: Storage** (downloads → storage/cache, exports → storage/exports)
2. **Phase 3: Tests** (root test_*.py → tests/manual/)
3. **Phase 3: Samples** (large datasets → storage/curated)
4. **Phase 4: Docs** (specs → docs/specs, reports → docs/*)
5. **Phase 4: Root docs** (stray .md files → appropriate docs/ locations)
6. **Phase 5: Cleanup** (delete patch.patch, __pycache__, test_history.md)
7. **Phase 6: Verification** (full test suite, manual smoke, docs review)

---

## 💾 Estimated Changes

- **Files to move**: ~35
- **Files to delete**: ~3
- **Code files to update**: ~10
- **Doc files to update**: ~15
- **New redirect stubs**: ~2
- **Total estimated LOC impact**: 200-300 (within PR limit)

---

**Next Step**: Review this inventory and approve Phase 2 (storage consolidation) to proceed.
