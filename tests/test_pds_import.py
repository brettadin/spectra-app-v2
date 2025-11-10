"""Tests for PDS3 multi-column table import via CSV importer."""

from pathlib import Path

import numpy as np
import pytest

from app.services.importers.csv_importer import CsvImporter
from app.services.data_ingest_service import DataIngestService
from app.services.units_service import UnitsService


@pytest.fixture
def sample_dir() -> Path:
    """Path to sample data directory."""
    return Path(__file__).parent.parent / "samples" / "solar_system"


@pytest.fixture
def ingest_service() -> DataIngestService:
    """Create a DataIngestService for testing."""
    units = UnitsService()
    return DataIngestService(units)


def test_pds_1995high_import(sample_dir: Path, ingest_service: DataIngestService):
    """Test importing 1995high.tab (Jupiter, Saturn, Uranus)."""
    tab_path = sample_dir / "1995high.tab"
    if not tab_path.exists():
        pytest.skip("Sample file not found")
    
    spectra = ingest_service.ingest(tab_path)
    
    # Should return 3 spectra (one per target)
    assert len(spectra) == 3
    
    # Check that we have Jupiter, Saturn, and Uranus
    names = [s.name for s in spectra]
    assert any("Jupiter" in name for name in names)
    assert any("Saturn" in name for name in names)
    assert any("Uranus" in name for name in names)
    
    # Check first spectrum (Jupiter)
    jupiter = spectra[0]
    assert jupiter.x_unit == "nm"
    assert "albedo" in jupiter.y_unit.lower()
    
    # Check wavelength range (should be ~520-995 nm)
    assert jupiter.x[0] >= 519
    assert jupiter.x[-1] <= 996
    assert len(jupiter.x) > 100  # Should have many data points
    
    # Check metadata
    assert "pds_label" in jupiter.metadata
    pds_meta = jupiter.metadata["pds_label"]
    assert "Jupiter" in pds_meta["targets"]
    assert "Saturn" in pds_meta["targets"]
    assert "Uranus" in pds_meta["targets"]
    assert pds_meta["instrument"] == "BOLLER & CHIVENS SPECTROGRAPH"


def test_pds_1995low_import(sample_dir: Path, ingest_service: DataIngestService):
    """Test importing 1995low.tab (adds Neptune and Titan)."""
    tab_path = sample_dir / "1995low.tab"
    if not tab_path.exists():
        pytest.skip("Sample file not found")
    
    spectra = ingest_service.ingest(tab_path)
    
    # Should return 5 spectra (Jupiter, Saturn, Uranus, Neptune, Titan)
    assert len(spectra) >= 5
    
    names = [s.name for s in spectra]
    assert any("Neptune" in name for name in names)
    assert any("Titan" in name for name in names)


def test_pds_importer_preserves_metadata(sample_dir: Path):
    """Test that PDS label metadata is correctly extracted."""
    tab_path = sample_dir / "1995high.tab"
    if not tab_path.exists():
        pytest.skip("Sample file not found")
    
    importer = CsvImporter()
    result = importer.read(tab_path)
    
    # Should detect PDS bundle format
    assert "bundle" in result.metadata
    assert result.metadata["bundle"]["format"] == "pds3-multi-target"
    
    # Should have PDS label metadata
    assert "pds_label" in result.metadata
    pds = result.metadata["pds_label"]
    assert pds["version"] == "PDS3"
    assert pds["instrument"] == "BOLLER & CHIVENS SPECTROGRAPH"
    assert pds["instrument_host"] == "EUROPEAN SOUTHERN OBSERVATORY"
    assert pds["start_time"] == "1995-07-06"
    assert pds["stop_time"] == "1995-07-10"


def test_non_pds_file_not_affected(tmp_path: Path):
    """Test that regular CSV files are not affected by PDS detection."""
    csv_path = tmp_path / "regular.tab"
    csv_path.write_text(
        """wavelength,intensity
400,0.5
500,0.6
600,0.7
""",
        encoding="utf-8",
    )
    
    importer = CsvImporter()
    result = importer.read(csv_path)
    
    # Should NOT have PDS bundle metadata
    bundle = result.metadata.get("bundle")
    assert bundle is None or bundle.get("format") != "pds3-multi-target"
    
    # Should still parse as regular CSV
    assert len(result.x) == 3
    assert np.isclose(result.x[0], 400.0)


def test_pds_wavelength_unit_detection(sample_dir: Path):
    """Test that wavelength units are correctly detected from PDS label."""
    tab_path = sample_dir / "1995high.tab"
    if not tab_path.exists():
        pytest.skip("Sample file not found")
    
    importer = CsvImporter()
    result = importer.read(tab_path)
    
    # 1995high uses NANOMETER unit
    assert result.x_unit == "nm"
    
    # First member should also have nm
    members = result.metadata["bundle"]["members"]
    assert members[0]["x_unit"] == "nm"
