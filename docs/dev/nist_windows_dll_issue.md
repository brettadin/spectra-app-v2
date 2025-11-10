# NIST Spectral Lines Fetching - Known Issues & Workarounds

## Issue: Windows DLL Crash (Error code 0xc06d007f)

### Problem
When fetching NIST spectral lines for most elements (except Hydrogen), the app fails with an "empty-output" error. The underlying cause is a Windows-specific native crash in the astropy library during coordinate transformation imports.

### Error Details
```
Windows fatal exception: code 0xc06d007f
astropy.coordinates.builtin_frames.icrs_fk5_transforms.py
```

This is a known issue with certain astropy/numpy/ERFA binary builds on Windows.

### Current Workaround

The app automatically falls back to built-in line lists for common elements when both the subprocess query and HTTP query fail. The following elements have built-in approximate line lists:

- **H** (Hydrogen): Balmer series (Hα, Hβ, Hγ, Hδ)
- **He** (Helium): Neutral He I lines
- **Na** (Sodium): D-lines
- **Fe** (Iron): Bright Fe I lines
- **Ca** (Calcium): H & K lines
- **Mg** (Magnesium): Triplet
- **O** (Oxygen): OI lines
- **N** (Nitrogen): NI lines

### User Impact

1. **Elements with built-in data**: Will display approximate lines even when NIST server is unavailable
2. **Other elements**: Will show an error message explaining the issue
3. **All cases**: Error messages now provide helpful guidance

### Future Solutions

#### Option 1: Fix astropy Installation
Try reinstalling astropy with compatible binaries:
```bash
conda uninstall astropy astroquery
conda install -c conda-forge astropy astroquery
```

#### Option 2: Use Alternative Python Environment
The crash is environment-specific. Creating a fresh conda environment may resolve it:
```bash
conda create -n spectra-fix python=3.11
conda activate spectra-fix
conda install astropy astroquery numpy scipy
```

#### Option 3: Expand Built-in Line Lists
Add more elements to `app/services/nist_http_fallback.py` in the `_BUILTIN_LINES` dictionary. Values should be vacuum wavelengths in nm with approximate relative intensities.

## Testing

To test if NIST fetching works in your environment:

```python
from app.services import nist_subprocess

result = nist_subprocess.safe_fetch(
    identifier="Fe",
    element="Fe",
    lower=400,
    upper=500,
    wavelength_unit="nm",
    wavelength_type="vacuum",
    use_ritz=True,
)

if "error" in result:
    print(f"Failed: {result.get('error')}: {result.get('message')}")
else:
    print(f"Success: {len(result.get('lines', []))} lines")
```

## Related Files

- **app/services/nist_subprocess.py**: Subprocess isolation for astropy crashes
- **app/services/nist_http_fallback.py**: HTTP fallback + built-in line lists
- **app/services/nist_asd_service.py**: Core NIST ASD query logic
- **app/ui/main_window.py**: UI integration with error handling

## Last Updated
November 10, 2025
