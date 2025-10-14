from pathlib import Path

import numpy as np
import pytest
from astropy.io import fits

from app.services import DataIngestService, UnitsService


def build_ingest_service() -> DataIngestService:
    units = UnitsService()
    return DataIngestService(units)


def test_csv_ingest_samples():
    service = build_ingest_service()
    sample_path = Path("samples/sample_spectrum.csv")
    spectrum = service.ingest(sample_path)
    ingest_meta = spectrum.metadata["ingest"]
    assert ingest_meta["importer"] == "CsvImporter"
    assert ingest_meta["source_path"].endswith("sample_spectrum.csv")
    assert np.isclose(spectrum.x[0], 400.0)


def test_percent_transmittance_conversion():
    service = build_ingest_service()
    sample_path = Path("samples/sample_transmittance.csv")
    spectrum = service.ingest(sample_path)
    expected = -np.log10(np.array([0.9, 0.8, 0.7, 0.6, 0.5]))
    assert np.allclose(spectrum.y, expected)


@pytest.fixture()
def mini_fits(tmp_path: Path) -> Path:
    wavelengths = np.array([500.0, 600.0, 700.0])
    flux = np.array([0.1, 0.2, 0.3])
    columns = [
        fits.Column(name="WAVELENGTH", array=wavelengths, format="D", unit="nm"),
        fits.Column(name="FLUX", array=flux, format="D", unit="erg/s/cm2/angstrom"),
    ]
    table = fits.BinTableHDU.from_columns(columns)
    table.header["OBJECT"] = "MiniFixture"
    table.header["INSTRUME"] = "TestSpec"
    table.header["BUNIT"] = "erg/s/cm2/angstrom"
    path = tmp_path / "mini.fits"
    fits.HDUList([fits.PrimaryHDU(), table]).writeto(path)
    return path


def test_fits_ingest_fixture(mini_fits: Path):
    service = build_ingest_service()
    spectrum = service.ingest(mini_fits)
    ingest_meta = spectrum.metadata["ingest"]
    assert ingest_meta["importer"] == "FitsImporter"
    assert ingest_meta["source_path"].endswith("mini.fits")
    assert np.isclose(spectrum.x[0], 500.0)
    assert spectrum.metadata.get("original_flux_unit") == "erg/s/cm2/angstrom"

