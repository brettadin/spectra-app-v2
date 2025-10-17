# Agent Onboarding Guide

Welcome to `spectra-app-beta`. Before making changes, align with the following
checklist so we preserve continuity across shifts:

## 1. Get oriented
- **Read `START_HERE.md`** for the current mission statement, environment setup,
  and escalation paths.
- Skim `docs/reviews/workplan.md` to understand which batch you are touching and
  which tasks remain open.
- Review the latest entries in `docs/history/KNOWLEDGE_LOG.md` and
  `docs/history/PATCH_NOTES.md` to absorb context on recent feature work. The
  knowledge log now records only high-impact insights; routine imports surface
  through the in-app Library dock instead.

## 2. Key documentation hubs
- `docs/link_collection.md` — curated external catalogues, laboratory primers,
  and internal navigation notes.
- `docs/user/remote_data.md` — Remote Data dialog UX, dependency requirements,
  and caching behaviour. Update this whenever provider semantics or the Library
  dock change.
- `docs/user/reference_data.md` — Bundled reference datasets, provenance, and
  overlay behaviour.
- `docs/dev/reference_build.md` — Regeneration instructions for JWST quick-look
  spectra, IR functional groups, and future catalogue expansions.
- `docs/atlas/` & `docs/brains/` — Architecture diagrams and service-level deep
  dives; consult before introducing new services or UI components.

## 3. Working agreements
- Honour the persistence setting: when disabled, remote downloads fall back to a
  temporary `LocalStore`. The Library dock should still enumerate cached entries
  from the active store so users can reload spectra without polluting the
  knowledge log.
- Remote MAST searches must translate free-text queries into supported
  `astroquery.mast` criteria (typically `target_name`). Downloads should route
  through `Observations.download_file` instead of raw HTTP. See
  `app/services/remote_data_service.py` and its tests for reference patterns.
- Keep colour palettes accessible: the Style tab exposes a “Trace colour mode”
  toggle for distinct vs. monochrome rendering. When modifying plot code, ensure
  both modes remain deterministic.
- When adding new data assets, record provenance in the cache index and update
  both the workplan and `docs/link_collection.md` with relevant sources.

## 4. Testing & tooling
- Prefer targeted `pytest` runs (e.g. `pytest tests/test_remote_data_service.py`)
  while iterating; execute the full suite before major merges when feasible.
- Respect optional dependency guards in services (requests/astroquery, etc.) and
  extend tests with monkeypatched stubs when network access is unavailable.

## 5. Handover notes
- Log significant architectural or scientific findings in
  `docs/history/KNOWLEDGE_LOG.md` with citations to code and tests.
- Capture workflow or documentation follow-ups in the workplan’s active batch
  so downstream agents can sequence their work without re-triage.
- Update this file whenever new foundational docs or processes are introduced.
