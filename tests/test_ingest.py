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
    spectra = service.ingest(sample_path)
    assert len(spectra) == 1
    spectrum = spectra[0]
    ingest_meta = spectrum.metadata["ingest"]
    assert ingest_meta["importer"] == "CsvImporter"
    assert ingest_meta["source_path"].endswith("sample_spectrum.csv")
    assert np.isclose(spectrum.x[0], 400.0)


def test_dat_ingest_uses_csv_importer():
    service = build_ingest_service()
    dat_path = Path("tests/data/mini.dat")
    spectra = service.ingest(dat_path)

    assert len(spectra) == 1
    spectrum = spectra[0]
    ingest_meta = spectrum.metadata["ingest"]
    assert ingest_meta["importer"] == "CsvImporter"
    assert spectrum.x_unit == "nm"
    assert spectrum.y_unit == "transmittance"
    assert np.allclose(spectrum.x, np.array([400.0, 410.0, 420.0, 430.0]))
    assert np.allclose(spectrum.y, np.array([0.12, 0.18, 0.22, 0.27]))


def test_percent_transmittance_conversion():
    service = build_ingest_service()
    sample_path = Path("samples/sample_transmittance.csv")
    spectra = service.ingest(sample_path)
    spectrum = spectra[0]
    expected = np.array([90.0, 80.0, 70.0, 60.0, 50.0])
    assert np.allclose(spectrum.y, expected)
    assert spectrum.x_unit == "nm"
    assert spectrum.y_unit == "percent_transmittance"


def test_fits_ingest_fixture(mini_fits: Path):
    service = build_ingest_service()
    spectra = service.ingest(mini_fits)
    spectrum = spectra[0]
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


def test_fits_importer_handles_tess_lightcurve():
    if importlib.util.find_spec("astropy.io.fits") is None:
        pytest.skip("astropy is required for FITS ingestion tests")

    path = Path("samples/fits data/tess2019112060037-s0011-0000000388857263-0143-s_lc.fits")
    if not path.exists():
        pytest.skip("TESS sample not available in minimal repo")
    importer = FitsImporter()
    result = importer.read(path)

    assert result.metadata.get("x_label") == "TIME"
    assert result.metadata.get("y_label") == "PDCSAP_FLUX"
    assert result.metadata.get("original_flux_unit") == "e-/s"
    assert result.x_unit.startswith("bjd")
    assert result.x.size == result.y.size


def test_export_bundle_csv_roundtrip(tmp_path: Path):
    service = build_ingest_service()
    bundle_path = tmp_path / "bundle.csv"
    bundle_path.write_text(
        """wavelength_nm,intensity,spectrum_id,spectrum_name,point_index,x_unit,y_unit
400,0.1,first,First lamp,0,nm,absorbance
410,0.2,first,First lamp,1,nm,absorbance
420,0.3,second,Second lamp,0,nm,absorbance
430,0.4,second,Second lamp,1,nm,absorbance
""",
        encoding="utf-8",
    )

    spectra = service.ingest(bundle_path)
    assert len(spectra) == 2
    names = [s.name for s in spectra]
    assert "First lamp" in names
    assert "Second lamp" in names
    for spectrum in spectra:
        assert spectrum.x_unit == "nm"
        assert spectrum.y_unit == "absorbance"
        assert spectrum.metadata.get("ingest", {}).get("bundle_member")
