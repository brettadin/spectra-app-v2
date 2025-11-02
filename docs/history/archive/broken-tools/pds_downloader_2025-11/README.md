# Broken: PDS Downloader (November 2025)

## Summary

The native Python PDS downloader (`tools/pds_downloader_native.py`) is currently **non-functional** due to:
1. PDS archive URL structure changes (404 errors)
2. Incorrect dataset targeting (downloading GRS gamma-ray data instead of MASCS optical spectra)
3. Missing URL validation before download attempts

## Investigation Status

**Last Investigated**: 2025-10-31  
**Investigator**: AI agent (GitHub Copilot)  
**Documented In**: `docs/dev/worklog/2025-10-31_pds_downloader_refinement.md`

### What We Found

1. **URL Issues**:
   - Target: `https://pds-geosciences.wustl.edu/missions/messenger/mascs_uvvs_cdr/`
   - Result: HTTP 404 Not Found
   - Estimated size showed ~2GB but no files accessible

2. **Wrong Dataset Filter**:
   - Script was configured to download GRS (Gamma Ray Spectrometer) data
   - Should target MASCS (Mercury Atmospheric and Surface Composition Spectrometer) optical data
   - Filter patterns needed: `ufc_`, `umc_`, `uvc_` (UVVS channels), `vnc_`, `vvc_` (VIRS channels)

3. **Missing Features**:
   - No resume capability for interrupted downloads
   - No URL verification before crawling
   - Pattern filters implemented but URLs broken

## Files Archived Here

- `pds_downloader_native.py` - Main crawler script
- `investigation_notes.md` - Detailed technical findings
- `parse_messenger_mascs.py` - Parser for downloaded files (untested)

## Can It Be Fixed?

**Yes**, with these steps:

1. **Verify PDS URLs**:
   - Browse https://pds-geosciences.wustl.edu manually
   - Find current MASCS optical data location
   - Update base URLs in script

2. **Add URL validation**:
   ```python
   def verify_url(url: str) -> bool:
       response = requests.head(url, timeout=5)
       return response.status_code == 200
   ```

3. **Test pattern filters**:
   - Confirm file naming conventions haven't changed
   - Update regex patterns for MASCS science files

4. **Add resume capability**:
   - Track downloaded files in manifest
   - Skip existing downloads
   - Verify checksums before skipping

## Restoration Plan

If you want to fix this:

1. Read the investigation worklog: `docs/dev/worklog/2025-10-31_pds_downloader_refinement.md`
2. Browse PDS archive manually to find correct URLs
3. Test with dry-run mode first
4. Update `QUICK_START_BULK_DATA.md` once working
5. Add to workplan as "Batch 15: Restore PDS bulk downloads"

## User Impact

**Current Workaround**: Manual curated downloads only
- Use Remote Data dialog (File → Fetch Remote Data)
- MAST archive for JWST/HST planetary observations
- Direct PDS website for MESSENGER MASCS if needed

**Documentation Updated**:
- `QUICK_START_BULK_DATA.md` notes manual-only downloads
- Removed automated PDS download instructions

## For Future Agents

If PDS changes their archive structure again:
1. Archive the broken version here with investigation notes
2. Update this README with failure analysis
3. Document workarounds for users
4. Consider alternative sources (MAST, Exo.MAST, NASA ADS)

Do **not** silently remove broken tools. Always document why they broke and what would be needed to fix them.

---

**Broken**: October 2025 (PDS URL structure change)  
**Archived**: 2025-11-02  
**Status**: Can be restored with URL verification + testing  
**Priority**: Low (manual downloads work, automated convenience only)
