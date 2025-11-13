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
- `SpectraMainWindow` in `app/main.py` arranges the primary docks: `dataset_dock` (tree view of loaded spectra with visibility toggles), `inspector_dock` (tabbed detail panes built by `_build_inspector_tabs()`), and `log_dock` (streaming application log). These docks are standard `QDockWidget` instances, so additional panes can be inserted with `addDockWidget()` and surfaced through the `View` menu alongside the existing toggle actions.
- The central plotting surface is the `PlotPane` widget (`app/ui/plot_pane.py`). It provides helpers such as `add_trace()`, `remove_trace()`, `set_visible()`, `set_crosshair_visible()`, and `autoscale()` for managing rendered spectra. When updating UI controls respond to `PlotPane` signals instead of private window hooks: `unitChanged(str)` fires when the display unit is modified via the toolbar, `pointHovered(float, float)` emits cursor positions for status bar updates, and `rangeChanged(x_range, y_range)` tracks zooming/panning. `PlotPane` also exposes methods like `begin_bulk_update()`/`end_bulk_update()` to coalesce redraws and `map_nm_to_display()` for translating canonical wavelengths to the active unit.
- Spectrum overlays are orchestrated through `OverlayService` (`app/services/overlay_service.py`) which converts canonical `Spectrum` data into view-ready traces. Retrieve overlay results and feed them into `PlotPane.add_trace()`/`update_style()` when responding to inspector actions or dataset changes.
- Inspector UI customisations currently live in `SpectraMainWindow._build_inspector_tabs()` (`app/main.py`). Extend this method (or refactor into a dedicated module, e.g., `app/ui/inspector.py`, if the inspector grows) to add new tabs that coordinate with `PlotPane` and overlay services.

## Provenance
- `ProvenanceService.create_manifest()` accepts operation descriptors; include algorithm parameters, version numbers and citations for new transforms or exporters. Use `manifest_for_operation()` when generating derived datasets in bulk workflows.

## Packaging
- PyInstaller spec (`packaging/spectra_app.spec`) collects `samples/` and requirements automatically. Add additional data folders to the `datas` list. For plugin distribution, consider bundling a plugin manifest and using `--collect-all` for optional dependencies.

## Testing
- Tests live in `tests/` and rely on `tests/conftest.py` to add the repo root to `sys.path`. Add fixtures there if services require shared setup (e.g., temporary plugin directories). Keep new unit tests focused on deterministic service behaviour per `specs/testing.md`.
