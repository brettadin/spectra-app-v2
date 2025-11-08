# Working with MODIS HDF4 Files

## Quick Start (No Extra Installation!)

**Use the CSV file instead:**
- Your mock CSV (`samples/solar_system/earth/mock_MODIS_reflectance_sample.csv`) works right now
- Just open it in the app: File → Open → select the CSV
- You'll get the same 7-point reflectance spectrum

The CSV file contains the same data structure the HDF importer would produce, so you can test and compare your spectra immediately.

## Why Can't We Just "Install It In Code"?

`pyhdf` is a Python wrapper around **compiled C libraries** (binary DLLs). These binary files:
- Are platform-specific (Windows/Mac/Linux)
- Can't be bundled as Python code
- Need to match your system architecture

The PyPI version of `pyhdf` is just the Python wrapper—it doesn't include the actual HDF4 DLLs on Windows.

## If You Really Want Native HDF4 Support

### Option 1: Use Conda (Adds Binary Libraries)

If you have Anaconda or Miniconda installed:

```powershell
conda install -c conda-forge pyhdf
```

This version includes the HDF4 binary libraries and will work immediately.

### Option 2: Build from Source (Advanced)

1. Download HDF4 libraries from https://portal.hdfgroup.org/display/support/Download+HDF4
2. Install a C compiler (Visual Studio Build Tools or MinGW)
3. Build `pyhdf` from source with the HDF4 path configured
4. This is complex and not recommended for most users.

### Option 3: Use GDAL with HDF4 Support

Install GDAL with HDF4 driver (also requires conda):

```bash
conda install -c conda-forge gdal
```

The MODIS importer will automatically fall back to GDAL if `pyhdf` is unavailable.

### Option 4: Pre-process to CSV (Workaround)

If you cannot install conda/pyhdf, you can:

1. Use NASA's Panoply tool (free, Java-based) to open the HDF file
2. Export each band (sur_refl_b01..b07) as CSV
3. Manually combine into a single CSV with wavelength column
4. Import the CSV into Spectra App

Or use the mock CSV we generated for testing.

## Verification

After installation, verify HDF4 support works:

```python
from pyhdf.SD import SD, SDC
print("HDF4 support available!")
```

If this runs without error, you're good to go.

## For Development

For CI/testing environments where HDF4 is optional, the importer gracefully falls back and provides clear error messages. Mock data can be used for unit tests.
