# 2025-10-31 - PDS Downloader Refinement and Issue Documentation

## Session Context

This worklog documents changes made to the PDS downloader tool (`tools/pds_downloader_native.py`) and issues encountered during testing. The goal was to tighten download criteria to ensure downloaded MESSENGER MASCS data is comparable and relevant for spectroscopic research.

## Changes Made

### 1. URL Refinement for Specific Datasets

**What**: Updated dataset URLs to point directly to specific data product directories
**Why**: To avoid downloading unnecessary metadata, documentation, and non-science files
**Where**: `DATASETS` dictionary in `tools/pds_downloader_native.py`

**Changes**:
- `uvvs_cdr`: Changed from `.../data/` to `.../data/cdr/uvvs/` (more specific path)
- `virs_cdr`: Changed from `.../data/` to `.../data/cdr/` (pointing to CDR directory)
- Replaced `uvvs_edr` and `virs_edr` with `uvvs_ddr` and `virs_ddr` (switched from raw EDR to derived DDR products)

**Rationale**: DDR (Derived Data Record) products provide:
- Binned, high-quality surface reflectance data
- Better signal-to-noise ratio than raw EDR files
- More suitable for comparative spectroscopy studies
- Smaller file sizes (~500 MB for UVVS DDR vs ~1 GB for UVVS EDR)

### 2. Added File Pattern Filtering

**What**: Implemented `required_patterns` and `exclude_patterns` filtering
**Why**: To download only science data files, excluding headers, engineering data, and metadata
**Where**: `PDSDownloader.__init__()` and new `should_download_file()` method

**Filter Patterns Added**:

#### UVVS CDR
- **Required patterns**: `["ufc_", "umc_", "uvc_"]` - UVVS CDR science files only
  - `ufc_` = FUV (Far-UV) channel files
  - `umc_` = MUV (Mid-UV) channel files  
  - `uvc_` = VIS (Visible) channel files
- **Exclude patterns**: `["_hdr.dat", "_eng.dat", "index", "catalog"]`

#### VIRS CDR
- **Required patterns**: `["vnc_", "vvc_"]` - VIRS CDR science files only
  - `vnc_` = NIR (Near-Infrared) channel files
  - `vvc_` = VIS (Visible) channel files
- **Exclude patterns**: `["_hdr.dat", "_eng.dat", "index", "catalog"]`

#### UVVS DDR
- **Required patterns**: `["uvs_", "uvd_"]` - UVVS DDR science files
- **Exclude patterns**: `["_eng.dat", "index", "catalog"]`

#### VIRS DDR
- **Required patterns**: `["vnd_", "vvd_"]` - VIRS DDR science files
- **Exclude patterns**: `["_eng.dat", "index", "catalog"]`

**Implementation Details**:
- Case-insensitive matching (converts to lowercase before checking)
- Must match at least ONE required pattern
- Must NOT match ANY exclude pattern
- Tracks filtered files separately in `self.filtered_count`

### 3. Enhanced Descriptions with Wavelength Ranges

**What**: Added specific wavelength coverage to dataset descriptions
**Why**: To help users understand what spectral range each dataset covers
**Where**: `description` field in `DATASETS` dictionary

**Wavelength Ranges Added**:
- **UVVS CDR**: 
  - FUV: 115-190 nm (Far-UV)
  - MUV: 160-320 nm (Mid-UV)
  - VIS: 250-600 nm (Visible)
- **VIRS CDR**:
  - VIS: 300-1050 nm (Visible to Near-IR)
  - NIR: 850-1450 nm (Near-Infrared)
- **UVVS DDR**: "UVVS derived surface reflectance (binned, high quality)"
- **VIRS DDR**: "VIRS derived surface reflectance (high quality)"

### 4. Improved Summary Reporting

**What**: Added filtered file count to download summary
**Why**: To track how many files were excluded by the new pattern filters
**Where**: `PDSDownloader.run()` summary output

**Output Example**:
```
Files downloaded: 0
Files skipped (existing): 0
Files filtered (non-MASCS/engineering): 42
Total size: 0.00 GB
```

## Issues Encountered

### 404 Error on UVVS CDR URL

**Command Executed**:
```bash
python tools/pds_downloader_native.py --dataset uvvs_cdr --output-dir "samples\SOLAR SYSTEM\Mercury_test" --max-size 0.5 --dry-run
```

**Error Message**:
```
❌ Error scanning https://pds-geosciences.wustl.edu/messenger/mess-e_v_h-mascs-3-uvvs-cdr-caldata-v1/messmas_1001/data/cdr/uvvs: 404 Client Error: Not Found for url: https://pds-geosciences.wustl.edu/messenger/mess-e_v_h-mascs-3-uvvs-cdr-caldata-v1/messmas_1001/data/cdr/uvvs
```

**Analysis**:
- The updated URL path may be incorrect or the directory structure has changed
- The PDS Geosciences node may have reorganized the MESSENGER MASCS archive
- The dataset size estimate of ~2 GB was shown but no files were found

**Next Steps to Investigate**:
1. Verify the correct URL structure by browsing the PDS Geosciences website manually
2. Check if the path should be `/data/uvvs/` instead of `/data/cdr/uvvs/`
3. Consult PDS documentation for MESSENGER MASCS data archive structure
4. Consider using the PDS API or query interface to locate the correct data paths
5. Test with the original broader URL (`.../data/`) to see if files are in a different subdirectory

## Recommendations for Future Work

### Short-term
1. **Verify PDS URLs**: Manually browse the PDS archive to confirm the correct directory structure
2. **Test Alternative Paths**: Try variations like:
   - `https://...messmas_1001/data/uvvs/` (without 'cdr' subdirectory)
   - `https://...messmas_1001/data/cdr/` (one level up)
3. **Add URL Validation**: Enhance the downloader to test URLs before starting the crawl
4. **Improve Error Messages**: Provide suggestions when 404 errors occur

### Medium-term
1. **Create URL Discovery Tool**: Build a script to automatically find the correct data directories
2. **Add Archive Versioning**: Track which archive version/revision is being used
3. **Document Archive Changes**: Keep a log of when PDS reorganizes data so URLs can be updated
4. **Add Resume Capability**: Allow interrupted downloads to resume from where they stopped

### Long-term
1. **Integrate with PDS API**: Use official PDS APIs for more reliable data access
2. **Add Data Quality Checks**: Validate downloaded files against checksums
3. **Create Automated Tests**: Set up CI to periodically test PDS URLs and alert when they break
4. **Build Metadata Parser**: Extract and store provenance metadata from .LBL files

## Technical Details

### File Naming Conventions (MESSENGER MASCS)

Based on the filter patterns, MASCS science files follow these naming conventions:

**UVVS (UV-Visible Spectrometer)**:
- `ufc_*.dat` - FUV channel (Far-UV, 115-190 nm)
- `umc_*.dat` - MUV channel (Mid-UV, 160-320 nm)
- `uvc_*.dat` - VIS channel (Visible, 250-600 nm)

**VIRS (Visible-Infrared Spectrograph)**:
- `vnc_*.dat` - NIR channel (Near-IR, 850-1450 nm)
- `vvc_*.dat` - VIS channel (Visible, 300-1050 nm)

**Files to Exclude**:
- `*_hdr.dat` - Header files (metadata only)
- `*_eng.dat` - Engineering/housekeeping data
- `index*` - Index files
- `catalog*` - Catalog files

### Code Architecture Notes

The refactored `should_download_file()` method now implements a three-stage filter:
1. **File type check** (`.DAT`, `.LBL`, `.FMT`)
2. **Required pattern check** (must match at least one)
3. **Exclude pattern check** (must match none)

This design allows for:
- Fine-grained control over what gets downloaded
- Easy addition of new datasets with different naming conventions
- Clear separation between "what we want" and "what we don't want"
- Visibility into filtering decisions via `filtered_count`

## Related Files

- `tools/pds_downloader_native.py` - Main downloader script (modified)
- `tools/pipeline_master.py` - Pipeline orchestration (may need updates)
- `tools/parse_messenger_mascs.py` - MASCS data parser (may need DDR format support)
- `docs/Telescope-Based Planetary datasets.md` - Reference documentation for MESSENGER data sources

## References

- [MESSENGER MASCS UVVS CDR Archive](https://pds-geosciences.wustl.edu/messenger/mess-e_v_h-mascs-3-uvvs-cdr-caldata-v1/)
- [MESSENGER MASCS VIRS CDR Archive](https://pds-geosciences.wustl.edu/messenger/mess-e_v_h-mascs-3-virs-cdr-caldata-v1/)
- [PDS Geosciences Node](https://pds-geosciences.wustl.edu/)
- PDS Data Standards and File Naming Conventions (need to locate specific document)
