# Developer Notes – Extension Points

## Importers & Data Ingest
- Importers implement `app.services.importers.Importer` and return `ImporterResult` instances.
- Register new importers through `DataIngestService.register_importer`; extensions are keyed by file suffix.
- Metadata can include `flux_context` for specialised conversions (e.g., absorption coefficients requiring path length).

## Spectrum Model
- `Spectrum.create()` enforces immutable numpy arrays and generates UUID identifiers. Use `with_name()` and `with_provenance()` helpers when deriving new spectra to preserve provenance chains.

## Math Operations
- Extend `MathService` with additional methods (e.g., normalised difference) that return `MathResult`. Respect the suppression pattern: return `suppressed=True` when trivial outputs occur and log meaningful metadata for provenance.

## UI Widgets
- `app/main.py` hosts `DataTab`, `CompareTab` and `ProvenanceTab`. Additional tabs can reuse `ServiceContainer` for dependency access. Chart rendering uses QtCharts; attach new signals to propagate overlay updates via `MainWindow._propagate_spectra_changed()`.

## Provenance
- `ProvenanceService.create_manifest()` accepts operation descriptors; include algorithm parameters, version numbers and citations for new transforms or exporters. Use `manifest_for_operation()` when generating derived datasets in bulk workflows.

## Packaging
- PyInstaller spec (`packaging/spectra_app.spec`) collects `samples/` and requirements automatically. Add additional data folders to the `datas` list. For plugin distribution, consider bundling a plugin manifest and using `--collect-all` for optional dependencies.

## Testing
- Tests live in `tests/` and rely on `tests/conftest.py` to add the repo root to `sys.path`. Add fixtures there if services require shared setup (e.g., temporary plugin directories). Keep new unit tests focused on deterministic service behaviour per `specs/testing.md`.
