# Spectra App – Agent Orientation

Welcome! Review these resources **before** making changes:

1. **Project overview & onboarding** – `START_HERE.md` outlines goals, architecture, and workflow expectations. Pair it with the root `README.md` for build/test instructions and environment notes.
2. **Documentation index** – `docs/link_collection.md` aggregates key references (remote archives, spectroscopy primers, UI guidelines). Consult it for domain context and upstream data sources.
3. **Workplan & history** – `docs/reviews/workplan.md` tracks backlog items by batch; `docs/history/PATCH_NOTES.md` and `docs/history/KNOWLEDGE_LOG.md` record what shipped and why. Update them when delivering new capability or insight.
4. **Reference data specs** – `docs/reference_sources/` and `specs/` describe ingestion pipelines, data formats, and analysis requirements. Review before touching importers, overlays, or reference bundles.
5. **Testing & tooling** – Unit tests live under `tests/`. Use `pytest` for validation. UI smoke tests may require the Qt bot fixtures. Utility scripts for data ingestion reside in `tools/` (see `docs/dev/reference_build.md`).

## Coding expectations
- Prefer pure Python (3.11) unless explicitly extending native modules—coordinate before adding C/C++.
- Keep imports at module top; avoid try/except around them unless guarding optional dependencies (pattern already used in `app/services/remote_data_service.py`).
- Maintain docstrings and inline comments explaining scientific reasoning (physics, chemistry) where applicable.
- When adding UI, ensure accessibility and test hooks (signals, slots) remain deterministic.

## Workflow checklist
1. Search for existing instructions in nested `AGENTS.md` files before editing a directory.
2. Update relevant documentation (user guides, developer notes, knowledge log, patch notes) whenever behaviour changes.
3. Run applicable tests (`pytest`, lint scripts, or data builders) and capture results.
4. Provide citations in final summaries using the repository-relative path + line numbers.

## Remote data & caching quick tips
- Remote catalogue providers are dependency-gated. Use `RemoteDataService.providers()` to determine availability and surface clear UI hints.
- MAST searches require translating user input to `target_name`; downloads must flow through astroquery helpers. Confirm both paths when editing remote data code.
- Cache bookkeeping lives in `LocalStore`; keep the knowledge log focused on high-level insights, not per-file metadata.

Stay aligned with the project mission: high-fidelity spectroscopic analysis that bridges laboratory and observational data. Document assumptions, cite sources, and leave breadcrumbs for the next agent.
