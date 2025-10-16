# Project Roadmap and Milestones

This roadmap replaces the previous reboot-by-week schedule with a backlog-oriented plan that maps feature delivery, data regeneration, and documentation tasks into cohesive workstreams. Each section tracks dependencies across code, data, and docs so the tactical backlog remains aligned with the strategic vision recorded in the workplan reviews.

## Importer Heuristics and Data Integrity

**Goal:** Hardening CSV, TXT, and FITS ingestion paths so wavelength/intensity axes are inferred correctly across noisy QA feeds and historical archives.

**Key backlog items**

- Capture the QA-provided background spectra that still swap axes and fold the findings into `CsvImporter` heuristics, fixtures, and cache coverage.
- Integrate IR functional group heuristics into importer header parsing to automate axis validation and prevent regressions.
- Expand regression coverage for header-driven swaps and document the rationale in importer metadata for future audits.

**Dependencies and documentation**

- Update `docs/user/reference_data.md` with a multi-file ingest overlay walkthrough so QA operators can validate importer behaviour end-to-end.
- Backfill `docs/history/KNOWLEDGE_LOG.md` to note the importer/overlay fixes, ensuring traceability for release reviews.
- Keep the importer regression suite runnable in CI once the Qt-dependent tests are stabilised (see QA section).

**Acceptance signals**

- Messy QA datasets load without axis inversions; automated heuristics capture unit hints and header overrides.
- Tests covering heuristic extensions run green locally and in CI, including fixtures that reproduce the prior regressions.
- Documentation walkthroughs reference the latest importer behaviour and link back to provenance notes for review teams.

## Reference Data Regeneration and Provenance

**Goal:** Maintain trusted reference overlays (NIST hydrogen lines, IR functional groups, JWST quick-look spectra) with reproducible regeneration scripts and clear provenance.

**Key backlog items**

- Regenerate bundled reference datasets using the reproducible build scripts, capturing generator versions and retrieval timestamps.
- Stage new provenance metadata in the inspector UI, ensuring reference overlays expose source citations and regeneration notes.
- Align documentation updates with asset refreshes so spectroscopy primers and reference guides explain the regeneration workflow.

**Dependencies and documentation**

- Propagate provenance metadata updates through `docs/user/reference_data.md` and related spectroscopy documentation.
- Coordinate with the Knowledge Log backfill so reference data updates are recorded alongside importer improvements.
- Ensure the Reference tab overlays continue to render through automated smoke tests before promoting regenerated assets.

**Acceptance signals**

- Regenerated reference JSON assets pass validation and can be overlaid both in the Reference tab preview and the main plot workspace.
- Provenance metadata is surfaced in-app and cross-linked within user documentation and release notes.
- Automated tests (including smoke workflows) cover reference overlay rendering using the refreshed assets.

## Physics Models and Analysis Enhancements

**Goal:** Introduce physically-motivated models into the overlay service to support spectroscopy workflows beyond static references.

**Key backlog items**

- Wire Doppler, pressure, and Stark broadening models into the overlay service using existing parameter scaffolding.
- Provide UI controls and presets so users can compare broadened line profiles against observed spectra.
- Extend regression coverage to validate parameter inputs and output consistency for the new models.

**Dependencies and documentation**

- Update analytical documentation (spectroscopy primer, analysis guides) to describe the new broadening options and expected usage patterns.
- Coordinate with importer enhancements so broadened overlays can draw on correctly normalised datasets.
- Capture parameter defaults and equations in developer docs to support future extension (e.g., turbulence or rotation profiles).

**Acceptance signals**

- Users can configure and overlay broadened line models alongside reference and observed data.
- Automated tests confirm model outputs for canonical parameter sets and protect against regressions.
- Documentation includes examples showing how broadened models interact with importer-normalised spectra.

## QA Automation and Documentation Alignment

**Goal:** Keep strategic and tactical plans in lockstep by eliminating skipped UI tests and synchronising documentation milestones.

**Key backlog items**

- Configure CI (or a documented headless recipe) to run Qt-dependent Inspector/Reference tests without skips, validating overlays and dock persistence end-to-end.
- Expand the user documentation set (reference data guide, importer walkthroughs) to reflect recent overlay and toolbar behaviour.
- Continue capturing QA findings within the Knowledge Log to maintain traceability between backlog tasks and release decisions.

**Dependencies and documentation**

- Coordinate with importer and reference data workstreams so CI recipes include regenerated fixtures and assets.
- Ensure documentation updates are mirrored in help menu links and in-app references once published.
- Track QA runs within the workplan reviews to provide historical evidence for sign-off.

**Acceptance signals**

- CI pipelines execute Qt-dependent tests successfully, providing confidence in Inspector and overlay behaviour.
- Documentation milestones from the workplan are completed, reviewed, and linked from the application help surfaces.
- QA logs remain up to date, showing alignment between backlog execution and release governance.

## Future Horizons

Beyond the active backlog, several strategic initiatives remain on the long-term radar:

- Replace digitised JWST tables with calibrated FITS ingestion and provenance links once the pipeline module is production-ready.
- Broaden the spectral line catalogue beyond hydrogen (e.g., He I, O III, Fe II) with citations and regression coverage.
- Incorporate additional importer safeguards (e.g., for netCDF/HDF5 archives) and expand machine-learning overlays for exoplanet diagnostics as resources allow.

These initiatives will be revisited as the current backlog stabilises and supporting infrastructure (tests, documentation, data pipelines) matures.
