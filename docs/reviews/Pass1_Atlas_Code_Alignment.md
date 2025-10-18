
Pass 1 — Atlas ↔ Code Alignment (what’s solid, what’s partial, what’s missing)
What I reviewed (from your ZIP)
	• Docs: docs/atlas/* (index + chapters 1–31), docs/history/* (MASTER_PROMPT, RUNNER_PROMPT, PATCH_NOTES, KNOWLEDGE_LOG), docs/user/* (quickstart, units_reference, importing, remote_data, plot_tools, in_app_documentation), specs/* (architecture, system_design), AGENTS.md, START_HERE.md, reports/*.
	• Code: app/services/* (units, ingest, importers CSV/FITS/JCAMP, overlay, math, provenance, remote, line_shapes, store, spectrum), app/ui/* (plot pane, palettes, remote dialog), app/main.py, app/data/reference/* (NIST H, JWST, IR groups, line-shape placeholders).
	• Tests: 25 files including units round-trip, importer heuristics, remote services, knowledge-log, overlay/line-shape, provenance/export, smoke workflow, plot perf stub.
Alignment snapshot
Area	Status	Notes
Units canon / idempotent conversions	✅ Solid	UnitsService stores canon (nm + absorbance), round-trip tests exist (test_units_roundtrip.py). User docs align.
Ingest (CSV/FITS/JCAMP)	✅ Solid	Heuristics + header handling; JCAMP present. Provenance recorded. Multi-select import working.
Provenance & export bundles	✅ Solid	ProvenanceService writes manifest + sources + CSVs + log; regression tests exist; docs describe structure.
Remote data (NIST/MAST)	✅ Solid	RemoteDataService + RemoteDataDialog with validation hints; optional deps guarded; caching via LocalStore; tests cover adapters + dialog behavior.
Plotting performance (LOD)	✅ Solid	PyQtGraph with max-points budget (configurable; persisted via QSettings); perf stub tests.
Library/History/Knowledge-log	✅/🟨	Knowledge-log service + docs; Library view mentioned & tested; ensure the Library dock class is explicitly implemented/linked in UI (I see tests, but no standalone library_* UI file—likely in main.py).
Line-shape previews (Doppler/pressure/Stark)	✅/🟨	Placeholder models + tests; UI previews via Reference tab; not yet a full Calibration Manager acting on user data.
Uncertainty ribbons	🟨 Partial	I see uncertainty rendering for some reference plots in main.py; make sure imported datasets can show ribbons and that they’re toggleable + persisted.
Identification/scoring rubric	❌ Missing	Atlas Ch.7 + Ch.11 specify explainable scoring; I don’t see a SimilarityService/ScoringService yet.
Calibration pipeline (LSF honesty + convolve-down + velocity frames)	❌ Missing	Atlas Ch.6 expects an explicit manager. Code has line-shape helpers but no full pipeline (LSF banners, kernel choice, velocity frame UI).
Architecture surface for multi-UI future	🟨 Partial	Atlas Chapters 14/29 outline React/TypeScript UI + Python Engine (API). Code is PySide6 desktop. This conflict needs an RFC to set a seam (keep PySide6 now, extract an Engine API).
Functional-group ML tagging (IR)	🟨 Planned	Reference JSON + UI overlay OK; predictive model integration (auto-tag + table) not wired yet.
Packaging hygiene	🟨 Minor	ZIP includes __pycache__/ and .pyc files. .gitignore likely covers it, but make sure release zips exclude them.

Gaps → concrete fixes (files & actions)
1) Calibration Manager (Atlas Ch.6)
Why: Align with Atlas “LSF honesty,” “convolve down,” and explicit frames (air/vacuum, heliocentric).
	• Add app/services/calibration_service.py
		○ Kernels: Gaussian (instrumental LSF), Lorentzian (pressure), Voigt (compose), Doppler shift (km/s).
		○ API: apply(data, steps=[...]) -> Spectrum, transforms[] (each step: type, params, citation).
	• UI: CalibrationDock (or a panel in Inspector) with: target resolution, kernel picker, “convolve down to lowest,” velocity frame selector, banner that states the active LSF + params.
	• Provenance: Append transform steps to export manifest; show “LSF banner” badge over the plot.
	• Tests: synthetic signals → assert matched FWHM; Doppler 30 km/s shift; provenance step order.
2) Uncertainty on imported datasets
	• Extend DataIngestService to accept optional σ arrays; table columns “y ± σy”; store with Spectrum metadata.
	• Plot: in PlotPane, add ribbon layer for selected traces; toggle via Inspector; persist via QSettings.
	• Docs: update plot_tools.md and units_reference.md with examples and limits.
	• Tests: headless rendering of ribbons + toggle persistence.
3) Explainable Identification/Scoring (Atlas Ch.7 & Ch.11)
	• Add app/services/similarity_service.py and scoring_service.py
		○ Peak matching (tolerance-aware), cross-correlation, cosine similarity.
		○ Output per-feature contributions + uncertainties + priors.
	• UI: “Explain” drawer shows per-feature table; export as CSV inside provenance bundle.
	• Docs: docs/user/identification.md + rubric table; acceptance thresholds.
	• Tests: seeded determinism; jitter tolerance; score deltas reflect calibration shifts.
4) Architecture seam for future multi-UI
	• RFC: docs/rfc/RFC-YYYYMMDD-frontend-architecture.md with options:
A) remain PySide6, B) React/Tauri + Engine API, C) hybrid (extract Engine API now).
	• If accepted (hybrid): add app/engine/api.py (thin façade over services) with a clean, documented surface; optional FastAPI adapter in tools/engine_http/ behind a feature flag.
	• Tests: contract tests for engine methods; keep PySide6 shell fully functional.
5) Functional-group prediction flow
	• Adapter structure in app/services/ml_service.py with optional model loader (CNN pipeline).
	• UI: “Identify functional groups” button annotates IR regions + writes to data table notes.
	• Provenance: model version + commit/weights hash + input ranges + confidence.
	• Tests: mock model path; deterministic annotations on fixtures.
6) Library/History Dock clarifications
	• If Library dock UI is embedded in main.py, extract to app/ui/library_dock.py for clarity (already tested behavior).
	• Ensure cross-link from a Library item → opens knowledge-log summary, as described in patch notes.
7) Packaging hygiene
	• Add ZIP task to exclude __pycache__/ and .pyc (keep .gitignore as is).
	• Verify app/version meta (JSON or module) exists and is injected into manifests.

Streamlining opportunities (quick wins)
	• Inspector grouping: Group overlay/line-shape/uncertainty controls and persist toggles; reduce panel hopping.
	• Plot presets: You already added palettes + LOD presets—add a one-click “Teaching mode” preset (large fonts, high-contrast, slow animations off).
	• Error paths: Remote dialog already blocks empty searches—mirror this pattern across importers (e.g., explicit error for missing headers with a “Learn more” link to docs).
	• Docs map: Add docs/MAP.md linking Atlas chapters → code modules/tests (a 1-page index reduces onboarding time).
	• Manifest schema file: Commit docs/specs/provenance_schema.json and validate in tests.

Where Atlas and code disagree
	• UI stack: Atlas (Ch.14/29) describes React/TypeScript UI; code (and specs folder) currently endorse PySide6. This is an intentional fork—treat it via RFC, don’t silently switch.
	• Calibration presence: Atlas expects a full manager; code has placeholders and previews. Implement manager as above.
	• Identification rubric: Atlas specifies explainable scoring; code hasn’t got that service yet.

Sanity checks that look great
	• Canon & conversions (and tests)
	• Ingest across CSV/FITS/JCAMP with heuristics
	• Remote data adapters + validation + caching
	• Provenance bundle layout + tests
	• Plot LOD budget with persistence
	• Palette presets and accessibility push
