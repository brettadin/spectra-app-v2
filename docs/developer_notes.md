# Developer Notes – Service Extension Points

## Documentation map
- `AGENTS.md` – Operating manual; review before editing code or docs.
- `docs/history/MASTER PROMPT.md` & `docs/history/RUNNER_PROMPT.md` – Coordinator
  mandate and execution loop (timestamps in America/New_York, ISO-8601).
- `docs/brains/README.md` + latest entries under `docs/brains/` – Architectural
  rationale and follow-up tasks.
- `docs/link_collection.md` – Curated spectroscopy datasets, standards, and
  instrument handbooks.
- `docs/user/*.md` – User guides (importing, remote data, reference overlays,
  plot tools, units). Keep behaviour changes in sync.
- `docs/dev/reference_build.md` – Scripts/manifests for regenerating bundled
  reference assets.
- `docs/history/PATCH_NOTES.md` & `docs/history/KNOWLEDGE_LOG.md` – Chronological
  change log and distilled insights; update with real timestamps alongside code.
- `docs/reviews/workplan.md` – Active batch tracker.
- `docs/reviews/workplan_backlog.md` – Scheduled backlog items awaiting capacity.

## Importers
- Implement `SupportsImport` protocol (`app/services/importers/base.py`) and
  register via `DataIngestService.register_importer`. Each importer should return
  `ImporterResult` with raw arrays, units, metadata, and optional `source_path`.
- Keep parsing non-destructive: do not mutate arrays; let
  `UnitsService.to_canonical` normalise units.

## Units & Conversions
- `UnitsService` maintains the nm / base-10 absorbance baseline. Add new units by
  updating `_normalise_x_unit`, `_to_canonical_wavelength`, and
  `_from_canonical_wavelength`, plus corresponding intensity helpers.
- When adding complex flux types (e.g. absorption coefficient), capture required
  parameters (path length, mole fraction) in metadata before conversion.

## Overlay Engine
- `OverlayService` stores canonical `Spectrum` objects and returns view
  dictionaries for UI consumption. Additional derived overlays (e.g. normalised
  traces) can wrap `Spectrum.view` to compute temporary arrays without modifying
  stored spectra.

## Math Operations
- `MathService` currently supports subtract and ratio on aligned grids. Extend
  with interpolation by introducing a resampling utility before invoking math
  operations. Ensure epsilon rules are respected and add metadata about masked
  points or suppressed results.

## Provenance
- `ProvenanceService.create_manifest` accepts iterable spectra and optional
  transform/citation lists. New services should append transform descriptors
  (name, parameters, timestamp) so they appear in exports. When adding ML
  features, include `ml_predictions` block per the schema in
  `specs/provenance_schema.json`.

## UI Shell
- `app/main.py` composes the services. Widgets can subscribe to overlay updates
  by calling `refresh_overlay()` after making service changes. When adding new
  tabs, reuse `OverlayService` views and update selectors to keep keyboard
  navigation consistent.

## Cache & Library
- `LocalStore` persists every ingest; the Library dock (tabified with Datasets)
  queries it via `LocalStore.list_entries()` so operators can reload cached
  spectra. When you extend ingest logic, refresh the Library view and avoid
  logging raw file paths in the knowledge log—keep that file for high-level
  insights.
- Remote downloads now branch: HTTP requests still use `requests`, while MAST
  records go through `astroquery.mast.Observations.download_file`. Update tests in
  `tests/test_remote_data_service.py` if you add new providers.
- The MAST adapter injects `dataproduct_type="spectrum"`, `intentType="SCIENCE"`,
  and `calib_level=[2, 3]` and prunes non-spectroscopic rows to keep the results
  focused on slit/grism/IFS products that align with laboratory references. Only
  override these defaults when a workflow explicitly requires imaging products
  and document the change in the workplan/user guide.
- Trace colouring can be toggled between the high-contrast palette and a uniform
  colour via the Style tab combo box; respect the `_use_uniform_palette`
  attribute when adding new plot interactions.

## Packaging
- Update `packaging/spectra_app.spec` when adding new data assets. Keep
  `requirements.txt` aligned with runtime dependencies to ensure PyInstaller
  bundles the correct versions.
