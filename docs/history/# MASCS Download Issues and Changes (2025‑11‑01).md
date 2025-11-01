# MASCS Download Issues and Changes (2025‑11‑01)

Summary
- Problem: Bulk downloader crawled MESSENGER GRNS/GRS (gamma-ray) instead of MASCS UVVS/VIRS (optical).
- Evidence: Dry-run showed URLs like `...messgrs_2001/.../grs_eng/...` with many `grs_eXX...` files.
- Impact: Wrong instrument data would corrupt consolidation and quality ranking.
- Additional issue: Native MASCS UVVS URL used (`...messmas_1001/data/cdr/uvvs`) returned 404.

What we changed
- Added strict guidance to always run `--dry-run` and verify instrument in URLs.
- Paused bulk MASCS auto-download; recommend curated/manual pulls for now.
- Tightened intended filename filters (plan): include only MASCS science prefixes, exclude engineering:
  - Include (UVVS): ufc_*, umc_*, uvc_* (+ matching .LBL)
  - Include (VIRS): vvc_*, vnc_* (+ matching .LBL)
  - Exclude: *_eng*, *_hdr*, INDEX/, CATALOG/, CHECKSUM.*, MD5.*, /grs_*/
- Doc updates:
  - Quick Start now warns about instrument mismatch and 404s.
  - New Planet Data Playbook to narrow searches per target.

Why this happened
- PDS directory traversal followed adjacent archive branches (GRNS) due to an overly broad root URL.
- Direct-typed MASCS URLs were not valid for the geosciences node path (mismatch in volume/collection layout).

Action items
- Re-verify MASCS UVVS/VIRS PDS3 volume IDs and directory maps at Geosciences/Atmospheres nodes.
- Implement hard “instrument allow-list” in downloader before any traversal.
- Add URL validation: reject if path contains `/grs_` or `messgrs_`.
- Add integration test: dry-run must report only MASCS and expected filename patterns.

Workarounds (now)
- Use curated/manual download via PDS search portals with filters (see playbook).
- Keep label files (.LBL) with data for correct parsing.

Logs (sample)
- See terminal output in chat showing `grs_eng` and `messgrs_2001` paths.