"""Integration tests covering ingest, overlay and math services."""

from pathlib import Path

import numpy as np
import pytest

from app.services import UnitsService, DataIngestService, OverlayService, MathService, Spectrum


CSV_CONTENT = """# demo dataset
wavelength(nm),intensity(%T)
400,50
500,60
"""


@pytest.fixture()
def sample_csv(tmp_path: Path) -> Path:
    file_path = tmp_path / 'sample.csv'
    file_path.write_text(CSV_CONTENT, encoding='utf-8')
    return file_path


def test_ingest_produces_canonical_spectrum(sample_csv: Path):
    units = UnitsService()
    ingest = DataIngestService(units)
    spectrum = ingest.ingest(sample_csv)
    assert spectrum.x_unit == 'nm'
    assert spectrum.y_unit == 'absorbance'
    assert 'source_units' in spectrum.metadata
    assert np.allclose(spectrum.x, np.array([400.0, 500.0]))
    assert np.allclose(spectrum.y, -np.log10(np.array([0.5, 0.6])))


def test_overlay_returns_views(sample_csv: Path):
    units = UnitsService()
    ingest = DataIngestService(units)
    overlay = OverlayService(units)
    spectrum = ingest.ingest(sample_csv)
    overlay.add(spectrum)
    views = overlay.overlay([spectrum.id], 'cm^-1', 'transmittance')
    assert len(views) == 1
    view = views[0]
    assert view['x_unit'] == 'cm^-1'
    assert view['y_unit'] == 'transmittance'
    assert np.allclose(view['y'], np.array([0.5, 0.6]))


def test_math_operations(sample_csv: Path):
    units = UnitsService()
    ingest = DataIngestService(units)
    math_service = MathService(epsilon=1e-6)
    spectrum = ingest.ingest(sample_csv)
    overlay = OverlayService(units)
    overlay.add(spectrum)

    spec2 = spectrum.with_metadata(note='copy')
    overlay.add(spec2)

    result, info = math_service.subtract(spectrum, spec2)
    assert result is None
    assert info['status'] == 'suppressed_trivial'

    altered = Spectrum.create('shifted', spectrum.x, spectrum.y + 0.1, metadata=spectrum.metadata)
    ratio_spec, ratio_info = math_service.ratio(altered, spectrum)
    assert ratio_info['operation'] == 'ratio'
    assert ratio_spec.metadata['operation']['name'] == 'ratio'
    assert np.isnan(ratio_spec.y).sum() == 0
