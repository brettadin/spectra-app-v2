# Spectra App Cleanup & Refactoring Master Plan

**Created**: 2025-11-02  
**Purpose**: Comprehensive audit and improvement roadmap for repository structure, code quality, and documentation hygiene  
**Status**: In Progress

---

## Executive Summary

This document tracks the complete cleanup, refactoring, and improvement effort for the Spectra App repository. It serves as:
1. **Snapshot Archive** - Records initial state before changes
2. **Action Tracker** - Details what to do, where, why, and how
3. **Progress Log** - Documents completed work with rationales
4. **Future Agent Guide** - Explains architectural decisions and patterns

---

## Initial Assessment (2025-11-02)

### Critical Issues Identified

#### 1. Documentation Chaos & Redundancy
**Severity**: HIGH  
**Impact**: Confuses users and developers, contradictory information

**Current State**:
- Multiple overlapping summaries: `IMPLEMENTATION_SUMMARY.md`, `ENHANCEMENT_PLAN_STATUS.md`, `IR_EXPANSION_SUMMARY.md`
- Duplicate capability docs: `repo_inventory.md` (1200+ lines) + `app_capabilities.md` (500+ lines)
- Unclear prompt hierarchy: `MASTER_PROMPT.md` vs `docs/history/MASTER_PROMPT.md` vs `RUNNER_PROMPT.md`
- Planet data docs scattered: multiple "Playbook" files with different names
- User guides overlap: `START_HERE.md` vs `README.md` vs `QUICK_START_BULK_DATA.md`

**Proposed Solution**:
```
docs/
├── INDEX.md                    ← NEW: Single entry point, maps all docs
├── quick_start/
│   ├── installation.md         ← Consolidate START_HERE + BUILD_WINDOWS
│   ├── first_spectrum.md       ← Extract from README
│   └── bulk_data.md            ← Keep QUICK_START_BULK_DATA, improve
├── user_guides/
│   ├── importing.md            ← Keep existing
│   ├── remote_data.md          ← Keep existing
│   ├── plotting.md             ← Keep existing
│   └── reference_data.md       ← Keep existing
├── developer/
│   ├── architecture.md         ← Merge app_capabilities + repo_inventory
│   ├── contributing.md         ← Keep CONTRIBUTING.md content
│   ├── testing.md              ← Expand current specs/testing.md
│   └── code_standards.md       ← NEW: Patterns, anti-patterns
├── specs/                      ← Keep existing technical specs
├── history/
│   ├── CHANGELOG.md            ← PATCH_NOTES becomes this
│   ├── KNOWLEDGE_LOG.md        ← Already cleaned
│   ├── decisions/              ← Move docs/brains/ here, rename
│   └── archive/                ← Old summaries, deprecated docs
└── reference_sources/          ← Keep external citations
```

**Action Items**:
- [ ] Create `docs/INDEX.md` with complete doc map
- [ ] Archive redundant files to `docs/history/archive/2025-11-02-pre-cleanup/`
- [ ] Consolidate architecture docs
- [ ] Update all cross-references

---

#### 2. Broken/Incomplete Features Referenced in Docs
**Severity**: HIGH  
**Impact**: Users attempt to use non-existent features, frustration

**Missing Features Still Referenced**:
1. Calibration service (`app/services/calibration_service.py`) - workplan mentions, doesn't exist
2. Identification stack - planned but absent
3. Dataset removal UI - mentioned but incomplete in main window
4. Export format options - partially implemented

**Proposed Solution**:
- Tag all unimplemented features with `[PLANNED vX.X]` in workplan
- Remove UI menu items that lead nowhere
- Add placeholder dialogs: "This feature is coming in version X.X"
- Create `docs/developer/feature_status.md` tracking implementation state

**Action Items**:
- [ ] Audit all docs for feature references
- [ ] Cross-check against actual codebase
- [ ] Create feature status matrix
- [ ] Update workplan with accurate tags

---

#### 3. PDS Downloader Broken
**Severity**: MEDIUM  
**Impact**: Bulk planetary data acquisition doesn't work

**Problem**:
- `tools/pds_downloader_native.py` targets wrong PDS datasets (GRS instead of MASCS optical)
- URLs return 404 errors
- Not actually downloading spectroscopic data

**Proposed Solution**:
- Archive broken tools to `tools/archive/broken_pds_2025-11/`
- Add `README.md` explaining issue and investigation status
- Update `QUICK_START_BULK_DATA.md` to note manual-only downloads
- Create workplan ticket: "Batch 15: Fix PDS MASCS URLs"

**Action Items**:
- [ ] Create archive location with explanation
- [ ] Move broken scripts
- [ ] Document investigation findings
- [ ] Update user-facing docs

---

#### 4. Samples Directory Disorganized
**Severity**: MEDIUM  
**Impact**: Confusion about what files exist, duplication

**Current Chaos**:
```
samples/
├── sample_manifest.json        ← Root level manifest
├── sample_spectrum.csv         ← Test fixture
├── sample_transmittance.csv    ← Test fixture
├── exoplanets/                 ← Mixed sources
├── fits data/                  ← Space in name!
├── IR data/                    ← Mixed lab data
├── lamp data/                  ← Calibration lamps
├── other file types/           ← Vague name
├── SOLAR SYSTEM/               ← ALL CAPS, Mercury data
├── solar_system/               ← lowercase, different content!
└── SUN AND MOON/               ← Separate from solar_system?
```

**Proposed Solution**:
```
samples/
├── README.md                   ← Explains structure, data sources, citations
├── test_fixtures/              ← For unit tests only
│   ├── sample_spectrum.csv
│   └── sample_transmittance.csv
├── calibration_standards/
│   ├── lamps/                  ← Mercury, Argon, etc.
│   └── reference_stars/        ← Vega, etc.
├── solar_system/
│   ├── manifest.json           ← Expanded with metadata
│   ├── README.md               ← Data sources, instruments
│   ├── inner_planets/
│   │   ├── mercury/
│   │   ├── venus/
│   │   ├── earth/
│   │   └── mars/
│   ├── outer_planets/
│   │   ├── jupiter/
│   │   ├── saturn/
│   │   ├── uranus/
│   │   └── neptune/
│   └── small_bodies/
│       ├── pluto/
│       └── moons/
├── exoplanets/
│   ├── README.md               ← JWST sources, wavelength coverage
│   ├── hot_jupiters/
│   ├── temperate/
│   └── transmission_spectra/
├── laboratory/
│   ├── README.md               ← Instruments, conditions
│   ├── infrared_gases/         ← CO2, H2O absorption
│   ├── visible_absorption/
│   └── calibration_runs/
└── fits_formats/               ← Example FITS from various instruments
    ├── jwst/
    ├── hubble/
    └── spex/
```

**Action Items**:
- [ ] Create new structure with READMEs
- [ ] Move files systematically
- [ ] Update manifests with proper metadata
- [ ] Fix test paths in code
- [ ] Document data provenance

---

#### 5. Code Organization - `app/main.py` Bloat
**Severity**: MEDIUM-HIGH  
**Impact**: Hard to maintain, test, debug

**Current State**:
- `app/main.py`: 4000+ lines (estimate from inspection)
- Mixes UI setup, business logic, event handlers
- Difficult to isolate bugs
- Tests require full Qt stack

**Problems**:
1. Window initialization mixed with data services
2. Event handlers inline (should be in separate controller)
3. Remote data workers duplicated in main file
4. Export logic scattered across methods
5. Plotting setup intertwined with data management

**Proposed Architecture**:
```
app/
├── main.py                     ← Slim entry point (~200 lines max)
├── qt_compat.py                ← Keep existing
├── __init__.py
├── controllers/                ← NEW: Business logic
│   ├── __init__.py
│   ├── spectrum_controller.py  ← Handles dataset operations
│   ├── export_controller.py    ← Export workflows
│   ├── remote_controller.py    ← Remote data coordination
│   └── plot_controller.py      ← Plotting state management
├── ui/
│   ├── main_window.py          ← NEW: Extract from main.py
│   ├── menu_factory.py         ← NEW: Menu construction
│   ├── dock_factory.py         ← NEW: Dock widget setup
│   ├── remote_data_dialog.py   ← Keep existing
│   └── ...other dialogs
├── services/                   ← Keep existing, no business logic
└── data/
```

**Refactoring Plan**:
1. **Phase 1**: Extract window setup
   - Create `ui/main_window.py` with frame setup
   - Move dock creation to `ui/dock_factory.py`
   - Move menu creation to `ui/menu_factory.py`

2. **Phase 2**: Extract controllers
   - Create `controllers/spectrum_controller.py` for dataset CRUD
   - Create `controllers/export_controller.py` for export workflows
   - Create `controllers/remote_controller.py` for remote data

3. **Phase 3**: Clean main.py
   - Reduce to initialization + event delegation
   - Remove inline business logic
   - Use controllers for all operations

**Action Items**:
- [ ] Analyze `app/main.py` line-by-line dependencies
- [ ] Create controller module structure
- [ ] Extract window setup (preserves existing behavior)
- [ ] Write integration tests before refactoring
- [ ] Refactor incrementally with test coverage

---

### Medium Priority Issues

#### 6. Test Organization & Coverage Gaps
**Severity**: MEDIUM  
**Impact**: Unclear what's tested, hard to run subsets

**Current State**:
- 73 test files, no index
- Mix of unit, integration, UI tests
- No clear documentation of coverage
- Hard to run specific test categories

**Proposed Solution**:
Create `tests/README.md`:
```markdown
# Test Suite Organization

## Quick Reference
```bash
# Run everything
pytest

# Fast tests only (no UI, no I/O)
pytest -m "not ui and not integration"

# Single module
pytest tests/test_units_service.py -v

# Coverage report
pytest --cov=app --cov-report=html
```

## Test Categories

### Unit Tests (Fast, No Dependencies)
- `test_units_service.py` - Unit conversions (nm↔cm⁻¹↔µm)
- `test_math_helpers.py` - Smoothing, normalization
- `test_spectrum.py` - Data structure operations

### Integration Tests (Require I/O)
- `test_ingest.py` - Full import pipeline
- `test_cache_index.py` - LocalStore operations
- `test_remote_data_service.py` - MAST queries (mocked)

### UI Tests (Require Qt)
- `test_remote_data_dialog.py` - Dialog behavior
- `test_main_window.py` - Window interactions
- `test_smoke_workflow.py` - End-to-end flows

## Coverage Gaps
- [ ] Export workflows (manifest, CSV, wide format)
- [ ] Overlay persistence across sessions
- [ ] Knowledge log event filtering
- [ ] FITS unit detection edge cases
```

**Action Items**:
- [ ] Create test README
- [ ] Add pytest markers to tests
- [ ] Run coverage report
- [ ] Identify gaps
- [ ] Write missing tests

---

#### 7. Knowledge Log Template Incomplete
**Severity**: LOW-MEDIUM  
**Impact**: Unclear what should be logged

**Current Problem**:
- Stub says "curated only" but no examples
- No clear template for quality entries
- Agents don't know what qualifies

**Proposed Solution**:
Replace `docs/history/KNOWLEDGE_LOG.md` header with:
```markdown
## Entry Template & Examples

### Good Entry Example
## 2025-11-02 14:30 – Remote data dialog thread cleanup

**Author**: agent (GitHub Copilot)

**Why**: Dialog crashed when closed during active MAST query; Qt warned about destroyed threads

**What changed**:
- Added cleanup handlers to accept/reject/close in RemoteDataDialog
- Workers now join threads before widget destruction
- Added busy indicator during cleanup

**Impact**: Users can safely cancel slow network operations without crashes

**References**: `app/ui/remote_data_dialog.py`, `tests/test_remote_data_dialog.py`

---

### What Qualifies for an Entry?
✅ **Log these**:
- Bug fixes that affect user workflows
- New features or capabilities added
- Architecture changes (file moves, refactors)
- Breaking changes to APIs or file formats
- Performance improvements (>10% speedup)
- Security fixes

❌ **Don't log these**:
- Routine refactors (variable renames)
- Documentation typos
- Test additions without behavior change
- Dependency version bumps (unless fixes critical bug)
```

**Action Items**:
- [ ] Update KNOWLEDGE_LOG.md with template
- [ ] Add examples of good vs bad entries
- [ ] Document in AGENTS.md

---

#### 8. Dependency Management
**Severity**: MEDIUM  
**Impact**: Installation issues, version conflicts

**Current Issues**:
- `requirements.txt` has loose pins
- No `requirements-dev.txt` for testing tools
- `sitecustomize.py` installs numpy automatically (can conflict)
- No lockfile (pip-compile or poetry)

**Proposed Solution**:
```
requirements/
├── base.txt           ← Runtime dependencies only
├── dev.txt            ← Testing, linting (includes base)
└── docs.txt           ← Sphinx, mkdocs (if needed)
```

**Action Items**:
- [ ] Split requirements by environment
- [ ] Pin exact versions in lockfile
- [ ] Test clean install
- [ ] Document in installation guide

---

### Lower Priority Enhancements

#### 9. Dataset Tooltips in Library Tab
**Severity**: LOW  
**Impact**: Quality of life improvement

**Proposal**: Show metadata on hover
- Instrument (JWST NIRSpec, SpeX, FTIR)
- Target (WASP-39 b, HD 31996, CO₂ lab)
- Wavelength range (e.g., 1-5 µm)
- Citation/DOI if available

---

#### 10. Archive Cleanup Automation
**Severity**: LOW  
**Impact**: Repository hygiene

**Proposal**: Create `tools/archive_old_docs.py`
- Moves files >90 days old from `docs/history/` to `archive/`
- Generates index of archived content
- Can run manually or via CI

---

## Archive Structure Plan

All deprecated/old files will go to:
```
docs/history/archive/
├── README.md                           ← Index of all archived content
├── 2025-11-02-pre-cleanup/
│   ├── README.md                       ← Why these were archived
│   ├── IMPLEMENTATION_SUMMARY.md
│   ├── ENHANCEMENT_PLAN_STATUS.md
│   ├── IR_EXPANSION_SUMMARY.md
│   ├── repo_inventory.md
│   └── app_capabilities.md
├── broken-tools/
│   ├── README.md                       ← Why broken, investigation status
│   └── pds_downloader_2025-11/
│       ├── pds_downloader_native.py
│       └── investigation_notes.md
└── deprecated-features/
    └── [future deprecated code]
```

**Archive README Template**:
```markdown
# Archive: [Name/Date]

## Why Archived
[Brief explanation]

## What Was Here
[List of files/features]

## Current Alternative
[Where users should go instead]

## Can It Be Restored?
[Yes/No, conditions if yes]

## Investigation Notes
[Any technical details for future reference]
```

---

## Refactoring Patterns & Standards

### Code Organization Principles

1. **Single Responsibility**: Each file has one clear purpose
2. **Dependency Injection**: Services passed to constructors, not globals
3. **Interface Segregation**: Controllers own business logic, UI owns display
4. **Testability First**: Can test logic without Qt

### File Size Guidelines
- **Entry Points** (`main.py`): <200 lines
- **Controllers**: <300 lines each
- **Services**: <400 lines each
- **UI Components**: <250 lines each
- **Utilities**: <150 lines each

If a file exceeds limits, split by responsibility.

### Naming Conventions
- **Controllers**: `{domain}_controller.py` (spectrum_controller, export_controller)
- **Services**: `{capability}_service.py` (data_ingest_service, units_service)
- **UI**: `{widget}_dialog.py` or `{widget}_dock.py`
- **Tests**: `test_{module_name}.py`

### Import Order
```python
# Standard library
import sys
from pathlib import Path

# Third-party
import numpy as np
from PySide6.QtWidgets import QMainWindow

# Local app
from app.services import UnitsService
from app.controllers import SpectrumController
```

---

## Progress Tracking

### Completed
- [x] Initial assessment documented
- [x] Archive structure planned
- [x] Refactoring patterns defined

### In Progress
- [ ] Documentation consolidation
- [ ] Code refactoring (main.py split)
- [ ] Samples reorganization

### Blocked
- None currently

---

## Future Agent Notes

### If You Need to Add a Feature
1. Check `docs/developer/feature_status.md` for conflicts
2. Add controller in `app/controllers/` if business logic
3. Add service in `app/services/` if reusable capability
4. Add UI in `app/ui/` if user-facing
5. Write tests first in `tests/`
6. Update this plan with changes

### If You Find a Bug
1. Check if feature is marked `[PLANNED]` (might not exist yet)
2. Write failing test case
3. Fix in appropriate module (controller vs service vs UI)
4. Update KNOWLEDGE_LOG.md with entry
5. Add to CHANGELOG.md

### If Something Is Confusing
1. Check `docs/INDEX.md` for documentation map
2. Check `docs/history/archive/` for old decisions
3. Check `docs/brains/` (future: `docs/history/decisions/`) for architecture rationale
4. Ask in PR/issue for clarification, document answer

---

---

## Additional Findings from Deep Code Analysis

### 11. Export Logic Scattered Across Multiple Files
**Severity**: MEDIUM  
**Impact**: Hard to maintain export formats, inconsistent behavior

**Current State**:
- `app/main.py` (line ~1002): `export_center()` method orchestrates exports
- `app/services/provenance_service.py`: Core export logic (bundle, wide CSV, composite)
- `app/ui/export_center_dialog.py`: UI for selecting export options
- Tests spread across `test_provenance.py`, `test_provenance_manifest.py`

**Problems**:
1. Export coordination logic in UI layer (main.py) should be in controller
2. ProvenanceService doing too much (bundle creation + CSV writing + file copying)
3. No clear separation between "what to export" (business logic) and "how to format" (formatters)

**Proposed Refactoring**:
```
app/
├── controllers/
│   └── export_controller.py        ← NEW: Orchestration logic
├── services/
│   ├── provenance_service.py       ← Keep: manifest creation only
│   └── export_formatters/          ← NEW: Format-specific writers
│       ├── __init__.py
│       ├── csv_formatter.py        ← Combined, wide, composite CSV
│       ├── json_formatter.py       ← Manifest JSON
│       └── bundle_formatter.py     ← Full bundle assembly
```

**Benefits**:
- Add new export formats without modifying ProvenanceService
- Test formatters independently
- Clearer dependencies (controller → service → formatters)

---

### 12. Duplicate Worker Classes
**Severity**: LOW-MEDIUM  
**Impact**: Code duplication, inconsistent behavior

**Current State**:
- `app/main.py` lines 54-155: `_RemoteSearchWorker`, `_RemoteDownloadWorker` (local to main.py)
- `app/ui/remote_data_dialog.py`: Similar workers for dialog

**Problems**:
1. ~200 lines of duplicated worker code
2. If bug found in one, must fix in both
3. Violates DRY principle

**Proposed Solution**:
```
app/workers/
├── __init__.py
├── remote_search_worker.py
└── remote_download_worker.py
```

Move shared worker classes here, import in both main.py and dialog.

---

### 13. Service Dependencies Not Clearly Documented
**Severity**: LOW  
**Impact**: Hard to understand what imports what

**Current State**:
- Services import each other without clear hierarchy
- Circular import risks
- No dependency graph

**Proposed Solution**:
Create `docs/developer/service_architecture.md` with:
- Layered diagram (UI → Controllers → Services → Data)
- Dependency graph showing which services use which
- Rules: "Services should not import from ui/ or controllers/"

Example diagram:
```
┌─────────────────────────────────────┐
│  UI Layer (app/ui/, app/main.py)   │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│  Controllers (business logic)       │
│  - SpectrumController               │
│  - ExportController                 │
│  - RemoteController                 │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│  Services (reusable capabilities)   │
│  - DataIngestService                │
│  - ProvenanceService                │
│  - UnitsService                     │
│  - OverlayService                   │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│  Data/Models                        │
│  - Spectrum                         │
│  - LocalStore                       │
└─────────────────────────────────────┘
```

---

### 14. Test Fixtures Duplicated
**Severity**: LOW  
**Impact**: Tests create similar test data repeatedly

**Current State**:
- Many tests create `Spectrum` objects inline
- `test_provenance_manifest.py` has `build_spectrum()` helper
- `conftest.py` has FITS fixture but not CSV/generic spectrum

**Proposed Solution**:
Expand `tests/conftest.py` with reusable fixtures:
```python
@pytest.fixture
def simple_spectrum():
    """Single spectrum for basic tests."""
    return Spectrum.create(
        'test-spectrum',
        np.array([400.0, 450.0, 500.0]),
        np.array([0.5, 0.8, 0.3]),
        x_unit='nm',
        y_unit='absorbance'
    )

@pytest.fixture
def spectrum_with_metadata(tmp_path):
    """Spectrum with full provenance metadata."""
    source = tmp_path / "source.csv"
    source.write_text("wavelength,flux\n400,0.5\n450,0.8")
    # ... create and return spectrum

@pytest.fixture
def multiple_spectra():
    """List of 3 spectra for overlay tests."""
    # ...
```

---

### 15. No Versioning for Export Formats
**Severity**: MEDIUM  
**Impact**: Can't evolve export formats without breaking old files

**Current State**:
- `manifest.json` has `app.version` but no `format_version`
- Wide CSV uses comment `# spectra-wide-v1` (good!)
- Combined CSV has no version marker

**Proposed Solution**:
1. Add `format_version` to manifests:
```json
{
  "app": {"name": "SpectraApp", "version": "0.1.0"},
  "format_version": "1.0",  // ← NEW
  "timestamp": "...",
  "sources": [...]
}
```

2. Add version comments to all CSV exports:
```csv
# spectra-export-v1
wavelength_nm,intensity,spectrum_id,...
```

3. Create `docs/specs/export_formats.md` documenting each version

---

### 16. Error Messages Not User-Friendly
**Severity**: LOW-MEDIUM  
**Impact**: Users see technical stack traces

**Current State** (from code inspection):
- Many `raise ValueError(...)` without context
- No user-facing error dialog wrapper
- Stack traces leak implementation details

**Proposed Solution**:
Create `app/ui/error_handler.py`:
```python
class UserFriendlyError(Exception):
    """Exception with both user and technical messages."""
    def __init__(self, user_msg: str, technical_msg: str = ""):
        self.user_msg = user_msg
        self.technical_msg = technical_msg or user_msg
        super().__init__(technical_msg)

def show_error_dialog(parent, error: Exception):
    """Display user-friendly error with optional details."""
    if isinstance(error, UserFriendlyError):
        msg = error.user_msg
        details = error.technical_msg
    else:
        msg = "An unexpected error occurred"
        details = str(error)
    
    dialog = QMessageBox(parent)
    dialog.setIcon(QMessageBox.Critical)
    dialog.setText(msg)
    dialog.setDetailedText(details)
    dialog.exec()
```

Replace in code:
```python
# Old
raise ValueError("No importer registered for extension '.xyz'")

# New
raise UserFriendlyError(
    "Cannot open this file type (.xyz)",
    f"No importer registered for extension '.xyz'. Supported: {exts}"
)
```

---

### 17. Magic Numbers and Strings Throughout Code
**Severity**: LOW  
**Impact**: Hard to maintain, error-prone

**Examples Found**:
- Provider strings: `"MAST"`, `"NIST"`, `"Solar System Archive"` (should be constants)
- File extensions: `".csv"`, `".fits"`, `".jdx"` (scattered)
- Unit strings: `"nm"`, `"absorbance"`, `"flux_density"` (duplicated)

**Proposed Solution**:
Create `app/constants.py`:
```python
# Data Providers
PROVIDER_MAST = "MAST"
PROVIDER_NIST = "NIST"
PROVIDER_SOLAR_SYSTEM = "Solar System Archive"
PROVIDER_EXOSYSTEMS = "MAST ExoSystems"

# File Extensions
EXT_CSV = ".csv"
EXT_FITS = ".fits"
EXT_JCAMP = ".jdx"
SUPPORTED_EXTENSIONS = (EXT_CSV, EXT_FITS, EXT_JCAMP)

# Units
UNIT_NM = "nm"
UNIT_UM = "um"
UNIT_ANGSTROM = "angstrom"
UNIT_WAVENUMBER = "cm^-1"

UNIT_ABSORBANCE = "absorbance"
UNIT_FLUX_DENSITY = "flux_density"
UNIT_TRANSMITTANCE = "transmittance"

# Export Formats
EXPORT_FORMAT_VERSION = "1.0"
WIDE_CSV_MARKER = "# spectra-wide-v1"
COMPOSITE_CSV_MARKER = "# spectra-composite-v1"
```

---

### 18. Missing Logging/Telemetry
**Severity**: LOW  
**Impact**: Hard to diagnose user issues

**Current State**:
- KnowledgeLogService exists but only for provenance
- No application logging (Python `logging` module not configured)
- No way to enable debug mode for troubleshooting

**Proposed Solution**:
1. Configure Python logging in `app/main.py`:
```python
import logging

def setup_logging(debug=False):
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('spectra_app.log'),
            logging.StreamHandler()
        ]
    )
    
# Check for --debug flag
if '--debug' in sys.argv:
    setup_logging(debug=True)
```

2. Add Help → "Open Log File" menu item
3. Document in troubleshooting guide

---

### 19. No Performance Profiling Hooks
**Severity**: LOW  
**Impact**: Can't measure where slowdowns occur

**Proposed Solution**:
Create `app/utils/profiling.py`:
```python
import time
import logging
from functools import wraps

logger = logging.getLogger(__name__)

def profile(func):
    """Decorator to time function execution."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        logger.debug(f"{func.__name__} took {elapsed:.3f}s")
        return result
    return wrapper
```

Use on slow operations:
```python
@profile
def ingest(self, path: Path) -> List[Spectrum]:
    ...
```

---

### 20. main.py Detailed Analysis
**File Stats**: 2496 lines, 123KB  
**Classes**: 1 main class (SpectraMainWindow)  
**Helper Classes**: 2 workers (_RemoteSearchWorker, _RemoteDownloadWorker)

**Method Breakdown** (estimated from inspection):
- UI Setup: ~360 lines (lines 378-741)
- Menu Creation: ~1370 lines (lines 741-2111)
- Event Handlers: ~380 lines (lines 2117+)
- Worker Management: ~100 lines

**Extraction Plan**:
```
Phase 1 (Week 1): Extract Window Setup
├── app/ui/main_window.py (~500 lines)
│   ├── __init__ (frame, status bar)
│   ├── _create_central_widget (plot pane)
│   ├── _create_docks (data, inspector, history, log)
│   └── _apply_layout (dock positioning)
└── app/ui/menu_factory.py (~200 lines)
    └── create_menu_bar() → QMenuBar

Phase 2 (Week 2): Extract Controllers
├── app/controllers/spectrum_controller.py (~300 lines)
│   ├── load_spectra (file selection + ingest)
│   ├── remove_spectrum
│   ├── toggle_visibility
│   └── apply_transform (smooth, normalize)
├── app/controllers/export_controller.py (~200 lines)
│   ├── export_manifest
│   ├── export_wide_csv
│   └── export_composite
└── app/controllers/remote_controller.py (~250 lines)
    ├── search (delegates to service)
    ├── download
    └── cancel

Phase 3 (Week 3): Extract Workers
└── app/workers/
    ├── remote_search_worker.py
    └── remote_download_worker.py

Phase 4 (Week 4): Clean main.py
- main.py becomes ~250 lines:
  - App initialization
  - Window instantiation
  - Controller wiring
  - Event routing
```

---

## Revised Priority Matrix

### Critical (Do First)
1. ✅ Create master plan document
2. Create archive structure
3. Create docs/INDEX.md
4. Begin main.py refactoring (Phase 1)

### High (Do Soon)
5. Archive redundant docs
6. Reorganize samples/
7. Split ProvenanceService/export logic
8. Move duplicate workers
9. Add export format versioning

### Medium (Do This Month)
10. Create test fixtures in conftest
11. Add service architecture diagram
12. Implement error handler wrapper
13. Add constants.py
14. Configure logging

### Low (Nice to Have)
15. Add profiling decorators
16. Dataset tooltips
17. Archive automation script
18. "Last Verified" doc metadata

---

## Next Steps (Immediate)

1. **Create Archive Structure** (30 min)
   - Make directories
   - Write README templates
   - Move first batch of files

2. **Create Documentation Index** (1 hour)
   - Map all existing docs
   - Identify consolidation candidates
   - Write `docs/INDEX.md`

3. **Analyze main.py Dependencies** (2 hours) ← IN PROGRESS
   - Map imports ✓
   - Identify method clusters ✓
   - Plan extraction order ✓
   - **Next**: Write integration tests before refactoring

4. **Begin Samples Reorganization** (1 hour)
   - Create new structure
   - Write READMEs
   - Start moving files

---

## Execution Plan (Easiest → Hardest)

This is the pragmatic order to execute work from lowest effort/fastest wins to highest effort/risk. Each item lists a rough time estimate and a crisp acceptance criterion.

### 1) Quick Wins (60–120 min total)
- Finalize docs/INDEX.md (45–60 min)
    - Accept: All links resolve locally; INDEX is linked from README.
- Update README to point to INDEX and Quick Start (20–30 min)
    - Accept: Top-level navigation clear; no stale sections remain.
- Archive redundant docs with stubs (45–75 min)
    - Accept: IMPLEMENTATION_SUMMARY.md, ENHANCEMENT_PLAN_STATUS.md, IR_EXPANSION_SUMMARY.md, docs/app_capabilities.md, docs/repo_inventory.md moved to archive with “replacement” pointers.

### 2) Small Code Shims (90–150 min)
- Introduce app/constants.py (45–60 min)
    - Accept: No behavior change; at least 5 hard-coded strings replaced safely in touched modules; tests still pass.
- Configure baseline logging (45–75 min)
    - Accept: app starts without warnings; a log file is created; Help → “Open Log File” menu entry works if present or noted for follow-up.

### 3) Samples Directory Skeleton (60–90 min)
- Create samples/{test_fixtures,calibration_standards,solar_system,exoplanets,laboratory}/ with README per folder
    - Accept: New READMEs exist; at least two representative files moved; tests referencing sample paths still pass or are updated.

### 4) MainWindow Extraction – Phase 1 (2–3 hours)
- Extract window setup and menu wiring into app/ui/main_window.py and app/ui/menu_factory.py
    - Accept: App launches and core flows (open CSV/FITS, plot, export) work unchanged; main.py shrinks meaningfully (>300 lines reduction).

### 5) Export Logic Split (2–3 hours)
- Move format-specific code into services/export_formatters (csv/json/bundle) and add a format_version
    - Accept: Exports produce identical artifacts plus a version marker; tests for manifest/CSV remain green.

### 6) Worker De-duplication (2–4 hours)
- Consolidate remote search/download workers into app/workers/
    - Accept: Both main window and remote dialog use shared workers; no duplicated classes remain; manual search/download still works.

### 7) Error Handling Wrapper (60–90 min)
- Add user-friendly error wrapper and apply to top 3 UI actions
    - Accept: Those actions show dialog instead of raw stack traces on error; logs capture technical details.

### 8) Test Hygiene (90–150 min)
- Expand tests/conftest.py with reusable spectrum fixtures; add tests/README.md
    - Accept: At least two test modules updated to use fixtures; quick test run passes.

### 9) Profiling Hooks and CI (60–90 min)
- Add lightweight @profile decorator and optional GitHub Actions workflow for pyright + pytest
    - Accept: Profile logs appear in DEBUG mode; CI job runs on PRs and reports status.

Notes:
- If any medium/large item shows unexpected risk, pause and land the previous small shims to keep the branch green.
- Prefer short PRs (≤400 LOC changes) that keep behavior stable and are easy to review.

---

**Last Updated**: 2025-11-02 16:30  
**Maintained By**: Development team and AI agents  
**Review Cadence**: Weekly during active cleanup, monthly after
