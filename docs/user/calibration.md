# Calibration

The Calibration tab in the Inspector lets you apply display-time adjustments without modifying your original data:

- Resolution matching (FWHM): enable and enter a target FWHM to approximate instrument resolution via a Gaussian blur.
- Radial velocity (km/s): shifts the wavelength axis by v/c to approximate Doppler effects.
- Frame: choose the target reference frame (observer or rest). Currently informational and reserved for future refinement.

Notes
- These transforms are applied to the plotted and tabulated data only; source spectra are not mutated.
- FWHM is interpreted in the current display axis units; for stability it’s applied internally in nanometers.
- Disable resolution matching by unchecking the Enable toggle.


Tips
- After changing settings, the plot and the Data Table will refresh automatically.
- Combine RV shift and resolution matching for quick comparison to line lists.

## Further reading
- [Atlas: calibration FWHM kernels](../atlas/README.md#calibration-fwhm-kernels)
