# Planning & Documentation Structure

This document clarifies the different planning and logging systems in the Spectra app repository.

## Tactical Planning: Workplan

**Location**: `docs/reviews/workplan.md` and `workplan_backlog.md`

**Purpose**: Batch-level feature tracking and task management

**Structure**:
- Active batches with checkboxes for features/tasks
- QA logs with timestamps
- Recently completed sections
- High-priority epics in backlog

**Update frequency**: Per-batch (multiple times per week during active development)

**When to update**:
- Starting a new feature batch
- Completing tasks/features
- Running QA (pytest, ruff, mypy)
- Moving backlog items to active work

**Example entry**:
```markdown
## Batch 14 (2025-10-17) — In Progress

- [x] Added MAST download fallback with direct HTTP
- [ ] Wire "Quick Plot" button for streaming
```

## Daily Narrative: Worklogs

**Location**: `docs/dev/worklog/YYYY-MM-DD.md`

**Purpose**: Daily session narratives capturing what/why/how

**Structure**:
- Summary
- Changes (what/why/how)
- Observed issues
- Next steps (execution-ready)
- Validation steps
- References

**Update frequency**: Daily (one file per coding session)

**When to update**:
- At end of each coding session
- When making significant code or doc changes
- To capture context for future agents

**Example entry**: See `docs/dev/worklog/2025-10-22.md`

## Architectural Memory: Neurons

**Location**: `docs/brains/*.md`

**Purpose**: Atomic, cross-linked concept files for long-term agent memory

**Structure**:
- Single concept per file
- Cross-links to related neurons
- References to atlas and worklog

**Update frequency**: After any code/doc change introducing new concepts

**When to update**:
- New architectural pattern
- New API or service method
- Threading model change
- Significant algorithm or flow change

**Example**: `docs/brains/mast_download_fallback.md`, `docs/brains/ingest_service_bytes.md`

## Historical Record

**Location**: 
- `docs/history/PATCH_NOTES.md` (user-facing changes)
- `docs/history/KNOWLEDGE_LOG.md` (curated insights)

**Purpose**: Consolidated changelog and knowledge base

**Update frequency**: Per feature/fix

## Relationship Between Systems

```
Daily Work Session
    ↓
Write Code/Docs
    ↓
Create/Update Neuron (if architectural)
    ↓
Update Daily Worklog (narrative)
    ↓
Update Workplan (check off tasks)
    ↓
Update PATCH_NOTES (user-facing changes)
    ↓
Update KNOWLEDGE_LOG (insights/decisions)
```

## Quick Reference

| Document | Type | Frequency | Focus |
|----------|------|-----------|-------|
| `workplan.md` | Tactical | Per-batch | Tasks/features |
| `worklog/*.md` | Narrative | Daily | What/why/how |
| `brains/*.md` | Conceptual | Per-concept | Architecture |
| `PATCH_NOTES.md` | Historical | Per-feature | User changes |
| `KNOWLEDGE_LOG.md` | Historical | Per-insight | Decisions |

## For All Agents

When you make changes:

1. ✅ Update code/docs
2. ✅ Write neuron if introducing new concepts
3. ✅ Update today's worklog entry
4. ✅ Check off workplan tasks
5. ✅ Add PATCH_NOTES entry
6. ✅ Cross-link everything

This structure ensures both tactical tracking (workplan) and narrative context (worklogs) remain current.
