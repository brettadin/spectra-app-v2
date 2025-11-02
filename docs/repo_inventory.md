# Repository Inventory and Status

> Archived notice (2025-11-02): This inventory has been archived to
> `docs/history/archive/2025-11-02-pre-cleanup/repo_inventory.md`.
> For a current overview, see `docs/INDEX.md` and browse the repository tree.

**Generated**: 2025-11-02T10:27:35-05:00 (America/New_York) / 2025-11-02T15:27:32+00:00 (UTC)

This document surveys the Spectra desktop preview repository, catalogues every tracked path, and summarises the functional status
of major features, libraries, and outstanding follow-up work.

## Project Overview

Spectra is a PySide6 desktop application for ingesting, analysing, and exporting spectroscopy datasets. The runtime focuses on
planetary, laboratory, and remote-catalogue spectra with provenance-first workflows and extensive bundled documentation. Core
services live under `app/services`, Qt widgets under `app/ui`, and bundled datasets under `samples/`. The repository also includes
tooling for dataset acquisition, packaging scripts, and a comprehensive documentation library.

## Feature and Capability Snapshot

### Implemented and Working
- **Remote data acquisition** via the `RemoteDataService` with MAST, NIST ASD, and curated Solar System providers, including
  asynchronous search/download workers in `app/main.py` and UI flows in `app/ui/remote_data_dialog.py`. Results persist through the
  `LocalStore` cache and can trigger ingest directly.【F:app/main.py†L36-L128】【F:app/services/remote_data_service.py†L1-L120】
- **Multi-format ingest pipeline** supporting CSV, FITS, JCAMP, and exoplanet catalogue bundles through `DataIngestService` and
  importer plugins, normalising units via `UnitsService` and storing provenance metadata.【F:app/services/data_ingest_service.py†L1-L125】
- **Plotting and overlay analysis** with pyqtgraph-based traces, trace styling, and reference overlays handled by
  `app/ui/plot_pane.py` and services such as `OverlayService` and `LineShapeModel`.【F:app/ui/plot_pane.py†L1-L120】【F:app/services/overlay_service.py†L1-L120】
- **Reference library** with IR functional-group datasets, spectral line retrieval, and knowledge-log recording delivered through
  `ReferenceLibrary`, `KnowledgeLogService`, and associated data bundles in `app/data/`.【F:app/services/reference_library.py†L1-L120】【F:app/services/knowledge_log_service.py†L1-L120】
- **Export workflows** (CSV, provenance bundles) driven by `ExportCenterDialog` and `ExportOptionsDialog`, wiring to the
  `ProvenanceService` and importer-aware round trips.【F:app/ui/export_center_dialog.py†L1-L120】【F:app/services/provenance_service.py†L1-L120】
- **Extensive user and developer documentation** providing onboarding, workplans, specs, and historical notes across `docs/`.

### Present but Incomplete or Not Yet Landed
- **Calibration service and dock** remain TODO per the Batch 14 workplan checklist (no corresponding `app/services/calibration_service.py`).【F:docs/reviews/workplan.md†L6-L15】
- **Identification stack** (peak scoring, UI, explainable scorecards) is still outstanding in the workplan backlog.【F:docs/reviews/workplan.md†L8-L12】
- **Dataset removal UI polish**, advanced visualization (thumbnails, snapshots), and expanded remote providers are tracked but not
  yet shipped.【F:docs/reviews/workplan.md†L16-L26】

### Known Issues and Gaps
- **Remote download URL stability** for the PDS downloader encountered 404 errors; further investigation is recorded in patch notes
  and worklogs.【F:docs/history/PATCH_NOTES.md†L1-L33】
- **MAST imaging expansion** depends on optional dependencies (requests, astroquery, pandas) and remains sensitive to missing
  wheels in constrained environments, documented in START_HERE and workplan guidance.【F:docs/reviews/workplan.md†L31-L43】

### Potential Upgrade Routes
- Extend the calibration manager, identification stack, and dataset categorisation backlog items outlined in Batch 14.
- Add more spectroscopy catalogues once dependency checks stabilise (e.g., ESO, PDS APIs) per workplan priorities.
- Explore ML integration for IR functional groups, building on `docs/specs/ml_functional_group_prediction.md` and
  `IR_EXPANSION_SUMMARY.md`.

## Library Usage
- **PySide6** provides the Qt bindings consumed via `app/qt_compat.py`, main-window widgets, and dialogs (`app/ui/*`).
- **pyqtgraph** renders the spectroscopy plots and trace manipulations inside `PlotPane` and overlay services.
- **numpy** underpins spectral arrays, math utilities, and importer normalisation.
- **astropy** supplies FITS handling and astrophysical units utilised by importers.
- **requests** and **astroquery** (optional) drive remote catalogue HTTP access and MAST API calls in `RemoteDataService`.
- **pytest** powers regression coverage with focused modules under `tests/`.

## Directory and File Descriptions

Each table lists immediate children for the given scope with concise descriptions. Subdirectories include additional tables.

### Top-Level Paths
| Path | Type | Description |
| --- | --- | --- |
| `.github/` | dir | GitHub configuration and CI workflows. |
| `.vscode/` | dir | VS Code workspace recommendations and debugger settings. |
| `AGENTS.md` | file | Operational manual for contributors and agents. |
| `AUDIT_REPORT.md` | file | Prior audit summary of repository state. |
| `CONTRIBUTING.md` | file | Contribution guidelines. |
| `HOUSEKEEPING_PLAN.md` | file | Ongoing maintenance checklist. |
| `IMPLEMENTATION_SUMMARY.md` | file | Detailed enhancement-plan status report. |
| `IR_EXPANSION_SUMMARY.md` | file | Notes on the IR functional groups dataset expansion. |
| `README.md` | file | Project introduction and onboarding pointers. |
| `RunSpectraApp.cmd` | file | Windows launcher ensuring dependency installation. |
| `SECURITY.md` | file | Security policy. |
| `START_HERE.md` | file | Onboarding instructions emphasising environment prep. |
| `app/` | dir | Application source code (services, UI, data). |
| `docs/` | dir | Comprehensive documentation library. |
| `downloads/` | dir | Placeholder tree for retrieved remote datasets. |
| `exports/` | dir | Sample export manifests and data products. |
| `goals.txt` | file | High-level product goals. |
| `packaging/` | dir | Packaging metadata and installer assets. |
| `patch.patch` | file | Historical patch sample. |
| `pyproject.toml` | file | Project metadata and dependencies. |
| `pyrightconfig.json` | file | Pyright static type checker settings. |
| `reports/` | dir | Research and audit reports. |
| `requirements.txt` | file | Dependency pin set for runtime tooling. |
| `samples/` | dir | Bundled sample spectra across domains. |
| `sitecustomize.py` | file | Test/bootstrap helper for dependency installation. |
| `specs/` | dir | Design specifications and roadmap documents. |
| `tests/` | dir | Automated test suite. |
| `tools/` | dir | Utility scripts for dataset processing and packaging. |
| `ui_screenshot*.png` | file | UI reference images for documentation. |

### `.github/`
| Path | Type | Description |
| --- | --- | --- |
| `.github/workflows/ci.yml` | file | Continuous integration workflow executing tests and linting. |

### `.vscode/`
| Path | Type | Description |
| --- | --- | --- |
| `.vscode/launch.json` | file | Debugger configurations for VS Code. |
| `.vscode/settings.json` | file | Workspace-specific editor settings. |

### `app/`
| Path | Type | Description |
| --- | --- | --- |
| `app/__init__.py` | file | Package marker exporting primary services. |
| `app/data/` | dir | Bundled JSON/reference assets consumed at runtime. |
| `app/main.py` | file | Application entry point with Qt bootstrap and background workers. |
| `app/qt_compat.py` | file | Helper selecting PySide6 vs PyQt bindings. |
| `app/services/` | dir | Domain services (ingest, remote data, provenance, math). |
| `app/ui/` | dir | Qt widgets and dialogs for Spectra UI. |

#### `app/data/`
| Path | Type | Description |
| --- | --- | --- |
| `app/data/reference/` | dir | Reference datasets (e.g., IR functional groups). |
| `app/data/samples_manifest.json` | file | Index of bundled sample datasets. |

#### `app/services/`
| Path | Type | Description |
| --- | --- | --- |
| `app/services/__init__.py` | file | Aggregates service exports for simplified imports. |
| `app/services/data_ingest_service.py` | file | Multi-format ingest orchestrator. |
| `app/services/knowledge_log_service.py` | file | Runtime knowledge log integration. |
| `app/services/line_shapes.py` | file | Line-shape modelling utilities. |
| `app/services/math_service.py` | file | Numerical helpers for spectra operations. |
| `app/services/nist_asd_service.py` | file | NIST Atomic Spectra Database client wrappers. |
| `app/services/overlay_service.py` | file | Overlay calculations and combinations. |
| `app/services/provenance_service.py` | file | Export provenance manifest builder. |
| `app/services/reference_library.py` | file | Handles reference datasets and curated overlays. |
| `app/services/remote_data_service.py` | file | Remote catalogue search/download manager. |
| `app/services/spectrum.py` | file | Spectrum data model and creation helpers. |
| `app/services/store.py` | file | Local cache persistence for ingested data. |
| `app/services/units_service.py` | file | Unit normalisation and conversion utilities. |

#### `app/ui/`
| Path | Type | Description |
| --- | --- | --- |
| `app/ui/__init__.py` | file | UI package exports. |
| `app/ui/export_center_dialog.py` | file | Export workflow coordinator dialog. |
| `app/ui/export_options_dialog.py` | file | Export format options and validation. |
| `app/ui/palettes.py` | file | Trace colour palette definitions and theming helpers. |
| `app/ui/plot_pane.py` | file | Main plotting widget with dataset management. |
| `app/ui/remote_data_dialog.py` | file | Remote data search/download UI. |

### `docs/`
| Path | Type | Description |
| --- | --- | --- |
| `docs/atlas/` | dir | Atlas chapters documenting spectroscopy concepts. |
| `docs/brains/` | dir | Knowledge “neurons” capturing architectural decisions. |
| `docs/dev/` | dir | Developer notes, worklogs, and onboarding references. |
| `docs/history/` | dir | Patch notes, knowledge logs, historical archives. |
| `docs/reference_sources/` | dir | Link collections and provenance references. |
| `docs/reviews/` | dir | Workplans, review dossiers, QA notes. |
| `docs/specs/` | dir | Design specs and roadmap documents. |
| `docs/user/` | dir | User guides (importing, remote data, plotting). |
| `docs/link_collection.md` | file | Canonical resource compendium. |

#### Documentation Subdirectories
- **`docs/atlas/`**: Structured narratives on spectroscopy topics by chapter.
- **`docs/brains/`**: Individual markdown entries for architectural insights with timestamps.
- **`docs/dev/`**: Worklogs (`docs/dev/worklog/*.md`), developer notes, quick references.
- **`docs/history/`**: Patch notes, knowledge log, historical archives, timelines.
- **`docs/reviews/`**: Workplan tracking, pass-review dossiers, backlog notes.
- **`docs/specs/`**: Feature designs (e.g., ML roadmap, calibration, pipeline specs).
- **`docs/user/`**: End-user documentation covering remote data flows, importing, plotting tools, unit references.

### Data and Sample Trees
| Path | Type | Description |
| --- | --- | --- |
| `downloads/` | dir | Empty staging directories for remote downloads (`_incoming`, `files/`). |
| `exports/` | dir | Example export outputs (CSV bundles under `spectra/` and manifests in `sources/`). |
| `samples/IR data/` | dir | Laboratory IR CSV/JCAMP datasets for CO₂/H₂O experiments. |
| `samples/SOLAR SYSTEM/` | dir | Mercury MASCS sample packages with PDS metadata. |
| `samples/SUN AND MOON/` | dir | Solar/lunar reference spectra. |
| `samples/exoplanets/` | dir | Curated exoplanet CSV datasets. |
| `samples/fits data/` | dir | FITS samples (SpeX library, JWST, TESS light curves). |
| `samples/lamp data/` | dir | Calibration lamp spectra (Neon, Mercury, etc.). |
| `samples/other file types/` | dir | Miscellaneous CSV/TXT samples and manifests. |
| `samples/solar_system/` | dir | Curated Solar System quick-pick manifests and spectra used by the remote provider. |

> **Note**: Each sample subdirectory retains raw datasets for demonstrations; see the [Complete Path Index](#complete-path-index)
> for an exhaustive list of individual files.

### Testing and Tooling
| Path | Type | Description |
| --- | --- | --- |
| `tests/` | dir | Pytest suites (unit, integration, fixtures, manual smoke tests). |
| `tests/data/` | dir | Test assets supporting importer/remote tests. |
| `tests/fixtures/` | dir | Pytest fixtures. |
| `tests/integration/` | dir | Higher-level regression tests. |
| `test_exoplanet_manual.py` | file | Manual script for exoplanet importer verification. |
| `test_spex_manual.py` | file | Manual SpeX FITS regression script. |
| `tools/` | dir | Utility scripts (PDS downloader, manifest builders, reference packaging). |
| `tools/reference_build/` | dir | Reference dataset build scripts and metadata. |

### Packaging and Reports
| Path | Type | Description |
| --- | --- | --- |
| `packaging/` | dir | Installer resources (manifests, icons). |
| `reports/` | dir | Analytical reports and exported documentation snapshots. |

## Complete Path Index

The following list is generated from `git ls-files` and enumerates every tracked file path in the repository for quick lookup.

```
.gitattributes
.github/copilot-instructions.md
.github/dependabot.yml
.github/pull_request_template.md
.github/workflows/ci.yml
.github/workflows/provenance.yml
.gitignore
.vscode/launch.json
AGENTS.md
AUDIT_REPORT.md
CONTRIBUTING.md
HOUSEKEEPING_PLAN.md
IMPLEMENTATION_SUMMARY.md
IR_EXPANSION_SUMMARY.md
README.md
RunSpectraApp.cmd
SECURITY.md
START_HERE.md
app/__init__.py
app/data/reference/ir_functional_groups.json
app/data/reference/ir_functional_groups_extended.json
app/data/reference/jwst_targets.json
app/data/reference/line_shape_placeholders.json
app/data/reference/nist_hydrogen_lines.json
app/main.py
app/qt_compat.py
app/services/__init__.py
app/services/data_ingest_service.py
app/services/importers/__init__.py
app/services/importers/base.py
app/services/importers/csv_importer.py
app/services/importers/exoplanet_csv_importer.py
app/services/importers/fits_importer.py
app/services/importers/jcamp_importer.py
app/services/knowledge_log_service.py
app/services/line_shapes.py
app/services/math_service.py
app/services/nist_asd_service.py
app/services/overlay_service.py
app/services/provenance_service.py
app/services/reference_library.py
app/services/remote_data_service.py
app/services/spectrum.py
app/services/store.py
app/services/units_service.py
app/ui/__init__.py
app/ui/export_center_dialog.py
app/ui/export_options_dialog.py
app/ui/palettes.py
app/ui/plot_pane.py
app/ui/remote_data_dialog.py
docs/BUILD_WINDOWS.md
docs/Comprehensive Enhancement Plan for Spectra App.md
docs/DATA_ACQUISITION_PIPELINE.md
docs/Development history of the Spectra App project.md
docs/ENHANCEMENT_PLAN_STATUS.md
docs/QUICK_START_BULK_DATA.md
docs/Telescope-Based Planetary Datasets (UV-VIS and IR).docx
docs/Telescope-Based Planetary Datasets (UV-VIS and IR).pdf
docs/Telescope-Based Planetary datasets.md
docs/atlas/0_index_stec_master_canvas_index_numbered.md
docs/atlas/README.md
docs/atlas/chapter_10_campus_workflows_that_actually_work.md
docs/atlas/chapter_11_minimal_scoring_rubric_for_identifications.md
docs/atlas/chapter_12_file_formats_your_future_self_wont_hate.md
docs/atlas/chapter_13_documentation_and_learning_module.md
docs/atlas/chapter_14_application_creation_development_and_use.md
docs/atlas/chapter_15_spectral_data_collection_consolidation_and_comparisons.md
docs/atlas/chapter_16_use_of_ai_in_application_development_and_persistent_self_teaching_and_referencing_approach.md
docs/atlas/chapter_17_goals_and_outcomes.md
docs/atlas/chapter_18_future_goals.md
docs/atlas/chapter_19_dreams_and_aspirations.md
docs/atlas/chapter_1_modalities_instruments_and_what_they_tell_you.md
docs/atlas/chapter_20_fun_additions.md
docs/atlas/chapter_21_useful_additions.md
docs/atlas/chapter_22_good_ui_design.md
docs/atlas/chapter_23_spectroscopy.md
docs/atlas/chapter_24_physics.md
docs/atlas/chapter_25_chemistry.md
docs/atlas/chapter_26_astrophysics.md
docs/atlas/chapter_27_astrochemistry.md
docs/atlas/chapter_28_physical_chemistry.md
docs/atlas/chapter_29_programming.md
docs/atlas/chapter_2_how_to_gather_the_spectra_cleanly_campus_edition.md
docs/atlas/chapter_30_instrumentation.md
docs/atlas/chapter_31_telescopes.md
docs/atlas/chapter_32_sources.md
docs/atlas/chapter_3_cross_relating_signals_across_modalities.md
docs/atlas/chapter_4_data_sources_to_ingest_and_align.md
docs/atlas/chapter_5_unifying_axes_and_units_in_the_app.md
docs/atlas/chapter_6_calibration_and_alignment_pipeline.md
docs/atlas/chapter_7_identification_and_prediction_logic.md
docs/atlas/chapter_8_provenance_and_reproducibility_you_will_not_skip.md
docs/atlas/chapter_9_app_features_this_workflow_expects.md
docs/atlas/remote_data_flow.md
docs/brains/2025-10-18T0924-remote-data-ux.md
docs/brains/2025-10-22T1625-planetary-spectroscopy-requirements.md
docs/brains/2025-10-25-remote-download-tuple-issue.md
docs/brains/2025-10-25T0230-ir-ml-integration.md
docs/brains/2025-10-31T1938-pds-downloader-filtering-strategy.md
docs/brains/README.md
docs/brains/ingest_service_bytes.md
docs/brains/mast_download_fallback.md
docs/brains/nist_threading.md
docs/brains/remote_data_pipeline.md
docs/dev/Accessing and Comparing Real Spectral Data from JWST and Other Telescopes.md
docs/dev/PLANNING_STRUCTURE.md
docs/dev/ci_gates.md
docs/dev/data_repository_reorg_plan.md
docs/dev/ingest_pipeline.md
docs/dev/ir_ml_quick_reference.md
docs/dev/knowledge_log_refactor_plan.md
docs/dev/path_notes.md
docs/dev/reference_build.md
docs/dev/reference_library.md
docs/dev/worklog/2025-10-22.md
docs/dev/worklog/2025-10-25.md
docs/dev/worklog/2025-10-25_remote_download_handoff.md
docs/dev/worklog/2025-10-26_normalization_fix.md
docs/dev/worklog/2025-10-29_repo_audit_kickoff.md
docs/dev/worklog/2025-10-31_pds_downloader_refinement.md
docs/dev/worklog/2025-10-31_pds_url_404_issue.md
docs/dev/worklog/QUICK_REFERENCE_pds_downloader.md
docs/dev/worklog/README.md
docs/developer_notes.md
"docs/history/# MASCS Download Issues and Changes (2025\342\200\22111\342\200\22101).md"
docs/history/KNOWLEDGE_LOG.md
docs/history/KNOWLEDGE_LOG_ARCHIVE_2025-11-01.md
docs/history/KNOWLEDGE_LOG_BACKUP_2025-11-01.md
docs/history/MASTER PROMPT.md
docs/history/MASTER_PROMPT.md
docs/history/PATCH_NOTES.md
docs/history/Planet Data Playbook What to get, where, and how much.md
docs/history/Planetary Data.md
docs/history/RUNNER_PROMPT.md
docs/history/past prompts/2025-10-14T065106_local-patch-milestone1_user-prompt.txt
docs/history/past prompts/2025-10-14T070029_local-patch-v1.0.0_user-prompt.txt
docs/history/past prompts/2025-10-14T152314_local-patch-v1.0.1_user-prompt.txt
docs/history/past prompts/2025-10-14T153709_local-patch-v1.0.2_user-prompt.txt
docs/history/past prompts/2025-10-14T154317_local-patch-v1.0.3_user-prompt.txt
docs/history/past prompts/Debugging_application_launch.pdf
docs/history/past prompts/app_review_previous.md
docs/history/past prompts/branch_debugging_launch_summary.md
docs/history/past prompts/first_prompt.txt
docs/link_collection.md
docs/reference_sources/README.md
docs/reference_sources/Telescope-Based Planetary Datasets (UV-VIS and IR).docx
docs/reference_sources/Telescope-Based Planetary Datasets (UV-VIS and IR).pdf
docs/reference_sources/goals.md
docs/reference_sources/ir_functional_groups.csv
docs/reference_sources/link_collection.md
docs/reference_sources/training_links.md
docs/reviews/Pass1_Atlas_Code_Alignment.md
docs/reviews/Pass2_UI_UX_behaviors.md
docs/reviews/Pass3_Calibration_&_dentification.md
docs/reviews/Pass4_Data_&_Provenance_Cohesion.md
docs/reviews/doc_inventory_2025-10-14.md
docs/reviews/pass1.md
docs/reviews/pass2.md
docs/reviews/pass3.md
docs/reviews/pass4.md
docs/reviews/workplan.md
docs/reviews/workplan_backlog.md
docs/specs/ml_functional_group_prediction.md
docs/specs/provenance_schema.json
docs/spectra_history.md
docs/user/GETTING_STARTED_WITH_REAL_DATA.md
docs/user/README.md
docs/user/importing.md
docs/user/in_app_documentation.md
docs/user/plot_tools.md
docs/user/quickstart.md
docs/user/real_spectral_data_guide.md
docs/user/reference_data.md
docs/user/remote_data.md
docs/user/spectroscopy_primer.md
docs/user/units_reference.md
downloads/_incoming/tmplat5jdey/jupiter__9407171405N_evt.fits
downloads/files/00/CO2 - 300 torr A.csv
downloads/files/04/bckgr.csv
downloads/files/06/uranus_ir.csv
downloads/files/0b/F6IV_HD11443.fits
downloads/files/0d/bkgrd 10 16 VAC.csv
downloads/files/0e/F0II_HD6130.fits
downloads/files/11/venus_ir.csv
downloads/files/12/plnt_Neptune.fits
downloads/files/16/F4III_HD21770.fits
downloads/files/16/run2.csv
downloads/files/1f/jupiter_uv.csv
downloads/files/21/F0Ib-II_HD135153.fits
downloads/files/21/sample_spectrum.csv
downloads/files/21/venus_visible.csv
downloads/files/23/neptune_visible.csv
downloads/files/2c/F0IIIa_HD89025.fits
downloads/files/2d/mercury_visible.csv
downloads/files/2d/umd_ob2_49_13044_005906_sci.csv
downloads/files/2e/goodo vapor run i think - Copy.csv
downloads/files/2e/goodo vapor run i think.csv
downloads/files/31/F1II_HD173638.fits
downloads/files/34/F0III-IVn_HD13174.fits
downloads/files/35/vacuumed cell.csv
downloads/files/36/F2Ib_HD182835.fits
downloads/files/3c/F5.5III-IV_HD75555.fits
downloads/files/43/pluto_ir.csv
downloads/files/44/H2O_Lamp.csv
downloads/files/45/F0Ia_HD7927_ext.fits
downloads/files/45/jupiter__9408090029N_vo.fits
downloads/files/48/neptune_uv.csv
downloads/files/48/table_WASP-17-b-Louie-et-al.-2025.csv
downloads/files/49/100 torr cold water.csv
downloads/files/4b/C-J4.5IIIa_C26j6_HD70138.fits
downloads/files/4d/h2o vapor test 1.csv
downloads/files/4e/bkgrd.csv
downloads/files/50/mars_ir.csv
downloads/files/50/open air A.csv
downloads/files/50/run4.csv
downloads/files/58/earth_ir.csv
downloads/files/62/F4V_HD16232.fits
downloads/files/62/earth_visible.csv
downloads/files/6a/h2o v2 10 27.csv
downloads/files/6a/tess2021118034608-s0038-0000000388857263-0209-s_lc.fits
downloads/files/6d/CO2 - 500 torr A.csv
downloads/files/70/F5Ib-G1Ib_HD213306.fits
downloads/files/72/F2-F5Ib_BD+38_2803.fits
downloads/files/72/F7III_HD124850.fits
downloads/files/76/F1V_HD213135.fits
downloads/files/78/C-N4.5C25.5MS3_HD76221.fits
downloads/files/78/F2Ib_HD182835_ext.fits
downloads/files/78/F7II-_HD201078.fits
downloads/files/79/F0IV_HD27397.fits
downloads/files/7c/C7,6e(N4)_HD31996.fits
downloads/files/7d/h2o run 1 10 27 - Copy.csv
downloads/files/7d/h2o run 1 10 27.csv
downloads/files/7d/tess2019112060037-s0011-0000000388857263-0143-s_lc.fits
downloads/files/7e/CO2 - 500 torr.csv
downloads/files/88/plnt_Saturn.fits
downloads/files/8e/plnt_Uranus.fits
downloads/files/8e/ufc_ob5_29_15094_155425_sci.csv
downloads/files/8f/uranus_uv.csv
downloads/files/90/.880torr~ w low vol h2o vapor - Copy.csv
downloads/files/90/.880torr~ w low vol h2o vapor.csv
downloads/files/90/10.8 Test 2.csv
downloads/files/90/_880torr~ w low vol h2o vapor.csv
downloads/files/90/saturn_visible.csv
downloads/files/91/Run1 no co2.csv
downloads/files/91/sketchy vapor test.csv
downloads/files/92/vacc'd again 244 pm.csv
downloads/files/96/C-J5-C25-j4_HD57160.fits
downloads/files/97/mercury_ir.csv
downloads/files/99/C-N4.5C24.5_HD92055.fits
downloads/files/9a/Methanol Blank.csv
downloads/files/9c/F2III-IV_HD40535.fits
downloads/files/9c/low vapor for the road.csv
downloads/files/9c/umc_ob5_65_15094_211347_sci.csv
downloads/files/a0/uranus_visible.csv
downloads/files/a1/ufc_ob5_29_15094_181139_sci.csv
downloads/files/a7/neptune_ir.csv
downloads/files/aa/pluto_visible.csv
downloads/files/aa/umd_ob2_49_13044_010912_sci.csv
downloads/files/ab/F0Ib-II_HD135153_ext.fits
downloads/files/ab/F5V_HD218804.fits
downloads/files/b0/F6V_HD215648.fits
downloads/files/b0/i froze h2o in the schlenk line oopsie.csv
downloads/files/b4/cold water test 1.csv
downloads/files/b6/jupiter_visible.csv
downloads/files/b8/F1II_HD173638_ext.fits
downloads/files/ba/saturn_ir.csv
downloads/files/bb/table_HAT-P-18-b-Fournier-Tondreau-et-al.-2024.csv
downloads/files/bd/F5V_HD27524.fits
downloads/files/c8/F4V_HD87822.fits
downloads/files/c8/F5III_HD17918.fits
downloads/files/ca/h2o run 3 good i think 10 27 - Copy.csv
downloads/files/ca/h2o run 3 good i think 10 27.csv
downloads/files/cc/F6III-IV_HD160365.fits
downloads/files/cf/10.8 Test 1.csv
downloads/files/cf/F5II-III_HD186155.fits
downloads/files/d2/F0Ia_HD7927.fits
downloads/files/d3/plnt_Jupiter.fits
downloads/files/d4/h2o all runs avg-composite.csv
downloads/files/d4/pluto_uv.csv
downloads/files/d6/100 torr h2o 4-1k - Copy.csv
downloads/files/d6/100 torr h2o 4-1k.csv
downloads/files/d6/C-N4C23.5_HD44984.fits
downloads/files/d7/jupiter_ir.csv
downloads/files/d8/7ish torr w h2o vapor - Copy.csv
downloads/files/d8/7ish torr w h2o vapor.csv
downloads/files/d9/F0II_HD6130_ext.fits
downloads/files/d9/table_WASP-96-b-Radica-et-al.-2023.csv
downloads/files/db/F2V_HD113139.fits
downloads/files/de/C-N5C26-_HD48664.fits
downloads/files/de/tess2021118034608-s0038-0000000388857263-0209-a_fast-lc.fits
downloads/files/df/F0V(n)_HD108519.fits
downloads/files/e0/table_Luhman-16-b-Biller-et-al.-2024.csv
downloads/files/e1/CO2 - 300 torr.csv
downloads/files/e1/F5Ib-G1Ib_HD213306_ext.fits
downloads/files/e2/F3V_HD26015.fits
downloads/files/e3/C-R2+IIIa_C22.5_HD76846.fits
downloads/files/e3/open air.csv
downloads/files/e8/umc_ob5_34_15094_004734_sci.csv
downloads/files/ed/table_WASP-178-b-Lothringer-et-al.-2022.csv
downloads/files/ef/bkgrd A.csv
downloads/files/f1/mercury_uv.csv
downloads/files/f7/mars_visible.csv
downloads/files/fe/tess2019140104343-s0012-0000000388857263-0144-s_lc.fits
downloads/index.json
exports/hydrogen_merged.csv
exports/log.txt
exports/merge test 1_wide.csv
exports/moon_manifest-composite.csv
exports/moon_manifest.csv
exports/moon_manifest.json
exports/moon_manifest.png
exports/sources/1003-pointing-at-moon-subt2-0-22-05-15-398-e0856eb2-6f97-4895-bb9a-615d24c65c13.txt
exports/sources/1003-pointing-at-moon-subt2-10-22-10-16-917-a5d5f41f-f73d-4f1b-92a8-13e54ed0c8d0.txt
exports/sources/1003-pointing-at-moon-subt2-11-22-12-59-897-87fe6e0c-bb89-4cfe-8ec0-0d2ef1631b30.txt
exports/sources/1003-pointing-at-moon-subt2-12-22-14-42-087-f00399d6-af1c-494e-9014-ded72a45a0e4.txt
exports/sources/1003-pointing-at-moon-subt2-2-22-06-33-699-e6490f07-cbde-432f-a50d-c1a3b23f2e57.txt
exports/sources/1003-pointing-at-moon-subt2-3-22-06-59-997-ac9a2b62-76ed-46f5-a828-98eaf7b2a97e.txt
exports/sources/1003-pointing-at-moon-subt2-4-22-07-16-794-d7b852d5-afd3-4b59-ad5b-2d47b23c48f8.txt
exports/sources/1003-pointing-at-moon-subt2-5-22-07-20-794-2ffc5847-517d-4819-bb22-9a112678900f.txt
exports/sources/1003-pointing-at-moon-subt2-6-22-07-21-694-69e4bc11-0f2a-4b4f-ae94-878285c5aaf3.txt
exports/sources/1003-pointing-at-moon-subt2-7-22-08-57-183-6a38ab25-5922-4e99-80c1-5a8f817998a8.txt
exports/sources/1003-pointing-at-moon-subt2-8-22-09-25-280-a5412186-2bea-49b1-bbf5-f685cf78323c.txt
exports/sources/1003-pointing-at-moon-subt2-9-22-09-26-080-a44b5f13-6fdd-432b-a79b-53fa09d6099f.txt
exports/spectra/1003-pointing-at-moon-subt2-0-22-05-15-398-e0856eb2-6f97-4895-bb9a-615d24c65c13.csv
exports/spectra/1003-pointing-at-moon-subt2-10-22-10-16-917-a5d5f41f-f73d-4f1b-92a8-13e54ed0c8d0.csv
exports/spectra/1003-pointing-at-moon-subt2-11-22-12-59-897-87fe6e0c-bb89-4cfe-8ec0-0d2ef1631b30.csv
exports/spectra/1003-pointing-at-moon-subt2-12-22-14-42-087-f00399d6-af1c-494e-9014-ded72a45a0e4.csv
exports/spectra/1003-pointing-at-moon-subt2-2-22-06-33-699-e6490f07-cbde-432f-a50d-c1a3b23f2e57.csv
exports/spectra/1003-pointing-at-moon-subt2-3-22-06-59-997-ac9a2b62-76ed-46f5-a828-98eaf7b2a97e.csv
exports/spectra/1003-pointing-at-moon-subt2-4-22-07-16-794-d7b852d5-afd3-4b59-ad5b-2d47b23c48f8.csv
exports/spectra/1003-pointing-at-moon-subt2-5-22-07-20-794-2ffc5847-517d-4819-bb22-9a112678900f.csv
exports/spectra/1003-pointing-at-moon-subt2-6-22-07-21-694-69e4bc11-0f2a-4b4f-ae94-878285c5aaf3.csv
exports/spectra/1003-pointing-at-moon-subt2-7-22-08-57-183-6a38ab25-5922-4e99-80c1-5a8f817998a8.csv
exports/spectra/1003-pointing-at-moon-subt2-8-22-09-25-280-a5412186-2bea-49b1-bbf5-f685cf78323c.csv
exports/spectra/1003-pointing-at-moon-subt2-9-22-09-26-080-a44b5f13-6fdd-432b-a79b-53fa09d6099f.csv
goals.txt
packaging/msix-template.xml
packaging/spectra_app.spec
packaging/windows_build.md
patch.patch
pyproject.toml
pyrightconfig.json
reports/bugs_and_issues.md
reports/developer_notes.md
reports/feature_parity_checklist.md
reports/feature_parity_matrix.md
reports/m1_feature_parity_checklist.md
reports/m1_progress_report.md
reports/milestone1_progress.md
reports/naming_and_logs.md
reports/repo_audit.md
reports/risk_register.md
reports/roadmap.md
reports/runtime.log
requirements.txt
samples/IR data/IR - CO2/10.8 Test 1.csv
samples/IR data/IR - CO2/10.8 Test 2.csv
samples/IR data/IR - CO2/CO2 - 300 torr A.csv
samples/IR data/IR - CO2/CO2 - 300 torr.csv
samples/IR data/IR - CO2/CO2 - 500 torr A.csv
samples/IR data/IR - CO2/CO2 - 500 torr.csv
samples/IR data/IR - CO2/Run1 no co2.csv
samples/IR data/IR - CO2/bckgr.csv
samples/IR data/IR - CO2/bkgrd A.csv
samples/IR data/IR - CO2/bkgrd.csv
samples/IR data/IR - CO2/desktop.ini
samples/IR data/IR - CO2/open air A.csv
samples/IR data/IR - CO2/open air.csv
samples/IR data/IR - CO2/run2.csv
samples/IR data/IR - CO2/run4.csv
samples/IR data/IR H2O/.880torr~ w low vol h2o vapor.csv
samples/IR data/IR H2O/10.8 Test 1.csv
samples/IR data/IR H2O/10.8 Test 2.csv
samples/IR data/IR H2O/100 torr cold water.csv
samples/IR data/IR H2O/100 torr h2o 4-1k.csv
samples/IR data/IR H2O/7ish torr w h2o vapor.csv
samples/IR data/IR H2O/_880torr~ w low vol h2o vapor.csv
samples/IR data/IR H2O/bkgrd 10 16 VAC.csv
samples/IR data/IR H2O/cold water test 1.csv
samples/IR data/IR H2O/goodo vapor run i think.csv
samples/IR data/IR H2O/h2o all runs avg-composite.csv
samples/IR data/IR H2O/h2o run 1 10 27.csv
samples/IR data/IR H2O/h2o run 3 good i think 10 27.csv
samples/IR data/IR H2O/h2o v2 10 27.csv
samples/IR data/IR H2O/h2o vapor test 1.csv
samples/IR data/IR H2O/i froze h2o in the schlenk line oopsie.csv
samples/IR data/IR H2O/low vapor for the road.csv
samples/IR data/IR H2O/sketchy vapor test.csv
samples/IR data/IR H2O/vacc'd again 244 pm.csv
samples/IR data/Lab/.880torr~ w low vol h2o vapor - Copy.csv
samples/IR data/Lab/.880torr~ w low vol h2o vapor.sp
samples/IR data/Lab/.csv
samples/IR data/Lab/100 torr cold water.sp
samples/IR data/Lab/100 torr h2o 4-1k - Copy.csv
samples/IR data/Lab/100 torr h2o 4-1k.sp
samples/IR data/Lab/7ish torr w h2o vapor - Copy.csv
samples/IR data/Lab/7ish torr w h2o vapor.sp
samples/IR data/Lab/CO2 - 300 torr A.csv
samples/IR data/Lab/CO2 - 300 torr.csv
samples/IR data/Lab/CO2 - 300 torr.sp
samples/IR data/Lab/CO2 - 500 torr A.csv
samples/IR data/Lab/CO2 - 500 torr.csv
samples/IR data/Lab/CO2 - 500 torr.sp
samples/IR data/Lab/Methanol Blank.csv
samples/IR data/Lab/bckgr.csv
samples/IR data/Lab/bckgr.sp
samples/IR data/Lab/bkgrd 10 16 VAC.csv
samples/IR data/Lab/bkgrd 10 16 VAC.sp
samples/IR data/Lab/bkgrd A.csv
samples/IR data/Lab/bkgrd.csv
samples/IR data/Lab/bkgrd.sp
samples/IR data/Lab/co2 gas vessel.csv
samples/IR data/Lab/goodo vapor run i think - Copy.csv
samples/IR data/Lab/goodo vapor run i think.csv
samples/IR data/Lab/goodo vapor run i think.sp
samples/IR data/Lab/h2o run 1 10 27 - Copy.csv
samples/IR data/Lab/h2o run 3 good i think 10 27 - Copy.csv
samples/IR data/Lab/i froze h2o in the schlenk line oopsie.csv
samples/IR data/Lab/i froze h2o in the schlenk line oopsie.sp
samples/IR data/Lab/low vapor for the road.csv
samples/IR data/Lab/low vapor for the road.sp
samples/IR data/Lab/open air A.csv
samples/IR data/Lab/open air.csv
samples/IR data/Lab/open air.sp
samples/IR data/Lab/run2.csv
samples/IR data/Lab/run4.csv
samples/IR data/Lab/sketchy vapor test.csv
samples/IR data/Lab/sketchy vapor test.sp
samples/IR data/Lab/vacc'd again 244 pm.csv
samples/IR data/Lab/vacc'd again 244 pm.sp
samples/IR data/Lab/vacuumed cell.csv
samples/SOLAR SYSTEM/Mercury/UVVCDR/labinfo.txt
samples/SOLAR SYSTEM/Mercury/UVVCDR/ob2/uvvs/fuv/ufc_ob5_29_15094_155425_hdr.dat
samples/SOLAR SYSTEM/Mercury/UVVCDR/ob2/uvvs/fuv/ufc_ob5_29_15094_155425_hdr.lbl
samples/SOLAR SYSTEM/Mercury/UVVCDR/ob2/uvvs/fuv/ufc_ob5_29_15094_155425_sci.csv
samples/SOLAR SYSTEM/Mercury/UVVCDR/ob2/uvvs/fuv/ufc_ob5_29_15094_155425_sci.dat
samples/SOLAR SYSTEM/Mercury/UVVCDR/ob2/uvvs/fuv/ufc_ob5_29_15094_155425_sci.lbl
samples/SOLAR SYSTEM/Mercury/UVVCDR/ob2/uvvs/fuv/ufc_ob5_29_15094_181139_hdr.dat
samples/SOLAR SYSTEM/Mercury/UVVCDR/ob2/uvvs/fuv/ufc_ob5_29_15094_181139_hdr.lbl
samples/SOLAR SYSTEM/Mercury/UVVCDR/ob2/uvvs/fuv/ufc_ob5_29_15094_181139_sci.csv
samples/SOLAR SYSTEM/Mercury/UVVCDR/ob2/uvvs/fuv/ufc_ob5_29_15094_181139_sci.dat
samples/SOLAR SYSTEM/Mercury/UVVCDR/ob2/uvvs/fuv/ufc_ob5_29_15094_181139_sci.lbl
samples/SOLAR SYSTEM/Mercury/UVVCDR/ob2/uvvs/muv/umc_ob5_34_15094_004734_hdr.dat
samples/SOLAR SYSTEM/Mercury/UVVCDR/ob2/uvvs/muv/umc_ob5_34_15094_004734_hdr.lbl
samples/SOLAR SYSTEM/Mercury/UVVCDR/ob2/uvvs/muv/umc_ob5_34_15094_004734_sci.csv
samples/SOLAR SYSTEM/Mercury/UVVCDR/ob2/uvvs/muv/umc_ob5_34_15094_004734_sci.dat
samples/SOLAR SYSTEM/Mercury/UVVCDR/ob2/uvvs/muv/umc_ob5_34_15094_004734_sci.lbl
samples/SOLAR SYSTEM/Mercury/UVVCDR/ob2/uvvs/muv/umc_ob5_65_15094_211347_hdr.dat
samples/SOLAR SYSTEM/Mercury/UVVCDR/ob2/uvvs/muv/umc_ob5_65_15094_211347_hdr.lbl
samples/SOLAR SYSTEM/Mercury/UVVCDR/ob2/uvvs/muv/umc_ob5_65_15094_211347_sci.csv
samples/SOLAR SYSTEM/Mercury/UVVCDR/ob2/uvvs/muv/umc_ob5_65_15094_211347_sci.dat
samples/SOLAR SYSTEM/Mercury/UVVCDR/ob2/uvvs/muv/umc_ob5_65_15094_211347_sci.lbl
samples/SOLAR SYSTEM/Mercury/UVVCDR/ob2/uvvs/vis/uvc_ob5_29_15094_155425_hdr.dat
samples/SOLAR SYSTEM/Mercury/UVVCDR/ob2/uvvs/vis/uvc_ob5_29_15094_155425_hdr.lbl
samples/SOLAR SYSTEM/Mercury/UVVCDR/ob2/uvvs/vis/uvc_ob5_29_15094_155425_sci.csv
samples/SOLAR SYSTEM/Mercury/UVVCDR/ob2/uvvs/vis/uvc_ob5_29_15094_155425_sci.dat
samples/SOLAR SYSTEM/Mercury/UVVCDR/ob2/uvvs/vis/uvc_ob5_29_15094_155425_sci.lbl
samples/SOLAR SYSTEM/Mercury/UVVCDR/ob2/uvvs/vis/uvc_ob5_29_15094_181139_hdr.dat
samples/SOLAR SYSTEM/Mercury/UVVCDR/ob2/uvvs/vis/uvc_ob5_29_15094_181139_hdr.lbl
samples/SOLAR SYSTEM/Mercury/UVVCDR/ob2/uvvs/vis/uvc_ob5_29_15094_181139_sci.csv
samples/SOLAR SYSTEM/Mercury/UVVCDR/ob2/uvvs/vis/uvc_ob5_29_15094_181139_sci.dat
samples/SOLAR SYSTEM/Mercury/UVVCDR/ob2/uvvs/vis/uvc_ob5_29_15094_181139_sci.lbl
samples/SOLAR SYSTEM/Mercury/UVVCDR/uvvs_cdr_ddr_sis.pdf
samples/SOLAR SYSTEM/Mercury/UVVCDR/uvvshdrc.fmt
samples/SOLAR SYSTEM/Mercury/UVVCDR/uvvshdrd_sur.fmt
samples/SOLAR SYSTEM/Mercury/UVVCDR/uvvsscic.fmt
samples/SOLAR SYSTEM/Mercury/UVVCDR/uvvsscid.fmt
samples/SOLAR SYSTEM/Mercury/UVVCDR/uvvsscid_sur.fmt
samples/SOLAR SYSTEM/Mercury/UVVCDR/virsnc.fmt
samples/SOLAR SYSTEM/Mercury/UVVCDR/virsnd.fmt
samples/SOLAR SYSTEM/Mercury/UVVCDR/virsvc.fmt
samples/SOLAR SYSTEM/Mercury/UVVCDR/virsvd.fmt
samples/SOLAR SYSTEM/Mercury/UVVDDR/labinfo.txt
samples/SOLAR SYSTEM/Mercury/UVVDDR/ob3/uvvs_atmosphere/05/ud_05_ld_ca.dat
samples/SOLAR SYSTEM/Mercury/UVVDDR/ob3/uvvs_atmosphere/05/ud_05_ld_ca.lbl
samples/SOLAR SYSTEM/Mercury/UVVDDR/ob3/uvvs_atmosphere/05/ud_05_ld_na.dat
samples/SOLAR SYSTEM/Mercury/UVVDDR/ob3/uvvs_atmosphere/05/ud_05_ld_na.lbl
samples/SOLAR SYSTEM/Mercury/UVVDDR/ob3/uvvs_atmosphere/05/ud_05_ls_ca.dat
samples/SOLAR SYSTEM/Mercury/UVVDDR/ob3/uvvs_atmosphere/05/ud_05_ls_ca.lbl
samples/SOLAR SYSTEM/Mercury/UVVDDR/ob3/uvvs_atmosphere/05/ud_05_ls_na.dat
samples/SOLAR SYSTEM/Mercury/UVVDDR/ob3/uvvs_atmosphere/05/ud_05_ls_na.lbl
samples/SOLAR SYSTEM/Mercury/UVVDDR/ob3/uvvs_atmosphere/05/ud_05_ns_ca.dat
samples/SOLAR SYSTEM/Mercury/UVVDDR/ob3/uvvs_atmosphere/05/ud_05_ns_ca.lbl
samples/SOLAR SYSTEM/Mercury/UVVDDR/ob3/uvvs_atmosphere/05/ud_05_ns_mg.dat
samples/SOLAR SYSTEM/Mercury/UVVDDR/ob3/uvvs_atmosphere/05/ud_05_ns_mg.lbl
samples/SOLAR SYSTEM/Mercury/UVVDDR/ob3/uvvs_atmosphere/05/ud_05_ns_na.dat
samples/SOLAR SYSTEM/Mercury/UVVDDR/ob3/uvvs_atmosphere/05/ud_05_ns_na.lbl
samples/SOLAR SYSTEM/Mercury/UVVDDR/ob3/uvvs_surface/mascs20130213/umd_ob2_49_13044_005906_hdr.dat
samples/SOLAR SYSTEM/Mercury/UVVDDR/ob3/uvvs_surface/mascs20130213/umd_ob2_49_13044_005906_hdr.lbl
samples/SOLAR SYSTEM/Mercury/UVVDDR/ob3/uvvs_surface/mascs20130213/umd_ob2_49_13044_005906_sci.csv
samples/SOLAR SYSTEM/Mercury/UVVDDR/ob3/uvvs_surface/mascs20130213/umd_ob2_49_13044_005906_sci.dat
samples/SOLAR SYSTEM/Mercury/UVVDDR/ob3/uvvs_surface/mascs20130213/umd_ob2_49_13044_005906_sci.lbl
samples/SOLAR SYSTEM/Mercury/UVVDDR/ob3/uvvs_surface/mascs20130213/umd_ob2_49_13044_010912_hdr.dat
samples/SOLAR SYSTEM/Mercury/UVVDDR/ob3/uvvs_surface/mascs20130213/umd_ob2_49_13044_010912_hdr.lbl
samples/SOLAR SYSTEM/Mercury/UVVDDR/ob3/uvvs_surface/mascs20130213/umd_ob2_49_13044_010912_sci.csv
samples/SOLAR SYSTEM/Mercury/UVVDDR/ob3/uvvs_surface/mascs20130213/umd_ob2_49_13044_010912_sci.dat
samples/SOLAR SYSTEM/Mercury/UVVDDR/ob3/uvvs_surface/mascs20130213/umd_ob2_49_13044_010912_sci.lbl
samples/SOLAR SYSTEM/Mercury/UVVDDR/ob3/virs/mascs20120403/nir/virsnd_ob2_12094_055036.csv
samples/SOLAR SYSTEM/Mercury/UVVDDR/ob3/virs/mascs20120403/nir/virsnd_ob2_12094_055036.dat
samples/SOLAR SYSTEM/Mercury/UVVDDR/ob3/virs/mascs20120403/nir/virsnd_ob2_12094_055036.lbl
samples/SOLAR SYSTEM/Mercury/UVVDDR/ob3/virs/mascs20120403/nir/virsnd_ob2_12094_093428.dat
samples/SOLAR SYSTEM/Mercury/UVVDDR/ob3/virs/mascs20120403/nir/virsnd_ob2_12094_093428.lbl
samples/SOLAR SYSTEM/Mercury/UVVDDR/ob3/virs/mascs20120403/nir/virsnd_ob2_12094_172502.dat
samples/SOLAR SYSTEM/Mercury/UVVDDR/ob3/virs/mascs20120403/nir/virsnd_ob2_12094_172502.lbl
samples/SOLAR SYSTEM/Mercury/UVVDDR/uvvs_cdr_ddr_sis.pdf
samples/SOLAR SYSTEM/Mercury/UVVDDR/uvvshdrc.fmt
samples/SOLAR SYSTEM/Mercury/UVVDDR/uvvshdrd_sur.fmt
samples/SOLAR SYSTEM/Mercury/UVVDDR/uvvsscic.fmt
samples/SOLAR SYSTEM/Mercury/UVVDDR/uvvsscid.fmt
samples/SOLAR SYSTEM/Mercury/UVVDDR/uvvsscid_sur.fmt
samples/SOLAR SYSTEM/Mercury/UVVDDR/virsnc.fmt
samples/SOLAR SYSTEM/Mercury/UVVDDR/virsnd.fmt
samples/SOLAR SYSTEM/Mercury/UVVDDR/virsvc.fmt
samples/SOLAR SYSTEM/Mercury/UVVDDR/virsvd.fmt
samples/SOLAR SYSTEM/Mercury/UVVEDR/OB5/mascs20150401/hk/masc_hk_15091.lbl
samples/SOLAR SYSTEM/Mercury/UVVEDR/OB5/mascs20150401/hk/mascs_hk_15091.dat
samples/SOLAR SYSTEM/Mercury/UVVEDR/OB5/mascs20150401/uvvs/ufe_ob5_29_15091_121600.dat
samples/SOLAR SYSTEM/Mercury/UVVEDR/OB5/mascs20150401/uvvs/ufe_ob5_29_15091_121600.lbl
samples/SOLAR SYSTEM/Mercury/UVVEDR/OB5/mascs20150401/uvvs/ufe_ob5_29_15091_122737.dat
samples/SOLAR SYSTEM/Mercury/UVVEDR/OB5/mascs20150401/uvvs/ufe_ob5_29_15091_122737.lbl
samples/SOLAR SYSTEM/Mercury/UVVEDR/OB5/mascs20150401/uvvs/ufe_ob5_29_15091_123801.dat
samples/SOLAR SYSTEM/Mercury/UVVEDR/OB5/mascs20150401/uvvs/ufe_ob5_29_15091_123801.lbl
samples/SOLAR SYSTEM/Mercury/UVVEDR/OB5/mascs20150401/uvvs/ufe_ob5_29_15091_152106.dat
samples/SOLAR SYSTEM/Mercury/UVVEDR/OB5/mascs20150401/uvvs/ufe_ob5_29_15091_152106.lbl
samples/SOLAR SYSTEM/Mercury/UVVEDR/OB5/mascs20150401/virs/virsne_ob5_15091_031741.dat
samples/SOLAR SYSTEM/Mercury/UVVEDR/OB5/mascs20150401/virs/virsne_ob5_15091_031741.lbl
samples/SOLAR SYSTEM/Mercury/UVVEDR/OB5/mascs20150401/virs/virsne_ob5_15091_051457.dat
samples/SOLAR SYSTEM/Mercury/UVVEDR/OB5/mascs20150401/virs/virsne_ob5_15091_051457.lbl
samples/SOLAR SYSTEM/Mercury/UVVEDR/OB5/mascs20150401/virs/virsne_ob5_15091_051606.dat
samples/SOLAR SYSTEM/Mercury/UVVEDR/OB5/mascs20150401/virs/virsne_ob5_15091_051606.lbl
samples/SOLAR SYSTEM/Mercury/UVVEDR/labelinfo.txt
samples/SOLAR SYSTEM/Mercury/UVVEDR/mascs.hk.fmt
samples/SOLAR SYSTEM/Mercury/UVVEDR/uvvs.fmt
samples/SOLAR SYSTEM/Mercury/UVVEDR/uvvsedrsis.pdf
samples/SOLAR SYSTEM/Mercury/UVVEDR/virs.fmt
samples/SOLAR SYSTEM/Mercury/uvvsedrsis.pdf
samples/SUN AND MOON/Good Sun reading questionable.txt
samples/SUN AND MOON/MOON/cleaner moon 2 files-composite.csv
samples/SUN AND MOON/MOON/mildly cloudy_Subt2__10__14-22-21-006.txt
samples/SUN AND MOON/MOON/mildly cloudy_Subt2__14__14-24-24-077.txt
samples/SUN AND MOON/MOON/mildly cloudy_Subt2__3__14-15-27-186.txt
samples/SUN AND MOON/MOON/mildly cloudy_Subt2__8__14-22-20-956.txt
samples/SUN AND MOON/MOON/moon_manifest-composite.csv
samples/SUN AND MOON/Sun outside no cover_USB4F034991__0__09-48-55-005.txt
samples/SUN AND MOON/Sun outside no cover_USB4F034991__1__09-49-01-484.txt
samples/SUN AND MOON/cloudy/3_57 pm cloudy_Subt2__2__15-59-37-611.txt
samples/SUN AND MOON/cloudy/3_57pm_merged.csv
samples/SUN AND MOON/cloudy/3_57pm_merged.json
samples/SUN AND MOON/cloudy/3_57pm_merged.png
samples/SUN AND MOON/cloudy/451_merged-plot.csv
samples/SUN AND MOON/cloudy/451_merged.csv
samples/SUN AND MOON/cloudy/451_merged.json
samples/SUN AND MOON/cloudy/451_merged.png
samples/SUN AND MOON/cloudy/4_51 _Subt2__0__16-51-23-322.txt
samples/SUN AND MOON/cloudy/4_51 _Subt2__1__16-51-23-367.txt
samples/SUN AND MOON/cloudy/4_51 _Subt2__2__16-53-38-520.txt
samples/SUN AND MOON/cloudy/644_merged-plot.csv
samples/SUN AND MOON/cloudy/644_merged.csv
samples/SUN AND MOON/cloudy/644_merged.json
samples/SUN AND MOON/cloudy/644_merged.png
samples/SUN AND MOON/cloudy/6_44 2.txt
samples/SUN AND MOON/cloudy/6_44 3.txt
samples/SUN AND MOON/cloudy/6_44.txt
samples/SUN AND MOON/cloudy/log.txt
samples/SUN AND MOON/cloudy/spectra/3-57-merged-1ae7e46c-6f99-47d7-b354-c938c5eb26bf.csv
samples/SUN AND MOON/cloudy/spectra/4-51pm-e3ae98b3-6185-484b-9998-a54a341ceea8.csv
samples/SUN AND MOON/cloudy/spectra/6-44-pm-28c420a1-3f39-4b39-9883-81d1ecb3baa2.csv
samples/SUN AND MOON/okay sun file.csv
samples/exoplanets/table_HAT-P-18-b-Fournier-Tondreau-et-al.-2024.csv
samples/exoplanets/table_Luhman-16-b-Biller-et-al.-2024.csv
samples/exoplanets/table_TRAPPIST-1-b-Rathcke-et-al.-2025.csv
samples/exoplanets/table_WASP-17-b-Louie-et-al.-2025.csv
samples/exoplanets/table_WASP-178-b-Lothringer-et-al.-2022.csv
samples/exoplanets/table_WASP-39-b-Rustamkulov-et-al.-2023.csv
samples/exoplanets/table_WASP-96-b-Radica-et-al.-2023.csv
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/C-J4.5IIIa_C26j6_HD70138.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/C-J5-C25-j4_HD57160.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/C-N4.5C24.5_HD92055.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/C-N4.5C25.5MS3_HD76221.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/C-N4C23.5_HD44984.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/C-N5C26-_HD48664.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/C-R2+IIIa_C22.5_HD76846.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/C7,6e(N4)_HD31996.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/F0III-IVn_HD13174.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/F0IIIa_HD89025.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/F0II_HD6130.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/F0II_HD6130_ext.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/F0IV_HD27397.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/F0Ia_HD7927.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/F0Ia_HD7927_ext.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/F0Ib-II_HD135153.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/F0Ib-II_HD135153_ext.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/F0V(n)_HD108519.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/F1II_HD173638.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/F1II_HD173638_ext.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/F1V_HD213135.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/F2-F5Ib_BD+38_2803.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/F2III-IV_HD40535.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/F2Ib_HD182835.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/F2Ib_HD182835_ext.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/F2V_HD113139.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/F3V_HD26015.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/F4III_HD21770.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/F4V_HD16232.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/F4V_HD87822.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/F5.5III-IV_HD75555.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/F5II-III_HD186155.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/F5III_HD17918.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/F5Ib-G1Ib_HD213306.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/F5Ib-G1Ib_HD213306_ext.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/F5V_HD218804.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/F5V_HD27524.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/F6III-IV_HD160365.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/F6IV_HD11443.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/F6V_HD215648.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/F7II-_HD201078.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/F7III_HD124850.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/F7V_HD126660.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/F8.5IV-V_HD102870.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/F8III_HD220657.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/F8IV_HD111844.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/F8Ia_HD190323.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/F8Ia_HD190323_ext.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/F8Ib_HD51956.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/F8Ib_HD51956_ext.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/F8V_HD219623.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/F8V_HD27383.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/F9.5V_HD114710.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/F9IIIa_HD6903.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/F9IIIa_HD6903_ext.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/F9V_HD176051.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/F9Vmetalweak_HD165908.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/G0Ib-II_HD185018.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/G0Ib-II_HD185018_ext.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/G0V_HD109358.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/G1-VFe-0.5_HD95128.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/G1.5V_HD20619.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/G1II-III_Fe-1CH0.5_HD216219.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/G1III_CH-1__HD21018.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/G1III_CH-1__HD21018_ext.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/G1Ib_HD74395.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/G1V_HD10307.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/G2II-III_HD219477.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/G2IV_HD126868.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/G2Ib-II_HD3421.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/G2Ib_HD39949.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/G2Ib_HD39949_ext.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/G2Ib_HD42454.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/G2Ib_HD42454_ext.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/G2V_HD76151.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/G3IIIbFe-1_HD88639.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/G3II_HD176123.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/G3II_HD176123_ext.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/G3Ib-IIWkH&Kcomp__HD192713.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/G3Ib-IIWkH&Kcomp__HD192713_ext.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/G3Va_HD10697.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/G4III-IIIb_HD94481.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/G4III_HD108477.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/G4Ia_HD6474.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/G4Ia_HD6474_ext.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/G4O-Ia_HD179821.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/G4O-Ia_HD179821_ext.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/G4V_HD214850.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/G5IIIa_HD193896.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/G5Ib_HD190113.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/G5Ib_HD190113_ext.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/G5V_HD165185.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/G5_III_CN-3CH-2H_delta-1_HD18474.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/G6.5V_HD115617.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/G6III_HD27277.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/G6IIb_HD58367.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/G6Ib-IIaCa1Ba0.5_HD202314.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/G6Ib-IIaCa1Ba0.5_HD202314_ext.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/G6IbH_delta1_HD161664.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/G6IbH_delta1_HD161664_ext.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/G7.5IIIa_HD16139.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/G7.5IIIa_HD16139_ext.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/G7IIIa_HD182694.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/G7II_HD25877.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/G7II_HD25877_ext.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/G7IV_HD114946.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/G7IV_HD20618.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/G7Ia_HD333385.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/G7Ia_HD333385_ext.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/G8IIIBa1CN-1CH1_HD104979.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/G8IIIFe-1_HD135722.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/G8Ib_HD208606.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/G8Ib_HD208606_ext.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/G8V_HD101501.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/G8V_HD75732.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/G8V_HD75732_ext.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/G8_III_Fe-5_HD122563.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/G9IICN1H_delta1_HD170820.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/G9IICN1H_delta1_HD170820_ext.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/G9III_HD222093.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/K0.5IIICN1_HD9852.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/K0.5IIICN1_HD9852_ext.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/K0.5IIb_HD164349.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/K0.5IIb_HD164349_ext.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/K0III_HD100006.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/K0II_HD179870.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/K0II_HD179870_ext.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/K0Ia_HD165782.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/K0Ia_HD165782_ext.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/K0Ib_HD44391.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/K0Ib_HD44391_ext.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/K0V_HD145675.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/K1-IIIFe-0.5_HD36134.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/K1-IIIbCN1.5Ca1_HD91810.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/K1.5IIIFe-0.5_HD124897_lines.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/K1.5IIIFe-0.5_HD124897_lines_ext.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/K1.5IIIFe-0.5_HD124897_shape.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/K1.5IIIFe-0.5_HD124897_shape_ext.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/K1III_HD25975.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/K1IV_HD165438.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/K1IVa_HD142091.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/K1Ia-Iab_HD63302.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/K1Ia-Iab_HD63302_ext.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/K1V_HD10476.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/K2.5II_HD23082.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/K2.5II_HD23082_ext.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/K2IIIFe-1_HD2901.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/K2III_HD132935.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/K2III_HD132935_ext.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/K2III_HD137759.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/K2O-Ia_HD212466.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/K2O-Ia_HD212466_ext.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/K2V_HD3765.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/K3+IIIFe-0.5_HD99998.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/K3+IIIFe-0.5_HD99998_ext.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/K3.5IIIbCN0.5CH0.5_HD114960.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/K3II-III_HD16068.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/K3II-III_HD16068_ext.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/K3IIIFe1_HD35620.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/K3IIIFe1_HD35620_ext.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/K3III_HD178208.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/K3III_HD178208_ext.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/K3III_HD221246.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/K3III_HD221246_ext.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/K3Iab-Ib_HD187238.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/K3Iab-Ib_HD187238_ext.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/K3V_HD219134.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/K4-III_HD207991.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/K4-III_HD207991_ext.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/K4Ib-II_HD201065.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/K4Ib-II_HD201065_ext.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/K4Ib_HD185622A.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/K4Ib_HD185622A_ext.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/K4V_HD45977.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/K4V_HD45977_ext.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/K5.5III_HD120477.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/K5III_HD181596.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/K5Ib_HD216946.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/K5Ib_HD216946_ext.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/K5V_HD36003.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/K6IIIa_HD3346.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/K7III_HD194193.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/K7IIa_HD181475.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/K7IIa_HD181475_ext.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/K7V_HD201092.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/K7V_HD237903.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/L0.5_2MASSJ0746+2000AB.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/L1_2MASSJ0208+2542.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/L1_2MASSJ1439+1929.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/L2_Kelu-1AB.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/L3.5_2MASSJ0036+1821.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/L3_2MASSJ1146+2230AB.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/L3_2MASSJ1506+1321.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/L4.5_2MASSJ2224-0158.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/L5_2MASSJ1507-1627.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/L5_SDSSJ0539-0059.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/L6(NIR)_2MASSJ1515+4847.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/L7.5_2MASSJ0825+2115.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/L8_DENISJ0255-4700.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/M0.5Ib_HD236697.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/M0.5Ib_HD236697_ext.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/M0.5V_HD209290.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/M0IIIb_HD213893.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/M0V_HD19305.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/M1+III_HD204724.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/M1-Iab-Ib_HD14404.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/M1-Iab-Ib_HD14404_ext.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/M1-M2Ia-Iab_HD39801.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/M1-M2Ia-Iab_HD39801_ext.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/M1.5Iab-Ib_HD35601.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/M1.5Iab-Ib_HD35601_ext.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/M1.5Ib_BD+60_265.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/M1.5Ib_BD+60_265_ext.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/M1.5V_HD36395.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/M10+III_IRAS14086-0703.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/M1Ia_HD339034.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/M1Ia_HD339034_ext.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/M1V_HD42581.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/M2-Ia_HD206936.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/M2-Ia_HD206936_ext.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/M2.5IIIBa0.5_HD219734.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/M2.5V_Gl381.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/M2.5V_Gl581.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/M2III_HD120052.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/M2II_HD23475.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/M2II_HD23475_ext.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/M2Ib_HD10465.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/M2Ib_HD10465_ext.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/M2V_Gl806.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/M2V_HD95735.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/M3-M4Iab_HD14469.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/M3-M4Iab_HD14469_ext.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/M3.5IIICa-0.5_HD28487.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/M3.5IIICa-0.5_HD28487_ext.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/M3.5IabFe-1var__HD14488.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/M3.5IabFe-1var__HD14488_ext.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/M3.5V_Gl273.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/M3III_HD39045.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/M3III_HD39045_ext.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/M3IIb_HD40239.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/M3Iab-Ia_CD-31_49.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/M3Iab-Ia_CD-31_49_ext.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/M3V_Gl388.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/M3toM4Ia-Iab_RW_Cyg.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/M3toM4Ia-Iab_RW_Cyg_ext.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/M4+III_HD214665.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/M4+IIIa_HD19058.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/M4-III_HD27598.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/M4.5IIIa_HD204585.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/M4.5V_Gl268AB.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/M4III_HD4408.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/M4V_Gl213.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/M4V_Gl299.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/M4V_Gl299_ext.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/M5.5III__HD94705.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/M5III_HD175865.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/M5Ib-II_HD156014.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/M5V_Gl51.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/M5V_Gl866ABC.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/M5V_Gl866ABC_ext.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/M5e-M9eIII_HD14386.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/M6-III__HD18191.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/M6.5StoM7SIII__HD142143.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/M6.5V_GJ1111.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/M6III_HD196610.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/M6V_Gl406.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/M6e-M9eIII_HD69243.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/M7-8III_BRIB2339-0447.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/M7-III__HD108849.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/M7-III__HD207076.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/M7-M7.5I_MY_Cep.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/M7V_Gl644C.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/M8-9III_IRAS14303-1042.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/M8-9III_IRAS14436-0703.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/M8-9III_IRAS21284-0747.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/M8III_IRAS01037+1219.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/M8V_Gl752B.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/M8V_LP412-31.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/M9.5V_BRIB0021-0214.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/M9III_BRIB1219-1336.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/M9III_IRAS15060+0947.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/M9V_DENIS-PJ1048-3956.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/M9V_LHS2065.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/M9V_LHS2924.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/M9V_LP944-20.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/S2.5Zr2_BD+44_2267.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/S4.5Zr2Ti4_HD64332.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/S5-S6Zr3to4Ti0_HD62164.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/SC5.5Zr0.5_HD44544.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/T2_SDSSJ1254-0122.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/T4.5_2MASSJ0559-1404.fits
samples/fits data/SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager/kA9hF2mF2(IV)_HD164136.fits
samples/fits data/jupiter__9408090029N_vo.fits
samples/fits data/tess2019112060037-s0011-0000000388857263-0143-s_lc.fits
samples/fits data/tess2019140104343-s0012-0000000388857263-0144-s_lc.fits
samples/fits data/tess2021118034608-s0038-0000000388857263-0209-a_fast-lc.fits
samples/fits data/tess2021118034608-s0038-0000000388857263-0209-s_lc.fits
samples/lamp data/Air_Lamp.csv
samples/lamp data/CO2_Lamp.csv
samples/lamp data/H2O AIR AND CO2 LAMP MERGED.csv
samples/lamp data/H2O_Lamp.csv
samples/lamp data/Helium_Lamp.csv
samples/lamp data/Hydrogen_Lamp.csv
samples/lamp data/Iodine_Lamp.csv
samples/lamp data/Krypton_Lamp.csv
samples/lamp data/Mercury_Lamp.csv
samples/lamp data/Neon_Lamp.csv
samples/lamp data/Star_Lamp.csv
samples/lamp data/Xenon_Lamp.csv
samples/other file types/Good Sun reading.txt
samples/other file types/okay sun file.csv
samples/sample_manifest.json
samples/sample_spectrum.csv
samples/sample_transmittance.csv
samples/solar_system/README.md
samples/solar_system/earth/earth_ir.csv
samples/solar_system/earth/earth_visible.csv
samples/solar_system/jupiter/jupiter_ir.csv
samples/solar_system/jupiter/jupiter_uv.csv
samples/solar_system/jupiter/jupiter_visible.csv
samples/solar_system/jupiter/plnt_Jupiter.fits
samples/solar_system/manifest.json
samples/solar_system/mars/mars_ir.csv
samples/solar_system/mars/mars_visible.csv
samples/solar_system/mercury/mercury_ir.csv
samples/solar_system/mercury/mercury_uv.csv
samples/solar_system/mercury/mercury_visible.csv
samples/solar_system/neptune/neptune_ir.csv
samples/solar_system/neptune/neptune_uv.csv
samples/solar_system/neptune/neptune_visible.csv
samples/solar_system/neptune/plnt_Neptune.fits
samples/solar_system/plnt_Jupiter.fits
samples/solar_system/plnt_Neptune.fits
samples/solar_system/plnt_Saturn.fits
samples/solar_system/plnt_Uranus.fits
samples/solar_system/pluto/pluto_ir.csv
samples/solar_system/pluto/pluto_uv.csv
samples/solar_system/pluto/pluto_visible.csv
samples/solar_system/saturn/plnt_Saturn.fits
samples/solar_system/saturn/saturn_ir.csv
samples/solar_system/saturn/saturn_visible.csv
samples/solar_system/uranus/plnt_Uranus.fits
samples/solar_system/uranus/uranus_ir.csv
samples/solar_system/uranus/uranus_uv.csv
samples/solar_system/uranus/uranus_visible.csv
samples/solar_system/venus/venus_ir.csv
samples/solar_system/venus/venus_visible.csv
sitecustomize.py
specs/architecture.md
specs/packaging.md
specs/plugin_dev_guide.md
specs/provenance_schema.md
specs/system_design.md
specs/testing.md
specs/ui_contract.md
specs/units_and_conversions.md
test_exoplanet_manual.py
test_spex_manual.py
tests/conftest.py
tests/data/mini.csv
tests/data/mini.dx.jcamp
tests/fixtures/export_example/manifest.json
tests/integration/__init__.py
tests/integration/test_remote_search_targets.py
tests/pyproject.toml
tests/test_cache_index.py
tests/test_csv_importer.py
tests/test_dataset_filter.py
tests/test_dataset_removal.py
tests/test_documentation_ui.py
tests/test_export_visibility.py
tests/test_ingest.py
tests/test_ingest_jcamp.py
tests/test_ingest_overlay_math.py
tests/test_knowledge_log_service.py
tests/test_library_view.py
tests/test_line_shapes.py
tests/test_main_import.py
tests/test_math.py
tests/test_merge_average.py
tests/test_normalization.py
tests/test_overlay.py
tests/test_overlay_service.py
tests/test_plot_perf_stub.py
tests/test_provenance.py
tests/test_provenance_manifest.py
tests/test_qaction_import.py
tests/test_reference_library.py
tests/test_reference_ui.py
tests/test_remote_data_dialog.py
tests/test_remote_data_service.py
tests/test_roundtrip_stub.py
tests/test_smoke_workflow.py
tests/test_ui_contract_stub.py
tests/test_units.py
tests/test_units_roundtrip.py
tests/test_units_service.py
tools/cleanup_solar_system_samples.py
tools/fetch_solar_system_datasets.py
tools/mascs_quality_filter.py
tools/parse_messenger_mascs.py
tools/pds_downloader_native.py
tools/pds_mascs_bulk_download.py
tools/pds_wget_bulk.py
tools/pipeline_master.py
tools/reference_build/__init__.py
tools/reference_build/build_hydrogen_asd.py
tools/reference_build/build_ir_bands.py
tools/reference_build/build_jwst_quicklook.py
tools/reference_build/jwst_targets_template.json
tools/validate_manifest.py
ui_screenshot.png
ui_screenshot_datasets.png
```

