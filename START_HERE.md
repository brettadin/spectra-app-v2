# Start Here - Spectra App Development Guide

## 🎯 Welcome to Spectra App Development
This guide orients new contributors. Spectra is a documentation-first,
scientifically rigorous spectroscopy toolkit. Read the referenced material before
changing code so units, calibration, provenance, and UI practices remain
consistent.

## 📋 Essential Reading
- **`docs/history/MASTER PROMPT.md`** – Product vision, guardrails, and planning
  loop.
- **`docs/history/RUNNER PROMPT.md`** – Execution checklist for each development
  session.
- **`AGENTS.md`** – Operating manual and testing expectations.
- **`docs/brains/README.md` + latest entries** – Architectural rationale and
  follow-up notes.
- **`docs/link_collection.md` & `docs/reference_sources/README.md`** – Curated
  spectroscopy data sources and acquisition notes.
- **`docs/reviews/workplan.md` & `docs/reviews/workplan_backlog.md`** – Active
  batches and scheduled backlog items.
- **User guides (`docs/user/*.md`)** – Importing, remote data, reference browser,
  plot tools, units, quickstart.
- **Developer references** – `docs/developer_notes.md`, `docs/dev/reference_build.md`,
  `specs/` (provenance schema, UI contracts), `tests/` (regression coverage).

If any required document is missing or stale, raise a workplan task and log the
issue in `docs/history/KNOWLEDGE_LOG.md` with the actual New York timestamp.

## 🚀 Environment Setup
```powershell
# Windows quick start
RunSpectraApp.cmd

# Manual setup
py -3.11 -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

Verify optional dependencies (`astropy`, `astroquery`) are installed when working
with remote catalogues or FITS ingest. Document any additional tools you add.

## ✅ Sanity Checks
```bash
pytest
python -m app.main
```
Run targeted suites (`pytest -k roundtrip`, `pytest -k ui_contract`) when you
modify exports or UI behaviour.

## 🔄 Development Workflow
1. **Plan** – Update the workplan with atomic tasks and acceptance criteria.
2. **Branch** – `feature/YYMMDD-bN-shortname` (never commit to `main`).
3. **Docs-first** – Update relevant documentation before or alongside code.
4. **Implement** – Touch the owning module only. Respect Atlas rules:
   units canon, calibration honesty, explainable identification, provenance
   completeness, clean UI.
5. **Test** – Run lint/type/test gates (`ruff`, `mypy`, `pytest`).
6. **Log** – Append patch notes and knowledge-log entries with ISO timestamps
   (America/New_York).
7. **Review & PR** – Ensure PRs are <≈300 LOC, text-only, with documented tests.

## 🗂 Repository Highlights
- `app/` – PySide6 UI and services.
- `tests/` – Pytest suites (importers, remote data, UI smoke, provenance).
- `samples/` – Spectroscopy datasets (lamps, standards). Maintain provenance.
- `docs/` – User, developer, Atlas, brains, history, and reference sources.
- `tools/` – Reference-build scripts, manifest validator.

## 🧭 Principles & Standards
- **Units** – Store wavelength axes in nanometres; conversions are idempotent.
- **Calibration** – Only convolve down; record frames, LSF, RV shifts, and
  uncertainty propagation.
- **Identification** – Deterministic peak detection, explainable scoring, and
  catalog provenance.
- **Provenance** – Every transform captured in manifests; “Export what I see”
  must replay the active view.
- **UI** – Progressive disclosure, accessible palettes, calibration banner,
  snap-to-peak, brush-to-mask, teaching preset.
- **Logging** – Knowledge log for curated insights, Library dock for ingest
  metadata. Use real timestamps.

## 🆘 Getting Help
- Review prior entries in `docs/history/KNOWLEDGE_LOG.md` and `docs/brains/` for
  similar problems.
- Cross-reference external resources in `docs/link_collection.md`.
- Use the test suite as executable documentation.

Welcome aboard—keep changes small, documented, and scientifically honest.
