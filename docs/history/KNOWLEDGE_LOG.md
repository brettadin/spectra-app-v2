# Consolidated Knowledge Log

This file serves as the single entry point for all historical notes, patches,
"brains" and "atlas" logs.  Previous iterations of Spectra‑App stored
information in many places (e.g. `brains`, `atlas`, `PATCHLOG.txt`) and often
used confusing naming schemes (sometimes based on the day of the month)【875267955107972†L63-L74】.
To avoid further fragmentation, every meaningful change or insight should be
recorded here with a timestamp and a clear description.

## Log Format

Each entry in this document should follow this structure:

```markdown
## YYYY‑MM‑DD HH:MM – [Component]

**Author**: human or agent name

**Context**: Short description of what part of the system this log refers to
  (e.g. Unit conversion, UI logic, Importer plugin).

**Summary**: Concise explanation of what was done, why it was necessary, and
  any immediate outcomes or open questions.

**References**: Links to relevant files, commits or external sources (use
  citation markers like 【875267955107972†L29-L41】 for primary documentation where
  applicable).

---

## 2025-10-21T20:38:53-04:00 / 2025-10-22T00:38:56+00:00 – CI numpy bootstrap and pytest marker registration

**Author**: agent

**Context**: Test infrastructure reliability and pytest configuration.

**Summary**: Added a `sitecustomize.py` bootstrap that installs `numpy>=1.26,<3` with `--prefer-binary` when the interpreter
  starts without NumPy, mirroring the recovery steps documented in `AGENTS.md`. This prevents CI runs from failing during
  collection when environments miss the dependency while still allowing developers to opt out via
  `SPECTRA_SKIP_AUTO_NUMPY`. Registered the custom `roundtrip` and `ui_contract` pytest markers inside `pyproject.toml` so the
  round-trip suite is recognised explicitly and pytest no longer warns about unknown marks.

**References**: `sitecustomize.py`, `pyproject.toml`, `docs/history/PATCH_NOTES.md`.

---
## 2025-10-21T20:17:41-04:00 / 2025-10-22T00:17:41+00:00 – Comprehensive real spectral data documentation

**Author**: agent

**Context**: User documentation for accessing legitimate spectral data from astronomical archives.

**Summary**: Created `docs/user/real_spectral_data_guide.md` as a comprehensive reference documenting how to access real, calibrated spectral observations from credible sources. The guide covers three main data categories with specific target examples and wavelength coverage:

1. **Solar system objects** (Jupiter, Mars, Saturn, moons) - JWST/HST observations spanning UV to mid-IR (0.1–30 µm)
2. **Stellar spectra** (Vega A0V standard, Tau Ceti G8V solar analog) - HST CALSPEC standards and Pickles library
3. **Exoplanet spectra** (WASP-39 b, TRAPPIST-1 system, hot Jupiters) - JWST transmission and emission spectra

Included comprehensive wavelength coverage table, data quality information (calibration levels 2 and 3), provenance tracking details, and proper citation guidance for MAST, JWST, NASA Exoplanet Archive, and NIST ASD. Explicitly documented that bundled JWST targets JSON contains deprecated example-only data and directed users to always fetch real calibrated data from MAST for scientific analysis.

Added troubleshooting section for common provider availability and download issues, plus cross-references to related documentation. This comprehensive guide directly addresses the requirement for "real, spectral data, from a wide range of wavelengths, all displayed correctly and accurately reflects the source data" from "credible sources" without synthesized or placeholder data.

**References**: `docs/user/real_spectral_data_guide.md`, `docs/user/remote_data.md`, `docs/link_collection.md`.



---
## 2025-10-21T20:15:49-04:00 / 2025-10-22T00:15:49+00:00 – User workflow documentation improvements

**Author**: agent

**Context**: Quickstart guide and remote data feature discoverability.

**Summary**: Enhanced `docs/user/quickstart.md` with a dedicated section on fetching real spectral data from MAST archives. Added step-by-step instructions for using the Remote Data dialog (File → Fetch Remote Data, Ctrl+Shift+R) with specific target examples across three categories: solar system objects (Jupiter, Mars), stars (Vega, Tau Ceti solar analog), and exoplanets (WASP-39 b, TRAPPIST-1 system). Clarified that all data comes from credible NASA MAST archives with wavelength coverage from UV to mid-IR (0.1–30 µm depending on instrument).

This addresses the requirement to improve the logical workflow of the application by making key features (remote data access) more discoverable and less "buried" in menus. The Remote Data feature is now prominently featured in the user onboarding guide, alongside the existing File menu location (Ctrl+Shift+R shortcut) and the comprehensive remote_data.md documentation.

**References**: `docs/user/quickstart.md`.

---
## 2025-10-21T20:12:22-04:00 / 2025-10-22T00:12:22+00:00 – Real spectral data access and placeholder deprecation

**Author**: agent

**Context**: Remote data service exoplanet archive integration and JWST reference data curation status.

**Summary**: Fixed the `NasaExoplanetArchive` import path in `RemoteDataService` from the incorrect `from astroquery.ipac.nexsci import NasaExoplanetArchive` to the correct `from astroquery.ipac.nexsci.nasa_exoplanet_archive import NasaExoplanetArchive`. This resolves the missing MAST ExoSystems provider, enabling users to fetch real calibrated spectral data for solar system objects (Jupiter, Mars, Saturn), stars (Vega, Tau Ceti, solar analogs), and exoplanets (WASP-39 b, TRAPPIST-1 system) directly from NASA MAST archives.

Updated `app/data/reference/jwst_targets.json` to prominently mark all bundled JWST targets as "DEPRECATED - Example data only" with curation status "digitized_placeholder_deprecated". Each target's provenance now explicitly directs users to fetch real calibrated data via the Remote Data dialog (File → Fetch Remote Data, Ctrl+Shift+R) by searching for the target name in the MAST ExoSystems provider. This aligns with the requirement to provide real, legitimate spectral data from credible sources and avoid synthesized or placeholder data.

Enhanced README.md with a dedicated "Accessing Real Spectral Data" section highlighting the Remote Data dialog workflow, available targets (solar system, stars, exoplanets), wavelength coverage (UV to mid-IR, 0.1–30 µm), and credible data sources (MAST, Exo.MAST, NASA Exoplanet Archive). The note clarifies that bundled reference data is for demonstration only and scientific analysis should always use the Remote Data dialog to fetch real observations.

All tests pass with updated expectations for the new curation status. The MAST ExoSystems provider is now functional and ready to deliver real spectral data across multiple wavelength ranges from legitimate astronomical archives.

**References**: `app/services/remote_data_service.py`, `app/data/reference/jwst_targets.json`, `README.md`, `tests/test_reference_library.py`, `docs/user/remote_data.md`.

---
## 2025-10-21T19:17:36-04:00 / 2025-10-21T23:17:36+00:00 – Remote Data dialog thread cleanup

**Author**: agent

**Context**: Remote Data dialog worker lifecycle management.

**Summary**: Hooked the dialog's accept, reject, and close handlers so they invoke the worker cleanup helpers, joining any
background search or download threads before the widget is destroyed. This prevents Qt from terminating with
`QThread: Destroyed while thread is still running` when operators close the dialog mid-operation.

**References**: `app/ui/remote_data_dialog.py`.
## 2025-10-21T19:21:16-04:00 / 2025-10-21T23:21:18+00:00 – Remote Data dialog shutdown responsiveness

**Author**: agent

**Context**: Remote Data dialog cancel/close workflow.

**Summary**: Reworked the dialog's reject path to defer closing until background search/download threads stop while keeping the
UI responsive. A Qt timer now polls thread completion instead of blocking on `thread.wait()`, and the cancel action shows a busy
indicator plus status message so analysts know shutdown is pending. This prevents the main window from freezing during slow
network calls.

**References**: `app/ui/remote_data_dialog.py`, `docs/history/PATCH_NOTES.md`.

---
## 2025-10-21T18:44:51-04:00 / 2025-10-21T22:44:53+00:00 – Curated search resiliency

**Author**: agent

**Context**: Solar System Archive provider resilience when bundled manifests/assets are missing.

**Summary**: Wrapped curated manifest and asset loading in guards so missing files no longer abort Solar System Archive searches,
allowing available bundles to remain discoverable. Added regression tests that append broken manifests/assets to the curated
roster to confirm searches continue returning valid targets, and documented the behaviour in the remote data user guide.

**References**: `app/services/remote_data_service.py`, `tests/test_remote_data_service.py`, `docs/user/remote_data.md`.
## 2025-10-21T18:42:11-04:00 / 2025-10-21T22:42:13+00:00 – JWST/exoplanet resource guidance

**Author**: agent

**Context**: Expanded the spectroscopy link collection with actionable steps and maintenance checks for the newly curated JWST
and exoplanet tooling repositories.

**Summary**: Augmented the JWST analysis and exoplanet retrieval sections in `docs/link_collection.md` with detailed usage
instructions (installation hints, workflow entry points) and maintenance tips (CRDS alignment, dependency/version pinning) so
future agents can adopt the resources without guessing their operational state. Emphasised verifying upstream release notes and
pinning commit hashes when relying on research-grade prototypes.

**References**: `docs/link_collection.md`, `docs/history/PATCH_NOTES.md`.

---
## 2025-10-21T18:13:33-04:00 / 2025-10-21T22:13:36+00:00 – Solar System Archive rename

**Author**: agent

**Context**: Renamed the curated remote provider and bundled samples to the Solar System Archive label.

**Summary**: Updated the remote data service/provider enums, UI copy, and curated manifest paths to adopt the Solar System Archive naming. Renamed the bundled directory to `samples/solar_system/`, refreshed associated manifests, and aligned the remote data user guide plus regression tests with the new terminology.

**References**: `app/services/remote_data_service.py`, `app/ui/remote_data_dialog.py`, `samples/solar_system/`, `tests/test_remote_data_service.py`, `docs/user/remote_data.md`.
## 2025-10-21T18:13:48-04:00 / 2025-10-21T22:13:50+00:00 – Remote data provider gating

**Author**: agent

**Context**: Remote Data dialog catalogue list vs. Reference dock workflows.

**Summary**: Added an `include_reference` toggle to `RemoteDataService.providers()` and had the Remote Data dialog call it so the
combo now lists only MAST and curated ExoSystems catalogues while the Reference dock retains exclusive NIST ASD access. Removed
the NIST hint/example branch, refreshed the Qt/UI regression coverage plus service-level provider tests, and updated the remote
data user guide to direct ASD line-list retrieval through the Reference dock with notes about cached query provenance.

**References**: `app/services/remote_data_service.py`, `app/ui/remote_data_dialog.py`, `tests/test_remote_data_dialog.py`,
`tests/test_remote_data_service.py`, `docs/user/remote_data.md`.
## 2025-10-21T18:13:39-04:00 / 2025-10-21T22:13:41+00:00 – Remote data link tooltips
## 2025-10-21T19:25:02-04:00 / 2025-10-21T23:25:04+00:00 – Exo.MAST encoding & preview guard

**Author**: agent

**Context**: Remote Data service/dialog stability for Exo.MAST enriched records.

**Summary**: Updated the Exo.MAST file-list fetcher to rely on `urllib.parse.quote`
alone so planet names with spaces (e.g. “WASP-39 b”) no longer double-encode and
silently drop citation metadata. Tightened the preview summary to ignore `NaN`
discovery years while still reporting discovery method/facility details so the
dialog remains responsive even when Astroquery returns incomplete metadata.
Extended the regression suite to cover both behaviours and documented the user
impact in the remote data guide.

**References**: `app/services/remote_data_service.py`, `app/ui/remote_data_dialog.py`,
`tests/test_remote_data_service.py`, `tests/test_remote_data_dialog.py`,
`docs/user/remote_data.md`.
---
## 2025-10-21T18:44:51-04:00 / 2025-10-21T22:44:53+00:00 – Curated search resiliency
## 2025-10-20T20:54:53-04:00 / 2025-10-21T00:54:55+00:00 – Exoplanet archive & MAST parity restored

**Author**: agent

**Context**: The Remote Data stack lost its Exo.MAST + NASA Exoplanet Archive integration, so MAST queries stalled at the observation level without product links, citation metadata, or curated solar-system fallbacks, leaving the UI incapable of displaying telescope/instrument context.

**Summary**: Reintroduced the chained archive workflow that resolves planets and host stars via PSCompPars, pulls curated Exo.MAST spectra, filters MAST product lists to spectroscopic assets, and surfaces mission/instrument/preview details in the dialog. Updated the user guide and regression suite to cover the new ExoSystems provider and the richer table layout.

**References**:
- `app/services/remote_data_service.py`
- `app/ui/remote_data_dialog.py`
- `tests/test_remote_data_service.py`
- `tests/test_remote_data_dialog.py`
- `docs/user/remote_data.md`
- `docs/history/PATCH_NOTES.md`

---
## 2025-10-20T15:39:03-04:00 / 2025-10-20T19:39:03+00:00 – Dependency window widened for NumPy 2.x wheels

**Author**: agent

**Context**: Windows launcher and onboarding docs still referenced the old
`numpy>=1.26,<2` range, causing setup failures on Python 3.12 where only 2.x
wheels are available.

**Summary**: Relaxed the numpy requirement to `<3` so the launcher resolves
published wheels, updated the recovery instructions in `RunSpectraApp.cmd`,
`AGENTS.md`, and `START_HERE.md`, and synced the workplan dependency note to
avoid future confusion.

**References**: `requirements.txt`, `RunSpectraApp.cmd`, `AGENTS.md`,
`START_HERE.md`, `docs/reviews/workplan.md`, `docs/history/PATCH_NOTES.md`.

---
## 2025-10-20T15:20:00-04:00 / 2025-10-20T19:20:00+00:00 – Windows pip binary guard reset

**Author**: agent

**Context**: The Windows launcher and manual setup instructions still allowed
inherited `PIP_NO_BINARY` settings, causing pip to build NumPy from source even
after adding `--prefer-binary`.

**Summary**: Cleared `PIP_NO_BINARY` and forced `PIP_ONLY_BINARY=numpy` /
`PIP_PREFER_BINARY=1` in `RunSpectraApp.cmd`, then mirrored the steps in
`START_HERE.md` and `AGENTS.md` so developers consistently request prebuilt
NumPy wheels during setup.

**References**:
- `RunSpectraApp.cmd`
- `AGENTS.md`
- `START_HERE.md`
- `docs/history/PATCH_NOTES.md`

---

## 2025-10-20 14:09 – Library hint stability & prefer-binary installs

**Author**: agent

**Context**: Windows UI ergonomics when reopening cached spectra and repeated
dependency build failures during launcher setup.

**Summary**: Fixed the Library tab hint label height and reinstated word wrap so
selecting cached spectra no longer forces the main window to expand or hide the
log dock on Windows. Updated the launcher script and onboarding docs to install
requirements with `--prefer-binary`, relaxed the numpy pin to `<2`, and widened
the requests range so environments without Visual Studio Build Tools can install
prebuilt wheels without manual edits.

**References**: `app/main.py`, `RunSpectraApp.cmd`, `requirements.txt`,
`AGENTS.md`, `START_HERE.md`, `docs/history/PATCH_NOTES.md`.

---

## 2025-10-19 19:38 – Data table toggle no longer auto-opens

**Author**: agent

**Context**: Plot data table ergonomics and layout stability on Windows builds.

**Summary**: Stopped the dataset selection handler from forcing the numerical
table to appear by default. The main window now remembers the last overlay
payload, repopulates the table only when **View → Show Data Table** is checked,
and leaves the layout unchanged otherwise.

**References**: `app/main.py`, `docs/user/plot_tools.md`,
`docs/history/PATCH_NOTES.md`, `docs/reviews/workplan.md`.

---

## 2025-10-19 18:46 – Data dock consolidation

**Author**: agent

**Context**: Workspace layout ergonomics and cache inspection UX.

**Summary**: Merged the Datasets dock and Library dock into a single Data dock
with tabbed navigation, rebuilt the library tab so it disables cleanly when the
persistent cache is off, and refreshed the user/developer guides plus workplan
to document the layout change. Confirmed the Qt regression suite remains green
after the refactor.

**References**: `app/main.py`, `docs/user/importing.md`, `docs/user/remote_data.md`,
`docs/user/plot_tools.md`, `docs/link_collection.md`, `docs/developer_notes.md`,
`docs/reviews/workplan.md`, `docs/history/PATCH_NOTES.md`.

---

## 2025-10-19 17:46 (America/New_York) / 21:46 (UTC) – Dataset dock filtering

**Author**: agent

**Context**: Usability improvements for managing large overlay sessions and
alignment of onboarding instructions with repository reality.

**Summary**: Added a search box to the Datasets dock so analysts can filter
aliases without unloading spectra; visibility updates in place and derived
groups respect the filter. Documented the workflow in the plot tools guide and
updated AGENTS/START_HERE to provide cross-platform timestamp commands and to
point contributors to the actual patch-note/knowledge-log locations.

**References**:
- `app/main.py`
- `tests/test_dataset_filter.py`
- `docs/user/plot_tools.md`
- `AGENTS.md`
- `START_HERE.md`
- `docs/history/PATCH_NOTES.md`

---

## 2025-10-19 16:50 – Export bundle variants

**Author**: agent

**Context**: Responding to feedback that combined CSV exports were difficult to
reuse and that analysts need averaged overlays when comparing multiple lamps.

**Summary**: Added an export options dialog so operators can emit the standard
manifest bundle, a wide paired-column CSV (`spectra-wide-v1`), and/or a
composite-mean CSV in one action. ProvenanceService gained helpers for both
formats, CsvImporter recognises the wide layout comments, and the user guides
document how each file re-imports. Regression coverage now guards the new
paths.

**References**:
- `app/main.py`
- `app/services/provenance_service.py`
- `app/services/importers/csv_importer.py`
- `tests/test_provenance.py`
- `tests/test_csv_importer.py`
- `docs/user/plot_tools.md`
- `docs/user/importing.md`
- `docs/history/PATCH_NOTES.md`

---

## 2025-10-19 15:14 (America/New_York) / 19:14 (UTC) – Export CSV axis ordering

**Author**: agent

**Context**: Provenance bundle exports should reload cleanly through the CSV importer.

**Summary**: Adjusted the combined export writer to place `wavelength_nm` and `intensity` at the start of each row while keeping spectrum metadata to the right. This prevents the importer from mis-identifying axes when reloading bundled CSVs and mirrors the structure documented in the importing guide.

**References**:
- `app/services/provenance_service.py`

---

## 2025-10-19 16:23 (America/New_York) / 20:23 (UTC) – Export bundle ingestion

**Author**: agent

**Context**: Importing provenance CSV bundles should restore every spectrum without manual splitting.

**Summary**: Taught `CsvImporter` to detect manifest-style CSV bundles and embed member metadata, then updated `DataIngestService` and the main window to expand those bundles into individual canonical spectra. Remote downloads and smoke tests now expect list-based ingestion, and the importing guide documents that re-importing a bundle restores each trace separately.

**References**:
- `app/services/importers/csv_importer.py`
- `app/services/data_ingest_service.py`
- `app/main.py`
- `docs/user/importing.md`
- `tests/test_csv_importer.py`
- `tests/test_ingest.py`
- `tests/test_provenance.py`
- `docs/user/importing.md`
- `docs/history/PATCH_NOTES.md`

---

## 2025-10-19 14:28 EDT / 18:28 UTC – Export Manifest Visibility Filter

**Author**: agent

**Context**: Provenance export workflow and dataset visibility state.

**Summary**: Ensured manifest bundles only include traces that remain visible in the workspace by filtering `export_manifest` against the dataset visibility map. Updated the user guides to clarify that hidden spectra stay out of the `spectra/` directory and added a Qt regression test (`tests/test_export_visibility.py`) that stubs the file dialog to confirm the filtered list is passed to the provenance service.

**References**: `app/main.py`, `docs/user/plot_tools.md`, `docs/user/importing.md`, `tests/test_export_visibility.py`, `docs/history/PATCH_NOTES.md`.

---

## 2025-10-19 14:09 – NIST overlay multi-pin

**Author**: agent

**Context**: Reference Inspector overlays and spectroscopy workflow clarity.

**Summary**: Reworked the NIST spectral-line pinning flow so every pinned set now projects onto the main workspace when the
overlay toggle is enabled, preserving per-set colours or collapsing to a uniform hue on demand. Adjusted the Inspector overlay
bookkeeping to manage multiple traces simultaneously, extended the Qt regression harness to assert the new behaviour, and
updated the reference data guide to describe the multi-set overlay output.

**NYC time**: 2025-10-19T14:09:10-04:00

**UTC time**: 2025-10-19T18:09:13+00:00

**References**:
- `app/main.py`
- `tests/test_reference_ui.py`
- `docs/user/reference_data.md`
- `docs/history/PATCH_NOTES.md`

---

## 2025-10-19 13:22 – Reference tab redesign

**Author**: agent

**Context**: Restructured the Inspector’s Reference tab around spectroscopy-first workflows.

**Summary**: Replaced the dataset combo with dedicated Spectral lines, IR groups, and Line-shape panels; wired the
embedded NIST form to astroquery so spectral lines plot and overlay directly; updated the reference data guide and added
Qt regression coverage for the new fetch path. UTC 2025-10-19T17:22:06Z.

**References**:
- `app/main.py`
- `docs/user/reference_data.md`
- `docs/history/PATCH_NOTES.md`
- `tests/test_reference_ui.py`

---

## 2025-10-19 13:42 – NIST pinboard & remote dialog alignment

**Author**: agent

**Context**: Inspector redesign follow-up to keep spectroscopy workflows front-and-centre while reducing redundancy between the
Reference tab and Remote Data dialog.

**Summary**: Introduced pinned NIST spectral-line sets with palette controls so multiple element/ion queries remain on the
inspector plot, refreshed the reference-data guide, and extended regression coverage. Removed the NIST provider from the Remote
Data dialog to avoid duplication, keeping MAST as the remote archive entry point and updating documentation/tests accordingly.

**Timestamps**:
- America/New_York: 2025-10-19T13:42:36-04:00
- UTC: 2025-10-19T17:42:45+00:00

**References**:
- `app/main.py`
- `app/ui/remote_data_dialog.py`
- `docs/user/reference_data.md`
- `docs/user/remote_data.md`
- `docs/reviews/workplan.md`
- `tests/test_reference_ui.py`
- `tests/test_remote_data_dialog.py`

---

## 2025-10-18 20:35 – NIST ASD astroquery line synthesis

**Author**: agent

**Context**: Remote catalogue alignment with the spectroscopy-first charter.

**Summary**: Replaced the ad-hoc NIST JSON search with the upstream astroquery
line-list helper so Spectra aggregates each element/ion query into a single
record, previews line counts, and generates provenance-rich CSV files for the
ingest pipeline. The remote service now detects the synthetic `nist-asd:` scheme
and regenerates the CSV via `astroquery.nist` before caching the download, while
tests and user docs cover the new workflow. (UTC 00:35)

**References**:
- `app/services/nist_asd_service.py`
- `app/services/remote_data_service.py`
- `tests/test_remote_data_service.py`
- `docs/user/remote_data.md`
- `docs/history/PATCH_NOTES.md`

---

## 2025-10-18 17:17 – Remote Data

**Author**: agent

**Context**: Remote catalogue dependencies, imaging toggle, and regression coverage.

**Summary**: Declared `requests`, `astroquery`, and `pandas` as required extras so
MAST/NIST catalogues stay enabled by default, exposed an **Include imaging** toggle
in the Remote Data dialog, and taught the MAST adapter to honour it while still
preferring calibrated spectra. Added pandas-aware dependency guards, refreshed the
user guide and agent manual, and extended the service/dialog regression tests to
cover the new flag and dependency messaging.

**References**: `requirements.txt`, `app/services/remote_data_service.py`,
`app/ui/remote_data_dialog.py`, `docs/user/remote_data.md`, `AGENTS.md`,
`tests/test_remote_data_service.py`, `tests/test_remote_data_dialog.py`,
`docs/history/PATCH_NOTES.md`.

---

## 2025-10-18 00:08 – Remote Data

**Author**: agent

**Context**: Remote catalogue UX hardening and spectroscopy-focused presets.

**Summary**: Added curated example queries to the Remote Data dialog, prevented
empty submissions from reaching the service, and raised a guard inside the MAST
adapter so archive calls always include spectroscopy filters. Updated the user
guide, workplan, and patch notes to reflect the scoped workflow.

**References**: `app/ui/remote_data_dialog.py`,
`app/services/remote_data_service.py`, `docs/user/remote_data.md`,
`docs/reviews/workplan.md`, `docs/history/PATCH_NOTES.md`.

---

## 2025-10-17 20:10 – Documentation

**Author**: agent

**Context**: Onboarding manuals, pass-review visibility, and brains directory
alignment.

**Summary**: Realigned the onboarding trailheads so agents read the decomposed
brains log, pass-review dossiers, and spectroscopy resources before coding.
Updated the master prompt, AGENTS manual, START_HERE guide, and workplan to
stress calibration/identification priorities and real-time timestamp
discipline. Added brains README plus pass1–pass4 summaries for continuity.

**References**: `docs/history/MASTER PROMPT.md`, `AGENTS.md`, `START_HERE.md`,
`docs/brains/README.md`, `docs/reviews/pass1.md`–`pass4.md`,
`docs/reviews/workplan.md`, `docs/history/PATCH_NOTES.md`.

---

## 2025-10-17 14:19 – Library metadata preview

**Author**: agent

**Context**: Cache inspection UX and provenance traceability.

**Summary**: Added a detail pane to the Library dock so selecting a cached
spectra entry now reveals its provenance, canonical units, and storage path
inline. Hooked selection changes to the preview, refreshed the empty-state
messaging, and documented the workflow in the importing guide. A new smoke test
guards the dock, ensuring metadata appears even in headless CI runs.

**References**:
- `app/main.py`
- `tests/test_smoke_workflow.py`
- `docs/user/importing.md`
- `docs/history/PATCH_NOTES.md`

---

```

Entries should be appended chronologically.  Older logs imported from the
original repository can be summarised and linked at the end of this file.
When summarising legacy content, include a note indicating that the details
come from a previous format (e.g. “Imported from brains/2023‑04‑10.md”).

### Automation support

The desktop preview now ships with a `KnowledgeLogService` that writes
automation events into this file by default.  The service can also be pointed
at an alternative runtime location (e.g. a temporary path during tests) by
passing a custom `log_path`, ensuring automated provenance never tramples the
canonical history while still following the structure defined here.

## Example Entry

```markdown
## 2025‑10‑14 15:23 – Units Service

**Author**: agent

**Context**: Implementation of the new UnitsService for the PySide6 rewrite.

**Summary**: Added support for converting wavelength between nm, μm and
  wavenumber, as well as intensity between absorbance and transmittance.  The
  service ensures idempotent conversions and records conversion metadata.
  Tested round‑trip conversions manually.【328409478188748†L22-L59】

**References**: `app/services/units_service.py`, design spec in
  `specs/units_and_conversions.md`, and original conversion formulas from
  `server/ir_units.py` in the legacy code【328409478188748†L22-L59】.

---
```

## Migration of Legacy Logs

To migrate existing `brains` and `atlas` logs, follow these steps:

1. Identify all existing log files in the old repository.  Normalize their
   names to the `YYYY‑MM‑DD_description.md` format.  If a file name refers
   to the day of the month rather than the actual date, determine the
   correct date by examining commit history or file metadata【875267955107972†L63-L74】.
2. Summarise the content of each file into a single entry in this log.  Use
   bullet points to capture key decisions, problems solved, and lessons
   learned.  Reference the original file location for traceability.
3. After migration, store the original files in an archive folder so that
   nothing is lost.

## Policy

* **Honesty**: Be transparent about decisions and mistakes.  If an entry
  describes an incorrect approach, annotate the outcome and how it was
  resolved.
* **Completeness**: Include enough information for future developers or
  agents to understand the context without having to search through commit
  history.  When in doubt, write more rather than less.
* **Citation**: Use tether IDs to cite official documents, academic papers or
  authoritative resources.  This ensures that claims can be verified.

---

## 2025-10-14 20:00 – Documentation

**Author**: agent

**Context**: User-facing onboarding documentation and planning artifacts.

**Summary**: Authored the first-run quickstart (`docs/user/quickstart.md`) so new operators can launch the desktop build, ingest bundled spectra, validate unit toggles, and export a provenance bundle without guesswork. Updated the README quick start section to highlight the guide and extended the Batch 3 workplan to track remaining documentation gaps aligned with the inventory. Captured the work in patch notes for traceability.

**References**: `docs/user/quickstart.md`, `README.md`, `docs/reviews/workplan.md`, `docs/history/PATCH_NOTES.md`.
## 2025-10-15 00:17 – Provenance Exports

**Author**: agent

**Context**: Provenance bundle hardening and documentation alignment.

**Summary**: Expanded export bundles to emit per-spectrum CSVs, copy source uploads, and write a structured activity log so downstream reviewers can trace every spectrum back to its canonical and raw forms.【F:app/services/provenance_service.py†L50-L108】 Regression coverage now confirms the manifest, CSVs, PNG snapshot, and log travel together and that canonical/exported paths are reflected inside the manifest for auditing.【F:tests/test_provenance_manifest.py†L24-L74】 Updated the importing guide’s provenance appendix so operators know what to expect in the bundle until the roadmap/workplan refresh lands, at which point I’ll backfill a direct planning link here.【F:docs/user/importing.md†L92-L111】【F:docs/reviews/workplan.md†L81-L85】

**References**: `app/services/provenance_service.py`, `tests/test_provenance_manifest.py`, `docs/user/importing.md`, `docs/reviews/workplan.md`.

---

## 2025-10-15 00:37 – Importer Heuristics & In-App Docs

**Author**: agent

**Context**: CSV/TXT heuristic upgrades and embedded documentation viewer.

**Summary**: Reworked the CSV importer to cache header layouts, scan messy tables for the dominant numeric block, and score candidate axes so we can recover wavelength/intensity pairs even when prose, Unicode units, or intensity-first exports get in the way.【F:app/services/importers/csv_importer.py†L93-L200】 Regression tests now cover preface-based unit detection, noisy-column scoring, cache invalidation, and axis corrections to keep heuristics honest.【F:tests/test_csv_importer.py†L11-L160】 Wired a Docs tab into the Inspector (and exposed it via Help → View Documentation) so all user guides render in-app for quick reference; I’ll link the refreshed roadmap/workplan doc when it’s published to capture this dependency there.【F:app/main.py†L1795-L1849】【F:docs/user/in_app_documentation.md†L1-L34】【F:docs/reviews/workplan.md†L87-L99】

**References**: `app/services/importers/csv_importer.py`, `tests/test_csv_importer.py`, `app/main.py`, `docs/user/in_app_documentation.md`, `docs/reviews/workplan.md`.

---

## 2025-10-15 01:04 – Normalization Pipeline & Axis Heuristics

**Author**: agent

**Context**: Overlay normalization plumbing and importer profile-based swaps.

**Summary**: Routed overlay rendering through a normalization helper so Max and Area modes scale reference spectra deterministically while keeping raw arrays intact for provenance.【F:app/services/overlay_service.py†L36-L92】 Added a profile-based swap to the CSV importer so monotonic intensity channels no longer masquerade as the independent axis, ensuring the plot toolbar’s normalization toggle manipulates the correct series.【F:app/services/importers/csv_importer.py†L174-L200】 Regression coverage now verifies both normalization paths and importer decisions, and the importing guide documents how raw units stay untouched until operators opt in to scaling; I’ll update this note with a roadmap/workplan link once that artifact is refreshed.【F:tests/test_overlay_service.py†L6-L41】【F:docs/user/importing.md†L34-L90】【F:docs/reviews/workplan.md†L100-L110】

**References**: `app/services/overlay_service.py`, `app/services/importers/csv_importer.py`, `tests/test_overlay_service.py`, `docs/user/importing.md`, `docs/reviews/workplan.md`.

---

## 2025-10-15 01:27 – Importer Header Safeguards

**Author**: agent

**Context**: Header-driven unit enforcement and conflict resolution.

**Summary**: Tightened the CSV importer so unit-only headers are trusted, conflicting axis labels trigger a swap with recorded rationale, and layout cache hits are ignored when validation fails, preventing subtle regressions on repeated ingest sessions.【F:app/services/importers/csv_importer.py†L176-L200】 Added regression tests to lock in the swap rationale, unit-only header handling, and cache miss flow, with documentation updates queued in the workplan backlog for follow-up linking once refreshed.【F:tests/test_csv_importer.py†L92-L184】【F:docs/reviews/workplan.md†L111-L123】

**References**: `app/services/importers/csv_importer.py`, `tests/test_csv_importer.py`, `docs/reviews/workplan.md`.

---

## 2025-10-15 03:24 – Reference Library & JWST Quick-Look Data

**Author**: agent

**Context**: Bundled reference datasets and inspector surfacing.

**Summary**: Staged hydrogen line lists, IR functional groups, line-shape placeholders, and digitised JWST spectra in the ReferenceLibrary so offline users can browse curated datasets with provenance metadata intact.【F:app/services/reference_library.py†L11-L126】 Regression coverage now asserts the catalogues include expected IDs, generators, and JWST quick-look metadata, while the reference guide narrates how overlays behave and calls out the planned swap to calibrated JWST pipelines—will backfill the roadmap/workplan link referencing that migration as soon as it lands.【F:tests/test_reference_library.py†L5-L45】【F:docs/user/reference_data.md†L1-L85】【F:docs/reviews/workplan.md†L150-L155】

**References**: `app/services/reference_library.py`, `tests/test_reference_library.py`, `docs/user/reference_data.md`, `docs/reviews/workplan.md`.

---

## 2025-10-17 01:45 – Remote data focus & cache library

**Author**: agent

**Context**: Remote catalogue reliability, cache UX, and documentation hygiene.

**Summary**: Rewired the Remote Data dialog to send provider-specific queries
(`spectra` vs `target_name`) and patched the download path so `mast:` URIs flow
through `astroquery.Observations.download_file`. Added regression coverage for
the translation/downloader. Introduced a Library dock that lists cached
artefacts via `LocalStore.list_entries()` so we can reload spectra without
polluting the knowledge log with raw file paths; updated `_ingest_path` and the
remote import hook to log concise summaries instead. Added a trace-colour mode
toggle (palette vs uniform) and refreshed user docs plus `docs/link_collection.md`
to keep the spectroscopy focus explicit.

**References**: `app/ui/remote_data_dialog.py`, `app/services/remote_data_service.py`,
`app/main.py`, `tests/test_remote_data_service.py`, `docs/user/remote_data.md`,
`docs/user/importing.md`, `docs/user/plot_tools.md`, `docs/user/reference_data.md`,
`docs/link_collection.md`, `docs/reviews/workplan.md`.

---

## 2025-10-16 23:10 – Remote Data Ingestion

**Author**: agent

**Context**: Remote catalogue search, caching, and UI integration.

**Summary**: Introduced a `RemoteDataService` that wraps NIST ASD and MAST lookups with dependency guards so optional `requests`/`astroquery` imports fail gracefully while cached downloads record provider URIs, checksums, and fetch timestamps in `LocalStore`.【F:app/services/remote_data_service.py†L1-L231】 Added a **File → Fetch Remote Data…** dialog that previews metadata, streams downloads through the standard ingest pipeline, and emits history entries for each remote import while logging the session status bar and knowledge log.【F:app/ui/remote_data_dialog.py†L1-L129】【F:app/main.py†L66-L896】 Documented the workflow, highlighted that remote imports behave like local overlays, updated patch notes, and wrote regression tests that mock remote APIs to assert URL construction, cache reuse, and provenance payloads.【F:docs/user/remote_data.md†L1-L52】【F:docs/user/plot_tools.md†L33-L37】【F:docs/history/PATCH_NOTES.md†L1-L9】【F:tests/test_remote_data_service.py†L1-L120】

**References**: `app/services/remote_data_service.py`, `app/ui/remote_data_dialog.py`, `app/main.py`, `tests/test_remote_data_service.py`, `docs/user/remote_data.md`, `docs/user/plot_tools.md`, `docs/history/PATCH_NOTES.md`.

---

## 2025-10-15 04:18 – Reference Regeneration Tooling

**Author**: agent

**Context**: Build scripts and provenance scaffolding for reference assets.

**Summary**: Added reproducible build scripts for hydrogen, IR bands, and JWST quick-look spectra so future refreshes capture generator metadata, retrieval timestamps, and pipeline settings inside each JSON asset.【F:tools/reference_build/build_jwst_quicklook.py†L1-L100】【F:docs/dev/reference_build.md†L1-L82】 Updated the reference guide to surface provenance fields in the inspector, noting the pending JWST pipeline replacement that we’ll link to the roadmap/workplan entry once updated.【F:docs/user/reference_data.md†L20-L63】【F:docs/reviews/workplan.md†L139-L148】

**References**: `tools/reference_build/build_jwst_quicklook.py`, `docs/dev/reference_build.md`, `docs/user/reference_data.md`, `docs/reviews/workplan.md`.

---

## 2025-10-15 07:05 – Reference Plotting & Multi-Import Workflow

**Author**: agent

**Context**: Inspector plot integration and batch ingest UX.

**Summary**: Ensured the Reference tab renders hydrogen bars, IR bands, and JWST curves inside an embedded plot while enabling File → Open to select multiple spectra in one pass; overlay toggles now mirror the active dataset without desynchronising the preview.【F:app/main.py†L900-L1040】 The smoke workflow regression covers the end-to-end path—instantiating the docs tab, plotting reference datasets, toggling overlays, and exporting manifests—which we’ll tie back to refreshed planning docs when available.【F:tests/test_smoke_workflow.py†L30-L142】【F:docs/reviews/workplan.md†L155-L160】

**References**: `app/main.py`, `tests/test_smoke_workflow.py`, `docs/reviews/workplan.md`.

---

## 2025-10-15 07:18 – Reference Overlay Fixes

**Author**: agent

**Context**: Overlay toggle persistence and documentation updates.

**Summary**: Patched the Reference inspector so combo-box selections stick, JWST datasets draw their sampled spectra, and overlay toggles follow the active dataset rather than the first entry, keeping the main plot and preview in sync.【F:app/main.py†L953-L1074】 Updated the reference guide to explain the synchronized overlay workflow and queued doc screenshot refreshes in the workplan backlog—link to be backfilled post-update.【F:docs/user/reference_data.md†L64-L77】【F:docs/reviews/workplan.md†L10-L14】

**References**: `app/main.py`, `docs/user/reference_data.md`, `docs/reviews/workplan.md`.

---

## 2025-10-15 07:45 – Reference Plotting & Importer Profile Swap

**Author**: agent

**Context**: Session persistence for reference selection and importer safeguards.

**Summary**: Persisted reference combo selections across sessions so JWST targets and IR overlays stay active after restarts while bolstering the importer’s profile-based safeguards that prevent jittery axes from being overwritten by monotonic intensity exports.【F:app/main.py†L961-L1040】【F:app/services/importers/csv_importer.py†L193-L200】 Regression coverage keeps combo changes, overlay payload swaps, and importer rationale in check; roadmap/workplan link will be backfilled once refreshed.【F:tests/test_smoke_workflow.py†L72-L96】【F:tests/test_csv_importer.py†L66-L133】【F:docs/reviews/workplan.md†L24-L32】

**References**: `app/main.py`, `app/services/importers/csv_importer.py`, `tests/test_smoke_workflow.py`, `tests/test_csv_importer.py`, `docs/reviews/workplan.md`.

---

## 2025-10-16 21:45 – Knowledge Log Automation

**Author**: agent

**Context**: KnowledgeLogService instrumentation and in-app history browser.

**Summary**: Built a reusable KnowledgeLogService that appends structured, provenance-ready events to the consolidated log (or a redirected runtime file), added filters/export helpers, and instrumented imports, overlays, exports, and math operations so SpectraMainWindow records session activity automatically. Surfaced the new History dock with search/filter controls and backed the flow with unit plus integration coverage.

**References**: `app/services/knowledge_log_service.py`, `app/main.py`, `tests/test_knowledge_log_service.py`, `tests/test_smoke_workflow.py`, `docs/history/PATCH_NOTES.md`.

---

## 2025-10-15 08:18 – Raw Intensity Defaults & Overlay Label Stacking

**Author**: agent

**Context**: Plot unit defaults and IR overlay readability.

**Summary**: Restored plot traces to display their source intensity units by default so `%T`, absorbance, and transmittance series remain untouched until operators choose normalization, with the plot pane wiring conversions accordingly.【F:app/ui/plot_pane.py†L258-L303】 Tightened overlay application so IR bands reuse the active dataset payload and stack labels within the band bounds, preventing collisions when multiple functional groups align.【F:app/main.py†L1496-L1686】 Tests assert raw unit preservation and stacked label spacing; the reference guide highlights the behaviour while awaiting updated roadmap/workplan links for documentation follow-ups.【F:tests/test_smoke_workflow.py†L144-L164】【F:tests/test_reference_ui.py†L62-L139】【F:docs/user/reference_data.md†L26-L37】【F:docs/reviews/workplan.md†L4-L8】

**References**: `app/ui/plot_pane.py`, `app/main.py`, `tests/test_smoke_workflow.py`, `tests/test_reference_ui.py`, `docs/user/reference_data.md`, `docs/reviews/workplan.md`.

---

## 2025-10-15 08:42 – Reference Selection & Importer Layout Cache

**Author**: agent

**Context**: Reference inspector state management and importer caching.

**Summary**: Fixed the Reference inspector so combo changes drive both the preview plot and overlay payloads, eliminating stale datasets when switching between hydrogen, IR, and JWST entries.【F:app/main.py†L953-L1074】 Added a session layout cache to the CSV importer so previously classified header arrangements reuse their confirmed column order while still validating cache hits before applying them.【F:app/services/importers/csv_importer.py†L163-L185】 Regression coverage locks in cache behaviour and overlay anchoring; roadmap/workplan linkage will be filled in once the updated planning doc lands.【F:tests/test_csv_importer.py†L92-L134】【F:tests/test_reference_ui.py†L90-L200】【F:docs/reviews/workplan.md†L6-L9】

**References**: `app/main.py`, `app/services/importers/csv_importer.py`, `tests/test_csv_importer.py`, `tests/test_reference_ui.py`, `docs/reviews/workplan.md`.

---

## 2025-10-15 09:10 – Importing Guide Provenance Appendix

**Author**: agent

**Context**: User documentation for export bundles.

**Summary**: Expanded the importing guide with a provenance export appendix that walks through manifest contents, canonical CSVs, copied sources, and log expectations, reinforcing the bundle hardening captured earlier.【F:docs/user/importing.md†L92-L111】 Will backfill direct roadmap/workplan links to this documentation sprint once the refreshed planning artifacts are available.【F:docs/reviews/workplan.md†L11-L14】

**References**: `docs/user/importing.md`, `docs/reviews/workplan.md`.

---

## 2025-10-15 18:45 – Reference Overlay Crash Fixes

**Author**: agent

**Context**: Startup stability and overlay resilience.

**Summary**: Deferred unit toolbar initialization and hardened overlay refresh logic so the Reference tab no longer crashes during startup, handles Unicode wavenumber tokens, and keeps the main plot responsive while default samples load.【F:app/main.py†L144-L156】【F:app/main.py†L1496-L1551】 The smoke test exercises launch plus overlay toggles to confirm clean startup; I’ll append roadmap/workplan links documenting this stabilization once those updates are published.【F:tests/test_smoke_workflow.py†L30-L101】【F:docs/reviews/workplan.md†L6-L9】

**References**: `app/main.py`, `tests/test_smoke_workflow.py`, `docs/reviews/workplan.md`.

---

## 2025-10-16 13:50 – Reference UI Overlay State

**Author**: agent

**Context**: Reference inspector overlay cleanup and regression coverage.

**Summary**: Collapsed duplicate overlay attribute initialisation in the preview shell and introduced `_reset_reference_overlay_state()` so every clear path shares a single bookkeeping helper, keeping the payload dictionary and annotation list stable across toggles.【F:app/main.py†L60-L75】【F:app/main.py†L174-L192】【F:app/main.py†L229-L244】 Added a GUI regression test that flips the overlay checkbox to assert the payload object survives clears, preventing future refactors from dropping labels mid-session.【F:tests/test_reference_ui.py†L8-L118】 Updated the plotting guide and patch notes to call out the single-source overlay state for operators tracking behaviour changes.【F:docs/user/plot_tools.md†L58-L74】【F:docs/history/PATCH_NOTES.md†L1-L12】

**References**: `app/main.py`, `tests/test_reference_ui.py`, `docs/user/plot_tools.md`, `docs/history/PATCH_NOTES.md`.

---

## 2025-10-16 14:30 – Local Cache Integration

**Author**: agent

**Context**: Automatic LocalStore writes and persistence controls for ingest.

**Summary**: Updated the ingest pipeline to accept a shared `LocalStore`,
recording canonical-unit provenance for every import and annotating spectra with
cache metadata so repeated loads reuse prior manifests.【F:app/services/data_ingest_service.py†L11-L72】 Wired the preview shell
to construct the store, expose an environment override and menu toggle for
persistence, and feed the instance into manual and sample ingest paths.【F:app/main.py†L1-L131】 Regression coverage now mocks the
store to confirm `record` invocations and metadata reuse, and the importing guide
and patch notes document the automatic caching behaviour and opt-out flow.【F:tests/test_cache_index.py†L1-L123】【F:docs/user/importing.md†L7-L38】【F:docs/history/PATCH_NOTES.md†L1-L10】

**References**: `app/services/data_ingest_service.py`, `app/main.py`,
`tests/test_cache_index.py`, `docs/user/importing.md`, `docs/history/PATCH_NOTES.md`.

---

## 2025-10-16 23:55 – Plot LOD Preference Control

**Author**: agent

**Context**: User-configurable downsampling budget for the plot pane.

**Summary**: Added a persisted "LOD point budget" spinner to the Inspector Style tab so analysts can adjust the downsampling envelope between 1k and 1M samples without leaving the session; the control writes through `QSettings` and immediately refreshes visible traces.【F:app/main.py†L76-L116】【F:app/main.py†L214-L275】【F:app/main.py†L410-L520】 Updated `PlotPane` to accept a constructor-provided limit, clamp invalid values, and expose a setter that re-renders existing traces on change.【F:app/ui/plot_pane.py†L35-L304】 Extended the plot performance stub to assert overrides and clamping, keeping the peak-envelope decimator aligned with the configured budget.【F:tests/test_plot_perf_stub.py†L14-L63】 Documented the new preference in the plotting guide and patch notes for operator awareness.【F:docs/user/plot_tools.md†L56-L65】【F:docs/history/PATCH_NOTES.md†L3-L8】

**References**: `app/main.py`, `app/ui/plot_pane.py`, `tests/test_plot_perf_stub.py`, `docs/user/plot_tools.md`, `docs/history/PATCH_NOTES.md`.

---

## 2025-10-17 02:30 – Remote Data & Documentation Map

**Author**: agent

**Context**: Remote catalogue UX hardening and documentation continuity.

**Summary**: Fixed the Remote Data dialog crash triggered by an undefined provider-change slot, enforced spectroscopic defaults for MAST searches (`dataproduct_type="spectrum"`, `intentType="SCIENCE"`, `calib_level=[2, 3]`), and filtered out imaging products via `_is_spectroscopic` so remote results stay aligned with laboratory comparisons.【F:app/ui/remote_data_dialog.py†L30-L219】【F:app/services/remote_data_service.py†L111-L212】 Added a Qt smoke test plus extended regression coverage to assert the injected filters, refreshed the remote-data user guide with the new hints, and published a developer documentation map so future agents can locate the operating manual, link collection, and workplan without guesswork.【F:tests/test_remote_data_dialog.py†L1-L75】【F:tests/test_remote_data_service.py†L1-L125】【F:docs/user/remote_data.md†L1-L99】【F:docs/developer_notes.md†L1-L42】【F:docs/history/PATCH_NOTES.md†L1-L17】

**References**: `app/ui/remote_data_dialog.py`, `app/services/remote_data_service.py`, `tests/test_remote_data_dialog.py`, `tests/test_remote_data_service.py`, `docs/user/remote_data.md`, `docs/developer_notes.md`, `docs/history/PATCH_NOTES.md`.

---

## 2025-10-17 03:45 – Knowledge Log Hygiene

**Author**: agent

**Context**: Import bookkeeping and history retention.

**Summary**: Added a non-persistent mode to `KnowledgeLogService.record_event` so
routine Import/Remote Import notifications stay in the in-app History dock
without appending to the canonical log. Updated `SpectraMainWindow` ingest hooks
to call `persist=False`, refreshed the regression suite to cover the new flag,
and confirmed the knowledge log contains only curated summaries.

**References**: `app/services/knowledge_log_service.py`, `app/main.py`,
`tests/test_knowledge_log_service.py`.

---

## 2025-10-17 04:30 – Knowledge Log Runtime Guard

**Author**: agent

**Context**: Knowledge-log policy enforcement and historical cleanup.

**Summary**: Hardened `KnowledgeLogService.record_event` so Import/Remote Import
components are always treated as runtime-only—even if callers forget to disable
persistence—by registering a default runtime-only component set. Extended the
regression suite to verify the guard and to allow opt-in overrides for tests,
then audited `docs/history/KNOWLEDGE_LOG.md` to ensure no automation-generated
Import/Remote Import entries remain after the cleanup.

**References**:
- `app/services/knowledge_log_service.py`
- `tests/test_knowledge_log_service.py`
- `docs/history/PATCH_NOTES.md`
- `docs/reviews/workplan.md`

---
## 2025-10-19T20:12:10-04:00 / 2025-10-20T00:12:10+00:00 – History dock default hidden

**Author**: agent

**Context**: UI layout polish requested after the History panel continued to force the workspace to shrink when browsing datasets.

**Summary**: Updated `SpectraMainWindow` so the History dock is constructed but hidden on launch, keeping the inspector and plot panes stable until analysts explicitly open the log from the View menu. Documented the new default in the plot tools guide and logged the behaviour change in patch notes.

**References**:
- `app/main.py`
- `docs/user/plot_tools.md`
- `docs/history/PATCH_NOTES.md`

---
## 2025-10-19T20:27:48-04:00 / 2025-10-20T00:27:48+00:00 – Library dock hint elision & numpy compatibility

**Author**: agent

**Context**: Library selections continued to stretch the Data dock over the log view and CI reported missing numpy wheels on Python 3.10/3.11.

**Summary**: Locked the Library splitter, elided hint paths, and added tooltips so cached entries no longer resize the dock when browsing stored spectra. Relaxed the numpy requirement to `>=1.26,<2` to align with the wheels published for GitHub Actions, keeping the test matrix green. Documented the UI tweak in the importing guide and added corresponding patch notes.

**References**:
- `app/main.py`
- `docs/user/importing.md`
- `requirements.txt`
- `docs/history/PATCH_NOTES.md`

---
## 2025-10-19T20:41:06-04:00 / 2025-10-20T00:41:06+00:00 – Library detail panel horizontal layout

**Author**: agent

**Context**: Selecting cached spectra still caused the Data dock to elongate vertically, hiding the bottom log panel despite the earlier splitter guard.

**Summary**: Swapped the Library splitter to a horizontal arrangement, fixed minimum widths for the table and detail pane, and updated the user guides so cached metadata renders beside the table without expanding downward. This keeps the log dock visible while preserving access to provenance details.

**References**:
- `app/main.py`
- `docs/user/importing.md`
- `docs/user/remote_data.md`
- `docs/history/PATCH_NOTES.md`

---
## 2025-10-19T22:08:48-04:00 / 2025-10-20T02:08:48+00:00 – Library hint clamp & dependency pin

**Author**: agent

**Context**: Loading cached spectra continued to stretch the application window because the hint label expanded vertically, and Windows installs still reported NumPy build errors when Visual Studio tooling was missing.

**Summary**: Restricted the Library hint label to a fixed-height strip so selections no longer raise the main window minimum size, and pinned NumPy to 1.26.4 while widening the requests cap so pip pulls prebuilt wheels on Windows. This keeps the UI stable and restores the one-command dependency install flow documented for analysts.

**References**:
- `app/main.py`
- `requirements.txt`
- `docs/history/PATCH_NOTES.md`

---
## 2025-10-20T15:05:18-04:00 / 2025-10-20T19:05:18+00:00 – CI binary wheels & timestamp guidance sync

**Author**: agent

**Context**: GitHub Actions on Windows continued to compile NumPy from source despite local guidance to prefer wheels, and the master prompt still listed Unix-only timestamp commands.

**Summary**: Updated the CI workflow to install dependencies with `--prefer-binary`, ensuring Windows runners reuse prebuilt wheels. Extended the master prompt’s time-discipline section with Windows PowerShell and Python fallback commands so onboarding docs stay consistent with the agent manual.

**References**:
- `.github/workflows/ci.yml`
- `docs/history/MASTER PROMPT.md`
- `docs/history/PATCH_NOTES.md`

---
## 2025-10-20T19:47:28-04:00 / 2025-10-20T23:47:28+00:00 – Remote data background workers

**Author**: agent

**Context**: Remote catalogue searches and downloads still ran on the UI thread, freezing the Spectra shell during long MAST responses and leaving no documented guidance for the responsive workflow.

**Summary**: Introduced background worker threads that keep the Remote Data dialog responsive while searches/downloads run, gated controls and aggregated warnings to surface once jobs finish, and updated the user guide plus Qt smoke tests to reflect the asynchronous behaviour.

**References**:
- `app/ui/remote_data_dialog.py`
- `tests/test_remote_data_dialog.py`
- `docs/user/remote_data.md`
- `docs/history/PATCH_NOTES.md`

---
## 2025-10-20T20:08:57-04:00 / 2025-10-21T00:08:57+00:00 – PySide6 signal guard

**Author**: agent

**Context**: Launching Spectra on Windows with PySide6 still failed because the Remote Data dialog attempted to read `QtCore.pyqtSignal`, which does not exist for PySide bindings.

**Summary**: Added a binding-aware helper that prefers `QtCore.Signal` when present and only falls back to `pyqtSignal` on PyQt, preventing the startup crash while keeping developer fallbacks intact.

**References**:
- `app/ui/remote_data_dialog.py`
- `docs/history/PATCH_NOTES.md`

---
## 2025-10-20T20:26:50-04:00 / 2025-10-21T00:26:50+00:00 – Remote data progress indicator fix

**Author**: agent

**Context**: Launching the Remote Data dialog raised a `NameError` because `_build_ui` referenced an undefined `progress_container`, leaving the status banner without its intended layout while the documentation already described a progress display.

**Summary**: Introduced an explicit progress layout housing a busy progress bar beside the status label and wired the search/download workflows to toggle it so asynchronous jobs expose their state without crashing at startup.

**References**:
- `app/ui/remote_data_dialog.py`
- `docs/user/remote_data.md`
- `docs/history/PATCH_NOTES.md`

---
---
## 2025-10-21T19:20:08-04:00 / 2025-10-21T23:20:10+00:00 – ExoSystems preview hardening

**Author**: agent

**Context**: Selecting planets with missing discovery years raised `ValueError` in the Remote Data dialog, and Exo.MAST file-list calls double-encoded planet names containing spaces, preventing metadata from resolving.

**Summary**: Added NaN-aware coercion before formatting discovery years and removed the redundant `%20` replacement ahead of URL quoting so Exo.MAST lookups succeed for common targets like WASP-39 b while the preview stays stable on incomplete records.

**References**:
- `app/ui/remote_data_dialog.py`
- `app/services/remote_data_service.py`
- `docs/user/remote_data.md`
- `docs/history/PATCH_NOTES.md`

