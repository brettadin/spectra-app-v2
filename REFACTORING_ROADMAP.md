# Refactoring Roadmap - Spectra App

**Date:** February 5, 2026
**Priority:** High
**Estimated Effort:** 3-5 days (can be done incrementally)

---

## Critical Issue: main_window.py Size

**Current State:**
- 📊 **6,916 lines** in a single file
- 🔴 Industry standard: 200-500 lines per file
- 🔴 Your file is **14-35x larger** than recommended

**Why This Matters:**
- Hard to navigate and understand
- Merge conflicts more likely
- Difficult to test in isolation
- Slower IDE performance
- Harder for new contributors

---

## Refactoring Strategy

Break `main_window.py` into logical, focused modules. This can be done incrementally without breaking functionality.

---

## Phase 1: Extract Worker Classes (1 day)

### Current Location
`app/ui/main_window.py` contains multiple QThread worker classes

### Target Structure
```
app/
└── workers/
    ├── __init__.py
    ├── search_worker.py      # Remote search operations
    ├── download_worker.py    # File download operations
    └── processing_worker.py  # Data processing operations
```

### Benefits
- Workers are reusable across UI components
- Easier to test background operations
- Cleaner separation of concerns

### Files to Create
1. `app/workers/search_worker.py` - Move search-related QThread classes
2. `app/workers/download_worker.py` - Move download-related QThread classes

---

## Phase 2: Extract Dialog Classes (1 day)

### Current Location
Dialog classes embedded in `main_window.py`

### Target Structure
```
app/
└── ui/
    └── dialogs/
        ├── __init__.py
        ├── export_dialog.py      # Export functionality
        ├── import_dialog.py      # Import file dialogs
        ├── settings_dialog.py    # Application settings
        └── label_editor_dialog.py # Plot label editing
```

### Benefits
- Dialogs can be opened from multiple locations
- Easier to unit test dialog logic
- Reduces main_window.py complexity

---

## Phase 3: Extract Plot Management (2 days)

### Current Location
Plotting logic scattered throughout `main_window.py`

### Target Structure
```
app/
└── ui/
    └── plotting/
        ├── __init__.py
        ├── plot_manager.py       # Coordinate plot updates
        ├── plot_renderer.py      # Rendering pipeline
        ├── plot_interactions.py  # Mouse/keyboard interactions
        └── plot_styles.py        # Visual styling
```

### Key Classes to Extract

#### 1. PlotManager (~300 lines)
Responsible for:
- Coordinating plot updates
- Managing visible spectra
- Handling axis units
- Applying calibration/normalization

Methods to move:
- `_get_visible_spectra()`
- `_get_all_spectra()`
- `_is_spectrum_visible()`
- `_apply_y_scale()`
- `_compute_display_uncertainty()`

#### 2. PlotRenderer (~200 lines)
Responsible for:
- Converting data to display coordinates
- Applying units (nm → display unit)
- Rendering spectra with styles
- Managing plot items (lines, markers)

Methods to move:
- `_nm_to_display()`
- `_display_to_nm()`
- `_apply_range_to_spectra()`
- `_get_current_display_unit()`

#### 3. PlotInteractions (~150 lines)
Responsible for:
- Mouse hover events
- Cursor tracking
- Peak finding
- Jump to max/min

Methods to move:
- `_on_plot_point_hovered()`
- `_on_jump_to_max()`
- `_on_find_peak_near_cursor()`
- `_center_view_on_x()`

---

## Phase 4: Extract Menu System (1 day)

### Current Location
Menu creation in `_setup_menu()` (~200 lines)

### Target Structure
```
app/
└── ui/
    └── menus/
        ├── __init__.py
        ├── menu_builder.py      # Menu construction
        ├── file_menu.py         # File operations
        ├── edit_menu.py         # Edit operations
        ├── view_menu.py         # View settings
        └── help_menu.py         # Help/docs
```

### Benefits
- Easier to add new menu items
- Better organization of actions
- Testable menu logic

---

## Phase 5: Extract Service Interfaces (1 day)

### Current Goal
Create clean interfaces between UI and services

### Target Structure
```
app/
└── ui/
    └── adapters/
        ├── __init__.py
        ├── data_adapter.py      # DataIngestService interface
        ├── math_adapter.py      # MathService interface
        └── export_adapter.py    # Export operations interface
```

### Benefits
- Cleaner dependency injection
- Easier to mock for testing
- Better separation of concerns

---

## Concrete Example: Extracting PlotManager

### Before (in main_window.py)
```python
class SpectraMainWindow(QtWidgets.QMainWindow):
    # ... 6,916 lines ...

    def _get_visible_spectra(self) -> List[Spectrum]:
        """Get all visible spectra."""
        return [spec for spec in self._get_all_spectra()
                if self._is_spectrum_visible(spec)]

    def _apply_y_scale(self, y: np.ndarray) -> np.ndarray:
        """Apply Y-axis scaling transform."""
        # 30 lines of logic...

    # ... hundreds more lines of plotting code ...
```

### After (extracted to plot_manager.py)
```python
# app/ui/plotting/plot_manager.py
from typing import List
import numpy as np
from app.services import Spectrum

class PlotManager:
    """Manages spectrum plotting and display transformations."""

    def __init__(self, dataset_panel, plot_pane):
        self.dataset_panel = dataset_panel
        self.plot_pane = plot_pane

    def get_visible_spectra(self) -> List[Spectrum]:
        """Get all visible spectra."""
        return [spec for spec in self.get_all_spectra()
                if self.is_spectrum_visible(spec)]

    def apply_y_scale(self, y: np.ndarray, mode: str) -> np.ndarray:
        """Apply Y-axis scaling transform."""
        # Same logic, but isolated and testable
        pass

    # ... other plotting methods ...
```

### In main_window.py
```python
from app.ui.plotting.plot_manager import PlotManager

class SpectraMainWindow(QtWidgets.QMainWindow):
    def __init__(self, ...):
        super().__init__()
        self.plot_manager = PlotManager(self.dataset_panel, self.plot_pane)

    def _get_visible_spectra(self):
        """Delegate to plot manager."""
        return self.plot_manager.get_visible_spectra()
```

**Result:** main_window.py shrinks by ~300 lines, plotting logic is testable

---

## Incremental Approach

You can refactor incrementally without breaking the app:

### Week 1: Workers
1. Create `app/workers/` directory
2. Copy worker classes to new files
3. Import from new location in main_window.py
4. Test thoroughly
5. Delete old code from main_window.py

### Week 2: Dialogs
1. Create `app/ui/dialogs/` directory
2. Copy dialog classes to new files
3. Update imports
4. Test each dialog
5. Delete old code

### Week 3: Plot Management
1. Create `app/ui/plotting/` directory
2. Create PlotManager class
3. Move methods one at a time
4. Update callers to use plot_manager
5. Test after each change

---

## Testing Strategy

After each refactoring phase:

```bash
# Windows
dev test       # Run all tests
dev lint       # Check for issues

# Linux/Mac
make test      # Run all tests
make lint      # Check for issues
```

Also manually test:
1. Import data
2. Plot spectra
3. Apply transformations
4. Export data
5. Remote search/download

---

## Quick Wins (Easy Improvements)

While planning the major refactor, you can make quick improvements:

### 1. Add Module Docstrings
```python
"""
Plot management module.

Handles spectrum rendering, display transformations, and user interactions
with the main plot area.
"""
```

### 2. Extract Constants
```python
# Instead of magic numbers throughout
PLOT_MAX_POINTS_KEY = "plot/max_points"
DEFAULT_LINE_WIDTH = 2
HOVER_TOLERANCE_PX = 10
```

### 3. Use Enum for States
```python
from enum import Enum

class YScaleMode(Enum):
    LINEAR = "linear"
    LOG10 = "log10"
    ASINH = "asinh"

# Instead of string comparisons
if self.y_scale_mode == YScaleMode.LINEAR:
    # ...
```

### 4. Type Hints Everywhere
```python
def _get_visible_spectra(self) -> List[Spectrum]:
    """Get all visible spectra."""
    # Type hints make IDE autocomplete work better
```

---

## Metrics to Track

### Before Refactoring
- main_window.py: 6,916 lines
- Largest file: 6,916 lines
- Average file size: ~300 lines
- Files > 1000 lines: 2

### Target After Refactoring
- main_window.py: <500 lines
- Largest file: <800 lines
- Average file size: ~250 lines
- Files > 1000 lines: 0

### Quality Metrics
- Cyclomatic complexity: <10 per function
- Test coverage: >80%
- Type hint coverage: >60%

---

## Resources

### Tools for Refactoring
- **Rope** (Python refactoring library)
  ```bash
  pip install rope
  ```
- **VS Code Refactor Tools** (built-in)
  - Right-click → "Extract Method"
  - Right-click → "Extract Variable"

### Best Practices
- **Rule of Thumb:** If you can't see a full class on your screen, it's too big
- **Single Responsibility:** Each class should do ONE thing well
- **DRY (Don't Repeat Yourself):** Extract common code to shared functions
- **KISS (Keep It Simple):** Simpler code is easier to maintain

---

## Questions to Ask During Refactoring

For each large method:
1. **What does this do?** (If you can't explain in one sentence, split it)
2. **Can this be tested in isolation?** (If no, it's too coupled)
3. **Does this belong here?** (If no, extract it)
4. **Is this used elsewhere?** (If yes, make it reusable)

---

## Example Commit Messages

When refactoring, use clear commit messages:

```
refactor: Extract search workers to app/workers/

- Move SearchWorker and DownloadWorker classes
- Update imports in main_window.py
- No functional changes
- Tests still pass (199/199)
```

```
refactor: Create PlotManager class for plot operations

- Extract 300 lines of plotting logic from main_window.py
- New class: app/ui/plotting/plot_manager.py
- Improves testability and code organization
- All tests passing
```

---

## Summary

Your Spectra App is functionally excellent, but the code organization needs improvement. The 6,916-line `main_window.py` should be broken into focused modules:

**Priority Order:**
1. ✅ Extract workers (easiest, high impact)
2. ✅ Extract dialogs (easy, good win)
3. ✅ Extract plot management (harder, highest impact)
4. ✅ Extract menus (easy, nice cleanup)
5. ✅ Create service adapters (advanced, best practices)

**Timeline:** 3-5 days of focused work, or do it incrementally over 2-3 weeks

**Result:** Professional, maintainable codebase that's easy to understand and extend

---

**Ready to start?** Pick Phase 1 (Extract Workers) and create the first file. Test after each change. Commit frequently. You've got this! 💪
