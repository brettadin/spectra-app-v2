# Reference Status Pluralisation Alignment

**Timestamp (UTC)**: 2025-10-25T14:29:52Z
**Authors**: Spectra Agent (GitHub Copilot Codex)
**Related Atlas Chapters**: 4 (Inspector workflows)
**Source Docs**: docs/history/KNOWLEDGE_LOG.md, docs/history/PATCH_NOTES.md, docs/dev/worklog/2025-10-25.md

## Context
The Reference dock pins multiple NIST ASD line-list queries for overlay. Recent UI updates pluralised the status label to report
"{count} pinned sets" whenever more than one collection is stored. The Qt regression test still expected the old singular copy,
causing failures even though runtime behaviour was correct.

## Decision
Update `tests/test_reference_ui.py::test_reference_nist_fetch_populates_table` to assert the pluralised "2 pinned sets" text,
keeping the UI contract test aligned with the runtime label while preserving the single-count check ("1 pinned set"). No runtime
code change is required; only the expectation shifts to match the current UI copy.

## Consequences
- Qt smoke tests pass again with the updated expectation.
- Documentation (patch notes, knowledge log, worklog) records the adjustment for future reference.
- Future copy edits should audit both the UI string and regression suite expectations together to avoid similar drifts.

## References
- `tests/test_reference_ui.py`
- `app/main.py`
- `docs/history/PATCH_NOTES.md`
- `docs/history/KNOWLEDGE_LOG.md`
