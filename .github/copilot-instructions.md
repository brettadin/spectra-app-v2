# Copilot / AI Agent Instructions for Spectra App

This file provides essential patterns and workflows specific to this spectroscopy desktop application. For comprehensive context, read `AGENTS.md` and `START_HERE.md` first.

## 🎯 Core Mission
Build a rigorous spectroscopic analysis tool (PySide6/Qt) with **provenance-first architecture**, **offline-first caching**, and **canonical unit storage** (nm internally, convert at display time only).

## 📐 Architecture at a Glance

### The "Unit Canon" Pattern (Critical!)
- **Storage**: All spectra stored in **nanometers** (`Spectrum.x_unit = "nm"`) with base-10 absorbance (`Spectrum.y_unit = "absorbance"`)
- **Display**: `UnitsService.convert()` transforms to Å/µm/cm⁻¹ at render time via `Spectrum.view(units_service, target_x, target_y)`
- **Never** mutate stored arrays through conversions—toggling units must be idempotent
- Example: `app/services/spectrum.py` (immutable `@dataclass(frozen=True)`) and `app/services/units_service.py`

### Service Layer (app/services/)
Pure Python business logic, UI-agnostic:
- `DataIngestService` — Multi-format import (CSV/FITS/JCAMP-DX) via plugin importers
- `UnitsService` — Canonical↔display conversions; see `_to_canonical_wavelength()` / `_from_canonical_wavelength()`
- `OverlayService` — Manages `Spectrum` objects; returns view dicts for UI via `get_overlay(key, x_unit, y_unit)`
- `ProvenanceService` — Generates `manifest.json` bundles (`specs/provenance_schema.md`)
- `KnowledgeLogService` — Appends to `docs/history/KNOWLEDGE_LOG.md` with `record_event(component, summary, persist=True/False)`
- `RemoteDataService` — NASA MAST/NIST queries (provider-specific; MAST needs optional `astroquery`)
- `MathService` — Spectrum math (A−B, A/B) on aligned grids

### UI Layer (app/ui/)
- `SpectraMainWindow` (`app/main.py`) — Main shell; orchestrates services, docks, menu actions
- `PlotPane` (`app/ui/plot_pane.py`) — PyQtGraph wrapper; `add_trace(key, alias, x_nm, y, style)` for plotting
- `RemoteDataDialog` — Remote data fetcher UI with provider dropdown and quick-pick targets

### Data Flow
```
File → Importer (base.py protocol) → UnitsService.to_canonical → Spectrum (immutable, nm) 
  → OverlayService.add(spec) → PlotPane.add_trace(view in target units) → Export → manifest.json
```

## 🔑 Critical Patterns & Examples

### 1. Adding a New Importer
Implement `SupportsImport` protocol in `app/services/importers/`:
```python
class MyImporter:
    def can_import(self, path: Path) -> bool: ...
    def import_file(self, path: Path) -> ImporterResult:
        # Return raw arrays + units; DO NOT convert here
        return ImporterResult(x=wavelengths, y=intensity, ...)
```
Register via `DataIngestService.register_importer()`. See `csv_importer.py`, `jcamp_importer.py` for patterns.

### 2. Recording Provenance Events
```python
# In UI code (e.g., app/main.py)
self._record_history_event(
    component="calibration",
    summary="Applied Gaussian LSF convolution (FWHM=0.5 nm)",
    references=["docs/user/calibration.md"],
    persist=True  # True = append to KNOWLEDGE_LOG.md
)
```
For runtime-only events (e.g., temporary overlays): `persist=False`. See `KnowledgeLogService.DEFAULT_RUNTIME_ONLY_COMPONENTS`.

### 3. Unit Conversions (Display Only)
```python
# WRONG: mutating stored spectrum
spectrum.x = convert_to_angstrom(spectrum.x)  # ❌ Breaks canon!

# RIGHT: display-time conversion
view_dict = spectrum.view(self.units_service, "angstrom", "absorbance")
self.plot.add_trace(key, alias, view_dict["x"], view_dict["y"], ...)
```

### 4. Extending Remote Providers
Edit `RemoteDataService._build_provider_query()` with provider-specific logic:
```python
if provider == "MAST":
    # MAST expects 'target_name' param
    return {"target_name": query, "dataproduct_type": "spectrum", ...}
elif provider == "NIST":
    return {"spectra": query}  # NIST expects 'spectra' param
```
Add tests to `tests/test_remote_data_service.py` and integration tests under `tests/integration/`.

## 🛠 Developer Workflows

### Launch App
```powershell
# Windows quick-start (auto venv setup)
.\RunSpectraApp.cmd

# Manual (from repo root only!)
python -m app.main
```
**Never** run from inside `app/` directory—breaks module imports.

### Testing
```bash
pytest                          # All tests
pytest tests/test_ingest.py     # Specific module
QT_QPA_PLATFORM=offscreen pytest tests/test_smoke_workflow.py  # Headless UI tests
```
Add tests alongside features: ingest changes → `test_csv_importer.py`; remote changes → `test_remote_data_service.py`.

### Docs-First Mandate
Every code change requires:
1. **Update user/dev docs** (e.g., `docs/user/importing.md`, `docs/dev/reference_build.md`)
2. **Add patch notes**: `docs/history/PATCH_NOTES.md` with America/New_York timestamp
3. **Knowledge log entry**: `docs/history/KNOWLEDGE_LOG.md` (see `AGENTS.md` §2 for timestamp commands)
4. **Workplan checkbox**: Mark progress in `docs/reviews/workplan.md`

### Timestamp Discipline
Use **real** America/New_York + UTC timestamps (ISO-8601). PowerShell example:
```powershell
[System.TimeZoneInfo]::ConvertTimeBySystemTimeZoneId([DateTime]::UtcNow,"Eastern Standard Time").ToString("o")
(Get-Date).ToUniversalTime().ToString("o")
```
See `AGENTS.md` §2 for bash/Python alternatives.

## 🚨 Non-Negotiables
- **No framework changes**: PySide6/Qt only (no Tauri/Electron/web—see `specs/architecture.md`)
- **No chained conversions**: nm is canonical; display conversions are projections
- **Immutable spectra**: `Spectrum` is `frozen=True`; derived spectra use `.derive()` with provenance chain
- **Provenance everywhere**: Every transform recorded in `manifest.json` exports
- **Atomic PRs**: <~300 LOC per PR with docs/tests/patch-notes included

## 📚 Where to Look

### Examples of Core Patterns
- **Ingest flow**: `app/main.py::_ingest_path()` → `DataIngestService.ingest()` → `OverlayService.add()`
- **Provenance export**: `app/main.py::_export_bundle()` → `ProvenanceService.create_manifest()`
- **Remote fetching**: `app/ui/remote_data_dialog.py::_on_search()` → `RemoteDataService.search_provider()`
- **Smoke test**: `tests/test_smoke_workflow.py` (full ingest→toggle units→export pipeline)

### Key Files to Understand
- `app/services/spectrum.py` — Immutable spectrum model with `.view()` and `.derive()` methods
- `app/services/units_service.py` — Canonical↔display conversions; add units via `_normalise_x_unit()`
- `app/main.py` — UI orchestration; search for `_record_history_event()`, `_ingest_path()`, `_refresh_library_view()`
- `specs/provenance_schema.md` — Manifest structure for exports
- `docs/dev/ingest_pipeline.md` — ASCII diagram of data flow

### Documentation Index
- `START_HERE.md` — Session primer and workflow loop
- `AGENTS.md` — Operating manual with spectroscopy conventions
- `docs/history/MASTER PROMPT.md` — Product charter and acceptance criteria
- `docs/brains/README.md` — How to log architectural decisions
- `docs/atlas/` — Legacy design materials (30+ chapters retained for provenance)
- `docs/reviews/pass*.md` — Backlog priorities (calibration, identification, UI polish)

## 🔧 Common Tasks

### Add a New Unit
1. Update `UnitsService._normalise_x_unit()` to recognize the unit string
2. Implement conversion in `_to_canonical_wavelength()` and `_from_canonical_wavelength()`
3. Add unit tests to `tests/test_units.py` and round-trip tests to `tests/test_units_roundtrip.py`
4. Update `docs/user/units_reference.md`

### Add Optional Dependency
```python
# Guarded import pattern (see RemoteDataService)
try:
    from astroquery.mast import Observations
    MAST_AVAILABLE = True
except ImportError:
    MAST_AVAILABLE = False

# UI feedback (see RemoteDataDialog)
if not MAST_AVAILABLE:
    provider_label += " (dependencies missing)"
```
Update `requirements.txt` with comment noting it's optional; add to `AGENTS.md` §1.

### Debug Persisted Cache
```python
# LocalStore writes to ~/.spectra/cache/ by default
from app.services.store import LocalStore
store = LocalStore()
entries = store.list_entries()  # List cached spectra
store.get_entry(entry_id)       # Load specific spectrum
```
Cache is SHA256-deduplicated; see `app/services/store.py`.

## ⚡ Performance Notes
- PyQtGraph uses Level-of-Detail (LOD); configure via `PlotPane.set_max_points()`
- Default 100K points/trace; test UI responsiveness with 1M+ point datasets
- Knowledge log writes are append-only; avoid logging per-spectrum in batch imports

---

**Quick checklist before committing**:
- [ ] Tests pass (`pytest`)
- [ ] Docs updated (user guide + dev notes)
- [ ] Patch notes entry with timestamp
- [ ] Knowledge log entry (if architectural change)
- [ ] No mutations of canonical nm storage
- [ ] Provenance recorded for new transforms