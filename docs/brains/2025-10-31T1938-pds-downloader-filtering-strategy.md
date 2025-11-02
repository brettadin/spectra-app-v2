# PDS Downloader Filtering Strategy for MESSENGER MASCS Data

**Date**: 2025-10-31T19:38:48-04:00 (EDT) / 2025-10-31T23:38:48+00:00 (UTC)

**Status**: Implemented

**Context**: The PDS downloader tool needed to be refined to ensure that only relevant, high-quality spectroscopic data from MESSENGER MASCS is downloaded, rather than including engineering files, headers, and metadata that aren't useful for spectroscopic analysis.

## Problem

The original PDS downloader was too permissive in what it downloaded from the PDS Geosciences archive:
1. Downloaded raw EDR (Experimental Data Record) data when derived DDR (Derived Data Record) would be more suitable
2. Included engineering files (`_eng.dat`), headers (`_hdr.dat`), and metadata files that aren't needed for spectroscopic research
3. Lacked clear filtering criteria, making it difficult to ensure comparability of downloaded datasets
4. Used broad URL paths that resulted in scanning unnecessary directories

## Decision

Implement a **three-stage filtering system** with explicit include/exclude patterns for MESSENGER MASCS data:

### Stage 1: File Type Check
- Only allow specific file types: `.DAT` (data), `.LBL` (labels), `.FMT` (format definitions)
- These are the essential files for PDS spectroscopic data

### Stage 2: Required Patterns (Positive Filter)
- Must match at least ONE required pattern to be downloaded
- Patterns correspond to specific MASCS instrument channels and data levels
- Ensures we only get science data files, not ancillary products

### Stage 3: Exclude Patterns (Negative Filter)
- Must NOT match ANY exclude pattern
- Filters out engineering data, headers, indexes, and catalogs
- Provides additional safety against downloading non-science files

### Dataset Quality: EDR → DDR Migration
- Switch from raw EDR (Experimental Data Record) to DDR (Derived Data Record)
- DDR provides:
  - Binned, high-quality surface reflectance
  - Better signal-to-noise ratio
  - Smaller file sizes (important for storage and transfer)
  - More suitable for comparative spectroscopy studies

## Rationale

### Why Three-Stage Filtering?

1. **Defense in Depth**: Multiple filter stages provide redundancy and catch different types of unwanted files
2. **Clarity**: Separates "what we want" (required patterns) from "what we don't want" (exclude patterns)
3. **Maintainability**: Easy to add new patterns or adjust criteria for different datasets
4. **Visibility**: Each stage is documented and tracked separately (via `filtered_count`)

### Why Pattern-Based Rather Than Directory-Based?

- PDS archives don't always have consistent directory structures
- File naming conventions are more stable than directory organization
- Patterns allow for fine-grained control (e.g., selecting specific channels)
- Makes it easy to distinguish between data types (CDR vs DDR, science vs engineering)

### Why DDR Over EDR?

For educational and research comparative spectroscopy:
- **Signal Quality**: DDR has undergone calibration and noise reduction
- **Comparability**: Derived products are normalized and more suitable for cross-mission comparisons
- **Size**: Smaller files mean faster downloads and less storage (UVVS: 500MB DDR vs 1GB EDR)
- **Processing**: Less preprocessing needed before analysis

### Why Explicit Channel Selection?

MASCS instruments have multiple channels:
- **UVVS**: FUV (Far-UV), MUV (Mid-UV), VIS (Visible)
- **VIRS**: VIS (Visible), NIR (Near-Infrared)

By explicitly selecting channel file prefixes:
- Download only the wavelength ranges needed for specific research
- Avoid duplicate wavelength coverage
- Make dataset composition transparent

## Implementation Details

### MESSENGER MASCS File Naming Patterns

**UVVS (Ultraviolet-Visible Spectrometer)**:
- CDR Level:
  - `ufc_*.dat` - FUV channel (115-190 nm)
  - `umc_*.dat` - MUV channel (160-320 nm)
  - `uvc_*.dat` - VIS channel (250-600 nm)
- DDR Level:
  - `uvs_*.dat` - Derived surface reflectance
  - `uvd_*.dat` - Derived data products

**VIRS (Visible-Infrared Spectrograph)**:
- CDR Level:
  - `vvc_*.dat` - VIS channel (300-1050 nm)
  - `vnc_*.dat` - NIR channel (850-1450 nm)
- DDR Level:
  - `vvd_*.dat` - Derived surface reflectance (VIS)
  - `vnd_*.dat` - Derived surface reflectance (NIR)

**Excluded File Types**:
- `*_hdr.dat` - Header metadata (redundant with .LBL files)
- `*_eng.dat` - Engineering/housekeeping data (not spectroscopic)
- `index*` - Index files (for catalog browsing, not data)
- `catalog*` - Catalog files (descriptive, not data)

### Code Architecture

```python
def should_download_file(self, filename: str) -> bool:
    """Check if file matches our STRICT criteria."""
    fname_lower = filename.lower()
    
    # Stage 1: Must match file type
    if self.file_types and not any(filename.upper().endswith(ft) for ft in self.file_types):
        return False
    
    # Stage 2: Must match at least one required pattern (MASCS science files only)
    if self.required_patterns:
        if not any(pattern.lower() in fname_lower for pattern in self.required_patterns):
            self.filtered_count += 1
            return False
    
    # Stage 3: Must NOT match any exclude pattern (no engineering/header files)
    if self.exclude_patterns:
        if any(pattern.lower() in fname_lower for pattern in self.exclude_patterns):
            self.filtered_count += 1
            return False
    
    return True
```

Key design choices:
- **Case-insensitive matching**: PDS archives aren't always consistent with case
- **Substring matching**: Allows flexible pattern definition (e.g., `ufc_` matches `ufc_obs123.dat`)
- **Early return**: Stops checking as soon as a filter fails
- **Tracking**: Counts filtered files separately from skipped/downloaded files

## Consequences

### Positive
- **Precise Data Selection**: Only downloads science-grade spectroscopic data
- **Reduced Storage**: DDR files are smaller than EDR (60-70% reduction for UVVS)
- **Better Comparability**: Derived products are more suitable for cross-dataset analysis
- **Clear Intent**: Code explicitly documents what data is wanted and why
- **Maintainable**: Easy to add new datasets or adjust criteria
- **Visibility**: Filtered count shows how many files were excluded

### Negative
- **Requires Pattern Knowledge**: Need to know MASCS file naming conventions
- **URL Dependency**: Updated URLs may break if PDS reorganizes archives
- **Less Flexible**: Can't easily download "everything" for exploratory analysis
- **Pattern Maintenance**: Patterns must be kept up-to-date with PDS standards

### Risks
1. **URL Changes**: PDS archives may reorganize, breaking hardcoded paths
   - *Mitigation*: Document URL structure, add URL validation, consider PDS API
2. **Pattern Drift**: PDS may change naming conventions in future missions
   - *Mitigation*: Document patterns clearly, add version tracking
3. **Over-Filtering**: May exclude useful data if patterns are too restrictive
   - *Mitigation*: Track filtered count, allow override flags in future

## Alternatives Considered

### Alternative 1: Download Everything, Filter Later
**Rejected because**:
- Wastes bandwidth and storage on unused files
- Requires post-processing step that may be forgotten
- Harder to document what data is actually needed

### Alternative 2: Use PDS API for Queries
**Deferred because**:
- Requires additional dependencies (pds4-tools, etc.)
- PDS API coverage varies by archive node
- Native HTTP approach is more reliable for bulk downloads
- Can be added in future iteration

### Alternative 3: Directory-Based Filtering Only
**Rejected because**:
- PDS directory structures aren't consistent
- Doesn't distinguish between data types in the same directory
- Less fine-grained control over channel selection

## Future Considerations

1. **URL Discovery Tool**: Automatically find correct data directories when URLs change
2. **Archive Versioning**: Track which PDS archive version is being used
3. **PDS API Integration**: Use official APIs for more reliable data location
4. **Metadata Validation**: Parse .LBL files to verify downloaded data quality
5. **Pattern Library**: Create reusable pattern definitions for other missions (e.g., Mars rovers, Cassini)
6. **Resume Capability**: Allow interrupted downloads to resume
7. **Checksum Verification**: Validate downloaded files against PDS checksums

## Related Decisions
- [Ingest Pipeline Design](../specs/ingest_pipeline.md) - How downloaded data flows into the app
- [Provenance Architecture](../specs/provenance_schema.md) - Tracking data source metadata
- [Units & Conversions](../specs/units_and_conversions.md) - Handling MASCS wavelength units

## References
- MESSENGER MASCS Instrument Paper: [McClintock & Lankton, 2007](https://doi.org/10.1007/s11214-007-9264-5)
- PDS4 Standards Reference: [https://pds.nasa.gov/datastandards/documents/](https://pds.nasa.gov/datastandards/documents/)
- MESSENGER Data Archive: [https://pds-geosciences.wustl.edu/missions/messenger/index.htm](https://pds-geosciences.wustl.edu/missions/messenger/index.htm)
- PDS Geosciences Node: [https://pds-geosciences.wustl.edu/](https://pds-geosciences.wustl.edu/)
- `tools/pds_downloader_native.py` - Implementation
- `docs/dev/worklog/2025-10-31_pds_downloader_refinement.md` - Detailed change documentation
- `docs/Telescope-Based Planetary datasets.md` - MESSENGER data sources reference
