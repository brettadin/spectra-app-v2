# Consolidated Knowledge Log (ARCHIVE 2025-11-01)

This is a full archival snapshot of the prior contents of `docs/history/KNOWLEDGE_LOG.md` as of 2025-11-01. New entries will not be added here; refer to `docs/history/KNOWLEDGE_LOG.md` for the current, concise log and policy going forward.

---

# Consolidated Knowledge Log

This file serves as the single entry point for all historical notes, patches,
"brains" and "atlas" logs.  Previous iterations of Spectra‑App stored
information in many places (e.g. `brains`, `atlas`, `PATCHLOG.txt`) and often
used confusing naming schemes (sometimes based on the day of the month).
To avoid further fragmentation, every meaningful change or insight should be
recorded here with a timestamp and a clear description.

## Log Format

Each entry in this document should follow this structure:

```markdown
## YYYY‑MM‑DD HH:MM – [Component]

**Author**: human or agent name

**Context**: Short description of what part of the system this log refers to
  (e.g. Unit conversion, UI logic, Importer plugin).

**Summary**: Concise explanation of what was done, why it was necessary, and
  any immediate outcomes or open questions.

**References**: Links to relevant files, commits or external sources (use
  citation markers like  for primary documentation where
  applicable).

---
```

## 2025-10-31T19:38:48-04:00 / 2025-10-31T23:38:48+00:00 – PDS Downloader Refinement for MESSENGER MASCS Data

**Author**: agent (GitHub Copilot)

**Context**: Data acquisition pipeline improvements for Mercury spectroscopy research. Tightening download criteria to ensure MESSENGER MASCS data is comparable and relevant for educational/research spectroscopic analysis.

**Summary**: Refined the native Python PDS downloader (`tools/pds_downloader_native.py`) to implement stricter filtering of MESSENGER MASCS optical spectroscopy data from the PDS Geosciences archive. The changes address the user's goal of ensuring downloaded data is directly comparable to their research needs by filtering out engineering files, headers, and non-spectroscopic data products.

**Key Changes**:
1. **Dataset URL Refinement**: Updated base URLs to point directly to specific data product directories (CDR/DDR subdirectories) rather than broad `/data/` paths. This reduces unnecessary scanning of metadata and documentation directories.

2. **Dataset Quality Upgrade**: Replaced EDR (Experimental Data Record, raw) datasets with DDR (Derived Data Record, surface reflectance) datasets:
   - UVVS: DDR provides binned, high-quality surface reflectance (~500 MB vs ~1 GB raw)
   - VIRS: DDR provides derived surface reflectance (~3 GB vs ~10 GB raw)
   - DDR products have better signal-to-noise and are more suitable for comparative spectroscopy

3. **Pattern-Based Filtering**: Implemented three-stage filtering system:
   - **Stage 1**: File type check (`.DAT`, `.LBL`, `.FMT`)
   - **Stage 2**: Required patterns (must match at least one MASCS science file prefix)
   - **Stage 3**: Exclude patterns (must not match any engineering/metadata files)
   
   Science file patterns for MESSENGER MASCS:
   - UVVS CDR: `ufc_` (FUV 115-190nm), `umc_` (MUV 160-320nm), `uvc_` (VIS 250-600nm)
   - VIRS CDR: `vnc_` (NIR 850-1450nm), `vvc_` (VIS 300-1050nm)
   - UVVS DDR: `uvs_`, `uvd_` (derived products)
   - VIRS DDR: `vnd_`, `vvd_` (derived products)
   
   Excluded patterns: `_hdr.dat` (headers), `_eng.dat` (engineering), `index`, `catalog` (metadata)

4. **Enhanced Reporting**: Added `filtered_count` metric to download summary showing how many files were excluded by pattern filters, providing visibility into filtering effectiveness.

**Issues Encountered**:
- 404 error when accessing the updated UVVS CDR URL during dry-run testing
- Estimated dataset size shown as ~2 GB but no files were accessible at the specified path
- Indicates potential issues with PDS archive URL structure or data reorganization

**Documentation Created**:
- Comprehensive worklog entry (`docs/dev/worklog/2025-10-31_pds_downloader_refinement.md`) documenting:
  - Detailed explanation of all changes and their rationale
  - MESSENGER MASCS file naming conventions
  - Technical details of the three-stage filtering implementation
  - Analysis of the 404 error and investigation steps
  - Recommendations for future improvements (URL discovery tool, API integration, resume capability)
  - References to PDS archive locations and related tools

**Next Steps**:
- Manual verification of PDS archive URL structure by browsing the website
- Testing alternative URL paths (e.g., `/data/uvvs/` without `cdr` subdirectory)
- Potentially updating `tools/parse_messenger_mascs.py` to handle DDR format if different from CDR
- Considering integration with PDS API for more reliable data access

**Impact**: These changes ensure that when the URL issue is resolved, the downloader will acquire only high-quality spectroscopic data suitable for comparative analysis, reducing storage requirements and processing time while maintaining scientific value.

**References**: `tools/pds_downloader_native.py`, `docs/dev/worklog/2025-10-31_pds_downloader_refinement.md`, `docs/history/PATCH_NOTES.md`, `docs/Telescope-Based Planetary datasets.md`, `tools/parse_messenger_mascs.py`, `tools/pipeline_master.py`.

---

[... full original content continues below ...]
