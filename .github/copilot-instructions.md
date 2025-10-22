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

## 📝 Documentation Workflows for AI Agents

### When to Create a Brains Entry (`docs/brains/`)
Create timestamped brains entry for **architectural decisions**:
```bash
# Filename format: YYYY-MM-DDTHHMM-short-description.md
docs/brains/2025-10-22T1430-planetary-data-requirements.md
```

**What belongs in brains**:
- Decisions about data sources/formats (e.g., "Why we use MAST for planetary spectra")
- Service architecture changes (e.g., "Why remote data moved to inspector tab")
- UI/UX paradigm shifts (e.g., "Progressive disclosure for complex features")
- Integration patterns (e.g., "How JWST/HST/ground-based data coexist")
- **Not**: Individual bug fixes, routine feature additions, or implementation details

**Template structure**:
```markdown
# [Decision Title]

**Date**: YYYY-MM-DDTHH:MM:SS-04:00 (EDT) / YYYY-MM-DDTHH:MM:SSZ (UTC)
**Status**: Proposed | Accepted | Superseded  
**Context**: What problem are we solving?
**Decision**: What did we decide?
**Rationale**: Why this approach over alternatives?
**Consequences**: Impact on codebase, workflows, users
**References**: Link to relevant code, docs, external sources
```

See `docs/brains/README.md` for full guidance and `docs/brains/2025-10-18T0924-remote-data-ux.md` for example.

### When to Update Atlas (`docs/atlas/`)
The Atlas contains **domain knowledge** and **workflow guidance**. Update when:
- Adding new spectroscopy modalities (UV/VIS, FTIR, Raman, AES, mass-spec)
- Documenting data sources (MAST, NIST, lab instruments)
- Explaining calibration/analysis workflows
- Adding educational content (e.g., planetary composition analysis for classroom labs)

**Key chapters to extend**:
- `chapter_1_modalities_instruments_and_what_they_tell_you.md` — New instrument types
- `chapter_4_data_sources_to_ingest_and_align.md` — New remote catalogs or file formats
- `chapter_5_unifying_axes_and_units_in_the_app.md` — Unit conversion additions
- `chapter_6_calibration_and_alignment_pipeline.md` — Calibration procedures
- `chapter_7_identification_and_prediction_logic.md` — Analysis techniques

**Create new chapters** for substantial new domains (e.g., "Planetary Spectroscopy Data Sources").

### Spectroscopy Domain Context

**This application targets multi-modal spectroscopy for educational and research use**:

**Supported Modalities** (current + planned):
- **UV-VIS** (200-800 nm): Electronic transitions, atomic emission
- **NIR** (800-2500 nm): Overtones, molecular vibrations
- **FTIR** (2.5-25 µm / 4000-400 cm⁻¹): Molecular vibrations, functional groups
- **Raman**: Complementary to IR; different selection rules
- **Atomic Emission Spectroscopy (AES)**: Elemental identification via emission lines
- **Mass Spectrometry**: Molecular mass determination (future integration)

**Key Use Case: Educational Planetary Composition Lab**
Students compare:
1. **Lab spectra**: Recorded locally (various modalities)
2. **Planetary spectra**: JWST/HST observations (UV-NIR-MIR, 0.1-30 µm)
3. **Stellar spectra**: Solar/stellar standards for reference
4. **Exoplanet transmission spectra**: Atmospheric composition analysis

**Workflow**: Overlay solar spectrum + exoplanet transit spectrum → Ratio/subtract → Identify atmospheric features (H₂O, CH₄, CO₂ bands) → Compare with lab IR/Raman of candidate molecules.

**Data Requirements**:
- **Real spectroscopic data only** (no synthetic/simulated data)
- **Wavelength coverage**: 0-2000 nm minimum (UV-VIS-NIR); extend to MIR where available
- **Calibration level**: Prefer Level 2+ (calibrated, flux units)
- **Provenance**: Full citation chain (mission → instrument → processing level → DOI)

### Accessing Real Planetary/Stellar Spectra

**Primary source**: NASA MAST archive via `astroquery`
```python
from astroquery.mast import Observations

# Planetary spectra from JWST/HST
results = Observations.query_criteria(
    target_name="Jupiter",
    dataproduct_type="spectrum",
    calib_level=[2, 3],  # Calibrated data only
    intentType="science"
)
```

**Quick-pick targets** (curated in `RemoteDataService._CURATED_TARGETS`):
- **Solar System**: Mercury, Venus, Earth, Mars, Jupiter, Saturn, Uranus, Neptune, Pluto + major moons
- **Stars**: Vega (A0V standard), Tau Ceti (solar analog), HD 189733 (exoplanet host)
- **Exoplanets**: WASP-39 b, TRAPPIST-1 system, HD 189733 b (transmission/emission spectra)

See `docs/user/real_spectral_data_guide.md` for comprehensive mission/wavelength coverage table.

---

**Quick checklist before committing**:
- [ ] Tests pass (`pytest`)
- [ ] Docs updated (user guide + dev notes)
- [ ] Patch notes entry with timestamp
- [ ] Knowledge log entry (if architectural change)
- [ ] Brains entry (if architectural decision)
- [ ] Atlas update (if new domain knowledge)
- [ ] No mutations of canonical nm storage
- [ ] Provenance recorded for new transforms