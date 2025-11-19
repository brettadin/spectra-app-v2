"""Test calibrated wavelength column support."""
from pathlib import Path
import pytest
from app.services.importers.csv_importer import CsvImporter


def test_calibrated_wavelength_preferred(tmp_path: Path) -> None:
    """CSV with wavelength_calibrated_nm should use calibrated values."""
    csv_path = tmp_path / "calibrated.csv"
    csv_path.write_text(
        "wavelength_nm,intensity,spectrum_id,spectrum_name,wavelength_calibrated_nm,x_unit,y_unit\n"
        "400.0,1.5,test1,Test Spectrum,398.5,nm,absorbance\n"
        "410.0,2.3,test1,Test Spectrum,408.3,nm,absorbance\n"
        "420.0,1.8,test1,Test Spectrum,418.2,nm,absorbance\n",
        encoding="utf-8"
    )
    
    importer = CsvImporter()
    result = importer.read(csv_path)
    
    # Should use calibrated wavelengths (398.5, 408.3, 418.2), not original (400, 410, 420)
    assert result.x[0] == pytest.approx(398.5)
    assert result.x[1] == pytest.approx(408.3)
    assert result.x[2] == pytest.approx(418.2)
    
    assert result.y[0] == pytest.approx(1.5)
    assert result.y[1] == pytest.approx(2.3)
    assert result.y[2] == pytest.approx(1.8)
    
    assert result.x_unit == "nm"
    assert result.y_unit == "absorbance"
    assert result.name == "Test Spectrum"


def test_fallback_to_original_wavelength(tmp_path: Path) -> None:
    """CSV without wavelength_calibrated_nm should use wavelength_nm."""
    csv_path = tmp_path / "original.csv"
    csv_path.write_text(
        "wavelength_nm,intensity,spectrum_id,spectrum_name,x_unit,y_unit\n"
        "400.0,1.5,test1,Test Spectrum,nm,absorbance\n"
        "410.0,2.3,test1,Test Spectrum,nm,absorbance\n"
        "420.0,1.8,test1,Test Spectrum,nm,absorbance\n",
        encoding="utf-8"
    )
    
    importer = CsvImporter()
    result = importer.read(csv_path)
    
    # Should use original wavelengths
    assert result.x[0] == pytest.approx(400.0)
    assert result.x[1] == pytest.approx(410.0)
    assert result.x[2] == pytest.approx(420.0)
    
    assert result.y[0] == pytest.approx(1.5)
    assert result.name == "Test Spectrum"


def test_multiple_spectra_with_calibration(tmp_path: Path) -> None:
    """Bundle with multiple spectra should handle calibrated wavelengths correctly."""
    csv_path = tmp_path / "multi_calibrated.csv"
    csv_path.write_text(
        "wavelength_nm,intensity,spectrum_id,spectrum_name,wavelength_calibrated_nm,x_unit,y_unit\n"
        "400.0,1.5,lamp1,Lamp A,398.5,nm,absorbance\n"
        "410.0,2.3,lamp1,Lamp A,408.3,nm,absorbance\n"
        "400.0,3.1,lamp2,Lamp B,399.0,nm,absorbance\n"
        "410.0,4.2,lamp2,Lamp B,409.0,nm,absorbance\n",
        encoding="utf-8"
    )
    
    importer = CsvImporter()
    result = importer.read(csv_path)
    
    # First spectrum should use calibrated values
    assert result.x[0] == pytest.approx(398.5)
    assert result.x[1] == pytest.approx(408.3)
    assert result.name == "Lamp A"
    
    # Check bundle metadata
    bundle = result.metadata.get("bundle")
    assert bundle is not None
    members = bundle.get("members")
    assert len(members) == 2
    
    # Verify both spectra have calibrated wavelengths
    lamp1 = members[0]
    assert lamp1["x"][0] == pytest.approx(398.5)
    assert lamp1["x"][1] == pytest.approx(408.3)
    
    lamp2 = members[1]
    assert lamp2["x"][0] == pytest.approx(399.0)
    assert lamp2["x"][1] == pytest.approx(409.0)
