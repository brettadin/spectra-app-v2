Analysis of brettadin/spectra‑app‑beta repository
Context and repository overview
brettadin/spectra‑app‑beta is the beta version of the Spectra App, a modern PySide6 desktop application for spectroscopic analysis. The README.md describes the application’s goals: a modular architecture, rigorous unit handling, provenance tracking and high‑performance plotting. The core features include multi‑format ingestion (CSV/TXT, FITS, JCAMP‑DX), remote data integration with services like NASA’s MAST and the NIST Atomic Spectra Database, offline‑first caching, unit conversion, mathematical operations, reference overlays and export capabilities[1]. The repository uses a docs‑first development approach with extensive documentation (quickstart guides, architecture specs, UI contracts, etc.), an automated test suite (pytest) and a roadmap for upcoming features and research work[2][3].
The repository structure contains:
•	app/ – the PySide6 application core, services and UI code. The main entry‑point app/main.py constructs the main window, wires up data ingestion, reference overlays and the plotting pane[4].
•	docs/ – user guides (quickstart, importing local spectra, plot tools), developer guides and AI logs. Important documents include START_HERE.md (development workflow and guidelines)[5], reports/feature_parity_matrix.md (maps legacy Streamlit prototype capabilities to the new desktop app and identifies future work)[6], and the roadmap[3].
•	specs/ – technical specifications, including architecture decisions[7] and proposed frameworks[8].
•	tests/, samples/, reports/ and packaging/ – tests, example data, planning documents and build scripts.
Status of current implementation
Based on the documentation:
•	Data ingestion: CSV/TXT ingestion is fully implemented with heuristics for messy tables (unit detection, numeric block scanning, column scoring, profile‑based axis swaps). The production pipeline now registers dedicated FITS and JCAMP importers alongside the CSV handler via DataIngestService.__post_init__ in app/services/data_ingest_service.py, so the desktop build routes .fits/.fit/.fts files through FitsImporter and .jdx/.dx/.jcamp files through JcampImporter. The FITS coverage comes from app/services/importers/fits_importer.py, which reads binary-table spectra and normalises units, while JCAMP support is provided by app/services/importers/jcamp_importer.py with ##XYDATA parsing and unit preservation. The importer currently filters the file dialog to CSV/TXT; other formats require manual entry[10].
•	Reference overlays: The desktop build supports interactive reference overlays (hydrogen lines, IR functional groups, JWST quick‑look spectra) with level‑of‑detail downsampling and label stacking[11]. Additional reference packs such as Raman or UV‑VIS are planned[12].
•	Provenance and unit services: The Provenance Service and Units Service track operations, export manifest bundles and manage unit conversions. Knowledge‑log integration is described but not yet implemented[13].
•	Plotting: The PyQtGraph plot pane supports pan/zoom gestures, reset, crosshair, snapshot export and normalisation modes, with LOD safeguards for millions of points[14][15]. A floating legend synchronises with the datasets dock.
•	Math and analysis: The docs list planned operations (A−B, A/B, baseline removal, Gaussian fitting, peak detection)[16] but there is no evidence of full implementation yet.
•	Remote data: Remote fetchers for NIST, ESO/SDSS and NASA/MAST spectra are still a backlog item[17]. The roadmap emphasises building a Remote Data dialog with caching and provenance[18].
Notable issues and potential bugs
1.	Incomplete ingestion pipeline – FITS and JCAMP‑DX support has not been implemented, and remote fetchers are missing. CSV/TXT parsing heuristics are robust, but LocalStore caching is only planned[19]. Without caching, repeated imports re‑parse large files, impacting performance.
2.	Duplicate attribute assignments in main.py – In the SpectraMainWindow constructor, attributes like _reference_overlay_payload and _reference_overlay_key are defined twice (lines 60–63 and again around lines 84–86 of the file)[20]. This redundancy could lead to confusing state or bugs if the attributes diverge. Consolidating the assignments and ensuring a single source of truth would reduce risk.
3.	Potential UI null references – Because _setup_ui() builds the toolbar before _setup_menu() runs, self.plot_toolbar is initialised ahead of the menu wiring. The existing if self.plot_toolbar is not None guard inside _setup_menu() also prevents the NoneType access the review previously cautioned against, so the menu actions remain protected[21].
4.	Gestures and LOD thresholds – The LOD cap is fixed at 120 000 points per trace[22]. On lower‑end hardware this may still cause lag; making this threshold configurable or adaptive (based on system performance) could improve responsiveness and future‑proof the app.
5.	Import heuristics limitations – The importer heuristics handle messy CSV/TXT layouts, but real‑world data may include units in unusual formats or multi‑dimensional FITS tables. When FITS parsing lands, robust error handling and validation will be needed to prevent misidentification of axes[23].
6.	Knowledge‑log integration missing – The feature parity matrix notes that automated wiring to record user actions into a History tab is not implemented[13]. Without it, provenance logs may not surface to users, limiting auditing.
Upgrades and new features to implement
Based on the roadmap and documentation, the following upgrades and features should be prioritised:
1 Implement missing importer formats
•	FITS and JCAMP‑DX ingest – Design and implement parsers for FITS 1D binary tables and JCAMP‑DX (##XYDATA) files with unit preservation, caching and provenance metadata[24]. The importer should reuse existing heuristics (numeric block scanning, column scoring) and record rationales in metadata.column_selection[23].
•	LocalStore caching – Implement the local cache integration described in the importing guide to avoid reparsing identical files[25]. Deduplicate uploads by computing SHA256 hashes and persist canonical nanometer arrays and raw source files.
2 Remote data integration
•	Remote Data dialog – Build a UI for browsing and fetching spectra from remote repositories (NIST, ESO, SDSS, JWST). Each fetcher should include dependency checks (e.g., astroquery, requests), maintain offline caching and record provenance (source URLs, timestamps, checksums)[26].
•	Asynchronous downloading and progress feedback – Use threads or async I/O so the UI remains responsive while downloading remote datasets. Display progress bars and handle network errors gracefully.
3 Enhance the Inspector and processing tools
•	Rich metadata/provenance panels – Populate the Inspector with detailed transformation logs, units, and origin information. Let users view and edit dataset aliases, sample counts, and import heuristics decisions[27]. Provide controls for applying and visualising mathematical operations (difference, ratio, baseline removal, smoothing) and record them in the provenance.
•	Math service expansions – Implement baseline correction (e.g., polynomial fitting, SNIP), Savitzky–Golay smoothing, continuum removal, and Gaussian/Lorentzian/Voigt fitting. Provide interactive UI controls (sliders or dialogues) and update the plot in real time.
4 Reference library and overlay enhancements
•	Additional reference packs – Extend the reference library beyond hydrogen and basic IR functional groups to include Raman lines and UV‑VIS functional groups[12]. Integrate atomic line lists for He I, O III, Fe II and others, with interactive redshift and Doppler shift controls.
•	Physics‑aware overlays – The Doppler, pressure and Stark broadening models already ship in app/services/line_shapes.py, and OverlayService.overlay now consumes the corresponding line_shapes metadata when assembling overlays. The remaining work focuses on exposing adjustable parameters and UI affordances for these models[28].
•	Automated screenshot generation – The feature parity matrix suggests adding automated screenshots of toolbar presets for the documentation[29]. Use PySide6’s grab() functions in tests to capture UI states and embed them in docs.
5 Knowledge Log and history tracking
•	History tab – Create a new tab in the main window that surfaces entries from the Knowledge Log service. Each user action (import, analysis operation, export) should write to the log, and the History tab should display a chronological feed with search and filter capabilities[13]. Allow users to export or clear the log.
•	AI‑assisted documentation – Integrate summarisation of log entries and code changes into patch notes, reducing documentation drift.
6 Plugin system and machine learning
•	Plugin architecture – Design a plugin manifest and loading mechanism to allow third‑party modules for functional‑group classification, similarity metrics or ML models[30]. Each plugin should declare its inputs/outputs and include documentation and tests. Consider packaging plugins as Python entry points discovered via importlib.metadata.
•	Local ML model sandbox – Provide a secure environment for running classification models offline. The sandbox should isolate models from core services and capture provenance metadata (model version, training dataset)[30].
7 Testing, documentation and CI improvements
•	Expand regression tests – Add tests for new importer formats, remote fetchers, math operations, and overlay functions. Use the existing tests/ structure as a model[31].
•	Performance benchmarks – Write performance tests to ensure the UI remains responsive with multi‑megabyte datasets and remote downloads. Use pytest markers and timeouts to track regressions.
•	Documentation sweep – The roadmap emphasises refreshing screenshots and guides once new features land[32]. Update user guides (docs/user/) and specs (specs/ui_contract/) in tandem with code changes.
•	Patch notes and versioning – Create patch notes in docs/patch_notes/ for each release, summarising new features, bug fixes and known limitations. Bump the version in app/version.json and update the quickstart accordingly.
High‑level recommendations for the STEC project
1.	Align with docs‑first workflow – Use the START_HERE.md guidelines to plan work sessions: review existing context, create a workplan with atomic tasks and acceptance criteria, implement, test, document and then prepare PRs[33].
2.	Focus on stability and performance – Ensure that the base application (ingestion, plotting, UI responsiveness) is rock solid before adding advanced analytics. Prioritise caching, error handling and interactive feedback.
3.	Use the roadmap to prioritise – Implement near‑term priorities from the October 2025 roadmap before exploring future horizons[34]. Document any deviations and record rationale in the Knowledge Log.
4.	Review AI logs and past conversations – When available, consult docs/ai_log/ to ensure continuity with previous STEC discussions. If tasks were discussed earlier (e.g., remote fetchers, plugin system), cross‑link them in your workplan.
5.	Engage with test-driven development – For each new feature or bug fix, write tests first to define expected behaviour and prevent regressions. Use the existing regression suite as a template.
6.	Collaborate via codex dev agent – Provide this analysis to your codex dev agent to guide implementation. Encourage them to trace each improvement back to the relevant documentation lines (cited above) and maintain the docs‑first ethos.
By addressing the missing importer formats, implementing remote data integration and caching, enriching the inspector and reference tools, adding a knowledge‑log history tab, designing a plugin system and strengthening testing and documentation, the Spectra App can evolve from a solid beta into a comprehensive tool for spectroscopic analysis.
________________________________________
[1] [16] raw.githubusercontent.com
https://raw.githubusercontent.com/brettadin/spectra-app-beta/main/README.md
[2] [5] [33] raw.githubusercontent.com
https://raw.githubusercontent.com/brettadin/spectra-app-beta/main/START_HERE.md
[3] [9] [17] [18] [24] [26] [28] [32] [34] raw.githubusercontent.com
https://raw.githubusercontent.com/brettadin/spectra-app-beta/main/reports/roadmap.md
[4] [20] [21] raw.githubusercontent.com
https://raw.githubusercontent.com/brettadin/spectra-app-beta/main/app/main.py
[6] [11] [12] [13] [29] [30] [31] raw.githubusercontent.com
https://raw.githubusercontent.com/brettadin/spectra-app-beta/main/reports/feature_parity_matrix.md
[7] [8] raw.githubusercontent.com
https://raw.githubusercontent.com/brettadin/spectra-app-beta/main/specs/architecture.md
[10] [19] [23] [25] raw.githubusercontent.com
https://raw.githubusercontent.com/brettadin/spectra-app-beta/main/docs/user/importing.md
[14] [15] [22] [27] raw.githubusercontent.com
https://raw.githubusercontent.com/brettadin/spectra-app-beta/main/docs/user/plot_tools.md
