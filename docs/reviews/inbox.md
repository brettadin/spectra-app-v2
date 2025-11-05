# Suggestions Inbox (Fresh Eyes Triage)

A rolling queue of suggestions from Fresh Eyes Reviews. Maintain ET timestamps and status. Promote items to
`docs/reviews/workplan.md` (active sprint) or `docs/reviews/workplan_backlog.md` (later) as appropriate.

Format:
- 2025-11-04 (ET) — [status: triage|planned|done]
  - Area: UI | Services | Docs | Packaging | Data | Tests | Process
  - Summary: One-line description
  - Details: 1–3 bullets, with file paths/links
  - Link: docs/dev/agent_reviews/YYYY-MM-DD.md#anchor (optional)

---

- 2025-11-04 — [status: triage]
  - Area: Docs
  - Summary: Add path alias helper in code; flip LocalStore/export centers
  - Details:
    - Implement `app/utils/path_alias.py` with env overrides
    - Update tests to cover resolution and override
  - Link: docs/specs/path_aliases.md
