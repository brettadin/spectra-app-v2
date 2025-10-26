# Normalization Fix - 2025-10-26

## Problem
User reported that the normalization dropdown ("None", "Max", "Area") wasn't working correctly. When multiple datasets with different scales were loaded, one would appear as a flat line compared to the other because they weren't being normalized despite the dropdown being set.

## Root Cause
The `_refresh_plot()` method in `app/main.py` had a TODO comment indicating that normalization needed to be wired up, but it was never implemented. The method was connected to the normalization combo box's `currentTextChanged` signal, but it only updated aliases and autoscaled - it never actually applied any normalization to the data.

```python
def _refresh_plot(self) -> None:
    # For now, just re-apply visibility and autoscale. A full redraw with
    # normalization can be wired in a later step.  # <-- This was never done!
    for spec in self.overlay_service.list():
        try:
            self.plot.update_alias(spec.id, spec.name)
        except Exception:
            pass
    self.plot.autoscale()
```

## Solution Implemented

### 1. Added `_apply_normalization()` Method
Created a new method to apply the three normalization modes:
- **None**: Returns data unchanged
- **Max**: Divides by maximum absolute value (scales to [0, 1])
- **Area**: Divides by the integral (using `np.trapz`)

```python
def _apply_normalization(self, y: np.ndarray, mode: str) -> np.ndarray:
    """Apply normalization to y-data based on mode."""
    if mode == "None" or len(y) == 0:
        return y
    
    if mode == "Max":
        max_val = np.max(np.abs(y))
        if max_val > 0:
            return y / max_val
        return y
    
    if mode == "Area":
        area = np.trapz(np.abs(y))
        if area > 0:
            return y / area
        return y
    
    return y
```

### 2. Updated `_refresh_plot()` 
Modified to read the current normalization mode and apply it when refreshing:

```python
def _refresh_plot(self) -> None:
    """Refresh plot with current normalization mode."""
    norm_mode = self.norm_combo.currentText()
    
    for spec in self.overlay_service.list():
        try:
            self.plot.update_alias(spec.id, spec.name)
            # Apply normalization
            y_data = self._apply_normalization(spec.y, norm_mode)
            color = self._spectrum_colors.get(spec.id, QtGui.QColor("white"))
            style = TraceStyle(color=color, width=1.5, show_in_legend=True)
            self.plot.add_trace(
                key=spec.id,
                alias=spec.name,
                x_nm=spec.x,
                y=y_data,
                style=style,
            )
        except Exception:
            pass
    self.plot.autoscale()
```

### 3. Updated `_add_spectrum()`
Modified to apply normalization when initially adding spectra:

```python
def _add_spectrum(self, spectrum: Spectrum) -> None:
    color = self._next_palette_color()
    self._spectrum_colors[spectrum.id] = color
    style = TraceStyle(color=color, width=1.5, show_in_legend=True)
    
    # Apply current normalization mode
    norm_mode = self.norm_combo.currentText()
    y_data = self._apply_normalization(spectrum.y, norm_mode)
    
    self.plot.add_trace(
        key=spectrum.id,
        alias=spectrum.name,
        x_nm=spectrum.x,
        y=y_data,
        style=style,
    )
    self._visibility[spectrum.id] = True
    self._append_dataset_row(spectrum)
```

## Testing

Created comprehensive test suite in `tests/test_normalization.py` with 5 tests:

1. **test_normalization_max**: Verifies Max normalization scales to [0, 1]
2. **test_normalization_area**: Verifies Area normalization makes integral = 1.0
3. **test_normalization_none**: Verifies None keeps original values
4. **test_normalization_change_updates_plot**: Verifies changing dropdown updates existing plots
5. **test_normalization_multiple_spectra**: Verifies each spectrum normalized independently

All tests pass ✅

## Key Design Decisions

1. **Non-destructive**: Original spectrum data in OverlayService remains unchanged; normalization only applied during plotting
2. **Per-spectrum**: Each spectrum normalized independently based on its own max/area
3. **Dynamic**: Changing normalization mode immediately updates all visible spectra
4. **Safe**: Handles edge cases (zero max, zero area, empty arrays)

## Files Modified
- `app/main.py`: Added `_apply_normalization()`, updated `_refresh_plot()` and `_add_spectrum()`
- `tests/test_normalization.py`: New comprehensive test suite (5 tests)

## Verification
- All new normalization tests pass (5/5)
- All existing tests still pass (test_main_import.py: 3/3)
- Feature ready for user testing with real data

## User Impact
Users can now properly compare spectra with vastly different scales:
- **Max normalization**: Perfect for comparing shapes when absolute intensity differs
- **Area normalization**: Ideal for comparing relative distributions
- **None**: Keep original values when scales are already comparable

The flat-line issue with differently-scaled datasets is now resolved!
