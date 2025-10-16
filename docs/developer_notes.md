# Developer Notes – Service Extension Points

## Reference materials
- Consult `docs/link_collection.md` for curated JWST, MAST, and Astropy ecosystem resources when scoping integrations or reviewing upstream tooling.

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

## Packaging
- Update `packaging/spectra_app.spec` when adding new data assets. Keep `requirements.txt` aligned with runtime dependencies to ensure PyInstaller bundles the correct versions.
