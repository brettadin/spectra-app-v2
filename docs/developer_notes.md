# Developer Notes – Service Extension Points

## Documentation map
- `AGENTS.md` – Top-level operating manual; review before editing code or docs.
- `docs/link_collection.md` – Curated spectroscopy datasets, standards, and
  instrument handbooks. Start here when sourcing new material.
- `docs/user/*.md` – User guides (importing, remote data, reference overlays,
  plot tools). Keep behaviour changes in sync.
- `docs/dev/reference_build.md` – Scripts and manifests for regenerating the
  bundled reference assets.
- `docs/history/PATCH_NOTES.md` & `docs/history/KNOWLEDGE_LOG.md` – Chronological
  change log and distilled insights; update alongside code.
- `docs/reviews/workplan.md` + `workplan_backlog.md` – Tactical batch tracker for features/tasks. Mark progress here.
- `docs/dev/worklog/YYYY-MM-DD.md` – Daily narrative logs (what/why/how for each session). See `docs/dev/worklog/README.md`.

## Importers
- Implement `SupportsImport` protocol (`app/services/importers/base.py`) and register via `DataIngestService.register_importer`. Each importer should return `ImporterResult` with raw arrays, units, metadata, and optional `source_path`.
- Keep parsing non-destructive: do not mutate arrays; let `UnitsService.to_canonical` normalise units.

## Units & Conversions
- `UnitsService` maintains the nm / base-10 absorbance baseline. Add new units by updating `_normalise_x_unit`, `_to_canonical_wavelength`, and `_from_canonical_wavelength`, plus corresponding intensity helpers.
- When adding complex flux types (e.g. absorption coefficient), capture required parameters (path length, mole fraction) in metadata before conversion.

## Overlay Engine
- `OverlayService` stores canonical `Spectrum` objects and returns view dictionaries for UI consumption. Additional derived overlays (e.g. normalised traces) can wrap `Spectrum.view` to compute temporary arrays without modifying stored spectra.

## Math Operations
- `MathService` currently supports subtract and ratio on aligned grids. Extend with interpolation by introducing a resampling utility before invoking math operations. Ensure epsilon rules are respected and add metadata about masked points or suppressed results.

## Provenance
- `ProvenanceService.create_manifest` accepts iterable spectra and optional transform/citation lists. New services should append transform descriptors (name, parameters, timestamp) so they appear in exports. When adding ML features, include `ml_predictions` block per the schema in `specs/provenance_schema.md`.

## UI Shell
- `app/main.py` composes the services. Widgets can subscribe to overlay updates by calling `refresh_overlay()` after making service changes. When adding new tabs, reuse `OverlayService` views and update selectors to keep keyboard navigation consistent.

## Cache & Library
- `LocalStore` persists every ingest; the Library tab inside the Data dock
   queries it via `LocalStore.list_entries()` so operators can reload cached
  spectra. When you extend ingest logic, refresh the Library view and avoid
  logging raw file paths in the knowledge log—keep that file for high-level
  insights.
- Remote downloads now branch: HTTP requests still use `requests`, while MAST
  records go through `astroquery.mast.Observations.download_file`. Update tests
  in `tests/test_remote_data_service.py` if you add new providers.
- The MAST adapter injects `dataproduct_type="spectrum"`, `intentType="SCIENCE"`,
  and `calib_level=[2, 3]` and prunes non-spectroscopic rows to keep the results
  focused on slit/grism/IFS products that align with laboratory references. Only
  override these defaults when a workflow explicitly requires imaging products
  and document the change in the workplan/user guide.
- Curated targets for quick-picks and host-star scaffolding live in
  `RemoteDataService._CURATED_TARGETS`. Each entry now carries a `category`
  (`"solar_system"`, `"host_star"`, `"exoplanet"`, etc.), canonical `names`, and
  citation metadata. Use `RemoteDataService.curated_targets()` to retrieve
  filtered copies in the UI. When adding moons or additional systems, extend the
  curated list, keep queries short (canonical name only), and update the quick
  pick tests in `tests/test_remote_data_dialog.py` plus the integration suite
  under `tests/integration/`.
- The Solar System quick-pick button in `RemoteDataDialog` reads from the
  curated targets. When extending the list, surface the new labels in the user
  guide and ensure `RemoteDataDialog._refresh_quick_pick_state` remains
  dependency-aware so the menu disables cleanly when ExoSystems support is
  absent.
- Trace colouring can be toggled between the high-contrast palette and a uniform
  colour via the Style tab combo box; respect the `_use_uniform_palette`
  attribute when adding new plot interactions.

## 2025-10-22 — Remote Data stability and streaming ingest
- Filters in Remote Data (All/Spectra/Images/Other), selection guards, and non-blocking worker cleanup
- Non-spectral skip during bulk ingest
- MAST: isolated temp-dir + persistent temp copy; fallback to direct HTTP (MAST Download API) on empty astroquery result
- NIST: registration fix; UI slots on main thread; CSV generation and ingest
- In-memory ingest: `DataIngestService.ingest_bytes` to support streaming/quick-plot flows

See also: `docs/atlas/remote_data_flow.md` and `docs/brains/*` neurons.

## Packaging
- Update `packaging/spectra_app.spec` when adding new data assets. Keep `requirements.txt` aligned with runtime dependencies to ensure PyInstaller bundles the correct versions.
