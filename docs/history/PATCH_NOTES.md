# Patch Notes

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

## 2025-10-21 (Remote dialog blocks on worker shutdown during app exit) (19:19 EDT / 23:19 UTC)

- Guarded the Remote Data dialog's `closeEvent` so Spectra waits for active
  search/download worker threads to finish when the application is quitting.
  Prevents Qt from tearing down running `QThread` instances if the main window
  closes immediately after dismissing the dialog.

## 2025-10-20 (Remote dialog threads shut down safely on close) (18:42 EDT / 22:42 UTC)

- Ensured the Remote Data dialog waits for active search/download worker threads
  to finish after requesting cancellation so closing the window no longer risks
  `QThread: Destroyed while thread is still running` crashes on long-running
  remote calls.
- Reused the worker-cleanup path to dispose threads/workers after joining so
  cancellation behaves consistently whether triggered via Reject or completion
  signals.
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

## 2025-10-20T23:18:18-04:00 — Remote data results table stabilised

- Restored the Remote Data table helpers so search results populate all rows, selection changes refresh the metadata preview, and the download button only activates when rows are highlighted.
- Added mission/instrument/product columns plus preview/download hyperlinks, and updated the user guide to describe the richer snapshot exposed for each catalogue match.

# #? maybe? ensure inserted at top after header?? need to check file start.
