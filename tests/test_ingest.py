from pathlib import Path

import importlib.util

import numpy as np
import pytest

from app.services import DataIngestService, UnitsService
from app.services.importers import FitsImporter


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


def test_fits_ingest_fixture(mini_fits: Path):
    service = build_ingest_service()
    spectrum = service.ingest(mini_fits)
    ingest_meta = spectrum.metadata["ingest"]
    assert ingest_meta["importer"] == "FitsImporter"
    assert ingest_meta["source_path"].endswith("mini.fits")
    assert np.isclose(spectrum.x[0], 500.0)
    assert spectrum.metadata.get("original_flux_unit") == "erg/s/cm2/angstrom"


def test_fits_importer_requires_astropy_when_missing(tmp_path: Path):
    try:
        fits_spec = importlib.util.find_spec("astropy.io.fits")
    except ModuleNotFoundError:  # pragma: no cover - interpreter behaviour
        fits_spec = None

    if fits_spec is not None:
        pytest.skip("astropy installed; runtime guard not triggered")

    importer = FitsImporter()
    with pytest.raises(RuntimeError):
        importer.read(tmp_path / "dummy.fits")
