# Pre-Cleanup Documentation Archive (2025-11-02)

## Why Archived

These documents were removed during the November 2025 repository cleanup to eliminate redundancy and establish single authoritative sources for each topic.

## What Was Here

### 1. IMPLEMENTATION_SUMMARY.md (root)
**Content**: Overview of all major features implemented up to October 2025  
**Redundant With**: `docs/app_capabilities.md`, `docs/repo_inventory.md`  
**Replacement**: Merged into `docs/developer/architecture.md` (planned)

### 2. ENHANCEMENT_PLAN_STATUS.md (root) 
**Content**: Status tracking for planned enhancements  
**Redundant With**: `docs/reviews/workplan.md`, `reports/roadmap.md`  
**Replacement**: Consolidated into `docs/reviews/workplan.md`

### 3. IR_EXPANSION_SUMMARY.md (root)
**Content**: Details about IR functional groups database expansion  
**Redundant With**: `docs/history/PATCH_NOTES.md`, `docs/history/KNOWLEDGE_LOG.md`  
**Replacement**: Already documented in history files, no need for separate summary

### 4. docs/app_capabilities.md
**Content**: 500+ line narrative of all app features and capabilities  
**Redundant With**: `docs/repo_inventory.md` (1200 lines, similar scope)  
**Replacement**: Best parts merged into new `docs/developer/architecture.md`

### 5. docs/repo_inventory.md
**Content**: Complete repository file listing with status notes  
**Redundant With**: `docs/app_capabilities.md`, partially overlaps with README  
**Replacement**: File structure info moved to `docs/developer/code_organization.md`

## Current Alternatives

| Old Document | New Location | Notes |
|--------------|--------------|-------|
| Feature lists | `docs/developer/architecture.md` | Single source for capabilities |
| Enhancement status | `docs/reviews/workplan.md` | Active planning document |
| File structure | `docs/developer/code_organization.md` | Focused on layout & patterns |
| Quick overview | `README.md` | User-facing summary only |
| Detailed history | `docs/history/CHANGELOG.md` | From PATCH_NOTES.md |

## Can It Be Restored?

**No** - This content was consolidated, not deleted. All useful information was preserved in the replacement documents. These archived versions remain for historical reference only.

## For Future Agents

If you're looking for:
- **"What features exist?"** → See `docs/developer/architecture.md`
- **"What's planned?"** → See `docs/reviews/workplan.md`
- **"How is code organized?"** → See `docs/developer/code_organization.md`
- **"What changed recently?"** → See `docs/history/CHANGELOG.md`

Do not restore these files. If you find gaps in the new documentation, improve the authoritative source instead of recreating redundancy.

---

**Archived**: 2025-11-02  
**Reason**: Redundancy elimination - consolidation to single sources  
**Restoration**: Not recommended - content preserved in merged docs
