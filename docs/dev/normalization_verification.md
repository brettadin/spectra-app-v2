# Normalization Feature Verification

## Issue Reported
User reported that with multiple spectra having vastly different intensity scales, normalization changes the Y-axis but smaller spectra become invisible because each is normalized independently.

## Investigation Results

### Original Behavior (Per-Spectrum Normalization)
- Each spectrum normalized to its own maximum
- Problem: Spectra with small absolute values remain tiny even after normalization
- Example: Spectrum with max=100 and spectrum with max=0.01 both normalize to max=1.0, but visually appear same relative size

### Root Cause
**Per-spectrum normalization** meant that when overlaying spectra with vastly different magnitudes:
- Large spectrum (max=100) → normalized to 1.0
- Small spectrum (max=0.01) → also normalized to 1.0
- But visually, both fill the plot equally, making comparison difficult

## Solution: Global Normalization Toggle

### New Feature: "Global" Checkbox
Added a checkbox next to the Normalize dropdown that controls normalization mode:

- **Unchecked (Per-Spectrum)**: Default behavior, each spectrum normalized independently
  - Best for: Comparing shapes of spectra with different scales
  - Each spectrum's peak reaches Y=1.0

- **Checked (Global)**: All spectra normalized relative to the highest peak across ALL spectra
  - Best for: Comparing relative intensities across spectra
  - Only the brightest spectrum's peak reaches Y=1.0
  - Smaller spectra scale proportionally and remain visible

### UI Changes

**Plot Toolbar** now shows:
```
Normalize: [None/Max/Area ▼]  [☐ Global]
```

**Tooltip**: "When checked, normalize all spectra together. When unchecked, normalize each spectrum independently."

## Implementation Details

### Code Changes

1. **Added Global Checkbox** (`app/ui/main_window.py`):
   ```python
   self.norm_global_checkbox = QtWidgets.QCheckBox("Global")
   self.norm_global_checkbox.setChecked(False)  # Per-spectrum by default
   ```

2. **New Method: `_compute_global_normalization_value()`**:
   - Iterates through all spectra
   - Computes global max or global total area
   - Returns single normalization value for all spectra

3. **Updated `_refresh_plot()`**:
   - Checks if global normalization is enabled
   - Computes global value once if needed
   - Passes to `_apply_normalization()` for each spectrum

4. **Updated `_apply_normalization()`**:
   - Now accepts optional `global_value` parameter
   - Uses global value if provided, otherwise computes per-spectrum
   - Computes scales on finite samples only (ignores NaNs/Infs)

5. **Updated `_add_spectrum()`**:
   - Triggers full plot refresh when adding spectrum with global norm enabled
   - Ensures all spectra rescale together

### Enhanced Autoscale

Also improved `autoscale()` in `plot_pane.py`:
```python
def autoscale(self) -> None:
    """Autoscale the plot to fit all visible data."""
    try:
        self._plot.enableAutoRange(axis=pg.ViewBox.XYAxes, enable=True)
        self._plot.autoRange()  # Force immediate autoscale
    except Exception:
        pass
```

## Expected Behavior

### Example Scenario (from user's screenshots):

**Setup**: 5 spectra overlaid
- "Test Spectrum": max ≈ 2.5
- 4 HD spectra: max ≈ 0.001 (much smaller)

**Without Global (Per-Spectrum)**:
- Set Normalize to "Max"
- Test Spectrum peak → Y=1.0
- Each HD spectrum peak → Y=1.0 (but invisible due to downsampling/scale)
- Y-axis: 0 to 1
- **Problem**: Can't see the HD spectra

**With Global (Checked)**:
- Set Normalize to "Max", check "Global"
- Test Spectrum peak → Y=1.0
- HD spectra peaks → Y=0.0004 (scaled by 0.001/2.5)
- Y-axis: 0 to 1
- **Solution**: HD spectra become visible as thin lines near the bottom!

### Y-scale transforms (post-normalization)

After normalization, apply Y-scale to improve visibility without changing data:

- Linear: identity
- Log10: signed log, `sign(y)*log10(1+|y|)` (handles zeros/negatives)
- Asinh: `arcsinh(y)` (linear near 0, ~log at large |y|)

These are view-only and affect plotting only, not exports.

## Testing

### Manual Test
Run the test script:
```bash
python test_global_normalization.py
```

This creates two spectra with 100:1 intensity ratio and demonstrates:
---
title: Normalization Feature Verification [Moved]
status: moved
date: 2025-11-04
canonical: ./docs/reviews/NORMALIZATION_VERIFICATION.md
---

# This page has moved

The canonical, reviewed copy is now at:

- `docs/reviews/NORMALIZATION_VERIFICATION.md`

Please update links to the new location; this stub preserves the old path while directing readers to the canonical doc.
 - NaN/Inf samples are ignored when computing scales (FITS robustness)
