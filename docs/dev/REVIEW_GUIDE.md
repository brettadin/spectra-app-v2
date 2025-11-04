# Fresh Eyes Review — Guide

Purpose: Encourage each agent (and human contributor) to take a short, opinionated pass on the repo with a newcomer’s perspective,
then turn that into actionable suggestions.

## How to run a Fresh Eyes Review
1) Generate a stub with timestamps:
   - `python tools/agent_review_helper.py`
   - Copy the suggested header and path (ET calendar date) to `docs/dev/agent_reviews/YYYY-MM-DD.md`.
2) Spend 20–40 minutes scanning:
   - README, docs/INDEX.md, AGENTS.md (process), recent PATCH_NOTES
   - Key UI and services: `app/ui/main_window.py`, `app/ui/plot_pane.py`, `app/services/*`
   - Workplan backlog and cleanup plan
3) Capture:
   - 5–10 top observations (what’s clear, what’s confusing)
   - Concrete suggestions (upgrades, additions, QOL)
   - Risks/rough edges; fast wins; larger bets
4) Triage:
   - Copy actionable items to `docs/reviews/inbox.md`
   - Promote near-term items into `docs/reviews/workplan.md` or backlog

## What good feedback looks like
- Specific: cite files, lines, behaviors, or screenshots
- Pragmatic: small steps that improve docs, UX, correctness, or performance
- Aligned: tie bigger ideas back to specs or acceptance criteria

## Acceptance
- Each PR includes a link to the latest Fresh Eyes Review (if non-trivial changes were made)
- Inbox triage keeps `docs/reviews/inbox.md` fresh with ET timestamps and status

## References
- Template: `docs/dev/AGENT_REVIEW_TEMPLATE.md`
- Inbox: `docs/reviews/inbox.md`
- Process: `AGENTS.md`
- Cleanup plan: `docs/reviews/cleanup_consolidation_plan.md`
