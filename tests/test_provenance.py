import json
import numpy as np

from app.services.provenance_service import ProvenanceService
from app.services.spectrum import Spectrum


def test_manifest_creation(tmp_path):
    service = ProvenanceService(app_version="0.1-test")
    spectrum = Spectrum.create(
        name="Sample",
        wavelength_nm=np.array([500.0, 600.0]),
        flux=np.array([0.1, 0.2]),
        flux_unit="absorbance",
        metadata={"source": {"path": "sample.csv", "checksum": "abc123"}},
        provenance=[{"event": "ingest", "importer": "CsvImporter"}],
    )
    manifest = service.create_manifest([spectrum], operations=[{"event": "noop"}])
    assert manifest["app"]["version"] == "0.1-test"
    assert manifest["spectra"][0]["id"] == spectrum.id
    assert manifest["spectra"][0]["metadata"]["source"]["path"] == "sample.csv"
    assert manifest["operations"][0]["event"] == "noop"

    manifest_path = tmp_path / "manifest.json"
    service.save_manifest(manifest, manifest_path)
    loaded = json.loads(manifest_path.read_text())
    assert loaded["spectra"][0]["name"] == "Sample"


def test_checksum_bytes():
    service = ProvenanceService()
    digest = service.checksum_bytes(b"abc")
    assert digest == service.checksum_bytes(b"abc")
