# Samples Directory Cleanup Analysis
**Date**: 2025-11-12  
**Branch**: clean-up-v2

## 📊 Current Structure & Sizes

### Total Size: 529 MB

| Directory | Size (MB) | Files | Issues |
|-----------|-----------|-------|--------|
| `solar_system/` | 428.88 | Many | **404MB HDF file!, PDFs, redundant CSVs** |
| `laboratory/` | 58.35 | Many | Needs audit |
| `fits data/` | 41.37 | Many | Needs organization |
| `exoplanets/` | 0.10 | 7 | OK (small CSVs) |
| `calibration_standards/` | 0.00 | 0 | Empty directory |
| `test_fixtures/` | 0.00 | Few | OK (small test files) |

---

## 🔥 Major Issues Found

### 1. Huge HDF File (404 MB!)
**File**: `samples/solar_system/earth/MOD09.A2025305.1535.061.2025307155046.hdf`
- **Size**: 403.9 MB (76% of total samples directory!)
- **Type**: MODIS satellite data (Earth observation)
- **Issue**: This is a full satellite granule, way too large for a sample
- **Action**: DELETE or move to storage/curated with warning note

### 2. Jupiter DAT File (26 MB)
**File**: `samples/solar_system/jupiter/t790105.dat`
- **Size**: 26.9 MB
- **Type**: Spectral dataset
- **Action**: Move to storage/curated (large demo data)

### 3. Mercury VIRS File (7.7 MB)
**File**: `samples/solar_system/mercury/virsvd_mf1_08014_191254.dat`
- **Size**: 7.7 MB
- **Type**: MESSENGER MASCS data
- **Action**: Move to storage/curated

### 4. PDFs in Samples (200+ KB each)
- `earth/Calibrated UV-Visible and Infrared Earth Spectral Datasets.pdf` (123 KB)
- `jupiter/Spectral Datasets for Jupiter's Atmosphere.pdf` (80 KB)
- **Issue**: Reference PDFs don't belong in samples/ (should be in docs/ or external links)
- **Action**: Move to `docs/reference_sources/` or link to external URLs

### 5. Empty/Redundant Directories
- `calibration_standards/` — Empty, delete
- Duplicate/mock files in earth/ (earth_modis vs mock_MODIS)

---

## 🎯 Proposed Cleanup

### Keep in samples/ (Small demos)
**Target: <5 MB total**

```
samples/
├── README.md (update with pointer to storage/curated)
├── sample_spectrum.csv (basic UV-Vis demo)
├── sample_transmittance.csv (basic IR demo)
├── sample_manifest.json (provenance example)
├── test_fixtures/ (unit test files only)
│   └── *.csv (small fixtures <100KB each)
└── exoplanets/ (7 small CSV tables, 0.1 MB total)
    └── table_*.csv
```

### Move to storage/curated/
**Large demo datasets that users can fetch on-demand**

```
storage/curated/
├── README.md (index with sizes, descriptions, how to use)
├── solar_system/
│   ├── earth/
│   │   └── MOD09...hdf (404 MB) ⚠️ WITH WARNING
│   ├── jupiter/
│   │   └── t790105.dat (27 MB)
│   ├── mercury/
│   │   └── virsvd_*.dat (8 MB)
│   └── uranus/, neptune/, etc. (smaller files OK)
├── laboratory/ (58 MB)
│   └── (audit and organize by instrument/type)
└── fits_data/ (41 MB)
    └── (organize by source/mission)
```

### Move to docs/reference_sources/
**Reference PDFs and papers**
```
docs/reference_sources/
├── planetary_spectra/
│   ├── earth_uv_vis_ir_datasets.pdf
│   └── jupiter_atmosphere_spectra.pdf
└── (or just add URLs to docs/link_collection.md)
```

### Delete
- `samples/calibration_standards/` (empty)
- `samples/solar_system/earth/mock_MODIS_reflectance_sample.csv` (if redundant with real data)
- `samples/solar_system/earth/11 7 notes.md` (internal notes, move to worklog if needed)

---

## 📋 Detailed File-by-File Actions

### Solar System (428 MB → Move most to storage/curated)

| File/Dir | Size | Keep/Move/Delete | Reason |
|----------|------|------------------|--------|
| `1995high.tab` | 195 KB | Move → curated | Reference spectrum |
| `1995low.tab` | 99 KB | Move → curated | Reference spectrum |
| `1995high.lbl`, `1995low.lbl` | 8-10 KB | Move → curated | Labels for above |
| `manifest.json` | 3 KB | Keep | Example manifest |
| `README.md` | 3 KB | Keep + update | Point to curated/ |
| `earth/MOD09...hdf` | **404 MB** | Delete or curated + warn | **Huge file!** |
| `earth/*.pdf` | 123 KB | Move → docs/reference_sources | Papers |
| `earth/earth_modis_reflectance_example.csv` | 0.1 KB | Keep as sample | Tiny |
| `earth/mock_MODIS_reflectance_sample.csv` | 1 KB | Delete if dup | Check redundancy |
| `earth/11 7 notes.md` | 12 KB | Delete/archive | Internal notes |
| `jupiter/*.dat` | 27 MB | Move → curated | Large |
| `jupiter/*.pdf` | 80 KB | Move → docs/reference | Papers |
| `jupiter/*.lbl` | 2 KB | Move → curated | Metadata |
| `mercury/*.dat` | 8 MB | Move → curated | Large |
| `uranus/*` | ? | Audit individually | TBD |

### Laboratory (58 MB → Audit needed)
**Action**: Check contents, organize by instrument type, move large files to curated
- CO₂ reference spectra?
- Background/calibration runs?
- Need to see what's actually useful vs clutter

### FITS Data (41 MB → Organize)
**Action**: Keep small FITS examples (<1 MB each), move large ones to curated
- Probably stellar standards, calibration stars
- Check if duplicates with other sources

### Exoplanets (0.1 MB → KEEP)
✅ Already small CSV tables, perfect for samples/

### Test Fixtures (tiny → KEEP)
✅ Small unit test files, essential for pytest

---

## 🔧 Implementation Steps

### Phase 3A: Samples Cleanup (Pre-approval)

1. **Audit laboratory/ contents**
   ```pwsh
   Get-ChildItem -Path "samples\laboratory" -File -Recurse | 
     Select Name, @{N="SizeKB";E={[math]::Round($_.Length/1KB,2)}} | 
     Sort SizeKB -Desc | Format-Table
   ```

2. **Audit fits data/ contents**
   ```pwsh
   Get-ChildItem -Path "samples\fits data" -File -Recurse | 
     Select Name, @{N="SizeKB";E={[math]::Round($_.Length/1KB,2)}} | 
     Sort SizeKB -Desc | Format-Table
   ```

3. **Present detailed file-by-file list** for manual approval

### Phase 3B: Execute Cleanup (Post-approval)

1. Create `storage/curated/` structure
2. Move large files with `git mv` (preserve history)
3. Update `samples/README.md` with pointers
4. Delete empty dirs and redundant files
5. Update code/docs referencing samples paths
6. Test that pytest still finds test_fixtures

---

## ✅ Success Metrics

### Space Savings:
- **Before**: samples/ = 529 MB
- **After**: samples/ < 5 MB, storage/curated/ = ~524 MB
- **Reduction**: 99% smaller samples/ (lightweight clone)

### Organization:
- Clear separation: small demos vs large datasets
- Easy to find small examples for quickstart
- Large data optional (documented in curated/README.md)

### Tests:
- `test_fixtures/` unchanged (tests still pass)
- `exoplanets/` unchanged (small enough to keep)
- Larger datasets documented but not required for basic tests

---

**Next**: Run audits of laboratory/ and fits data/, then present complete file-by-file list for approval before moving anything.
