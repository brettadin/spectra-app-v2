# Knowledge Log (Concise)

This file is the concise, human-curated history for Spectra App. Routine automation events (e.g., Ingest, Remote Import) are no longer persisted here. See the archive below for the full historical record.

- Full archive snapshot (frozen): `docs/history/KNOWLEDGE_LOG_ARCHIVE_2025-11-01.md`

## Usage and Policy

- Scope: Summarize meaningful decisions, fixes, features, and lessons learned.
- Format: Use the template below. Keep entries short (5–10 lines) and link to code, tests, or docs.
- Automation: KnowledgeLogService persists only curated events. Routine events must set `persist=False` (enforced by default).
- Provenance: Prefer linking to PRs/commits and specs; include brief rationale and impact.

### Entry template

## YYYY-MM-DD HH:MM – [Component]

**Author**: human or agent name

**Context**: What part of the system this refers to (e.g., Units, Importers, UI).

**Summary**: What changed, why it mattered, and the outcome. Keep it concise.

**References**: Relative links to files, PRs, tests, or external docs.

---

## 2025-11-01 15:00 – Knowledge log pruning and policy reset

**Author**: agent (GitHub Copilot)

**Context**: History hygiene and clarity.

**Summary**: Archived the previous, lengthy knowledge log to a dated snapshot and reset this file to a concise, curated log. Routine automation (Ingest/Remote Import) no longer writes here; only meaningful summaries should be added going forward.

**References**: `docs/history/KNOWLEDGE_LOG_ARCHIVE_2025-11-01.md`, `app/services/knowledge_log_service.py`, `app/main.py`.
# Consolidated Knowledge Log

This file serves as the single entry point for all historical notes, patches,
"brains" and "atlas" logs.  Previous iterations of Spectra‑App stored
information in many places (e.g. `brains`, `atlas`, `PATCHLOG.txt`) and often
used confusing naming schemes (sometimes based on the day of the month).
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
  citation markers like  for primary documentation where
  applicable).

---

## 2025-10-31T19:38:48-04:00 / 2025-10-31T23:38:48+00:00 – PDS Downloader Refinement for MESSENGER MASCS Data

**Author**: agent (GitHub Copilot)

**Context**: Data acquisition pipeline improvements for Mercury spectroscopy research. Tightening download criteria to ensure MESSENGER MASCS data is comparable and relevant for educational/research spectroscopic analysis.

**Summary**: Refined the native Python PDS downloader (`tools/pds_downloader_native.py`) to implement stricter filtering of MESSENGER MASCS optical spectroscopy data from the PDS Geosciences archive. The changes address the user's goal of ensuring downloaded data is directly comparable to their research needs by filtering out engineering files, headers, and non-spectroscopic data products.

**Key Changes**:
1. **Dataset URL Refinement**: Updated base URLs to point directly to specific data product directories (CDR/DDR subdirectories) rather than broad `/data/` paths. This reduces unnecessary scanning of metadata and documentation directories.

2. **Dataset Quality Upgrade**: Replaced EDR (Experimental Data Record, raw) datasets with DDR (Derived Data Record, surface reflectance) datasets:
   - UVVS: DDR provides binned, high-quality surface reflectance (~500 MB vs ~1 GB raw)
   - VIRS: DDR provides derived surface reflectance (~3 GB vs ~10 GB raw)
   - DDR products have better signal-to-noise and are more suitable for comparative spectroscopy

3. **Pattern-Based Filtering**: Implemented three-stage filtering system:
   - **Stage 1**: File type check (`.DAT`, `.LBL`, `.FMT`)
   - **Stage 2**: Required patterns (must match at least one MASCS science file prefix)
   - **Stage 3**: Exclude patterns (must not match any engineering/metadata files)
   
   Science file patterns for MESSENGER MASCS:
   - UVVS CDR: `ufc_` (FUV 115-190nm), `umc_` (MUV 160-320nm), `uvc_` (VIS 250-600nm)
   - VIRS CDR: `vnc_` (NIR 850-1450nm), `vvc_` (VIS 300-1050nm)
   - UVVS DDR: `uvs_`, `uvd_` (derived products)
   - VIRS DDR: `vnd_`, `vvd_` (derived products)
   
   Excluded patterns: `_hdr.dat` (headers), `_eng.dat` (engineering), `index`, `catalog` (metadata)

4. **Enhanced Reporting**: Added `filtered_count` metric to download summary showing how many files were excluded by pattern filters, providing visibility into filtering effectiveness.

**Issues Encountered**:
- 404 error when accessing the updated UVVS CDR URL during dry-run testing
- Estimated dataset size shown as ~2 GB but no files were accessible at the specified path
- Indicates potential issues with PDS archive URL structure or data reorganization

**Documentation Created**:
- Comprehensive worklog entry (`docs/dev/worklog/2025-10-31_pds_downloader_refinement.md`) documenting:
  - Detailed explanation of all changes and their rationale
  - MESSENGER MASCS file naming conventions
  - Technical details of the three-stage filtering implementation
  - Analysis of the 404 error and investigation steps
  - Recommendations for future improvements (URL discovery tool, API integration, resume capability)
  - References to PDS archive locations and related tools

**Next Steps**:
- Manual verification of PDS archive URL structure by browsing the website
- Testing alternative URL paths (e.g., `/data/uvvs/` without `cdr` subdirectory)
- Potentially updating `tools/parse_messenger_mascs.py` to handle DDR format if different from CDR
- Considering integration with PDS API for more reliable data access

**Impact**: These changes ensure that when the URL issue is resolved, the downloader will acquire only high-quality spectroscopic data suitable for comparative analysis, reducing storage requirements and processing time while maintaining scientific value.

**References**: `tools/pds_downloader_native.py`, `docs/dev/worklog/2025-10-31_pds_downloader_refinement.md`, `docs/history/PATCH_NOTES.md`, `docs/Telescope-Based Planetary datasets.md`, `tools/parse_messenger_mascs.py`, `tools/pipeline_master.py`.

---

## 2025-10-25T10:30:18-04:00 / 2025-10-25T14:30:20+00:00 – IR functional group provenance backfill

**Author**: agent (GitHub Copilot)

**Context**: Documentation and provenance for the expanded IR functional groups database and ML roadmap assets.

**Summary**: Reconstructed the historical record for the previously undocumented IR functional group expansion. Added patch notes summarising the shipped 50+ group dataset (`app/data/reference/ir_functional_groups_extended.json`) and the runtime auto-detection behaviour in `ReferenceLibrary`. Cross-referenced the ML integration design (`docs/specs/ml_functional_group_prediction.md`), atlas additions, and the 2025-10-25 brains entry to keep provenance aligned with the delivered assets. Verified that README and `IR_EXPANSION_SUMMARY.md` already surface the same messaging so contributors have a single source of truth across guides.

**References**: `docs/history/PATCH_NOTES.md`, `docs/brains/2025-10-25T0230-ir-ml-integration.md`, `IR_EXPANSION_SUMMARY.md`, `docs/specs/ml_functional_group_prediction.md`, `app/services/reference_library.py`.

---

## 2025-10-24T22:30:00-04:00 / 2025-10-25T02:30:00+00:00 – IR Functional Groups Database Expansion and ML Integration Documentation

**Author**: agent (GitHub Copilot)

**Context**: Reference data library expansion with comprehensive IR functional groups database and machine learning integration roadmap for automated functional group prediction.

**Summary**: Documented the comprehensive expansion of IR functional groups reference data from 8 to 50+ groups, including hydroxyl, carbonyl, amine, aromatic, aliphatic, nitrogen, sulfur, and halogen families. The extended database (`app/data/reference/ir_functional_groups_extended.json`) includes rich metadata for each group: wavenumber ranges (min, max, peak), intensity descriptions, vibrational modes, chemical classes, related groups, diagnostic value ratings, and identification notes. The database is ML-ready with relationship mapping and structured for future neural network training.

Created comprehensive ML integration design document (`docs/specs/ml_functional_group_prediction.md`) outlining a phased implementation approach:
- **Phase 1**: Enhanced rule-based peak detection using scipy (4 weeks)
- **Phase 2**: Data collection from NIST WebBook and SDBS (~52K spectra) with RDKit label generation (6 weeks)  
- **Phase 3**: Neural network prototype with 1D CNN and attention mechanisms (8 weeks)
- **Phase 4**: Integration and UI with "Analyze Functional Groups" panel (4 weeks)
- **Phase 5**: Hybrid ensemble combining rule-based and ML predictions (4 weeks)

Modified `app/services/reference_library.py` to automatically detect and use extended database when available, falling back to basic 8-group database for backward compatibility. This approach maintains provenance-first architecture while enabling future ML-powered identification with explainable predictions.

Research incorporated from FG-BERT (idrugLab) transformer-based approach and FTIR prediction neural networks (aaditagarwal). Performance targets established: rule-based (80% precision, 70% recall), neural network (90% precision, 85% recall), ensemble (92% precision, 88% recall).

This expansion directly supports the educational use case of comparing lab-collected IR/FTIR spectra with planetary/stellar observations for molecular identification, providing students with comprehensive reference data for functional group analysis.

**References**: `app/data/reference/ir_functional_groups_extended.json`, `docs/specs/ml_functional_group_prediction.md`, `app/services/reference_library.py`, `IR_EXPANSION_SUMMARY.md`, `docs/brains/2025-10-25T0230-ir-ml-integration.md`, `docs/atlas/chapter_7_identification_and_prediction_logic.md`.

---

## 2025-10-24T16:07:16-04:00 / 2025-10-24T20:07:16+00:00 – Main module import path fix

**Author**: agent (GitHub Copilot)

**Context**: Application entry point (`app/main.py`) import resolution for direct script execution.

**Summary**: Fixed `ModuleNotFoundError: No module named 'app'` when running `app/main.py` directly (e.g., via VS Code debugger with `python app/main.py`). The issue was caused by a duplicate docstring at lines 15-20 and improper import ordering. The path adjustment code (`sys.path.insert(0, ...)`) was present at line 24 but came after the imports were already parsed. Simplified the file by removing the duplicate docstring and duplicate `from typing import Any` import. The fix ensures both execution modes work:
- **Module mode** (preferred): `python -m app.main`
- **Direct mode** (IDE/debugger): `python app/main.py`

Added `tests/test_main_import.py` to verify both import mechanisms work correctly. All existing tests continue to pass.

**References**: `app/main.py`, `tests/test_main_import.py`, `docs/history/PATCH_NOTES.md`.

---

## 2025-10-23T00:49:35-04:00 / 2025-10-23T04:49:35+00:00 – Test suite maintenance and numpy deprecation cleanup

**Author**: agent (GitHub Copilot)

**Context**: Test suite integrity and numpy API modernization.

**Summary**: Fixed failing test `test_download_mast_uses_astroquery` by updating the mock `DummyObservations.download_file()` to accept the `local_path` parameter that was added to the real astroquery.mast API. This parameter is used by `RemoteDataService._fetch_via_mast()` to specify a temporary download directory. Also replaced all instances of deprecated `np.trapz()` with `np.trapezoid()` in `app/services/overlay_service.py` and `tests/test_overlay_service.py` to eliminate deprecation warnings from numpy 2.x. These changes ensure the test suite remains clean and aligned with current dependencies.

**References**: `tests/test_remote_data_service.py`, `app/services/overlay_service.py`, `tests/test_overlay_service.py`, `docs/history/PATCH_NOTES.md`.

---

## 2025-10-22T00:34:36-04:00 / 2025-10-22T04:34:39+00:00 – Numpy bootstrap recursion guard

**Author**: agent

**Context**: CI/runtime bootstrap for ensuring numpy availability.

**Summary**: Adjusted the `sitecustomize.py` installer to clone the current environment and inject `SPECTRA_SKIP_AUTO_NUMPY=1`
into the child `python -m pip` invocation. This ensures the bootstrap only executes in the parent interpreter, preventing the
recursive Python→pip spawn loop that occurred when numpy was missing. Pip can now proceed with installation instead of repeatedly
restarting the interpreter.

**References**: `sitecustomize.py`, `docs/history/PATCH_NOTES.md`.

---

## 2025-10-21T20:53:07-04:00 / 2025-10-22T00:53:07+00:00 – CI round-trip numpy bootstrap

**Author**: agent

**Context**: CI round-trip pytest job pulling in Spectra services.

**Summary**: Added a pytest `conftest.py` bootstrap that mirrors the runtime
`sitecustomize` installer so the GitHub Actions round-trip workflow installs
`numpy>=1.26,<3` before importing service modules while retaining the FITS
ingestion fixture used by smoke tests. Exported `ensure_numpy()` and the shared
`NUMPY_SPEC` constant from `sitecustomize.py` to avoid duplicating the
dependency specification and allow future tooling to reuse the installer.
Failures now surface as a `pytest.UsageError` instructing operators to install
numpy manually when the automation is disabled.

**References**: `tests/conftest.py`, `sitecustomize.py`, `docs/history/PATCH_NOTES.md`

---

## 2025-10-21T20:44:44-04:00 / 2025-10-22T00:44:41+00:00 – Remote Data dialog Qt signal fallback

**Author**: agent

**Context**: Remote Data dialog compatibility with PySide6 runtime.

**Summary**: Adjusted the Qt signal/slot alias detection in `remote_data_dialog.py` so PySide6 builds resolve `QtCore.Signal`
  and `QtCore.Slot` without trying to access PyQt-specific names. The dialog now tests for the native attributes before
  requesting `pyqtSignal`/`pyqtSlot`, eliminating the `AttributeError` that prevented the application from starting on the
  packaged PySide6 environment. Documented the fix in the patch notes and workplan so future agents know the regression cause
  and mitigation.

**References**: `app/ui/remote_data_dialog.py`, `docs/history/PATCH_NOTES.md`, `docs/reviews/workplan.md`.

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