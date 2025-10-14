from pathlib import Path
import numpy as np
import pytest

from app.services import DataIngestService, ProvenanceService, UnitsService


def build_ingest_service() -> DataIngestService:
    units = UnitsService()
    provenance = ProvenanceService()
    return DataIngestService(units_service=units, provenance_service=provenance)


def test_csv_ingest_samples():
    service = build_ingest_service()
    sample_path = Path("samples/sample_spectrum.csv")
    spectrum = service.ingest(sample_path)
    assert spectrum.metadata["source"]["importer"] == "CsvImporter"
    assert spectrum.metadata["source"]["path"].endswith("sample_spectrum.csv")
    assert spectrum.provenance[0]["event"] == "ingest"
    assert spectrum.wavelength_nm[0] == pytest.approx(400.0)


def test_percent_transmittance_conversion():
    service = build_ingest_service()
    sample_path = Path("samples/sample_transmittance.csv")
    spectrum = service.ingest(sample_path)
    expected = -np.log10(np.array([0.9, 0.8, 0.7, 0.6, 0.5]))
    assert np.allclose(spectrum.flux, expected)
