import csv
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

    bundle = result.metadata.get("bundle")
    assert isinstance(bundle, dict)
    members = bundle.get("members") if isinstance(bundle, dict) else None
    assert isinstance(members, list)
    assert len(members) == 2
    first = members[0]
    second = members[1]
    assert first["name"] == "lamp-a"
    assert second["name"] == "lamp-b"
    assert pytest.approx(first["x"][0]) == 345.0
    assert pytest.approx(second["x"][0]) == 400.0


def test_wide_csv_round_trip(tmp_path: Path) -> None:
    service = ProvenanceService()
    spec_a = Spectrum.create('lamp-a', np.array([345.0, 350.0]), np.array([1.0, 0.5]))
    spec_b = Spectrum.create('lamp-b', np.array([400.0, 405.0, 410.0]), np.array([0.1, 0.2, 0.3]))

    wide_path = tmp_path / 'bundle' / 'wide.csv'
    service.write_wide_csv(wide_path, [spec_a, spec_b])

    importer = CsvImporter()
    result = importer.read(wide_path)
    bundle = result.metadata.get("bundle")
    assert isinstance(bundle, dict)
    members = bundle.get("members") if isinstance(bundle, dict) else None
    assert isinstance(members, list)
    assert len(members) == 2
    ids = [member["id"] for member in members]
    assert ids == [spec_a.id, spec_b.id]


def test_composite_csv_mean(tmp_path: Path) -> None:
    service = ProvenanceService()
    spec_a = Spectrum.create('lamp-a', np.array([500.0, 510.0, 520.0]), np.array([1.0, 2.0, 3.0]))
    spec_b = Spectrum.create('lamp-b', np.array([500.0, 510.0, 520.0]), np.array([3.0, 2.0, 1.0]))

    composite_path = tmp_path / 'bundle' / 'composite.csv'
    service.write_composite_csv(composite_path, [spec_a, spec_b])

    with composite_path.open('r', encoding='utf-8', newline='') as handle:
        reader = list(csv.reader(handle))
    assert reader[0] == ['wavelength_nm', 'intensity', 'source_count']
    assert reader[1][0] == '500.0'
    assert reader[1][2] == '2'

    importer = CsvImporter()
    result = importer.read(composite_path)
    assert np.allclose(result.x, np.array([500.0, 510.0, 520.0]))
    assert np.allclose(result.y, np.array([2.0, 2.0, 2.0]))


def test_composite_csv_descending_inputs(tmp_path: Path) -> None:
    service = ProvenanceService()
    spec_a = Spectrum.create('lamp-a', np.array([520.0, 510.0, 500.0]), np.array([3.0, 2.0, 1.0]))
    spec_b = Spectrum.create('lamp-b', np.array([520.0, 510.0, 500.0]), np.array([1.0, 2.0, 3.0]))

    composite_path = tmp_path / 'bundle' / 'composite-desc.csv'
    service.write_composite_csv(composite_path, [spec_a, spec_b])

    importer = CsvImporter()
    result = importer.read(composite_path)

    assert np.allclose(result.x, np.array([500.0, 510.0, 520.0]))
    assert np.allclose(result.y, np.array([2.0, 2.0, 2.0]))
