import json
import numpy as np

from app.services.provenance_service import ProvenanceService
from app.services.spectrum import Spectrum


def dummy_spectrum(tmp_path: Path) -> Spectrum:
    data_path = tmp_path / 'dummy.csv'
    data_path.write_text('lambda,intensity\n1,2\n3,4\n', encoding='utf-8')
    spec = Spectrum.create('dummy', np.array([1.0, 2.0]), np.array([0.1, 0.2]), source_path=data_path)
    return spec


def test_manifest_creation_and_sha256(tmp_path):
    service = ProvenanceService(app_version='0.1-test')
    spec = dummy_spectrum(tmp_path)
    manifest = service.create_manifest([spec])
    assert manifest['app']['version'] == '0.1-test'
    assert len(manifest['sources']) == 1
    src = manifest['sources'][0]
    assert src['name'] == 'dummy'
    assert 'checksum_sha256' in src

    manifest_path = tmp_path / 'manifest.json'
    service.save_manifest(manifest, manifest_path)
    loaded = json.loads(manifest_path.read_text(encoding='utf-8'))
    assert loaded['sources'][0]['checksum_sha256'] == src['checksum_sha256']


def test_transforms_receive_timestamp(tmp_path):
    service = ProvenanceService()
    spec = dummy_spectrum(tmp_path)
    manifest = service.create_manifest([spec], transforms=[{'name': 'unit_conversion', 'parameters': {'target': 'cm^-1'}}])
    assert manifest['transforms'][0]['name'] == 'unit_conversion'
    assert 'timestamp_utc' in manifest['transforms'][0]
