"""Extract MODIS HDF4 reflectance to CSV without requiring pyhdf.

This script attempts multiple extraction methods:
1. Using h5py (works for some HDF formats)
2. Using GDAL if available
3. Instructions for manual extraction with Panoply

Run this script and it will tell you the best approach for your system.
"""
from pathlib import Path
import sys

hdf_path = Path(r"c:\Code\spectra-app-v2\samples\solar_system\earth\MOD09.A2025305.1535.061.2025307155046.hdf")
output_csv = Path(r"c:\Code\spectra-app-v2\samples\solar_system\earth\earth_modis_extracted.csv")

# Band center wavelengths (nm)
BAND_CENTERS = {
    "sur_refl_b01": 645.0,
    "sur_refl_b02": 858.5,
    "sur_refl_b03": 469.0,
    "sur_refl_b04": 555.0,
    "sur_refl_b05": 1240.0,
    "sur_refl_b06": 1640.0,
    "sur_refl_b07": 2130.0,
}

print("=" * 70)
print("MODIS HDF4 Data Extractor")
print("=" * 70)
print(f"Input file: {hdf_path.name}")
print(f"Output CSV: {output_csv.name}")
print()

if not hdf_path.exists():
    print(f"ERROR: File not found: {hdf_path}")
    sys.exit(1)

# Try Method 1: GDAL
print("Method 1: Trying GDAL...")
try:
    from osgeo import gdal
    gdal.UseExceptions()
    
    ds = gdal.Open(str(hdf_path))
    if ds is None:
        raise RuntimeError("GDAL couldn't open file")
    
    subdatasets = ds.GetSubDatasets()
    print(f"  ✓ GDAL opened file successfully!")
    print(f"  Found {len(subdatasets)} subdatasets")
    
    # Extract reflectance bands
    import numpy as np
    bands_data = {}
    
    for name, desc in subdatasets:
        for band_name in BAND_CENTERS.keys():
            if band_name in name:
                print(f"  Reading {band_name}...")
                sub = gdal.Open(name)
                if sub:
                    arr = sub.ReadAsArray()
                    # Mask invalid values and scale
                    mask = (arr >= 0) & (arr <= 10000)
                    valid = arr[mask]
                    if valid.size:
                        scaled = valid * 0.0001
                        median_value = float(np.nanmedian(scaled))
                        bands_data[band_name] = median_value
                        print(f"    → Median reflectance: {median_value:.4f}")
    
    if bands_data:
        # Sort by wavelength and write CSV
        sorted_bands = sorted(bands_data.items(), key=lambda x: BAND_CENTERS[x[0]])
        
        with open(output_csv, 'w') as f:
            f.write("wavelength_nm,reflectance\n")
            for band_name, value in sorted_bands:
                wavelength = BAND_CENTERS[band_name]
                f.write(f"{wavelength},{value}\n")
        
        print()
        print("=" * 70)
        print(f"SUCCESS! Extracted data to: {output_csv}")
        print("=" * 70)
        print("You can now open this CSV in your Spectra app!")
        sys.exit(0)
    
except Exception as e:
    print(f"  ✗ GDAL failed: {e}")
    print()

# Try Method 2: h5py (unlikely to work for HDF4, but worth trying)
print("Method 2: Trying h5py...")
try:
    import h5py
    import numpy as np
    
    with h5py.File(hdf_path, 'r') as f:
        print(f"  ✓ h5py opened file!")
        print(f"  Keys: {list(f.keys())}")
        # HDF4 files usually won't work with h5py, but we try anyway
        
except Exception as e:
    print(f"  ✗ h5py failed: {e}")
    print()

# If we get here, neither worked
print("=" * 70)
print("MANUAL EXTRACTION NEEDED")
print("=" * 70)
print()
print("Neither GDAL nor h5py could read this HDF4 file.")
print()
print("Option A: Install conda and pyhdf")
print("-" * 70)
print("  1. Download Miniconda: https://docs.conda.io/en/latest/miniconda.html")
print("  2. Install pyhdf: conda install -c conda-forge pyhdf")
print("  3. Restart your app - the HDF file will open directly")
print()
print("Option B: Use NASA's Panoply tool (Easier!)")
print("-" * 70)
print("  1. Download: https://www.giss.nasa.gov/tools/panoply/download/")
print("  2. Open your HDF file in Panoply")
print("  3. For each band (sur_refl_b01 to sur_refl_b07):")
print("     - Right-click the dataset")
print("     - Export → CSV")
print("     - Note the median/mean value")
print("  4. Create a CSV like this:")
print()
print("     wavelength_nm,reflectance")
print("     469.0,<value_from_b03>")
print("     555.0,<value_from_b04>")
print("     645.0,<value_from_b01>")
print("     858.5,<value_from_b02>")
print("     1240.0,<value_from_b05>")
print("     1640.0,<value_from_b06>")
print("     2130.0,<value_from_b07>")
print()
print("Option C: Use the example CSV (for now)")
print("-" * 70)
print("  The example CSV already loaded in your app contains")
print("  realistic MODIS-style reflectance values you can use")
print("  for testing and comparison.")
print()
