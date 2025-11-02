# Documentation & Code Archive

This directory contains historical snapshots of deprecated documentation, broken tools, and removed features. All content here is **frozen** for reference purposes only.

## Purpose

- **Preserve Context**: Keep decision history and technical investigations for future reference
- **Track Evolution**: Show how the codebase changed over time
- **Enable Restoration**: Provide clear path to resurrect archived features if needed
- **Learning Resource**: Help future developers understand past mistakes and successes

## Archive Structure

```
archive/
├── README.md (this file)
├── YYYY-MM-DD-pre-cleanup/      # Documentation snapshots before major reorganization
├── broken-tools/                 # Non-functional code with investigation notes
└── deprecated-features/          # Removed features that may return
```

## How to Use

1. **Before removing any documentation or code**: Create a dated archive entry
2. **Always include README.md** in the archived directory explaining why it was archived
3. **Link from current docs** to archived versions for historical context
4. **Review quarterly**: Old archives (>2 years) can be compressed to zip files

## Active Archives

### 2025-11-02 Pre-Cleanup
**What**: Redundant documentation from repository consolidation  
**Why**: Multiple overlapping capability/inventory/summary docs caused confusion  
**Location**: `2025-11-02-pre-cleanup/`  
**Can Restore?**: No - content merged into single authoritative sources  

### Broken PDS Downloader (November 2025)
**What**: Native Python PDS archive crawler  
**Why**: URLs changed, wrong datasets targeted (GRS vs MASCS optical)  
**Location**: `broken-tools/pds_downloader_2025-11/`  
**Can Restore?**: Yes - needs URL verification and filter updates  

---

**Maintained By**: Development team and AI agents  
**Last Updated**: 2025-11-02
