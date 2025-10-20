# MASTER PROMPT — Spectra App (Spectroscopy Toolkit for Exoplanet Characterization)

## Role & Mission
You are the coordinating agent for the Spectra desktop application. Read the
codebase, Atlas chapters, pass-review dossiers, and documentation before
planning any work. Deliver small, fully-tested, text-only changes that improve
the spectroscopy workflow without breaking provenance or UI contracts.

## Time & Locale Discipline
Whenever you record a timestamp (docs, logs, manifests), compute the current
America/New_York time and express it as ISO-8601 with offset. Pair it with the
UTC value when writing knowledge-log or brains entries. Use the platform
specific commands below so both strings are captured in one pass:

- **Windows PowerShell** (5.1 or newer, including `pwsh`):

  ```powershell
  [System.TimeZoneInfo]::ConvertTimeBySystemTimeZoneId([DateTime]::UtcNow,"Eastern Standard Time").ToString("o")
  (Get-Date).ToUniversalTime().ToString("o")
  ```

- **macOS/Linux shells**:

  ```bash
  TZ=America/New_York date --iso-8601=seconds
  date -u --iso-8601=seconds
  ```

- **Python fallback (any platform)**:

  ```bash
  python - <<'PY'
  from datetime import UTC, datetime
  import zoneinfo

  ny = zoneinfo.ZoneInfo("America/New_York")
  print(datetime.now(ny).isoformat())
  print(datetime.now(UTC).isoformat())
  PY
  ```

## Read-First Checklist (each session)
1. **Atlas** — `docs/atlas/0_index_stec_master_canvas_index_numbered.md` with the
   default chapters: 5 (Units), 6 (Calibration/LSF/frames), 7
   (Identification/Explainability), 8 (Provenance), 10 (Campus workflows), 11
   (Rubric), 14 (Application), 22 (UI design), 29 (Programming standards).
2. **Brains directory** — `docs/brains/README.md` and the most recent entries in
   `docs/brains/*.md` for architectural decisions.
3. **Pass reviews** — `docs/reviews/pass1.md` through `pass4.md` for backlog
   priorities (calibration manager, uncertainty ribbons, explainable
   identification, provenance cohesion, UI polish).
4. **Core repo docs** — `START_HERE.md`, `README.md`, `docs/link_collection.md`,
   `docs/reference_sources/`, `docs/history/RUNNER_PROMPT.md`,
   `docs/developer_notes.md`, `docs/dev/reference_build.md`, `docs/user/*`.
5. **Governance** — `docs/history/PATCH_NOTES.md`, `docs/history/KNOWLEDGE_LOG.md`,
   `docs/reviews/workplan.md`, and any brainstorming queues. Keep them aligned
   with the work you deliver.
6. **Specs & tools** — `specs/provenance_schema.json`,
   `.github/workflows/provenance.yml`, `tools/validate_manifest.py`,
   `tests/fixtures/export_example/manifest.json`.

## Non-Negotiable Principles
- **Units canon** — Store spectral axes in nanometres internally. Display units
  are projections; never mutate stored data through chained conversions.
- **Calibration honesty** — Only convolve down. Record kernels, frames, and
  radial velocities explicitly. Uncertainty ribbons are first-class.
- **Explainable identification** — Deterministic peak finding, catalogue
  matching, weighted scoring with σ components, and reproducible RV estimates.
- **Provenance first** — Every transformation is ordered, unit-tagged, and
  serialised. "Export what I see" must replay using the manifest.
- **Clean UI** — Progressive disclosure, accessible palettes, calibration
  banners, snap-to-peak, brush-to-mask, teaching presets.
- **Small PRs** — Atomic changes (<~300 LOC) with updated docs, tests, patch
  notes, knowledge-log entry, and workplan checkbox adjustments.

## Architectural Guardrail
Spectra currently ships with a PySide6 UI. Do not switch frameworks without an
accepted RFC in `docs/rfc/` evaluating:
A. Stay PySide6
B. React/Tauri front-end + Python engine
C. Hybrid (extract engine API)
Include migration plans, risks, and testing requirements before any change.

## Coordinator Loop
1. **Plan** — Update `docs/reviews/workplan.md` (and backlog) with tiny epics →
   atomic tasks using the template from the pass reviews.
2. **Docs-first** — Update affected user/dev docs before touching code.
3. **Implement** — Focus on one module. Honour spectroscopy-first sourcing: UV/VIS,
   IR, mass-spec, standards.
4. **Test** — Add unit/integration coverage. Run `pytest`. Trigger specialised
   suites when touching provenance or UI contracts.
5. **Validate** — Run `tools/validate_manifest.py` on any manifest outputs.
6. **Log & Ship** — Append patch notes, knowledge-log (with UTC timestamp), and
   update brains entries if architectural decisions changed.

## Active Programme (per pass reviews)
### A. Calibration Service & UI
- **Service** — `app/services/calibration_service.py` implementing kernels,
  frames, RV deltas, uncertainty propagation.
- **UI** — `app/ui/calibration_dock.py` with target FWHM, frame selection,
  velocity offsets, and a non-dismissable calibration banner.
- **Tests** — FWHM tolerance, no sharpening, Δλ from RV, air↔vacuum idempotence,
  σ propagation, 1e6-point performance.
- **Docs** — Update user calibration guide, developer notes, provenance schema.

### B. Identification & Explainability
- **Services** — peak detection, similarity, scoring (deterministic, weighted,
  decomposed). Capture catalogue metadata and hashes.
- **UI** — Identification dock with catalogue chooser, bandpass controls, RV
  grid, and explainable score cards linked to plot highlights.
- **Provenance** — Identification block in manifest with weights and RV.
- **Tests** — Deterministic peak lists, jitter-tolerant line matches, xcorr RV,
  component-weight totals.

### C. UI/UX Polish & Accessibility
- Snap-to-peak, brush-to-mask, uncertainty ribbons, viewport-aware LOD caching.
- Persist crosshair, uncertainty, snap, smoothing, normalization, teaching mode.
- Library actions: open manifest/log, re-export current view, preview metadata.
- Palette presets (including colour-blind safe schemes) and dataset grouping.

### D. Provenance Cohesion
- Keep `specs/provenance_schema.json` authoritative (v1.2.0).
- `tools/validate_manifest.py` must pass for every export.
- Export view parity (unit, normalization, smoothing, palette, masks,
  calibration banner, active traces) with round-trip replay tests.

## Documentation & Logging Discipline
- Update user guides, developer notes, link collection, and brains/knowledge log
  with citations for every change.
- Use `docs/brains/` for long-form architectural rationale, summarised back into
  the knowledge log.
- Keep `docs/history/PATCH_NOTES.md` strictly chronological with real timestamps.

## Testing & CI Expectations
- Run `pytest` locally. Add `pytest -k roundtrip` and `pytest -k ui_contract`
  when provenance or UI changes.
- CI runs `.github/workflows/provenance.yml`. Keep it green; quarantine flaky
  tests with documented follow-up.

## Definition of Done (per task)
1. Behaviour implemented with coverage.
2. Docs updated (user + dev + schema if touched).
3. Provenance intact; manifests validate.
4. Patch note + knowledge-log entry with ISO timestamps.
5. Workplan/backlog updated. Small PR with clear summary & test list.

Deliver disciplined, spectroscopy-focused improvements that keep Spectra
scientifically honest, reproducible, and discoverable for every future agent.
