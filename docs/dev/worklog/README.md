# Daily Worklog Policy

We maintain one worklog file per real calendar day in America/New_York (Eastern Time). If you work multiple times in a day, append additional entries to the same file and increment the entry number.

- Timezone for day boundaries: America/New_York (ET)
- Filename: `docs/dev/worklog/YYYY-MM-DD.md`
- Multiple sessions/day: add `Entry #2`, `Entry #3`, etc.
- Each entry header includes local and UTC times and the agent name/handle.
- Use the template: `docs/dev/worklog/TEMPLATE.md`

These narrative logs complement the tactical **workplan** (`docs/reviews/workplan.md`). Each entry should include:
- Summary of changes (what/why/how)
- User-visible effects and validation steps
- Known issues and next steps
- Links to `docs/brains/*` neurons and `docs/atlas/*` maps
- Cross-reference to workplan batch items when applicable

## Example

`docs/dev/worklog/2025-11-03.md`:

```
## [Entry #1] 09:42 (Local ET) / 14:42Z (UTC) — Agent: alice
...entry content...

## [Entry #2] 16:18 (Local ET) / 21:18Z (UTC) — Agent: bob
...entry content...
```

## Helper tool

To get the correct ET date, current ET/UTC times, and a ready-to-copy header stub, run:

- Python (any platform): `python tools/worklog_helper.py`

It prints the suggested filename (based on America/New_York) and an entry header like:

```
## [Entry #N] HH:MM (Local ET) / HH:MMZ (UTC) — Agent: <name>
```

## Recent Worklogs

## Recent Worklogs

### 2025-10-31 - PDS Downloader Refinement
- **`2025-10-31_pds_downloader_refinement.md`** - Comprehensive documentation of PDS downloader changes
  - Three-stage filtering implementation
  - EDR → DDR dataset migration
  - MESSENGER MASCS file naming conventions
  - Technical recommendations for future work
  
- **`2025-10-31_pds_url_404_issue.md`** - Investigation guide for 404 error
  - Step-by-step troubleshooting
  - Root cause analysis
  - Priority action items
  - Temporary workarounds
  
- **`QUICK_REFERENCE_pds_downloader.md`** - Quick start guide
  - TL;DR for anyone picking up the PDS downloader work
  - What's done, what needs investigation
  - Test commands and success criteria
  
See also:
- Brain entry: `docs/brains/2025-10-31T1938-pds-downloader-filtering-strategy.md`
- Knowledge log: `docs/history/KNOWLEDGE_LOG.md` (search "2025-10-31T19:38")
- Patch notes: `docs/history/PATCH_NOTES.md` (search "2025-10-31")

### 2025-10-29 - Repository Audit
- **`2025-10-29_repo_audit_kickoff.md`** - Audit initialization

### 2025-10-26 - Normalization Fix
- **`2025-10-26_normalization_fix.md`** - Normalization pipeline updates

### 2025-10-25 - Remote Download
- **`2025-10-25_remote_download_handoff.md`** - Remote data pipeline work
- **`2025-10-25.md`** - Session notes
