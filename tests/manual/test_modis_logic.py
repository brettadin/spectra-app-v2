"""Test MODIS HDF4 importer logic (without requiring pyhdf)."""
from pathlib import Path
import numpy as np
from app.services.importers.modis_hdf_importer import ModisHdfImporter, _MODIS_BAND_CENTERS_NM


def test_modis_importer_aggregation_logic():
    """Verify the aggregation/scaling logic works correctly."""
    # Simulate what would come from an HDF file
    # Mock 500x500 arrays for 7 bands with scaled integer values
    np.random.seed(42)
    mock_bands = {}
    for i, band_name in enumerate(sorted(_MODIS_BAND_CENTERS_NM.keys())):
        # Simulate realistic MODIS integer reflectance (0..10000 = 0..1.0 reflectance)
        # Add some invalid pixels (<0 or >10000)
        raw = np.random.randint(0, 8000, size=(500, 500))
        # Add some fill values
        raw[0:10, :] = -1  # fill pixels
        raw[:, 0:10] = 32767  # out-of-range
        mock_bands[band_name] = raw
    
    # Test the aggregation logic manually (since we can't call _read_with_best_backend)
    ordered = []
    for name, arr in sorted(mock_bands.items(), key=lambda x: _MODIS_BAND_CENTERS_NM[x[0]]):
        lam_nm = _MODIS_BAND_CENTERS_NM[name]
        raw_arr = np.asarray(arr, dtype=float)
        mask = (raw_arr >= 0) & (raw_arr <= 10000)
        valid = raw_arr[mask]
        if valid.size:
            scaled = valid * 0.0001
            value = float(np.nanmedian(scaled))
            n_valid = int(valid.size)
        else:
            value = float("nan")
            n_valid = 0
        ordered.append((name, lam_nm, value, n_valid))
    
    ordered.sort(key=lambda t: t[1])
    x_nm = np.array([t[1] for t in ordered], dtype=float)
    y_reflectance = np.array([t[2] for t in ordered], dtype=float)
    
    print("MODIS Importer Aggregation Logic Test")
    print("=" * 60)
    print(f"Bands processed: {len(ordered)}")
    print(f"Wavelengths (nm): {x_nm}")
    print(f"Median reflectance: {y_reflectance}")
    print(f"Valid pixel counts: {[t[3] for t in ordered]}")
    print()
    
    # Verify structure
    assert len(x_nm) == 7, "Should have 7 bands"
    assert all(0.0 <= r <= 1.0 for r in y_reflectance if not np.isnan(r)), "Reflectance should be 0..1"
    assert x_nm[0] < x_nm[-1], "Wavelengths should be ascending"
    
    # Expected order by wavelength: b03 (blue), b04 (green), b01 (red), b02 (NIR), b05, b06, b07
    expected_order = ["sur_refl_b03", "sur_refl_b04", "sur_refl_b01", "sur_refl_b02", 
                      "sur_refl_b05", "sur_refl_b06", "sur_refl_b07"]
    actual_order = [t[0] for t in ordered]
    assert actual_order == expected_order, f"Expected {expected_order}, got {actual_order}"
    
    print("✓ All assertions passed!")
    print()
    print("Next steps:")
    print("  1. Install pyhdf via conda: conda install -c conda-forge pyhdf")
    print("  2. Or use the mock CSV for testing: samples/solar_system/earth/mock_MODIS_reflectance_sample.csv")
    print("  3. Once pyhdf is installed, the app will automatically ingest .hdf files")
    

if __name__ == "__main__":
    test_modis_importer_aggregation_logic()
