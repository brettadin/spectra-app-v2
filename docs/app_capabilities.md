# Spectra App Capability Atlas (2025-11-02)

*Compiled 2025-11-02T10:43:33-05:00 / 2025-11-02T15:43:35+00:00 by agent.*

This atlas is an exhaustive, narrative map of everything the Spectra desktop application currently does, the pathways that make
those features possible, the diagnostic signals proving they still work, and the seams where functionality has regressed or was
partially reimplemented over time. It aggregates implementation notes, UI affordances, service behaviors, regression coverage,
and repository hygiene opportunities into one location so future maintainers can see the full operational surface without having
to stitch together dozens of documents.

---

## Table of Contents

1. [Top-Level Shell Experience](#top-level-shell-experience)
    1. [Window Frame & Dock Layout](#window-frame--dock-layout)
    2. [Dataset Lifecycle Entry Points](#dataset-lifecycle-entry-points)
    3. [Inspector & Library Surfaces](#inspector--library-surfaces)
    4. [History, Provenance, and Notifications](#history-provenance-and-notifications)
2. [Remote & Local Data Acquisition](#remote--local-data-acquisition)
    1. [Remote Data Dialog Capabilities](#remote-data-dialog-capabilities)
    2. [Curated Archives & Bundled Assets](#curated-archives--bundled-assets)
    3. [Importer Stack, File Type Coverage, and Edge Handling](#importer-stack-file-type-coverage-and-edge-handling)
    4. [Download, Cache, and Rehydration Pipeline](#download-cache-and-rehydration-pipeline)
3. [Spectral Analysis & Visualization Toolkit](#spectral-analysis--visualization-toolkit)
    1. [Plotting Engine and Trace Management](#plotting-engine-and-trace-management)
    2. [Unit Systems, Math Tools, and Line Shapes](#unit-systems-math-tools-and-line-shapes)
    3. [Reference Overlays and Spectral Libraries](#reference-overlays-and-spectral-libraries)
    4. [Export Center, Manifests, and Provenance Bundles](#export-center-manifests-and-provenance-bundles)
4. [Automation, Logging, and Knowledge Stewardship](#automation-logging-and-knowledge-stewardship)
    1. [Knowledge Log Runtime Path](#knowledge-log-runtime-path)
    2. [Workplan, Patch Notes, and Operational Rituals](#workplan-patch-notes-and-operational-rituals)
    3. [Brains, Specs, and Historical Atlases](#brains-specs-and-historical-atlases)
5. [Testing, QA, and Continuous Validation](#testing-qa-and-continuous-validation)
    1. [Pytest Contract Coverage](#pytest-contract-coverage)
    2. [Manual Validation Guides](#manual-validation-guides)
    3. [Smoke Workflows and Windows Tooling](#smoke-workflows-and-windows-tooling)
6. [Functional Gaps, Lost Features, and Regression Risks](#functional-gaps-lost-features-and-regression-risks)
    1. [Dormant or Incomplete Features](#dormant-or-incomplete-features)
    2. [Known Bugs and User Pain Points](#known-bugs-and-user-pain-points)
    3. [Technical Debt and Refactoring Targets](#technical-debt-and-refactoring-targets)
7. [Repository Cleanup Opportunities](#repository-cleanup-opportunities)
    1. [Docs, Duplicates, and Legacy Assets](#docs-duplicates-and-legacy-assets)
    2. [Packaging and Dependency Alignment](#packaging-and-dependency-alignment)
    3. [Test Data, Samples, and Downloads](#test-data-samples-and-downloads)
8. [Forward-Looking Enhancements](#forward-looking-enhancements)
    1. [High-Confidence Extensions](#high-confidence-extensions)
    2. [Exploratory Research Threads](#exploratory-research-threads)
    3. [Community and Collaboration Hooks](#community-and-collaboration-hooks)

---

## Top-Level Shell Experience

### Window Frame & Dock Layout

The Spectra shell is defined in `app/main.py`, which instantiates a Qt main window, arranges toolbars, and wires the dock panels
that analysts rely on for ingest, visualization, and provenance. The frame bootstraps pyqtgraph (`pg.QtGui.QMainWindow`) and
applies a deterministic dock configuration to avoid chaotic layouts:

- **Data Dock Tabs** (`datasets` + `library`): Delivered via the `PlotPane` class and supplementary inspector widgets. The dock is
  tabified to keep dataset selection and cached library browsing unified.
- **Inspector Dock**: Hosts overlays, reference controls, and metadata forms. The Reference tab is the canonical entry point for
  NIST ASD queries after the remote dialog was re-scoped to astronomy sources.
- **History Dock**: Hidden by default (per `PATCH_NOTES` entry 2025-10-19T20:12:10-04:00) to keep the main canvas focused on
  spectra. Users can re-enable it from **View → History** when they need session-level logging.
- **Status & Notification Banner**: Inline status widgets surface asynchronous job states (remote searches, downloads, exports)
  without blocking the UI. The remote data workers (`_RemoteSearchWorker`, `_RemoteDownloadWorker`) emit progress hooks back into
  the banner for visibility.
- **Theme and Palette Controls**: Trace styling (uniform palette, colorblind-safe options) is exposed through the plot pane,
  referencing `app/ui/palettes.py` for curated color sets.

### Dataset Lifecycle Entry Points

Dataset ingress flows through a combination of menu actions, context shortcuts, and drop targets:

- **File → Import Data**: Launches importer selection logic from `DataIngestService`. Handles CSV, TSV, FITS, provenance bundles,
  composite CSV manifests, and zipped archives via dedicated importer classes under `app/services/importers/`.
- **File → Fetch Remote Data** (Ctrl+Shift+R): Opens `RemoteDataDialog`. The dialog orchestrates remote search, preview, and
  download sequences across MAST, MAST ExoSystems, and NIST (for direct line-list retrieval when the Reference tab is not
  sufficient).
- **Drag-and-Drop**: Files dropped on the window are routed to `_ingest_path` in `main.py`, which defers to `DataIngestService` and
  records provenance via `ProvenanceService`.
- **Sample Data Gallery**: Bundled datasets under `samples/` are surfaced through curated menus so analysts can quickly load JWST
  reference spectra, laboratory standards, and historical CSVs for tutorials.

### Inspector & Library Surfaces

The Inspector area, primarily controlled by `PlotPane` and associated Qt widgets, exposes analysis toggles and metadata views:

- **Overlays Tab**: Adds, removes, and styles overlays for spectral line sets, IR functional groups, and user-defined markers.
  Overlay persistence is handled by `OverlayService`, which remembers pinned overlays between sessions when caching is enabled.
- **Reference Tab**: Integrates the NIST ASD search form, allowing users to request line lists (vacuum wavelengths, Ritz toggles,
  intensity filters). Results can be pinned, colour-coded, and exported.
- **Library Tab**: Displays cached dataset metadata from `ReferenceLibrary` and `LocalStore`. Users can inspect ingested file
  attributes, wavelength ranges, and unit states without reloading the dataset.
- **Datasets Tab**: Manages the active dataset stack. Users can toggle visibility, rename traces, and adjust normalization states.

### History, Provenance, and Notifications

Runtime history is orchestrated by `KnowledgeLogService` with a non-persistent default, ensuring only curated events land in the
canonical log. Key runtime affordances include:

- **History Dock Feed**: Shows ingest, remote download, overlay, and export events for the current session. Entries are buffered in
  memory and optionally persisted to `LocalStore`.
- **Provenance Snapshots**: `ProvenanceService` constructs manifest files (JSON + CSV) capturing dataset lineage, import
  parameters, and overlay states. Exported manifests can be re-ingested via the import pipeline.
- **Notifications & Alerts**: The status banner reflects long-running operations (downloads, exports, math transforms). Failures
  propagate descriptive messages (e.g., skipped non-spectral downloads) for operator action.

---

## Remote & Local Data Acquisition

### Remote Data Dialog Capabilities

The remote dialog (`app/ui/remote_data_dialog.py`) combined with `RemoteDataService` powers astronomy-grade querying:

- **Provider Matrix**:
  - `RemoteDataService.PROVIDER_MAST`: Accesses the Mikulski Archive for Space Telescopes via `astroquery.mast.Observations`
    searching spectra first, then optional imaging. Mission batches cover JWST, HST, IUE/FUSE/GALEX, and photometric missions
    (Kepler/K2/TESS) for follow-up.
  - `RemoteDataService.PROVIDER_EXOSYSTEMS`: Bridges the Exo.MAST planet/star catalogues to fetch curated transit and phase curve
    spectra with host metadata.
  - `RemoteDataService.PROVIDER_NIST`: Requests laboratory line lists directly when needed, using `astroquery.nist` under the hood.
- **Progressive Search Strategy**: Background workers stream results, updating the table as records arrive. This avoids UI freezes
  on large JWST queries and respects cancellation signals.
- **Download Management**: `_RemoteDownloadWorker` enforces file-type filters, skipping non-spectral assets (images, logs) and
  pushing ingestion results back onto the main thread. Progress bars display received vs. total bytes.
- **Preview & Metadata Panels**: The dialog surfaces summary fields (target, instrument, obs ID, proposal, spectral coverage,
  citation). For ExoSystems results, host star parameters and planetary context (radius, equilibrium temperature) are included.
- **Quick-Pick Catalogues**: Buttons map to curated Solar System targets, bundling canonical query parameters per mission.
- **Imaging Toggle**: Optional retrieval of imaging products when analysts require context imagery alongside spectra.

### Curated Archives & Bundled Assets

Beyond live remote queries, Spectra ships a curated archive under `samples/` and `app/services/remote_data_service.py` metadata:

- **Solar System Archive**: Local JSON manifests referencing high-quality spectra (e.g., JWST NIRSpec observations of Jupiter, HST
  UV spectra of auroral regions, laboratory CH₄ standards). These serve as offline training material.
- **Reference Line Libraries**: `app/services/reference_library.py` exposes default overlays (hydrogen Balmer, CO₂ bands, IR
  functional groups) to bootstrap analyses.
- **Downloads Cache**: `downloads/` captures previously retrieved remote assets, enabling offline re-ingest and provenance audits.
- **Exports Repository**: `exports/` stores provenance bundles, processed CSVs, and user-defined exports for cross-session sharing.

### Importer Stack, File Type Coverage, and Edge Handling

`DataIngestService` coordinates a suite of importer classes defined under `app/services/importers/`:

- **CSVImporter**: Handles standard spectral CSVs (wavelength, flux), wide-format composites, and column-detected metadata. The
  importer guesses delimiters, unit metadata, and column roles.
- **FITSImporter**: Wraps `astropy.io.fits` to load spectral cubes, 1D extracted spectra, and data-quality masks. It normalizes axes
  orientation (wavelength vs. flux) using heuristics defined in `spectral_axis.py` helpers.
- **ProvenanceImporter**: Rehydrates exported manifests, instantiating `Spectrum` objects with saved overlays, math transforms, and
  custom labels intact.
- **ZipArchiveImporter**: Expands zipped bundles of CSV/FITS assets, iterating through them sequentially to preserve provenance.
- **Guard Clauses**: The service blocks empty selections, enforces file existence, and surfaces descriptive errors when parsing
  fails (invalid encoding, missing headers, unsupported binary layouts).

### Download, Cache, and Rehydration Pipeline

The ingest pipeline ensures remote downloads become first-class spectra:

1. **Search**: Remote dialog or automation script requests candidate records.
2. **Download**: `RemoteDataService.download` streams bytes to a temporary file, invoking progress hooks.
3. **Validation**: Non-spectral file types are skipped with warnings; zipped or multi-extension FITS files are unpacked.
4. **Ingest**: `DataIngestService.ingest` identifies the appropriate importer, constructs a `Spectrum` object, and registers the
   dataset with `ReferenceLibrary`.
5. **Cache Registration**: `LocalStore` records file paths, metadata, and overlay states so the Library tab can resurface them.
6. **Provenance Update**: `ProvenanceService` appends entries capturing remote source, query parameters, and fetch timestamps.

---

## Spectral Analysis & Visualization Toolkit

### Plotting Engine and Trace Management

Plotting is powered by pyqtgraph, orchestrated via `app/ui/plot_pane.py`:

- **Trace Layers**: Each `Spectrum` renders as a trace with toggleable visibility, normalization state, and color assignment.
- **Axis Controls**: Users can switch between wavelength, frequency, and wavenumber units using toolbar actions backed by
  `UnitsService`. Log scaling is available for flux axes.
- **Crosshair & Cursor Tools**: Interactive crosshair readouts display coordinate pairs and delta measurements; snapping to peaks is
  a planned enhancement (see [Forward-Looking Enhancements](#forward-looking-enhancements)).
- **Region Highlighting**: Brushing selections feeds into math services (integration, smoothing) and overlay alignment routines.
- **Uniform Palette Mode**: `TraceStyle` toggles allow high-contrast or uniform coloring for presentations and accessibility needs.

### Unit Systems, Math Tools, and Line Shapes

Scientific transformations rely on the service layer under `app/services/`:

- **UnitsService**: Converts between Angstrom, nm, µm, THz, cm⁻¹, and eV. Maintains context for each spectrum so conversions remain
  reversible and consistent with metadata exports.
- **MathService**: Implements smoothing, normalization, background subtraction, integration routines built on NumPy operations,
  and arithmetic combining of spectra.
- **LineShapeModel & line_shapes.py**: Provides Gaussian, Lorentzian, and Voigt profile generation for modeling emission/absorption
  features. Parameters include FWHM, amplitude, center, and baseline adjustments.
- **OverlayService**: Couples math outputs with overlays, enabling difference plots, derivative traces, and manual annotations.

### Reference Overlays and Spectral Libraries

Reference intelligence keeps analyses grounded:

- **NIST ASD Integration**: Users can fetch line lists by element, ionization stage, and wavelength band. Results include wavelengths,
  transition probabilities, intensity rankings, and energy levels.
- **IR Functional Groups**: Pre-bundled overlays highlight characteristic absorption bands for organics, minerals, and volatiles.
- **Custom Overlay Imports**: CSV overlays can be ingested and saved alongside spectra for recurring comparisons.
- **Library Search & Categorization**: `ReferenceLibrary` indexes cached datasets with instrument, mission, and target metadata, paving
  the way for future grouping/filtering enhancements.

### Export Center, Manifests, and Provenance Bundles

The Export Center (`app/ui/export_center_dialog.py`) delivers reproducible outputs:

- **Export Targets**:
  - **CSV (narrow)**: Standard wavelength/flux pair exports respecting current unit selections.
  - **CSV (wide/composite)**: Multi-trace exports where each column corresponds to a dataset, facilitating spreadsheet analysis.
  - **Provenance Bundle**: ZIP containing manifests, overlays, and normalized CSVs for archival sharing.
  - **Image Snapshot**: Plot PNG export capturing the current viewport and annotations.
- **Manifest Structure**: JSON documents summarizing each spectrum’s origin (local path, remote identifier, query parameters), unit state,
  applied math transformations, overlays, and export timestamp.
- **Round-Trip Import**: Provenance bundles can be re-imported, reconstructing the session state including overlays and math results.
- **Validation Hooks**: Export center checks for writable destinations, existing files, and ensures hidden traces are excluded unless
  explicitly requested.

---

## Automation, Logging, and Knowledge Stewardship

### Knowledge Log Runtime Path

`KnowledgeLogService` (see `app/services/knowledge_log_service.py`) centralizes narrative logging:

- **persist=False Default**: Routine ingest and download events are excluded from the canonical log, preventing noise.
- **Curated Entries**: Agents record significant changes manually in `docs/history/KNOWLEDGE_LOG.md`, following timestamp standards and
  referencing code paths.
- **Remote History Events**: `_record_remote_history_event` in `main.py` stores runtime events for the History dock without polluting the
  long-term log.

### Workplan, Patch Notes, and Operational Rituals

The team maintains forward momentum via living documents:

- **`docs/reviews/workplan.md`**: Tracks batch goals, completed items, QA runs, and backlog features. Batch 14 currently targets calibration
  services, identification stack, and plotting enhancements.
- **`docs/history/PATCH_NOTES.md`**: Time-ordered changelog capturing shipped features, bug fixes, and documentation updates.
- **`docs/history/KNOWLEDGE_LOG.md`**: Concise curated insights linking to relevant modules, tests, or docs.
- **Ritual**: Every code/doc change requires synchronized updates to all three artifacts plus a daily worklog entry under
  `docs/dev/worklog/`.

### Brains, Specs, and Historical Atlases

Knowledge is also captured across specialized archives:

- **Brains (`docs/brains/`)**: Atomic architectural decisions and insights (e.g., remote data pipeline, NIST threading model).
- **Specs (`specs/`)**: Requirements, feature narratives, and roadmap documents guiding implementation priorities.
- **Atlases & Summaries**: `IMPLEMENTATION_SUMMARY.md`, `IR_EXPANSION_SUMMARY.md`, and `DATA_ACQUISITION_PIPELINE.md` outline past work and
  ongoing enhancements.
- **Historical Threads**: `docs/spectra_history.md` chronicles the project timeline, while `docs/repo_inventory.md` lists every tracked file.

---

## Testing, QA, and Continuous Validation

### Pytest Contract Coverage

- **Unit & Integration Tests**: 73 tests across `tests/` validate remote services, importer heuristics, Qt UI contracts, and service math.
- **Qt Smoke Tests**: UI-level tests instantiate the main window, simulate remote searches, and verify asynchronous state changes using
  PySide6/PyQt-specific helpers.
- **Marker Strategy**: Custom markers (`roundtrip`, `ui_contract`) gate longer-running suites while keeping CI noise low.
- **CI Wheel Enforcement**: `sitecustomize.py` and `RunSpectraApp.cmd` ensure NumPy and related dependencies install from wheels, preventing
  pipeline failures.

### Manual Validation Guides

- **User Guides (`docs/user/`)**: Remote data workflows, importing, plotting tools, and unit references include manual validation steps and
  troubleshooting tips.
- **Quick Start Playbooks**: `START_HERE.md`, `QUICK_START_BULK_DATA.md`, and `BUILD_WINDOWS.md` provide environment setup, dataset fetch,
  and packaging instructions.
- **Operator Checklists**: Patch notes include references to smoke workflows, while knowledge log entries document manual QA sessions.

### Smoke Workflows and Windows Tooling

- **`RunSpectraApp.cmd`**: Windows-specific bootstrapper that prefers binary wheels, clears conflicting environment variables, and installs
  dependencies before launching.
- **`packaging/` Scripts**: Provide instructions for building distributables, signing installers, and verifying dependencies.
- **`tools/` Utilities**: Include dataset processing scripts, provenance auditors, and maintenance helpers for cache management.

---

## Functional Gaps, Lost Features, and Regression Risks

### Dormant or Incomplete Features

- **Calibration Service (`app/services/calibration_service.py`)**: Placeholder referenced in the workplan but not yet implemented. UI hooks
  for calibration banners and σ propagation remain TODO.
- **Identification Stack**: Planned services for peak detection and spectral matching are tracked in Batch 14 but absent from the codebase.
- **Dataset Removal UI**: Removal controls were scoped but not executed; dataset management still relies on manual toggles and context menus.
- **Advanced Visualization**: Snapshot thumbnails, brush-to-mask workflows, and uncertainty ribbons are design concepts awaiting implementation.

### Known Bugs and User Pain Points

- **Spectral Line Search Confusion**: Users have reported difficulty discovering the Reference tab workflow after NIST was pulled from the
  remote dialog; additional in-app guidance is needed.
- **FITS Edge Cases**: Multi-extension FITS files with non-standard WCS headers occasionally load with inverted axes, requiring manual
  adjustment. Tests cover common cases but not the full diversity of astronomical data.
- **Remote Download Robustness**: Network blips during large JWST downloads sometimes leave partially written files; the service should resume
  or cleanly retry.
- **Library Grouping**: Cached datasets lack grouping by instrument/mission, making large libraries unwieldy.

### Technical Debt and Refactoring Targets

- **Remote Worker Duplication**: `_RemoteSearchWorker` and `_RemoteDownloadWorker` duplicate logic found in remote dialog modules. Extracting
  shared worker classes would reduce divergence.
- **Importer Heuristics**: CSV auto-detection logic has grown ad hoc; centralizing column inference and unit parsing would reduce maintenance
  overhead.
- **UI Signal Handling**: Mixed PyQt/PySide compatibility shims exist throughout `app/ui/`. Consolidating them in `qt_compat.py` would
  simplify future upgrades.
- **Documentation Redundancy**: Multiple documents (inventory, enhancement summaries, quick starts) repeat capability descriptions; the new
  atlas aims to consolidate but further deduplication is needed.

---

## Repository Cleanup Opportunities

### Docs, Duplicates, and Legacy Assets

- **Legacy Link Collections**: `docs/reference_sources/link_collection.md` and `docs/reference_sources/training_links.md` retain raw historical
  URLs. Consider archiving or merging into the canonical `docs/link_collection.md` to avoid drift.
- **Outdated Summaries**: Older enhancement summaries may contradict recent work. Schedule periodic audits to sunset superseded documents.
- **Large Binary Assets**: `.docx` and `.pdf` files in `docs/` inflate repo size; convert to Markdown or host externally if licensing allows.
- **Atlas Alignment**: Cross-reference this atlas with `docs/repo_inventory.md` and `IMPLEMENTATION_SUMMARY.md` to ensure consistent narratives.

### Packaging and Dependency Alignment

- **Requirements Synchronization**: `requirements.txt`, `pyproject.toml`, and `RunSpectraApp.cmd` must stay in lockstep. Audit pinned versions
  quarterly.
- **Optional Dependencies**: Remote providers depend on `astroquery`, `pandas`, and `requests`. Ensure environment setup scripts flag these as
  optional but recommended, with graceful UI degradation when absent.
- **Sitecustomize Hooks**: `sitecustomize.py` implements wheel-first installation. Confirm this remains necessary as dependency ecosystems evolve.

### Test Data, Samples, and Downloads

- **Downloads Folder Hygiene**: Periodically prune expired remote downloads to reduce repo clutter, keeping only canonical samples with clear
  provenance.
- **Sample Metadata**: Ensure every bundled sample includes a manifest with citation, wavelength coverage, and instrument details.
- **Test Fixtures**: Consolidate duplicated FITS/CSV fixtures across `tests/` to shrink repo size and ease updates.
- **Exports Archive**: Review `exports/` for outdated manifests and snapshots; move historical exports to an archive folder with retention rules.

---

## Forward-Looking Enhancements

### High-Confidence Extensions

- **Calibration Manager**: Implement the planned calibration banner with controls for wavelength alignment, FWHM targets, and reference lamp
  corrections. Integrate with `LineShapeModel` for feedback.
- **Identification Dock**: Build peak detection services leveraging math utilities, deliver explainable scorecards, and integrate with overlays
  for labeling.
- **Palette Presets & Teaching Mode**: Provide saved palette profiles, add crosshair persistence, and expose a teaching overlay for classrooms.
- **Library Grouping**: Categorize cached datasets by mission/instrument with search filters and bulk actions.

### Exploratory Research Threads

- **Machine Learning Augmentation**: Investigate pybind11-backed feature extraction for spectral classification; keep optional and documented.
- **High-Resolution IR Expansion**: Extend curated archives with laboratory spectra from VAMDC, ExoMol, and HITRAN, ensuring license compliance.
- **Photometric Bridges**: Carefully explore photometric datasets (e.g., TESS) for complementary context without diluting spectroscopy focus.
- **Realtime Telemetry Hooks**: Evaluate streaming ingestion for observatory partners using websockets or queued ingestion services.

### Community and Collaboration Hooks

- **Tutorial Notebooks**: Provide Jupyter notebooks demonstrating ingestion, analysis, and export workflows using `pyqtgraph` offline mode.
- **Plugin Architecture**: Define an extension API for custom importers, overlays, or exporters. Document lifecycle hooks and security guidance.
- **Data Citation Templates**: Offer citation generators for remote datasets to streamline publication readiness.
- **Accessibility Enhancements**: Implement keyboard-only navigation paths, screen-reader hints, and high-contrast presets across the UI.

---

## Appendix A: Service Capability Matrix

| Service | Module | Responsibilities | Key Dependencies | Notes |
| --- | --- | --- | --- | --- |
| `UnitsService` | `app/services/units_service.py` | Convert units, manage session defaults, expose UI bindings | `numpy` | Handles wavelength/frequency/wavenumber conversions.
| `MathService` | `app/services/math_service.py` | Signal processing (smoothing, integration, normalization) | `numpy` | Uses NumPy vector operations for interpolation, masking, and alignment.
| `DataIngestService` | `app/services/data_ingest_service.py` | Route files to importers, register spectra, handle drag/drop | `pandas`, `astropy` | Guards empty selections and missing files.
| `OverlayService` | `app/services/overlay_service.py` | Manage overlay lifecycle, persistence, styling | Qt models | Integrates with `PlotPane` for display.
| `RemoteDataService` | `app/services/remote_data_service.py` | Query/download remote archives, cache metadata | `astroquery`, `requests`, `pandas` | Implements mission batches and curated catalogues.
| `ReferenceLibrary` | `app/services/reference_library.py` | Cache dataset metadata, expose library models | `LocalStore` | Powers the Library tab view.
| `ProvenanceService` | `app/services/provenance_service.py` | Generate manifests, orchestrate exports | `json`, `zipfile` | Ensures round-trip import/export fidelity.
| `KnowledgeLogService` | `app/services/knowledge_log_service.py` | Manage curated log entries, enforce persistence policy | `pathlib`, `datetime` | Default `persist=False` to keep log clean.
| `LocalStore` | `app/services/store.py` | Persist cached artifacts and runtime state | `sqlite3` | Backs library cache and history records.
| `LineShapeModel` | `app/services/line_shapes.py` | Generate analytic line profiles | `numpy` | Feeds calibration and overlay modeling.

---

## Appendix B: UI Action Cheat Sheet

- **File Menu**
  - Import Data… (`Ctrl+O`): Launch file chooser with importer detection.
  - Fetch Remote Data… (`Ctrl+Shift+R`): Open remote dialog for MAST/NIST/ExoSystems.
  - Export Center…: Launch export dialog for CSV/manifests/images.
  - Preferences…: Placeholder for future configurable settings (units, palette defaults).
- **View Menu**
  - Toggle History Dock: Show/hide runtime event log.
  - Toggle Library Dock: Manage cached dataset visibility.
  - Reset Layout: Restore default dock arrangement.
- **Tools Menu**
  - Math Operations: Apply smoothing, normalization, baseline subtraction.
  - Overlay Manager: Quick access to overlay creation/removal.
  - Units: Cycle between wavelength/frequency/wavenumber sets.
- **Help Menu**
  - Documentation Hub: Opens local docs (remote data guide, importing guide, plot tools).
  - Keyboard Shortcuts: Displays inline cheat sheet for analysts.

---

## Appendix C: Data Flow Narratives

1. **Remote JWST Spectrum Acquisition**
   - Analyst opens Fetch Remote Data, selects MAST, enters target `WASP-39 b`.
   - Search worker batches missions, retrieving JWST calibrated spectra first.
   - User selects a NIRSpec observation, triggers download with progress feedback.
   - Download worker streams file, ingestion identifies FITS structure, `FITSImporter` parses extensions, `Spectrum` registered.
   - Provenance records JWST observation ID, pipeline stage (Calibrated), wavelengths in µm.
   - Export center later produces a provenance bundle with the processed trace.

2. **Laboratory Reference Overlay**
   - Analyst switches to Reference tab, queries NIST ASD for `CH4` between 2.2–3.5 µm.
   - Results load into overlay table, user pins the set to the plot.
   - Overlay service assigns a palette, metadata stored in `ReferenceLibrary` for reuse.
   - Math service calculates a continuum-subtracted version of a JWST trace for overlay comparison.

3. **Composite CSV Export**
   - Multiple spectra selected, Export Center invoked.
   - Composite CSV writer aligns wavelength grids via interpolation, writes header describing units and source files.
   - Manifest zipped with CSV, saved to `exports/`.
   - Another analyst imports the bundle later, rehydrating overlays and math products.

---

## Appendix D: Historical Feature Notes & Cleanup Targets

- **2019 Legacy UI**: Early Qt Designer `.ui` files were removed; modern code constructs widgets programmatically. Ensure no stale `.ui`
  assets remain.
- **Deprecated Providers**: Early releases included NASA PDS hooks that were later deprecated. `RemoteDataService` retains scaffolding for
  expansion; revisit when catalog APIs stabilize.
- **Atlas Alignment**: `IR_EXPANSION_SUMMARY.md` references future overlays; cross-check to avoid duplication with current overlay definitions.
- **Telemetry Hooks**: Old branches experimented with WebSocket ingestion; no traces remain in `main.py`, but caution when reintroducing
  streaming features to maintain thread safety.
- **Scripting Interface**: CLI wrappers under `tools/` provide batch ingest/export scripts; revisit to ensure they still work against the
  modern service APIs.

---

## Appendix E: Capability Index Snapshot (Cross-Link to repo_inventory)

Below is a high-level index linking major capabilities to their implementation anchors for cross-referencing with the full inventory.

- **Remote Spectroscopy Acquisition**: `app/services/remote_data_service.py`, `app/ui/remote_data_dialog.py`, `docs/user/remote_data.md`
- **Local Import & Provenance**: `app/services/data_ingest_service.py`, `app/services/importers/`, `docs/user/importing.md`
- **Spectral Plotting & Analysis**: `app/ui/plot_pane.py`, `app/services/units_service.py`, `app/services/math_service.py`,
  `docs/user/plot_tools.md`
- **Overlay Management**: `app/services/overlay_service.py`, `docs/user/reference_data.md`
- **Reference Libraries**: `app/services/reference_library.py`, `docs/user/reference_data.md`
- **Export & Sharing**: `app/ui/export_center_dialog.py`, `app/services/provenance_service.py`, `docs/user/exporting.md`
- **Knowledge Stewardship**: `app/services/knowledge_log_service.py`, `docs/history/KNOWLEDGE_LOG.md`, `docs/reviews/workplan.md`
- **Operational Rituals**: `START_HERE.md`, `AGENTS.md`, `docs/history/PATCH_NOTES.md`
- **Testing & QA**: `tests/`, `tools/`, `docs/developer_notes.md`
- **Roadmap & Enhancements**: `docs/reviews/workplan.md`, `IMPLEMENTATION_SUMMARY.md`, `docs/ENHANCEMENT_PLAN_STATUS.md`

---

## Appendix F: Cleanup Task Seeds (For Future Tickets)

1. **Remote Worker Consolidation**
   - Extract shared worker base class for remote dialog and main window to avoid drift.
   - Document threading expectations in `docs/developer_notes.md`.
2. **Importer Heuristic Audit**
   - Catalogue all importer heuristics, write regression fixtures for edge cases.
   - Consider configuration files for dataset-specific overrides.
3. **Library Grouping Implementation**
   - Design grouping UX (mission, instrument, custom tags) and extend `ReferenceLibrary` schema.
   - Update UI and export flows to respect group metadata.
4. **Calibration Service Delivery**
   - Finalize schema for calibration tasks, integrate with overlays and math services.
   - Create dedicated UI dock with status indicators and guidance.
5. **Documentation Deduplication**
   - Map overlapping content across inventory, atlas, enhancement plans.
   - Establish single-source-of-truth sections with cross-links to prevent divergence.
6. **Downloads Folder Policy**
   - Write retention policy, create cleanup script under `tools/`.
   - Automate manifest regeneration for canonical samples.
7. **Accessibility Audit**
   - Evaluate keyboard navigation coverage, add screen reader metadata where Qt permits.
   - Expand documentation with accessibility guidance for analysts.
8. **Telemetry & Streaming Experiment**
   - Prototype streaming ingestion using asynchronous workers.
   - Document performance implications and fallback strategies.

---

*End of Capability Atlas.*
