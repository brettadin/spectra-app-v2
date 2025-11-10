"""Tests for PDS3 label parser."""

from pathlib import Path

import pytest

from app.services.pds_label_parser import parse_pds_label, PDSLabel


@pytest.fixture
def sample_dir() -> Path:
    """Path to sample data directory."""
    return Path(__file__).parent.parent / "samples" / "solar_system"


def test_parse_1995high_label(sample_dir: Path):
    """Test parsing 1995high.lbl (Jupiter, Saturn, Uranus spectra)."""
    label_path = sample_dir / "1995high.lbl"
    if not label_path.exists():
        pytest.skip("Sample file not found")
    
    label = parse_pds_label(label_path)
    assert label is not None
    
    # Check basic metadata
    assert label.version_id == "PDS3"
    assert "1995high.tab" in label.data_file.lower()
    assert label.rows == 4750
    assert label.row_bytes == 42
    
    # Check targets
    assert len(label.target_names) == 3
    assert "Jupiter" in label.target_names
    assert "Saturn" in label.target_names
    assert "Uranus" in label.target_names
    
    # Check columns
    assert len(label.columns) == 6
    assert label.columns[0].name == "VACUUM WAVELENGTH"
    assert label.columns[1].name == "AIR WAVELENGTH"
    assert label.columns[2].name == "METHANE ABSORPTION COEFFICIENT"
    assert label.columns[3].name == "JUPITER ALBEDO"
    assert label.columns[4].name == "SATURN ALBEDO"
    assert label.columns[5].name == "URANUS ALBEDO"
    
    # Check units
    assert label.columns[0].unit == "NANOMETER"
    assert label.columns[3].unit is None  # I/F not captured as unit
    
    # Check wavelength detection
    wavelength_col = label.get_wavelength_column()
    assert wavelength_col is not None
    assert wavelength_col.name == "AIR WAVELENGTH"  # Should prefer air over vacuum
    
    # Check target column extraction
    target_cols = label.get_target_columns()
    assert len(target_cols) == 3
    names = [name for name, _ in target_cols]
    assert "Jupiter" in names
    assert "Saturn" in names
    assert "Uranus" in names


def test_parse_1995low_label(sample_dir: Path):
    """Test parsing 1995low.lbl (adds Neptune and Titan)."""
    label_path = sample_dir / "1995low.lbl"
    if not label_path.exists():
        pytest.skip("Sample file not found")
    
    label = parse_pds_label(label_path)
    assert label is not None
    
    # Check basic metadata
    assert label.version_id == "PDS3"
    assert "1995low.tab" in label.data_file.lower()
    assert label.rows == 1875
    
    # Should have 5 targets
    target_cols = label.get_target_columns()
    assert len(target_cols) >= 5  # Neptune and Titan added
    names = [name for name, _ in target_cols]
    assert "Neptune" in names or "Titan" in names


def test_wavelength_column_preference():
    """Test that air wavelength is preferred over vacuum."""
    from app.services.pds_label_parser import PDSColumn, PDSLabel
    
    columns = [
        PDSColumn("VACUUM WAVELENGTH", 1, "nm", "REAL", 1, 10, "F10.4", ""),
        PDSColumn("AIR WAVELENGTH", 2, "nm", "REAL", 11, 10, "F10.4", ""),
        PDSColumn("FLUX", 3, "W/m^2", "REAL", 21, 10, "F10.4", ""),
    ]
    
    label = PDSLabel(
        version_id="PDS3",
        data_file="test.tab",
        target_names=["Test"],
        instrument_name="TEST",
        instrument_host="TEST",
        start_time=None,
        stop_time=None,
        product_name="Test",
        note=None,
        columns=columns,
        rows=100,
        row_bytes=30,
    )
    
    wl = label.get_wavelength_column()
    assert wl is not None
    assert wl.name == "AIR WAVELENGTH"


def test_target_column_filtering():
    """Test that wavelength and absorption columns are filtered out."""
    from app.services.pds_label_parser import PDSColumn, PDSLabel
    
    columns = [
        PDSColumn("WAVELENGTH", 1, "nm", "REAL", 1, 10, "F10.4", ""),
        PDSColumn("METHANE ABSORPTION", 2, None, "REAL", 11, 10, "F10.4", ""),
        PDSColumn("JUPITER ALBEDO", 3, "I/F", "REAL", 21, 10, "F10.4", ""),
        PDSColumn("SATURN ALBEDO", 4, "I/F", "REAL", 31, 10, "F10.4", ""),
    ]
    
    label = PDSLabel(
        version_id="PDS3",
        data_file="test.tab",
        target_names=["Jupiter", "Saturn"],
        instrument_name="TEST",
        instrument_host="TEST",
        start_time=None,
        stop_time=None,
        product_name="Test",
        note=None,
        columns=columns,
        rows=100,
        row_bytes=40,
    )
    
    target_cols = label.get_target_columns()
    assert len(target_cols) == 2
    names = [name for name, _ in target_cols]
    assert "Jupiter" in names
    assert "Saturn" in names
    # Wavelength and absorption should be excluded
    assert "Wavelength" not in names
    assert "Methane" not in names


def test_invalid_label_returns_none(tmp_path: Path):
    """Test that non-PDS files return None."""
    # Create a non-PDS file
    not_pds = tmp_path / "not_pds.txt"
    not_pds.write_text("This is not a PDS file\n")
    
    label = parse_pds_label(not_pds)
    assert label is None


def test_missing_file_returns_none(tmp_path: Path):
    """Test that missing files return None."""
    missing = tmp_path / "does_not_exist.lbl"
    label = parse_pds_label(missing)
    assert label is None
