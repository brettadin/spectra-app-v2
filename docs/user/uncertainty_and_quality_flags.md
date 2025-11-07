# Uncertainty and Quality Flag System

## Overview

The Spectra App now includes a comprehensive system for tracking **measurement uncertainties** and **data quality issues** throughout the analysis pipeline. This ensures scientifically rigorous error propagation and enables users to identify potentially problematic data points.

## Features

### 1. Uncertainty Propagation

Each spectrum can now include an **uncertainty array** (`sigma`) that represents the standard deviation or error for each data point. When you perform mathematical operations, uncertainties are propagated using standard error formulas:

#### Subtraction
For `C = A - B`:
```
σ_C = √(σ_A² + σ_B²)
```

#### Ratio
For `C = A / B`:
```
σ_C = |A/B| × √((σ_A/A)² + (σ_B/B)²)
```

#### Averaging
For `C = average(A₁, A₂, ..., Aₙ)`:
```
σ_C = σ_individual / √N
```

This assumes independent measurements with similar uncertainties.

### 2. Quality Flags

Each data point can be marked with **quality flags** that indicate potential issues. Flags are stored as 8-bit integers and can be combined using bitwise OR:

| Flag | Value | Description |
|------|-------|-------------|
| `GOOD` | 0x00 | No issues detected |
| `BAD_PIXEL` | 0x01 | Known bad/dead detector pixel |
| `COSMIC_RAY` | 0x02 | Cosmic ray hit detected |
| `SATURATED` | 0x04 | Detector saturation |
| `LOW_SNR` | 0x08 | Signal-to-noise ratio below threshold |
| `INTERPOLATED` | 0x10 | Value was interpolated from neighbors |
| `EXTRAPOLATED` | 0x20 | Value was extrapolated (beyond range) |
| `USER_FLAGGED` | 0x40 | Manually flagged by user |
| `QUESTIONABLE` | 0x80 | Automatically flagged as suspicious |

When operations combine spectra, quality flags are merged with bitwise OR, preserving all quality issues.

### 3. Interpolation Validation

When comparing spectra with different wavelength grids, the system automatically:
- Finds the overlapping wavelength range
- Chooses the finer grid as the interpolation target
- Uses linear interpolation (preserves data integrity)
- Warns if large gaps exist (>1.5× median spacing)

### 4. Plot UI Integration

- Error bars are drawn automatically when a spectrum carries uncertainty and the plot has a moderate number of points (≤ 5,000) for smooth interactivity.
- Quality flags are shown as small coloured markers along the bottom of the plot:
    - Red = BAD_PIXEL, Magenta = COSMIC_RAY, Orange = SATURATED, Gold = LOW_SNR
- Error bars are transformed with the current Y-scale when feasible:
    - Linear: exact
    - Log10 / Asinh: first-order derivative approximation for display scale
- Notes/limits:
    - For very large traces, error bars are suppressed to keep the UI responsive.
    - Flags are rendered as markers at the bottom to avoid obscuring data.
    - Calibration effects on uncertainty are not applied (assumed negligible or multiplicative).

## Usage Examples

### Creating a Spectrum with Uncertainty

```python
from app.services import Spectrum
import numpy as np

# Create spectrum with uncertainty data
x = np.array([400.0, 450.0, 500.0])
y = np.array([1.0, 2.0, 3.0])
sigma = np.array([0.1, 0.15, 0.12])  # Standard deviations

spectrum = Spectrum.create(
    name="Sample Data",
    x=x,
    y=y,
    x_unit="nm",
    y_unit="absorbance",
    uncertainty=sigma,
)
```

### Adding Quality Flags

```python
from app.services import Spectrum, QualityFlags
import numpy as np

# Mark specific data points with quality issues
flags = np.array([
    QualityFlags.GOOD,
    QualityFlags.LOW_SNR,
    QualityFlags.BAD_PIXEL | QualityFlags.COSMIC_RAY,  # Multiple flags
], dtype=np.uint8)

spectrum = Spectrum.create(
    name="Noisy Data",
    x=x,
    y=y,
    x_unit="nm",
    y_unit="absorbance",
    quality_flags=flags,
)
```

### Performing Math Operations

```python
from app.services import MathService, UnitsService

math_service = MathService(units_service=UnitsService())

# Subtract two spectra - uncertainties automatically propagated
result, meta = math_service.subtract(spectrum_a, spectrum_b)

# Access propagated uncertainty
if result.uncertainty is not None:
    print(f"Result uncertainty: {result.uncertainty}")

# Check combined quality flags
if result.quality_flags is not None:
    bad_points = result.quality_flags != QualityFlags.GOOD
    print(f"Flagged {bad_points.sum()} questionable data points")
```

### Checking for Specific Quality Issues

```python
# Find all saturated pixels
saturated_mask = (spectrum.quality_flags & QualityFlags.SATURATED) != 0

# Find any flagged points (excluding GOOD)
any_issues = spectrum.quality_flags != QualityFlags.GOOD

# Check if a specific point has multiple issues
point_flags = spectrum.quality_flags[10]
if point_flags & QualityFlags.COSMIC_RAY:
    print("Point affected by cosmic ray")
if point_flags & QualityFlags.LOW_SNR:
    print("Point has low signal-to-noise ratio")
```

## Best Practices

### 1. Always Include Uncertainty When Available
If your instrument provides error estimates, include them:
```python
# Good: Include measurement uncertainty
spectrum = Spectrum.create(..., uncertainty=instrument_errors)

# Acceptable: No uncertainty data available
spectrum = Spectrum.create(...)  # uncertainty defaults to None
```

### 2. Flag Known Issues Immediately
Mark problematic data points when loading data:
```python
flags = np.zeros(len(x), dtype=np.uint8)
flags[saturated_indices] = QualityFlags.SATURATED
flags[bad_pixel_indices] = QualityFlags.BAD_PIXEL

spectrum = Spectrum.create(..., quality_flags=flags)
```

### 3. Understand Linear Interpolation Limits
When comparing spectra with different wavelength ranges:
- Linear interpolation is accurate for smooth spectra
- Sharp features (emission lines) may be poorly sampled
- Large gaps trigger warnings automatically
- Consider resampling original data if possible

### 4. Propagated Uncertainties Are Conservative
The error propagation formulas assume:
- **Independent measurements** (no correlation)
- **Gaussian error distributions**
- **First-order approximations** (small relative errors)

For highly correlated data or large uncertainties, consult a statistician.

### 5. Quality Flags Are Advisory
Flags indicate **potential** issues but don't automatically exclude data:
- Review flagged points manually
- Document why specific points were flagged
- Consider the impact on your scientific conclusions

## Scientific Rationale

### Why Linear Interpolation?

We use `np.interp()` for wavelength alignment because:
1. **Preserves data integrity** - no arbitrary smoothing
2. **Widely accepted** in spectroscopy
3. **Fast and deterministic** - same result every time
4. **Conservative** - doesn't create artificial features

Alternative approaches (spline fitting, polynomial interpolation) can introduce artifacts or oscillations near sharp features.

### Why Propagate Uncertainties?

Error propagation is essential for:
- **Quantifying confidence** in derived results
- **Comparing measurements** fairly
- **Publication requirements** (many journals require error bars)
- **Quality control** during data processing

Without uncertainty tracking, you may:
- Over-interpret noise as signal
- Miss statistically insignificant differences
- Make scientifically unsupported claims

### Quality Flags vs. Data Removal

We use **flags** instead of removing bad data because:
- **Traceability** - you can see what was flagged and why
- **Reversibility** - you can change flagging criteria later
- **Transparency** - collaborators know which points are questionable
- **Flexibility** - different analyses may tolerate different issues

## Technical Details

### Data Structures

```python
@dataclass(frozen=True)
class Spectrum:
    x: np.ndarray              # Wavelength/frequency
    y: np.ndarray              # Intensity/flux
    uncertainty: np.ndarray | None = None     # Standard deviation (same shape as y)
    quality_flags: np.ndarray | None = None   # uint8 bit flags (same shape as y)
    # ... other fields
```

### Uncertainty Interpolation

When aligning spectra, uncertainties are linearly interpolated just like the y-values:
```python
target_x = ...  # Common wavelength grid
sigma_interp = np.interp(target_x, original_x, original_sigma)
```

This is appropriate because uncertainty represents the *width* of the measurement distribution, which varies smoothly with wavelength.

### Quality Flag Interpolation

Quality flags use **nearest-neighbor** interpolation:
```python
indices = np.searchsorted(original_x, target_x)
flags_interp = original_flags[indices]
```

This prevents inappropriate averaging of discrete categories.

## Future Enhancements

Planned improvements include:
- [ ] **Error bar visualization** in plot pane
- [ ] **Flagged region highlighting** with color coding
- [ ] **SNR calculation** with automatic LOW_SNR flagging
- [ ] **Cosmic ray detection** algorithms
- [ ] **Manual flagging tools** in the UI
- [ ] **Uncertainty budget analysis** showing error sources
- [ ] **Weighted averaging** using uncertainties as weights

## References

- Bevington, P. R., & Robinson, D. K. (2003). *Data Reduction and Error Analysis for the Physical Sciences*. McGraw-Hill.
- Taylor, J. R. (1997). *An Introduction to Error Analysis*. University Science Books.
- Hughes, I., & Hase, T. (2010). *Measurements and their Uncertainties*. Oxford University Press.
