# Patch Notes

## 2025-11-03 (Calibration UI, Global normalisation, Y‑scale, NaN‑robust scales)
- Reference overlays
  - NIST bars now rescale when zooming or after normalization changes and draw behind traces (reduced clutter).
  - Bars anchor to y=0 when visible to avoid negative offsets.
  - Each pinned set receives a distinct colour; double‑click a pin in the list to remove it.
  - Library view gained a “Samples” section listing files for one‑click ingest.


Display‑time calibration and visibility improvements

- Added a lightweight Calibration tab (Inspector) that applies FWHM blurring and radial‑velocity (RV km/s) shifts at display time in nm‑space. The transform precedes normalisation and plotting; underlying data remains unchanged.
- Introduced a Global checkbox next to the Normalize control. When enabled, a single factor is computed across all visible spectra:
  - Max: finite‑only max(|y|) across traces
  - Area: sum of per‑trace absolute areas (index‑based integration to match tests)
- Added Y‑scale transforms applied after normalisation to improve dynamic‑range visibility: Linear (identity), Log10 (signed log: sign(y)*log10(1+|y|)), and Asinh.
- Hardened normalisation scale calculations to ignore NaNs/Infs so FITS masked values don’t collapse visibility. NaNs remain in arrays for provenance but are excluded from scale computation.
- Plot autoscale path updated to force re‑range on refresh so changes from calibration/normalisation/Y‑scale are immediately visible.

Docs & tests

- Updated `docs/user/plot_tools.md` to document Global normalisation, Y‑scale transforms, and FITS/NaN robustness.
- Refreshed `README.md` feature list to call out Calibration, Global normalisation, Y‑scale, and FITS scale robustness.
- Extended `NORMALIZATION_VERIFICATION.md` with Y‑scale notes and NaN behaviour and confirmed existing tests remain green.

Notes

- Area scaling continues to use index‑based integration to preserve current unit tests; x‑weighted integration can be revisited with adjusted expectations.
- Global factors recompute automatically on add/remove/visibility changes.

## 2025-11-02 (Capability atlas & cleanup audit) (10:43 EST / 15:43 UTC)

**Mapped active features & cleanup targets**
- Authored `docs/app_capabilities.md` to describe current UI surfaces, services, datasets, and data flows in a single long-form atlas.
- Highlighted dormant features (calibration manager, identification stack) and repository hygiene tasks so cleanup work can be scoped accurately.
- Updated the workplan, knowledge log, and worklog to keep provenance aligned with the new documentation.

## 2025-11-02 (Repository inventory audit) (10:28 EST / 15:28 UTC)

**Documented repository state**
- Authored `docs/repo_inventory.md` detailing features, library usage, and status snapshots across the app.
- Added a complete tracked-path index to aid provenance reviews and onboarding.
- Summarised outstanding backlog items (calibration, identification stack, remote providers) to align with the workplan.

## 2025-10-31 (PDS Downloader Refinement for MESSENGER MASCS Data) (19:38 EDT / 23:38 UTC)

**Tightened Download Criteria for Mercury Spectroscopy**
- Refined PDS downloader (`tools/pds_downloader_native.py`) to filter MESSENGER MASCS optical spectroscopy data more precisely
- Updated dataset URLs to point directly to specific data product directories (CDR/DDR subdirectories)
- Switched from EDR (raw) to DDR (derived surface reflectance) datasets for better quality and smaller file sizes:
  - `uvvs_ddr`: ~500 MB (was `uvvs_edr`: ~1 GB)
  - `virs_ddr`: ~3 GB (was `virs_edr`: ~10 GB)

**File Pattern Filtering**
- Added `required_patterns` to download only MASCS science files:
  - UVVS CDR: `ufc_`, `umc_`, `uvc_` (FUV/MUV/VIS channels)
  - VIRS CDR: `vnc_`, `vvc_` (NIR/VIS channels)
  - UVVS DDR: `uvs_`, `uvd_` (derived products)
  - VIRS DDR: `vnd_`, `vvd_` (derived products)
- Added `exclude_patterns` to skip non-science files:
  - `_hdr.dat` (headers), `_eng.dat` (engineering), `index`, `catalog` (metadata)
- Implemented three-stage filtering: file type → required patterns → exclude patterns
- Added `filtered_count` to summary report showing how many files were excluded

**Enhanced Dataset Descriptions**
- Added specific wavelength ranges to dataset descriptions:
  - UVVS: FUV 115-190nm, MUV 160-320nm, VIS 250-600nm
  - VIRS: VIS 300-1050nm, NIR 850-1450nm
- Clarified that downloader targets optical spectroscopy only (no engineering/housekeeping data)

**Issues Documented**
- Encountered 404 error when accessing updated UVVS CDR URL during dry run
- Created detailed worklog (`docs/dev/worklog/2025-10-31_pds_downloader_refinement.md`) documenting:
  - What was changed and why
  - File naming conventions for MASCS data
  - Issues encountered (404 error on new URL)
  - Recommendations for future investigation and improvements
  - Technical details about filter implementation

**Next Steps**
- Need to verify correct PDS archive URL structure (manual browsing of PDS website)
- Consider testing alternative URL paths or using broader directory paths
- May need to update parser (`tools/parse_messenger_mascs.py`) to handle DDR format

## 2025-10-25 (Re-authored IR functional group expansion provenance) (10:30 EDT / 14:30 UTC)

**Restored documentation for IR database expansion**
- Captured the missing provenance for the extended IR functional groups database (50+ groups) that shipped in `app/data/reference/ir_functional_groups_extended.json` but previously lacked historical notes.
- Logged how the analyzer auto-detects the extended dataset and falls back to the legacy 8-group bundle for backward compatibility (`app/services/reference_library.py`).
- Linked the supporting ML roadmap design in `docs/specs/ml_functional_group_prediction.md` so the documentation trail matches the shipped assets.

**Historical records brought back online**
- Added the companion knowledge-log entry (`docs/history/KNOWLEDGE_LOG.md`) with Eastern/UTC timestamps and cross-references to the atlas, brains entry (`docs/brains/2025-10-25T0230-ir-ml-integration.md`), and IR expansion summary.
- Noted that README and IR expansion summary already describe the dataset so future contributors see consistent messaging across guides.

## 2025-10-24 (IR Functional Groups Database Expansion and ML Integration Documentation) (22:30 EDT / 02:30 UTC)

**Extended IR Functional Groups Database (50+ groups)**
- Expanded IR functional groups reference from 8 to 50+ comprehensive groups covering:
  - Hydroxyl groups: O-H free vs hydrogen-bonded, phenolic, carboxylic
  - Carbonyl groups: ketone, aldehyde, ester, acid, amide, anhydride, acid chloride variants
  - Amine groups: primary (NH₂), secondary (NH), tertiary (N)
  - Aromatic groups: C-H stretch, C=C stretch/bending, substitution patterns
  - Aliphatic groups: sp³/sp²/sp C-H systems, alkene/alkyne
  - Nitrogen groups: nitriles (C≡N), nitro compounds (doublet), azo
  - Sulfur groups: thiols (S-H), sulfoxides (S=O), sulfones (SO₂)
  - Halogen compounds: C-F, C-Cl, C-Br, C-I
- Added rich metadata: wavenumber ranges (min/max/peak), intensity descriptions, vibrational modes, chemical classes, related groups, diagnostic value ratings, identification notes
- Structured for ML training with relationship mapping between functional groups
- Database auto-detection in `app/services/reference_library.py` - uses extended database when available, falls back to basic

**ML Integration Design Document**
- Created comprehensive roadmap at `docs/specs/ml_functional_group_prediction.md`
- Phased implementation (26 weeks total):
  - Phase 1: Enhanced rule-based peak detection with scipy (4 weeks)
  - Phase 2: Data collection from NIST/SDBS with RDKit label generation (6 weeks)
  - Phase 3: 1D CNN with attention mechanisms (8 weeks)
  - Phase 4: UI integration with confidence scores and evidence display (4 weeks)
  - Phase 5: Hybrid ensemble combining rule-based and ML (4 weeks)
- Performance targets: Rule-based (80%/70% precision/recall) → NN (90%/85%) → Ensemble (92%/88%)
- Research from FG-BERT and FTIR prediction neural networks incorporated
- Training sources: NIST WebBook (~18K spectra), SDBS (~34K spectra)

**Documentation Updates**
- Created brains entry: `docs/brains/2025-10-25T0230-ir-ml-integration.md`
- Updated Atlas Chapter 7 with IR/ML functional group identification sections
- Updated Atlas Chapter 1 with expanded IR spectroscopy coverage
- Enhanced user documentation for extended IR functional groups
- Updated workplan with ML implementation phases and milestones
- Added developer notes for ML dependencies (scipy, rdkit, tensorflow/pytorch, scikit-learn, h5py)

**File Changes**
- `app/data/reference/ir_functional_groups_extended.json` - 50+ groups with comprehensive metadata
- `docs/specs/ml_functional_group_prediction.md` - Complete ML integration design
- `IR_EXPANSION_SUMMARY.md` - Summary document at repo root
- All changes maintain provenance-first architecture and canonical unit storage (cm⁻¹ for IR)

## 2025-10-24 (Fixed ModuleNotFoundError when running main.py directly) (16:06 EDT / 20:06 UTC)

- Removed duplicate docstring in `app/main.py` (lines 15-20) that was causing confusion
- Removed duplicate `from typing import Any` import
- Fixed import order: path adjustment (`sys.path.insert`) now happens before Qt imports
- This ensures both execution modes work correctly:
  - `python -m app.main` (module import - preferred)
  - `python app/main.py` (direct execution - debugger/IDE support)
- Added `tests/test_main_import.py` to verify both import modes work

The issue occurred when running the script directly (e.g., via VS Code debugger). The path adjustment code was present but came after imports were already parsed, causing `ModuleNotFoundError: No module named 'app'`.

## 2025-10-23 (Test fixes and numpy deprecation cleanup) (00:49 EDT / 04:49 UTC)

- Fixed `test_download_mast_uses_astroquery` to accept `local_path` parameter in mock, matching real astroquery.mast API signature.
- Replaced deprecated `np.trapz()` with `np.trapezoid()` in `app/services/overlay_service.py` and corresponding test to eliminate deprecation warnings.
- All tests now pass cleanly (73 passed, 20 skipped, 0 warnings).

## 2025-10-22 (Remote Data stability, MAST fallback, and streaming ingest)

- Remote Data dialog: filters, selection guards, non-blocking thread cleanup, improved status text
- Skip non-spectral file types during bulk ingest
- MAST download stability: temp-dir isolation, persistent temp copy, direct HTTP fallback for `mast:` URIs
- NIST line search: registration fix, main-thread UI updates, local CSV generation
- In-memory ingest: `DataIngestService.ingest_bytes`

See: `docs/dev/worklog/2025-10-22.md` and neurons in `docs/brains/*`.

## 2025-10-22 (Bootstrap numpy installer avoids recursive pip launches) (00:34 EDT / 04:34 UTC)

- Updated `sitecustomize.py` to propagate `SPECTRA_SKIP_AUTO_NUMPY=1` into the child environment when invoking `python -m pip`
  so the bootstrap only runs once per interpreter. This prevents recursive subprocess spawning when numpy is missing, allowing
  pip to install the dependency instead of repeatedly launching new Python interpreters.

## 2025-10-21 (Round-trip pytest job bootstraps numpy) (20:53 EDT / 00:53 UTC)

- Added a `tests/conftest.py` bootstrap that mirrors the runtime `sitecustomize`
  installer so GitHub Actions can pull in `numpy>=1.26,<3` before test collection
  when the wheel is missing while keeping the FITS ingestion fixture intact. The
  hook raises a descriptive usage error if the automation is disabled via
  `SPECTRA_SKIP_AUTO_NUMPY`.
- Exported `ensure_numpy()` and the shared `NUMPY_SPEC` constant from
  `sitecustomize.py` so the pytest bootstrap and future tooling reuse the
  installation logic without copying the spec.
- This keeps the `pytest -k roundtrip` CI run aligned with local expectations
  and prevents service imports from failing with `ModuleNotFoundError` when
  numpy is absent.

## 2025-10-21 (Remote Data dialog Signal fallback works on PySide6) (20:44 EDT / 00:44 UTC)

- Guarded the Remote Data dialog's Qt Signal/Slot imports so PySide6 launches no longer attempt to access `pyqtSignal` and
  `pyqtSlot`. The dialog now resolves the native attribute first and only falls back to the PyQt names when present, restoring
  compatibility with the packaged PySide6 runtime.

## 2025-10-21 (Bootstrap numpy availability for tests) (20:38 EDT / 00:38 UTC)

- Added `sitecustomize.py` to auto-install `numpy>=1.26,<3` with `--prefer-binary` when the module is missing, aligning with the
  agent manual's recovery guidance and allowing CI to import Spectra services without manual intervention.
- Registered the `roundtrip` and `ui_contract` pytest markers in `pyproject.toml` so custom-marked suites no longer trigger
  warnings and round-trip checks show up under their dedicated mark.
- Ensured the new bootstrap respects `SPECTRA_SKIP_AUTO_NUMPY` for environments that pre-manage dependencies.

## 2025-10-21 (Create comprehensive real spectral data access guide) (20:17 EDT / 00:17 UTC)

- Created `docs/user/real_spectral_data_guide.md` as a comprehensive reference for accessing legitimate spectral data from credible astronomical archives.
- Documented three main categories with specific examples:
  - Solar system objects: Jupiter, Mars, Saturn and moons (JWST/HST observations, UV to mid-IR)
  - Stellar spectra: Vega (A0V standard), Tau Ceti (G8V solar analog), CALSPEC standards
  - Exoplanet spectra: WASP-39 b, TRAPPIST-1, hot Jupiters (JWST transmission/emission spectra)
- Included wavelength coverage table showing UV/visible/near-IR/mid-IR availability for each source.
- Added data quality section explaining calibration levels, provenance tracking, and proper citations.
- Clearly marked bundled JWST targets as deprecated example-only data with explicit warnings.
- Provided troubleshooting guidance and references to related documentation.
- This comprehensive guide makes it easy for users to understand what real data is available and how to access it, addressing the requirement for "real, spectral data, from a wide range of wavelengths" from "credible sources."

## 2025-10-21 (Enhance quickstart guide with remote data workflow) (20:15 EDT / 00:15 UTC)

- Updated `docs/user/quickstart.md` to include a new section on fetching real spectral data from MAST archives.
- Added step-by-step instructions for using the Remote Data dialog (File → Fetch Remote Data, Ctrl+Shift+R) with specific examples for solar system objects (Jupiter, Mars), stars (Vega, Tau Ceti), and exoplanets (WASP-39 b, TRAPPIST-1).
- Clarified that real data comes from credible sources (NASA MAST archives) and spans UV to mid-IR wavelengths (0.1–30 µm).
- This improves the logical workflow by making the Remote Data feature more discoverable in the user onboarding documentation.

## 2025-10-21 (Fix NasaExoplanetArchive import and clarify placeholder data status) (20:12 EDT / 00:12 UTC)

- Fixed `NasaExoplanetArchive` import path in `app/services/remote_data_service.py` from incorrect `from astroquery.ipac.nexsci import NasaExoplanetArchive` to correct `from astroquery.ipac.nexsci.nasa_exoplanet_archive import NasaExoplanetArchive`. This enables the MAST ExoSystems provider to work properly for fetching exoplanet and solar system spectral data.
- Updated `app/data/reference/jwst_targets.json` metadata to clearly mark the bundled JWST targets as "DEPRECATED - Example data only" with status "digitized_placeholder_deprecated" and added prominent notes directing users to fetch real calibrated spectra from MAST using the Remote Data dialog (File → Fetch Remote Data or Ctrl+Shift+R).
- Updated each JWST target's provenance from "digitized_release_graphic" to "digitized_release_graphic_example_only" with instructions on how to fetch real data (e.g., search for "Jupiter" or "WASP-96 b" in MAST ExoSystems provider).
- Updated README.md with prominent "Accessing Real Spectral Data" section highlighting solar system objects (Jupiter, Mars, Saturn), stars (Vega, Tau Ceti), and exoplanets (WASP-39 b, TRAPPIST-1) available from MAST with wavelength coverage information (UV to mid-IR, 0.1–30 µm).
- Updated test expectation in `tests/test_reference_library.py` to reflect new curation status.
- All changes align with requirement to provide real, legitimate spectral data from credible sources and avoid placeholder/synthesized data.

## 2025-10-21 (Remote Data dialog joins worker threads before closing) (19:17 EDT / 23:17 UTC)

- Ensured the Remote Data dialog calls its worker cleanup helpers during accept, reject, and close events so any in-flight search
  or download threads are joined before Qt destroys the dialog widget. (`app/ui/remote_data_dialog.py`)
## 2025-10-21 (Remote Data cancel waits asynchronously) (19:21 EDT / 23:21 UTC)

- Updated the Remote Data dialog cancel/close path to poll background search/download threads with a Qt timer so the UI stays
  responsive while we wait for synchronous network calls to finish. (`app/ui/remote_data_dialog.py`)
- Surfaced a busy indicator and status copy that explains the dialog is waiting on outstanding background tasks during shutdown.
## 2025-10-21 (Exo.MAST names and preview summary hardening) (19:25 EDT / 23:25 UTC)

- Stopped `_fetch_exomast_filelist` from double-encoding planet names so Exo.MAST
  lookups succeed for identifiers with spaces and the dialog receives citation
  metadata consistently. (`app/services/remote_data_service.py`)
- Guarded the preview summary against `NaN` discovery years and expanded the
  discovery context without crashing the Remote Data dialog. (`app/ui/remote_data_dialog.py`)
- Added regression coverage for both fixes and noted the behaviour change in the
  remote data user guide. (`tests/test_remote_data_service.py`,
  `tests/test_remote_data_dialog.py`, `docs/user/remote_data.md`)

## 2025-10-21 (Curated search skips missing bundles) (18:44 EDT / 22:44 UTC)

- Hardened the Solar System Archive search loop so missing or malformed curated manifests/assets are skipped instead of aborting
  the entire search call. (`app/services/remote_data_service.py`)
- Added regression coverage that appends broken manifests/assets to the curated roster and asserts searches still return valid
  results. (`tests/test_remote_data_service.py`)
- Documented the resilient behaviour in the Remote Data user guide so analysts know curated searches continue even when bundles
  are offline. (`docs/user/remote_data.md`)
## 2025-10-21 (Resource guide adds usage & maintenance notes) (18:42 EDT / 22:42 UTC)

- Expanded the JWST/exoplanet tooling sections in `docs/link_collection.md` with
  per-repository usage steps and maintenance tips so agents know how to run each
  pipeline and verify whether upstream dependencies are still current.
- Highlighted CRDS alignment checks for JWST notebooks/pipelines and reminded
  analysts to pin commit hashes when relying on research-grade retrieval codes.

## 2025-10-21 (Solar System Archive rename and curated bundle refresh) (18:13 EDT / 22:13 UTC)

- Renamed the curated remote provider to **Solar System Archive**, updating constants, provider lists, and cache metadata. (`app/services/remote_data_service.py`)
- Refreshed Remote Data dialog placeholders, hints, and examples to use Solar System Archive terminology. (`app/ui/remote_data_dialog.py`)
- Moved curated manifests and spectra to `samples/solar_system/`, adjusting manifest paths/descriptions plus regression tests. (`samples/solar_system/*`, `tests/test_remote_data_service.py`)
- Updated the remote data user guide and historical documentation to reflect the new label. (`docs/user/remote_data.md`, `docs/history/KNOWLEDGE_LOG.md`)
## 2025-10-21 (Remote Data dialog defers NIST to Reference dock) (18:13 EDT / 22:13 UTC)

- Added an `include_reference` flag to `RemoteDataService.providers()` and taught the Remote Data dialog to pass it so only
  MAST and curated ExoSystems catalogues surface in the combo box while the Reference dock retains NIST access.
- Removed the NIST placeholder/hint/example branch from the dialog UI and refreshed the Qt smoke tests to assert the combo
  excludes NIST, handles reference-only services gracefully, and still wires the **Include imaging** toggle for MAST.
- Documented the workflow change in the Remote Data user guide, steering ASD line-list retrieval through the Reference dock and
  clarifying how cached exports capture query parameters.
## 2025-10-21 (Remote data dialog consolidates link widgets) (18:13 EDT / 22:13 UTC)

- Consolidated the duplicate preview/download widget helpers in the Remote Data dialog so a single implementation now guards
  empty hyperlinks and preserves provider URIs in the tooltip alongside the sanitized browser link. (`app/ui/remote_data_dialog.py`)
- Added a focused regression test that instantiates the dialog with mock records to assert the rendered links and tooltips for
  both download and preview cells. (`tests/test_remote_data_dialog.py`)
- Documented the tooltip behaviour in the remote data user guide so operators know where to copy the original URI versus the
  browser-safe link. (`docs/user/remote_data.md`)

## 2025-10-21 (Link collection adds JWST/exoplanet tooling cross-references) (18:03 EDT / 22:03 UTC)

- Documented JWST analysis toolkits and exoplanet/astrochemistry packages in
  `docs/link_collection.md`, highlighting how each integrates with Spectra
  workflows.
- Cross-referenced the new sections from the Remote Data user guide so operators
  know which pipelines to run before importing JWST spectra and how to pair
  Solar System Archive manifests with retrieval tooling.
- Added developer guidance pointing to the curated notebooks/packages when
  extending ingestion scripts or choosing external dependencies.

## 2025-10-21 (Curated Solar System Archive manifests ship with citations) (17:18 EDT / 21:18 UTC)

- Added a lightweight search branch for the Solar System Archive provider so curated names map to local manifests and emit `RemoteRecord`
  entries with mission/instrument metadata and citation lists. (`app/services/remote_data_service.py`, `samples/solar_system/`)
- Wired the new provider into the Remote Data dialog with dedicated placeholders/examples and taught the preview pane to render
  citation bullets pulled from manifest metadata. (`app/ui/remote_data_dialog.py`)
- Bundled synthetic spectra/manifest pairs for each curated target and extended regression coverage to exercise the Solar System Archive
  search and download paths. (`samples/solar_system/*`, `tests/test_remote_data_service.py`)
- Documented the curated workflow in the remote data user guide and noted the enhanced preview output. (`docs/user/remote_data.md`)

## 2025-10-21 (Remote Data dialog restores NIST provider) (14:22 EDT / 18:22 UTC)

- Reintroduced the NIST ASD catalogue to the Remote Data dialog and refreshed provider hints, placeholders, and examples so
  keyword-aware element/ion parsing keeps search context in cached exports. (`app/ui/remote_data_dialog.py`)
- Extended the Qt regression suite to assert NIST availability, cover NIST-only service scenarios, and verify the query builder
  forwards `element=`/`keyword=` clauses. (`tests/test_remote_data_dialog.py`)
- Updated the remote data user guide to describe the reinstated NIST workflow and when to hand off to the Inspector’s pinned
  view for long-lived overlays. (`docs/user/remote_data.md`)

## 2025-10-21 (Fixed NumPy deprecation and pytest marker warnings) (10:04 EDT / 14:04 UTC)

- Replaced deprecated `np.trapz` with `np.trapezoid` in `overlay_service.py` and `test_overlay_service.py` to eliminate NumPy 2.x deprecation warnings.
- Added pytest marker registration in `pyproject.toml` for `roundtrip` and `ui_contract` custom marks.
- Updated normalization metadata basis from "abs-trapz" to "abs-trapezoid" for consistency.
- All 68 tests pass with 0 warnings (down from 4 warnings).

## 2025-10-21 (Added all solar system planets to curated targets) (09:57 EDT / 13:57 UTC)

- Extended `RemoteDataService._CURATED_TARGETS` to include all major solar system planets (Mercury, Venus, Earth/Moon, Uranus, Neptune) in addition to existing Mars, Jupiter, Saturn.
- Planets are now ordered from innermost to outermost following solar system structure.
- Each new planet entry includes proper classification, display names, MAST object names, and scientific citations with DOIs.
- Added comprehensive test `test_curated_targets_include_all_solar_system_planets` to validate all 8 planets are present with required metadata fields.
- All 68 tests pass (20 skipped) with new planetary data accessible via MAST remote data dialog.

## 2025-10-21 (Fixed missing records variable in MAST search) (00:30 EDT / 04:30 UTC)

- Fixed `NameError` in `RemoteDataService._search_mast` where `records` variable was not initialized (was incorrectly named `systems`).
- Updated test expectations in `test_search_mast_filters_products_and_records_metadata` to match the current implementation which uses observation `obsid` as identifier rather than `productFilename`.
- Removed unused `get_product_list` method from test mock to avoid confusion.
- All 67 tests now pass with 20 skipped.

## 2025-10-20 (Numpy window widened for Python 3.12+) (15:39 EDT / 19:39 UTC)

- Relaxed the numpy dependency to `>=1.26,<3` so Windows launches on Python 3.12+
  resolve published 2.x wheels instead of attempting unavailable 1.26 builds.
- Updated `RunSpectraApp.cmd`, `START_HERE.md`, and `AGENTS.md` to reference the
  wider range in their recovery instructions.
- Adjusted the workplan dependency summary to match the new ceiling and avoid
  confusion for future onboarding.

## 2025-10-20 (Windows pip clears binary overrides) (15:20 EDT / 19:21 UTC)

- Updated `RunSpectraApp.cmd` to clear `PIP_NO_BINARY` and set
  `PIP_ONLY_BINARY=numpy` / `PIP_PREFER_BINARY=1` before installing
  dependencies so Windows launches always request prebuilt NumPy wheels.
- Refreshed `AGENTS.md` and `START_HERE.md` with the same guidance for manual
  setups, ensuring agents know how to recover if global pip settings force
  source builds.

## 2025-10-20 (Library hint stays fixed, prefer-binary install guidance) (14:09 EDT / 18:09 UTC)

- Fixed the Library tab hint label height and kept word wrapping enabled so
  selecting cached spectra no longer forces the main window to expand or emit
  Windows geometry warnings when graphs are visible.
- Updated `RunSpectraApp.cmd`, `START_HERE.md`, and `AGENTS.md` to run
  `pip install --prefer-binary` by default and document how to resolve numpy
  builds without local C++ toolchains.
- Relaxed the numpy requirement to `>=1.26,<2` and lifted the `requests`
  ceiling to `<3` so both Windows and Linux environments can consume the
  latest wheels without manual edits.

## 2025-10-19 (Library dock stays compact, CI pins numpy) (20:27 EDT / 00:27 UTC)

- Locked the Library dock splitter and elided long cache paths so selecting
  cached spectra no longer forces the Data dock to expand over the log panel.
- Added tooltips for full cache paths and documented the behaviour in
  `docs/user/importing.md` so analysts know where to find the complete
  locations.
- Relaxed the numpy requirement to `>=1.26,<2` to keep GitHub Actions green on
  Python 3.10/3.11, matching the wheels available on both Windows and Linux.
- Ran `pytest` to confirm the UI regression tests still pass with the updated
  layout and dependency pin.

## 2025-10-19 (Data table toggle respects user choice) (19:38 EDT / 23:38 UTC)

- Stopped the Data dock from forcing the numerical table open when selecting a
  dataset by tracking the latest overlay views and only populating the table
  when **View → Show Data Table** remains checked.
- Added `_last_display_views` bookkeeping so manual toggles repopulate the panel
  on demand without requerying the overlay service.
- Documented the change in `docs/user/plot_tools.md` and refreshed the workplan
  plus knowledge log with the timestamped entry.

## 2025-10-19 (Data dock consolidation) (18:46 EDT / 22:46 UTC)

- Replaced the standalone Library dock with a tab inside the Data dock so
  cached spectra sit alongside the Datasets tree, rebuilding the tab on
  persistence toggles and adding a disabled placeholder when the cache is off.
- Updated `docs/user/importing.md`, `docs/user/remote_data.md`,
  `docs/user/plot_tools.md`, `docs/link_collection.md`, and
  `docs/developer_notes.md` to describe the new layout, and refreshed the
  workplan entry tracking datasets/library organisation.
- Kept Qt coverage green by running `pytest` after the refactor.

## 2025-10-19 (Manifest export gains wide/composite options) (16:50 EDT / 20:50 UTC)

- Added an export options dialog in `app/main.py` so you can choose between the
  standard provenance bundle, a wide paired-column CSV, and a composite-mean
  CSV before saving.
- Extended `ProvenanceService` with helpers to generate the new CSV formats and
  taught `CsvImporter` to recognise the `spectra-wide-v1` layout comments.
- Documented the workflow in `docs/user/plot_tools.md` and `docs/user/importing.md`,
  highlighting that wide/composite exports re-import cleanly.
- Expanded the provenance and importer test suites to cover wide/composite
  round-trips, and patched the export visibility regression test to honour the
  new dialog.

## 2025-10-19 (Export respects visibility state) (14:28 EDT / 18:28 UTC)

- Updated `app/main.py::export_manifest` so provenance bundles include only datasets marked visible in the workspace, preventing hidden traces and background samples from polluting merged exports.

## 2025-10-19 (Provenance CSV round-trips) (15:14 EDT / 19:14 UTC)

- Reordered the combined export CSV in `app/services/provenance_service.py` so wavelength/intensity columns lead each row, keeping the file compatible with the CSV importer.
- Documented the new ordering in `docs/user/importing.md` and added `tests/test_provenance.py::test_export_bundle_csv_round_trips` to guard the regression.
- Documented the behaviour shift in `docs/user/plot_tools.md` and `docs/user/importing.md`, clarifying that hidden traces stay out of the `spectra/` directory while visible series continue to export at full resolution.
- Added `tests/test_export_visibility.py::test_export_skips_hidden_spectra` to exercise the UI path with patched dialogs, ensuring only visible IDs reach the provenance service.

## 2025-10-19 (Bundle CSV imports expand into multiple spectra) (16:23 EDT / 20:23 UTC)

- Extended `CsvImporter` with `_try_parse_export_bundle` so manifest CSV exports containing `spectrum_id` metadata embed a `bundle` block describing every trace in the file.
- Updated `DataIngestService` and the UI ingest paths to return lists of spectra, expanding export bundles into individual canonical datasets while maintaining cache provenance.
- Adjusted remote-download wiring and smoke tests to accommodate list-based ingestion and added regression coverage in `tests/test_csv_importer.py` and `tests/test_ingest.py` for the new bundle format.
- Refreshed `docs/user/importing.md` to explain that re-importing a provenance CSV restores each spectrum separately rather than merging traces.

## 2025-10-18 (NIST ASD astroquery integration) (20:35 EDT / 00:35 UTC)

- Replaced the NIST remote search implementation with the astroquery-backed
  line-list helper used by the upstream Spectra project, aggregating each query
  into a single record that previews line counts and metadata before download.
  The Remote Data dialog now synthesises CSV payloads from the returned line
  tables so the existing CSV importer can ingest them without manual edits.
- Added a dedicated `app/services/nist_asd_service.py` module that resolves
  element/ion identifiers, queries `astroquery.nist`, and normalises the
  response into nm-relative intensities and provenance metadata. Remote downloads
  detect the synthetic `nist-asd:` scheme and emit annotated CSV files instead of
  issuing HTTP requests.
- Updated the remote data regression suite (`tests/test_remote_data_service.py`)
  to mock the astroquery wrapper, assert the generated CSV path, and verify
  provider availability logic now checks the astroquery dependency directly.
  Refreshed the user guide to describe the spectroscopy-first workflow and the
  new CSV synthesis path for NIST results.

## 2025-10-18 (Remote data dependencies & imaging toggle) (17:17 EDT / 21:17 UTC)

- Declared `requests`, `astroquery`, and `pandas` in `requirements.txt` and updated
  onboarding guides so remote catalogue workflows install the optional
  dependencies by default. The Remote Data dialog now relays clearer
  unavailability messages when any package is missing.
- Added an **Include imaging** toggle to the Remote Data dialog and taught the
  MAST adapter to honour it, defaulting to calibrated spectra while allowing
  operators to pull calibrated imaging products on demand.
- Guarded `_ensure_mast` and provider lists behind a pandas-aware check,
  refreshed the remote data user guide, and extended the regression suite to
  cover the new flag and dependency messaging.

## 2025-10-18 (Remote Data examples & validation) (00:08 EDT)

- Added curated example queries to the Remote Data dialog for both NIST and MAST
  so operators can fetch spectroscopy targets without retyping common names.
- Blocked empty submissions in the dialog and raised a service-level error when
  MAST criteria are missing, preventing unbounded archive sweeps.
- Updated the remote data user guide and workplan to document the scoped searches
  and new example menu.

## 2025-10-17 (Onboarding docs realignment) (20:10 EDT / 00:10 UTC)

- Rewrote the master prompt to reflect the decomposed brains directory, pass
  review priorities, and spectroscopy-first guardrails, including explicit time
  discipline for all documentation updates.
- Updated `AGENTS.md` and `START_HERE.md` so new agents read the correct
  artefacts (pass dossiers, brains README, link collection) and know how to
  capture real timestamps for patch notes and knowledge-log entries.
- Added `docs/brains/README.md` plus pass review summaries (`pass1.md` –
  `pass4.md`) and refreshed the workplan backlog to focus on calibration,
  identification, provenance parity, and UI polish milestones.

## 2025-10-17 (Library provenance preview) (14:19 UTC)

- Expanded the Library dock with a metadata preview splitter so selecting a cache
  entry reveals provenance, unit, and storage details without leaving the app.
- Updated the importing guide to document the new preview pane and search
  filtering, keeping the user workflow in sync with the UI.
- Added a smoke regression ensuring the dock populates and surfaces metadata in
  headless test runs.

## 2025-10-17 (Knowledge log runtime guard) (04:30 am UTC)

- Registered Import/Remote Import as runtime-only components inside
  `KnowledgeLogService`, ensuring they never touch the canonical log even if a
  caller omits `persist=False`.
- Updated the knowledge-log regression suite to cover the runtime-only guard and
  allow tests to override the component set when persistence is required.
- Audited the consolidated log to confirm no automation-generated Import/Remote
  Import entries remain after the cleanup.
- Added `*.egg-info/` to `.gitignore` so setuptools artefacts from test runs do
  not clutter the working tree.

## 2025-10-17 (Knowledge log hygiene) (03:45 am UTC)

- Added a non-persistent mode to `KnowledgeLogService.record_event` so routine
  Import/Remote Import notifications stay in the History dock without appending
  to `docs/history/KNOWLEDGE_LOG.md`.
- Updated the Spectra shell ingest hooks to call the new flag, preventing cache
  loads from spamming the canonical log while still surfacing activity in the
  UI.
- Extended the knowledge-log regression suite to assert that `persist=False`
  avoids creating a log file and retains the returned entry for in-memory
  display.

## 2025-10-17 (Spectroscopy-focused remote catalogue pass) (02:30 am UTC)

- Fixed the **Fetch Remote Data…** crash caused by a missing provider-change
  slot and added regression coverage (`tests/test_remote_data_dialog.py`) to
  instantiate the dialog safely under pytest.
- Tightened the MAST adapter so free-text searches now inject
  `dataproduct_type="spectrum"`, `intentType="SCIENCE"`, and `calib_level=[2, 3]`
  filters, pruning non-spectroscopic rows before presenting them in the UI.
  The user guide calls out the new defaults and the service filters results via
  `_is_spectroscopic` to keep the workflow aligned with lab comparisons.
- Updated developer notes with a documentation map plus guidance for future
  remote-catalogue work, ensuring every agent knows where the curated resources
  live and how to keep docs/tests in sync.
- Extended the remote-data regression suite to assert the injected filters and
  confirm HTTP/MAST download routing remains intact after the change.

## 2025-10-17 (Remote search & cache library) (01:45 am UTC)

- Reworked the Remote Data dialog to emit provider-specific queries (`spectra`
  for NIST, `target_name` for MAST) and surfaced contextual hints so operators
  know which spectroscopic assets to request. Updated
  `app/services/remote_data_service.py` to translate legacy payloads, download
  `mast:` URIs via `astroquery.mast.Observations.download_file`, and exercised
  the new paths in `tests/test_remote_data_service.py`.
- Introduced a Library dock driven by `LocalStore.list_entries()` so cached
  spectra can be reloaded without re-downloading. Routine ingest events now log
  concise knowledge-log summaries while file-level metadata lives in the Library
  view.
- Added a trace-colour mode toggle to the Inspector Style tab (high-contrast vs
  uniform) and refreshed rendering so palette changes propagate to the plot and
  dataset icons in real time.
- Authored `docs/link_collection.md`, refreshed the remote/importing/reference
  guides, and created `AGENTS.md` to document repository conventions, knowledge
  log policy, and spectroscopy-first sourcing.

## 2025-10-16 (Adjustable plot LOD budget) (11:55 pm UTC)

- Added a configurable "LOD point budget" control to the Inspector Style tab so users can raise or lower the plot downsampling threshold from 1k to 1M samples while Spectra persists the preference via `QSettings`.
- Taught `PlotPane` to accept a constructor-provided budget with validation plus a runtime setter that clamps unreasonable values and re-renders existing traces accordingly.
- Extended the plot performance stub tests to exercise the override path and ensure the peak-envelope downsampling honours the user-selected limit, alongside documentation updates for the new control.

## 2025-10-16 (Remote catalogue ingestion) (11:10 pm UTC)

- Added a `RemoteDataService` with dependency guards for `requests`/`astroquery`,
  caching remote downloads in the shared `LocalStore` with provider metadata,
  fetch timestamps, and checksums so repeated requests reuse cached artefacts.
- Wired a **File → Fetch Remote Data…** dialog that searches NIST ASD/MAST
  catalogues, previews metadata, and pipes downloads into the existing ingest
  pipeline so imported spectra immediately populate overlays and history logs.
- Authored user documentation for the remote workflow, noted the plotting
  integration, and recorded regression tests covering URL construction, cache
  reuse, and provenance payloads for remote downloads.

## 2025-10-16 (Knowledge log automation & history dock) (9:45 pm UTC)

- Added a `KnowledgeLogService` that appends structured entries to the consolidated log (or an alternate runtime file) and
  exposes helpers for filtering/exporting provenance events.
- Instrumented SpectraMainWindow imports, overlays, math operations, and exports so each workflow records provenance-ready
  metadata while updating the new History dock in real time.
- Introduced a History dock with search and component filters plus export controls, refreshed docs to describe the automation
  pathway, and added regression coverage for the service and UI integration.

## 2025-10-16 (Automatic ingest caching) (2:30 pm UTC)

- Wired `DataIngestService` to accept a `LocalStore`, recording canonical units
  and provenance metadata after every import so the cache index updates without
  manual intervention.
- Instantiated a shared `LocalStore` in the preview shell with a toggleable
  persistence preference (plus the `SPECTRA_DISABLE_PERSISTENCE` environment
  override) so manual imports and sample loads land in the cache consistently.
- Documented the new behaviour, regression coverage, and knowledge-log entry to
  highlight the automatic caching flow and opt-out controls.

## 2025-10-16 (Reference overlay state consolidation) (1:50 pm UTC)

- Deduplicated the Reference inspector's overlay attributes so the payload, key, and annotations initialise once at startup and
  reset through a shared helper when overlays are cleared.
- Added `_reset_reference_overlay_state()` to centralise cleanup paths, ensuring toggles reuse the existing payload dictionary
  and annotation list rather than replacing them mid-session.
- Extended the GUI regression suite to cover overlay toggling semantics and updated the plotting guide to mention the
  single-source overlay bookkeeping; logged the activity in the consolidated knowledge log for traceability.

## 2025-10-16 (Line-shape previews & overlay integration) (11:45 am UTC)

- Promoted Doppler, pressure, and Stark placeholders to `ready` with units and example parameters so the Inspector can seed
  sample profiles from the reference catalogue.
- Added a `LineShapeModel` service that parses the placeholder definitions, applies relativistic Doppler shifts, Lorentzian
  pressure kernels, and Stark wing scaling, exposing the results to the overlay pipeline with provenance metadata.
- Updated the Reference Inspector to preview the simulated profiles, wire selection changes into the overlay toggle, and added
  regression coverage plus documentation updates for the new controls.

## 2025-10-16 (IR overlay anchoring documentation) (9:30 am UTC)

- Documented the anchored IR functional-group overlays and label stacking safeguards in
  `docs/user/reference_data.md`, aligning the guide with the behaviour exercised by
  `tests/test_reference_ui.py::test_ir_overlay_label_stacking`.
- Logged the regression coverage and plotting changes in preparation for a broader documentation
  sweep tracked in `docs/reviews/workplan.md`.

## 2025-10-15 (Reference selection + importer layout cache) (8:42 pm UTC)

- Fixed the Reference inspector so combo-box changes always drive the preview plot and overlay payloads, preventing the first dataset from lingering when toggling between hydrogen, IR, and JWST entries.
- Added a session layout cache to the CSV/TXT importer so once a header layout has been classified the same column order is reused for future files from the same instrument, with regression coverage for the cache hit path.
- Hardened wavenumber conversions by normalising Unicode tokens and mapping zero values to `inf` without runtime warnings; documented the toolbar visibility and reference-overlay workflow for the updated UI.

## 2025-10-15 (Raw intensity defaults & overlay label fixes) (8:18 pm UTC)

- Converted plot traces and overlays back into their source intensity units by default, updating the y-axis label and data table headers so `%T`, transmittance, or absorbance values remain untouched until you opt into normalization.
- Ensured Reference overlays reuse the active dataset’s payload when swapping combos and added a regression smoke test that locks in `%T` rendering to prevent accidental pre-normalization.
- Documented the raw-intensity workflow in the plotting and importing guides so users know where the source-unit metadata originates.

## 2025-10-15 (Reference plotting + importer profile swap) (7:45 pm UTC)

- Fixed the Reference inspector so dataset selection persists across sessions, JWST targets render in the preview canvas,
  and IR functional-group bands display labelled regions with optional overlays tied to the active combo-box choice.
- Normalised Unicode wavenumber symbols, guarded the documentation logger until the log dock exists, and exposed the Plot
  toolbar toggle through the View menu so manual normalization controls stay discoverable.
- Added a profile-based safeguard to the CSV/TXT importer so monotonic intensity columns no longer replace jittery
  wavenumber exports, with regression coverage capturing the new swap rationale.

## 2025-10-15 (Reference regeneration scaffolding) (4:18 am UTC)

- Added `tools/reference_build` scripts for NIST ASD, IR functional groups, and JWST quick-look spectra, recording build
  provenance inside each JSON asset and documenting usage in `docs/dev/reference_build.md`.
- Enriched the bundled reference datasets with per-target provenance (curation status, planned MAST URIs, retrieval
  timestamps) and expanded line-shape placeholders for Zeeman, collisional shift, and turbulence scaffolding.
- Updated the inspector UI to surface provenance details, refreshed user primers with the new workflow, and extended
  regression tests to assert the generator metadata for hydrogen, IR, and JWST entries.

## 2025-10-15 (Reference library & JWST quick-look data) (3:24 am UTC)

- Added a reference data service, inspector tab, and local JSON assets covering NIST hydrogen lines, IR functional groups,
  line-shape placeholders, and digitised JWST spectra for WASP-96 b, Jupiter, Mars, Neptune, and HD 84406.
- Bundled spectroscopy/JWST primers plus developer documentation so agents can extend the data store and cite sources from the
  in-app viewer.
- Logged regression coverage for the reference library to guard bundled IDs, metadata, and bibliographic entries.

## 2025-10-15 (Importer header conflict safeguards) (1:27 am UTC)

- Extended the CSV/TXT importer to honour unit hints inside headers, swap
  misidentified axes when intensity and wavelength labels conflict, and record
  the column-selection rationale in ingest metadata.
- Added regression coverage for unit-only headers and header-driven swaps while
  documenting the new safeguards in the importing guide.

## 2025-10-15 (Normalization pipeline & axis heuristics) (1:04 am UTC)

- Tightened CSV/TXT column scoring so wavelength/wavenumber spans outrank intensity-first exports, preventing swapped axes.
- Routed the plot toolbar's Normalize control through overlay service scaling with Max/Area modes, updating the data table and provenance metadata.
- Added unit tests for normalization math and importer regression, refreshed the importing and plot documentation to match, and logged the fixes in the workplan.

## 2025-10-15 (Importer heuristics & embedded docs) (12:37 am UTC)

- Reworked the CSV/TXT importer to scan messy files for contiguous numeric blocks,
  infer wavelength/intensity units from prose, and normalise descending wavenumber tables.
- Added regression coverage for heuristic parsing edge cases in `tests/test_csv_importer.py`
  and extended the Qt smoke test to assert the Docs tab renders repository guides.
- Introduced an in-app documentation viewer (Help → View Documentation) and documented
  the workflow in `docs/user/in_app_documentation.md`.

## 2025-10-15 (Provenance bundle structure hardening) (12:17 am UTC)

- `ProvenanceService.export_bundle` now creates per-spectrum CSVs under `spectra/`, copies original uploads into `sources/`, and records a structured `log.txt` inside each export bundle.
- Manifest source entries now include relative paths to the canonical CSV and copied source file, aligning behaviour with the importing guide appendix.
- Added regression coverage for the new bundle layout to ensure the manifest, CSVs, PNG snapshot, and provenance log are all emitted together.

## 2025-10-15 (Reference overlay crash fixes) (6:45 pm UTC)

- Prevented the Reference tab from crashing startup by initialising the unit toolbar lazily and defaulting to nanometres until the widget is ready.
- Updated the overlay refresh flow to tolerate Unicode wavenumber tokens and keep the main plot responsive during default sample ingestion.
- Confirmed the fix with linting, typing, and the pytest smoke suite so the app launches cleanly before the next feature pass.

## 2025-10-15 (Reference plotting & multi-import) (7:05 pm)

- Fixed the Reference inspector so dataset selections persist, the plot canvas renders Balmer intensities faithfully, and the overlay toggle mirrors hydrogen/IR/JWST datasets into the main graph.
- Normalised Unicode wavenumber aliases, guarded documentation logging during startup, and restored the normalization toolbar at launch.
- Switched **File → Open** to accept multi-select batches and updated smoke tests/docs to cover the new reference plotting workflow.

## 2025-10-15 (Reference overlay fixes) (7:18 pm UTC)

- Patched the Reference inspector so combo-box selection sticks, JWST datasets draw their sampled spectra, and the overlay toggle mirrors the active dataset instead of the first entry.
- Allowed **File → Open** and **File → Load Sample** to queue multiple files at once while batching plot refreshes.
- Documented the toolbar location for normalization modes and refreshed the reference-data walkthrough with the new overlay behaviour.

# 2025-10-18 (Remote Data examples & validation) (12:04 am EDT)

- Added curated example queries to the Remote Data dialog for both NIST and
  MAST so operators can fetch spectroscopy targets without retyping common
  names.
- Blocked empty submissions in the dialog and raised a service-level error when
  MAST criteria are missing, preventing unbounded archive sweeps.
- Updated the remote data user guide and workplan to document the scoped
  searches and new example menu.

## 2025-10-19 (Reference tab redesign & NIST integration) (13:22 EDT)

- Reworked the Inspector’s Reference tab to present dedicated Spectral lines, IR groups, and Line-shape panels with a
  spectroscopy-first layout; NIST line searches now use an embedded astroquery form that previews and overlays results
  directly on the main plot.
- Updated `docs/user/reference_data.md` to reflect the new workflow and removed the outdated JWST placeholder guidance.
- Added regression coverage for the NIST fetch path and refreshed the Qt smoke tests. (`pytest`)

## 2025-10-19 (13:42 ET) – Pinned NIST line sets & remote dialog cleanup

- Added pinned NIST spectral-line collections with palette controls so multiple queries stay visible on the inspector plot and
  updated the reference data guide plus regression suite to cover the workflow.
- Removed the NIST option from the Remote Data dialog, leaving MAST as the scoped catalogue and updating remote-data guidance
  and smoke tests to reflect the separation between line lists and archive downloads.

## 2025-10-19 (NIST pinned overlays) (2:09 pm edt)

- Let the Reference tab project every pinned NIST spectral-line set onto the workspace at once, keeping palette colours or
  collapsing to a uniform hue on demand.
- Extended the regression suite to ensure multi-set overlays populate and remain addressable via the Inspector toggle.
- Documented the behaviour shift in `docs/user/reference_data.md` so operators understand how the overlay toggle now affects
  all pinned line sets simultaneously.

## 2025-10-19 (17:46 ET)

- Added a case-insensitive search field to the Datasets dock so large sessions
  can be filtered without unloading spectra; the UI refreshes in real time and
  respects group visibility.
- Documented the new filter in `docs/user/plot_tools.md`, refreshed
  `AGENTS.md`/`START_HERE.md` with cross-platform timestamp guidance, and noted
  the actual patch-note/knowledge-log workflow used by the repository.

## 2025-10-15 (Importing Guide Provenance Appendix) (9:10 am)

- Expanded `docs/user/importing.md` with a provenance export appendix covering the structure of the manifest bundle.
- Clarified that exported directories include canonical CSVs, original sources, and a chronological log for audit trails.
- Highlighted unit round-trip safety when sharing exported spectra with collaborators.

## 2025-10-14 (Plot Interaction Guide) (8:45 pm)

- Added `docs/user/plot_tools.md` covering pan/zoom gestures, crosshair usage, legend management, and the 120k-point LOD cap.
- Wired the Cursor toolbar toggle and new **View → Reset Plot** action to the plot pane so the documentation matches the UI.
- Linked the new guide from the quickstart and README documentation index.
- Extended the plot performance stub tests to exercise the crosshair visibility API.

## 2025-10-14 (Units Reference) (7:38 pm est)

- Authored `docs/user/units_reference.md` to document supported spectral units, idempotent conversions, and provenance guarantees.
- Linked the quickstart guide to the new reference and marked the Batch 3 workplan item complete.

## 2025-10-14 (Quickstart Guide) (7:24 pm est)

- Added `docs/user/quickstart.md` with a step-by-step walkthrough covering launch, ingest, unit toggles, and provenance export using the bundled sample spectrum.
- Updated the Batch 3 workplan to track remaining documentation gaps and recorded the pytest run that validates the smoke workflow.
- Linked upcoming documentation sprint items back to the inventory for traceability.

## 2025-10-14 (7:20 pm est)

- Logged the latest CI gate outcomes (lint, type-check, pytest) and noted the missing coverage plugin.
- Made FITS ingestion optional when `astropy` is absent, providing a clear runtime error instead of import failures.
- Updated user guidance to call out the optional dependency and created a developer snapshot documenting the CI results.

## 2025-10-14 (Documentation Inventory) (7:00 pm est)

- Catalogued missing user, developer, and historical documentation deliverables in `docs/reviews/doc_inventory_2025-10-14.md` to prep for the next feature batch.
- Marked the Batch 2 workplan item complete with a reference to the new inventory document to aid scheduling.

## 2025-10-14 (6:30 pm est)

- Added an automated smoke workflow test that instantiates the preview shell, ingests CSV/FITS data, exercises unit toggles, and exports a provenance bundle.
- Centralised the reusable FITS fixture under `tests/conftest.py` to support regression suites.
- Documented the new smoke validation loop for developers and provided a matching user checklist.
## 2025-10-19T20:12:10-04:00 — History dock hidden by default

- Hid the History dock on launch so the inspector layout no longer jumps when browsing datasets; the dock stays available under **View → History**.
- Updated the plot tools guide to explain the new default and how to re-enable the runtime log when needed.

## 2025-10-19T20:41:06-04:00 — Library detail moved to side panel

- Reoriented the Library splitter horizontally so cached metadata lives beside the table, preventing the dock from pushing the bottom log out of view when entries are selected.
- Documented the side-panel layout in the importing and remote-data guides to keep the user workflow aligned with the UI.

## 2025-10-19T22:08:48-04:00 — Library hint clamp & dependency alignment

- Limited the Library hint label to a fixed-height strip so cached selections no longer force the main window to grow when browsing stored spectra.
- Pinned NumPy to 1.26.4 and relaxed the requests cap to allow 2.32.4 so Windows installs pull prebuilt wheels and match the workflow guidance.

## 2025-10-20T15:05:18-04:00 — CI binary wheels & cross-platform timestamp guidance

- Updated `.github/workflows/ci.yml` so dependency installs pass `--prefer-binary`, keeping Windows runners on prebuilt NumPy wheels in line with the launcher guidance.
- Synced `docs/history/MASTER PROMPT.md` with the agent manual by documenting Windows, Unix, and Python fallback commands for capturing ISO timestamps.

## 2025-10-20T19:47:28-04:00 — Remote data background workers

- Offloaded Remote Data searches and downloads onto background threads, locking controls and aggregating warnings so long-running JWST queries no longer freeze the shell.
- Updated `docs/user/remote_data.md` and the Qt smoke test to document and exercise the asynchronous workflow.

## 2025-10-20T20:08:57-04:00 — Restore PySide6 signal wiring

- Replaced the Remote Data dialog's Qt signal detection with a binding-aware helper so PySide6 uses `Signal` directly and PyQt keeps the `pyqtSignal` fallback.
- Removes the startup crash observed on Windows now that the dialog no longer references `QtCore.pyqtSignal` when running under PySide6.

## 2025-10-20T20:26:50-04:00 — Remote data progress container fix

- Wrapped the Remote Data status banner in a dedicated layout with a busy progress bar so the dialog no longer references an undefined `progress_container` during initialisation.
- Search and download workflows now toggle the indicator while work is running, keeping the asynchronous UX aligned with the documentation.

## 2025-10-20T20:54:53-04:00 — Exoplanet archive pipeline restored

- Rebuilt the remote fetching stack so Exo.MAST, NASA’s Exoplanet Archive, and MAST product listings are chained together, yielding telescope, instrument, and citation metadata for solar-system targets, stellar standards, and transiting exoplanets.
- Expanded the Remote Data dialog with mission/instrument columns, preview links, and enriched previews while documenting the new ExoSystems provider in the user guide.
- Added regression coverage for the product-level MAST flow and the exoplanet resolution path, keeping the pipeline stable when dependencies are mocked in tests.

## 2025-10-21T19:20:08-04:00 — Exo.MAST metadata resilience

- Guarded the ExoSystems preview against `NaN` discovery years so selecting planets with incomplete archive records no longer raises errors.
- Removed manual `%20` replacements when building Exo.MAST file-list requests so planets with spaces in their names (e.g. WASP-39 b) resolve citations again.
- Documented the behaviour changes in the remote data guide and recorded the regression run in the workplan.


## 2025-10-22T13:35:22-04:00 — Solar system quick-picks & science-ready filters

- Added a Solar System quick-pick menu to the Remote Data dialog covering Mercury through Pluto, expanded curated targets to include HD 189733 (host + planet), and wired the button to fire short ExoSystems queries automatically.
- Refactored `RemoteDataService` with `curated_targets()` helpers, category metadata, and tightened science-ready filtering (`dataproduct_type="spectrum"`, `calib_level=[2,3]`, `intentType="SCIENCE"`) for MAST/ExoSystems results.
- Updated README, remote data guides, developer notes, and workplan entries alongside new unit/integration tests exercising the quick-pick UI and calibrated product gating.
