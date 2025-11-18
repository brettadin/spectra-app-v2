# 🚨 Manual Approval Required: File-by-File Cleanup Plan
**Date**: 2025-11-12  
**Branch**: clean-up-v2

---

## Quick Summary

| Category | Current | After Cleanup | Space Saved |
|----------|---------|---------------|-------------|
| **samples/** | 529 MB | < 5 MB | **524 MB (99%)** |
| **downloads/** | 69 MB | → storage/cache | (relocated) |
| **exports/** | 8 MB | → storage/exports | (relocated) |
| **Root test files** | 7 files | → tests/manual | (organized) |
| **Root docs** | 6 files | → docs/* | (organized) |
| **reports/** | 15 files | → docs/* | (distributed) |

**Total repo size reduction: ~500 MB** (from committed samples)

---

## Phase 2: Storage Moves (downloads/ & exports/)

### Action: Move, Don't Delete
These are user data directories that need relocation + code updates.

| Current | New Location | Why |
|---------|--------------|-----|
| `downloads/` | `storage/cache/` | Consolidate cached remote data |
| `exports/` | `storage/exports/` | Separate user exports from cache |

**Code changes needed**:
- Add `storage://exports` alias in `app/utils/path_alias.py`
- Update `LocalStore` default path in `app/services/store.py`
- Update `RemoteDataService` cache location
- Fix duplication issue (local imports shouldn't copy to cache)
- Update docs references

✅ **Approved to proceed?** (No deletions, just moves + code updates)

---

## Phase 3: Samples Cleanup (THE BIG ONE)

### 🔴 CRITICAL: Delete Huge Files

| File | Size | Location | Action | Reason |
|------|------|----------|--------|--------|
| **MOD09.A2025305.1535.061.2025307155046.hdf** | **404 MB** | `samples/solar_system/earth/` | **DELETE** | 76% of total! Full satellite granule, not needed |  
| okay sun file.csv (2 duplicates) | 22 MB ea | `samples/laboratory/` | **DELETE 1, KEEP 1** | Duplicate |
| t790105.dat | 27 MB | `samples/solar_system/jupiter/` | Move → storage/curated | Large Jupiter spectrum |
| virsvd_mf1_08014_191254.dat | 8 MB | `samples/solar_system/mercury/` | Move → storage/curated | MESSENGER data |

❓ **Approve deletion of 404 MB HDF file?** YES 
❓ **Approve moving 35 MB of large planetary data to storage/curated?** YES

---

### 📄 PDFs: Move to docs/reference_sources/

| File | Size | Current Location | New Location |
|------|------|------------------|--------------|
| Calibrated UV-Visible and Infrared Earth Spectral Datasets.pdf | 123 KB | `samples/solar_system/earth/` | `docs/reference_sources/planetary/` |
| Spectral Datasets for Jupiter's Atmosphere.pdf | 80 KB | `samples/solar_system/jupiter/` | `docs/reference_sources/planetary/` |

❓ **Approve moving PDFs out of samples/?** YES 
*(Alternative: Just add URLs to docs/link_collection.md and delete PDFs)*

---

### 🧪 Laboratory Directory: Heavy Duplicates

**Issue**: 176 files, 58 MB total, MANY duplicates with " - Copy" or identical content

| Pattern | Count | Example | Action |
|---------|-------|---------|--------|
| Lamp spectra (22 MB sun files) | 2x duplicates | `okay sun file.csv` (x2) | Delete 1 duplicate |
| CO2/H2O runs (50+ KB each) | 10+ duplicates | Various `.csv` with " - Copy" | Delete copies |
| Background/calibration (50 KB) | 5+ duplicates | `bkgrd.csv`, `bckgr.csv`, `bkgrd A.csv` | Consolidate to 1 |
| Lamp exports (300-400 KB) | Many | Various merged/lamp CSVs | Keep representative samples |
| .sp files (30 KB spectrum binary) | Many | Various `.sp` files | Probably temp exports, delete |
| Internal notes/debris | Several | `.csv` (blank name), duplicates | Delete |

**Proposed**: Delete ~40 MB of duplicates/temp files, keep ~18 MB of unique samples

❓ **Approve aggressive duplicate cleanup in laboratory/?** YES 
*(I'll present specific file list before deleting)*

---

### 🔭 FITS Data: Stellar Library

**Issue**: 314 files, 41 MB total, mostly stellar standards (good reference data)

| Type | Count | Size | Action |
|------|-------|------|--------|
| Stellar standards (CALSPEC) | ~250 | 35 MB | Move → storage/curated (useful reference) |
| TESS lightcurves | 4 | 15 MB | DELETE (not spectroscopy) |
| Single Jupiter FITS | 1 | 42 KB | KEEP as sample |

❓ **Approve moving 35 MB of stellar standards to storage/curated?** YES  
❓ **Approve deleting 15 MB of TESS lightcurves?** YES

---

### ✅ Keep in samples/ (Small & Essential)

| File/Dir | Size | Why Keep |
|----------|------|----------|
| `README.md` | 3 KB | Explains samples |
| `sample_spectrum.csv` | ~1 KB | Basic demo |
| `sample_transmittance.csv` | ~1 KB | Basic demo |
| `sample_manifest.json` | 3 KB | Provenance example |
| `test_fixtures/` | ~100 KB | Unit test data |
| `exoplanets/` (7 tables) | 100 KB | Small reference tables |
| 1-2 representative lamp spectra | ~500 KB | Quickstart examples |

**Final samples/ size**: < 5 MB (minimal for quick clones)
 * note we should also make sure the open and sample functionality in the UI properly reflect storage locations. * 
---

## Phase 4: Root-Level Files

### Move to docs/

| Current | Target | Why |
|---------|--------|-----|
| `goals.txt` | `docs/reviews/goals.md` | Planning doc (convert to MD) |
| `HOUSEKEEPING_PLAN.md` | Merge → `docs/reviews/cleanup_consolidation_plan.md` | Superseded by this cleanup |
| `IMPLEMENTATION_SUMMARY.md` | `docs/history/implementation_summary.md` | Historical recap |
| `IR_EXPANSION_SUMMARY.md` | `docs/history/ir_expansion_summary.md` | Historical recap |
| `NORMALIZATION_VERIFICATION.md` | `docs/dev/normalization_verification.md` | Dev QA doc |
| `AUDIT_REPORT.md` | `docs/history/audit_report_2025-11-04.md` | Historical snapshot |

❓ **Approve moving 6 root docs to docs/?** YES 

---

### Move to tests/manual/

| Current | Purpose | Target |
|---------|---------|--------|
| `test_exoplanet_manual.py` | Manual exoplanet test | `tests/manual/test_exoplanet_manual.py` |
| `test_global_normalization.py` | Manual norm test | `tests/manual/test_global_normalization.py` |
| `test_math_operations.py` | Manual math test | `tests/manual/test_math_operations.py` |
| `test_modis_logic.py` | Manual MODIS test | `tests/manual/test_modis_logic.py` |
| `test_normalization_debug.py` | Debug test | `tests/manual/test_normalization_debug.py` |
| `test_qt_simple.py` | Simple Qt test | `tests/manual/test_qt_simple.py` |
| `test_spex_manual.py` | Manual SPEX test | `tests/manual/test_spex_manual.py` |

❓ **Approve moving 7 test files to tests/manual/?** YES 

---

### Delete (Obsolete)

| File | Why Delete |
|------|------------|
| `patch.patch` | Abandoned patch, superseded by git |
| `test_history.md` | Unclear purpose, likely obsolete |
| `__pycache__/` (root) | Should be in .gitignore |
| `actual clean up.md` | Temporary working doc (this cleanup) | *DO NOT DELETE YET* this was our initial plan. we should update this as we go   unless i am misunderstanding. if its specifically a temp file then i guess we can get rid of it. or if its something like "this has been moved to x location." i think theres a few lurking in the code. use your best judgment, keep in mind i am dumb :)
| `CLEANUP_INVENTORY.md` | Temporary working doc |
| `STORAGE_ANALYSIS.md` | Temporary working doc |
| `SAMPLES_ANALYSIS.md` | Temporary working doc |

❓ **Approve deleting ~6 temporary/obsolete files?** YES 

---

## Phase 5: reports/ Distribution

**Total**: 15 files in reports/

| File | Target Location | Type |
|------|----------------|------|
| `AUDIT_REPORT.md` | `docs/history/audit_report_2025-11-04.md` | Historical |
| `state_of_repo_2025-11-04.md` | `docs/history/state_of_repo_2025-11-04.md` | Historical |
| `bugs_and_issues.md` | `docs/reviews/bugs_and_issues.md` | Active tracking |
| `risk_register.md` | `docs/reviews/risk_register.md` | Active planning |
| `roadmap.md` | `docs/reviews/roadmap.md` | Planning |
| `developer_notes.md` | `docs/dev/developer_notes_archive.md` | Dev reference |
| `feature_parity_checklist.md` | `docs/history/milestones/feature_parity_checklist.md` | Historical |
| `feature_parity_matrix.md` | `docs/history/milestones/feature_parity_matrix.md` | Historical |
| `m1_feature_parity_checklist.md` | `docs/history/milestones/m1_feature_parity_checklist.md` | Historical |
| `m1_progress_report.md` | `docs/history/milestones/m1_progress_report.md` | Historical |
| `milestone1_progress.md` | `docs/history/milestones/milestone1_progress.md` | Historical |
| `naming_and_logs.md` | `docs/dev/naming_and_logs.md` | Dev guidance |
| `repo_audit.md` | `docs/history/repo_audit.md` | Historical |
| `logs/` directory | `docs/history/logs/` | Archive |
| `runtime.log` | DELETE | Temporary runtime file |

❓ **Approve distributing reports/ into docs/ structure?** YES

---

## Phase 6: Root specs/ → docs/specs/

**Current**: 8 files in root-level `specs/`

| File | Check for Duplicate | Action |
|------|---------------------|--------|
| `architecture.md` | vs `docs/specs/` | Merge if exists, else move |
| `packaging.md` | vs `docs/specs/` | Merge if exists, else move |
| `plugin_dev_guide.md` | vs `docs/specs/` | Merge if exists, else move |
| `provenance_schema.md` | vs `docs/specs/` | Merge if exists, else move |
| `system_design.md` | vs `docs/specs/` | Merge if exists, else move |
| `testing.md` | vs `docs/specs/` | Merge if exists, else move |
| `ui_contract.md` | vs `docs/specs/` | Merge if exists, else move |
| `units_and_conversions.md` | vs `docs/specs/` | Merge if exists, else move |

❓ **Approve consolidating root specs/ into docs/specs/?** YES

---

## 🎯 Summary of Approvals Needed

**Please respond with YES/NO for each:**

I HAVE DONE SO FOR EACH AS THEY WERE LISTED ABOVE.

1. ✅ Phase 2: Move downloads/ → storage/cache, exports/ → storage/exports (with code updates)
2. ❓ Delete 404 MB HDF file from samples/
3. ❓ Move 35 MB planetary data to storage/curated
4. ❓ Move PDFs to docs/reference_sources (or just link & delete)
5. ❓ Aggressive duplicate cleanup in laboratory/ (~40 MB deleted)
6. ❓ Move 35 MB stellar standards to storage/curated
7. ❓ Delete 15 MB TESS lightcurves (not spectroscopy)
8. ❓ Move 6 root docs to docs/
9. ❓ Move 7 root test files to tests/manual/
10. ❓ Delete 7 obsolete/temp files
11. ❓ Distribute reports/ into docs/ structure
12. ❓ Consolidate root specs/ into docs/specs/

---

**Once approved, I will:**
1. Execute moves with `git mv` (preserves history)
2. Update all code references
3. Update all doc cross-references
4. Run pytest after each phase
5. Document every change in PATCH_NOTES.md
6. Create redirect stubs for moved docs
7. Verify manually with `python -m app.main`

**Estimated time**: 2-3 hours of systematic work, phase by phase

---

**Ready to proceed? Please review and approve each section above.** 🎯
