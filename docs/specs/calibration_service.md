# Calibration Service (v0)

Purpose: provide display-time transforms for spectra to support apples-to-apples comparison without mutating cached data.

What it does now:
- Radial velocity (RV) shift: apply a small Doppler shift to the x-axis (wavelength) using non-relativistic factor `(1 + v/c)`.
- Frame toggle: prepare for observer/rest frame conversions via RV factor reuse.
- Resolution matching: approximate convolution to a target FWHM using a Gaussian kernel (σ derived from FWHM).
- Uncertainty handling: propagate σ through the same convolution (approximate; independent Gaussian errors assumption).

Non-goals in v0:
- High-accuracy line-spread functions per instrument
- Blaze-function correction and full spectrophotometric calibration
- Pipelines that fetch bias/dark/flat frames

## API

```
from app.services.calibration_service import CalibrationService, CalibrationConfig

svc = CalibrationService(CalibrationConfig(target_fwhm=2.0, rv_kms=-12.3, frame='observer'))
X2, Y2, S2, meta = svc.apply(x, y, sigma)
```

- Inputs: array-like `x`, `y`, optional `sigma`
- Config:
  - `target_fwhm: float | None` – desired resolution in current x-units
  - `rv_kms: float` – radial velocity in km/s (positive = receding)
  - `frame: 'observer'|'rest'`
- Output: transformed `(x, y, sigma, meta)` where `meta` records which steps were applied

If `numpy` is unavailable, `apply` is a no-op and returns inputs unchanged with a warning in `meta`.

## UI Sketch (dock)

- Non-dismissable banner: explain transforms are view-only and captured in provenance
- Controls:
  - Target resolution (FWHM) [spin] in current x-units
  - Radial velocity [spin, km/s], frame toggle (observer/rest)
  - Preview actions: Apply to visible / Reset

The dock can land in the Inspector; wiring uses small signals to update the plot on change, similar to the Reference dock.

## Next steps

- Add a minimal Inspector dock to surface the three controls
- Integrate with plot redraws and provenance metadata
- Add unit tests around `apply` behaviour (happy path + edge cases)
