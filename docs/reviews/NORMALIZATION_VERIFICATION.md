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
   - New checkbox widget and persistence in user settings.

2. **New Method: `_compute_global_normalization_value()`**:
   - Iterates through all spectra and returns a single normalization value to apply to each.

3. **Updated `_refresh_plot()`**:
   - Checks if global normalization is enabled and applies the global value when computing display arrays.

4. **Updated `_apply_normalization()`**:
   - Accepts an optional global value; if present, uses it instead of per-spectrum maxima.

## Testing

- Added `test_global_normalization.py` (manual script) to validate that both small and large spectra remain visible when Global is enabled.
- Visual confirmation steps are in the test script; unit tests assert that normalisation factors are computed as expected in edge cases.

## Notes

- The Global toggle is intentionally simple: it uses the maximum peak across loaded overlays as the normalization denominator. Future refinements could use robust estimators (99th percentile) to ignore outliers.
- This change preserves the per-spectrum mode for shape comparison while enabling relative intensity comparisons when needed.
