"""Tests for HDF5 importer."""

import pytest
import numpy as np
from pathlib import Path

try:
    import h5py
    HDF5_AVAILABLE = True
except ImportError:
    HDF5_AVAILABLE = False

from app.services.importers.hdf5_importer import Hdf5Importer


@pytest.mark.skipif(not HDF5_AVAILABLE, reason="h5py not installed")
def test_hdf5_importer_eureka_format(tmp_path):
    """Test importing Eureka! Stage 4 format HDF5 files."""
    # Create a mock Eureka! output file
    h5_path = tmp_path / "test_eureka.h5"
    
    wave = np.linspace(2.4, 4.2, 100)  # microns
    flux = np.random.normal(1.0, 0.01, (50, 100))  # 50 time steps, 100 wavelengths
    errors = np.random.normal(0.001, 0.0001, (50, 100))
    
    with h5py.File(h5_path, "w") as f:
        f.create_dataset("wavelength", data=wave)
        f.create_dataset("spectrum", data=flux)
        f.create_dataset("errors", data=errors)
    
    # Import
    importer = Hdf5Importer()
    assert importer.can_import(h5_path)
    
    result = importer.read(h5_path)
    
    # Check results
    assert result.x_unit == "µm"
    assert result.y_unit == "intensity"
    assert len(result.x) == 100
    assert len(result.y) == 100
    assert "uncertainty" in result.metadata
    assert len(result.metadata["uncertainty"]) == 100
    assert "Eureka" in result.metadata.get("format", "")


@pytest.mark.skipif(not HDF5_AVAILABLE, reason="h5py not installed")
def test_hdf5_importer_generic_format(tmp_path):
    """Test importing generic wavelength/flux HDF5 files."""
    h5_path = tmp_path / "test_generic.h5"
    
    wave = np.linspace(400, 700, 50)  # nm
    flux = np.random.normal(1.0, 0.1, 50)
    
    with h5py.File(h5_path, "w") as f:
        f.create_dataset("wavelength", data=wave)
        f.create_dataset("flux", data=flux)
    
    # Import
    importer = Hdf5Importer()
    assert importer.can_import(h5_path)
    
    result = importer.read(h5_path)
    
    # Check results
    assert result.x_unit == "nm"  # Should detect nm range
    assert result.y_unit == "intensity"
    assert len(result.x) == 50
    assert len(result.y) == 50


@pytest.mark.skipif(not HDF5_AVAILABLE, reason="h5py not installed")
def test_hdf5_importer_rejects_non_hdf5(tmp_path):
    """Test that importer rejects non-HDF5 files."""
    txt_path = tmp_path / "test.txt"
    txt_path.write_text("not an hdf5 file")
    
    importer = Hdf5Importer()
    assert not importer.can_import(txt_path)


@pytest.mark.skipif(not HDF5_AVAILABLE, reason="h5py not installed")
def test_hdf5_importer_handles_2d_flux(tmp_path):
    """Test that importer correctly handles 2D flux arrays."""
    h5_path = tmp_path / "test_2d.h5"
    
    wave = np.linspace(2.0, 5.0, 200)
    flux_2d = np.random.normal(1.0, 0.01, (10, 200))  # 10 exposures
    
    with h5py.File(h5_path, "w") as f:
        f.create_dataset("wave", data=wave)
        f.create_dataset("data", data=flux_2d)
    
    # Import
    importer = Hdf5Importer()
    result = importer.read(h5_path)
    
    # Should collapse to 1D via median
    assert result.y.ndim == 1
    assert len(result.y) == 200


def test_hdf5_importer_graceful_when_h5py_missing():
    """Test that importer fails gracefully when h5py is not installed."""
    if HDF5_AVAILABLE:
        pytest.skip("h5py is installed, cannot test missing dependency")
    
    importer = Hdf5Importer()
    test_path = Path("test.h5")
    
    # Should return False for can_import
    assert not importer.can_import(test_path)
    
    # Should raise helpful error for read
    with pytest.raises(ImportError, match="h5py is required"):
        importer.read(test_path)
