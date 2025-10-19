import json
from pathlib import Path

import numpy as np
import pytest

from app.services.importers.csv_importer import CsvImporter
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


def test_export_bundle_csv_round_trips(tmp_path: Path) -> None:
    service = ProvenanceService()
    spec_a = Spectrum.create('lamp-a', np.array([345.0, 350.0]), np.array([1.0, 0.5]))
    spec_b = Spectrum.create('lamp-b', np.array([400.0, 405.0, 410.0]), np.array([0.1, 0.2, 0.3]))

    manifest_path = tmp_path / 'bundle' / 'manifest.json'
    export = service.export_bundle([spec_a, spec_b], manifest_path)

    csv_path = export['csv_path']
    csv_text = csv_path.read_text(encoding='utf-8').splitlines()
    assert csv_text[0].startswith('wavelength_nm,intensity,')

    importer = CsvImporter()
    result = importer.read(csv_path)

    assert result.x[0] == pytest.approx(345.0)
    assert result.y[0] == pytest.approx(1.0)
    assert result.x[2] == pytest.approx(400.0)
    assert result.y[2] == pytest.approx(0.1)
