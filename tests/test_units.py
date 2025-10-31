"""Unit tests for UnitsService."""

import numpy as np
import pytest

from app.services.spectrum import Spectrum
from app.services.units_service import UnitsService


def test_wavelength_round_trip_nm_um():
    service = UnitsService()
    x = np.array([500.0, 1000.0])
    y = np.array([0.1, 0.2])
    canonical_x, canonical_y, metadata = service.to_canonical(x, y, 'um', 'absorbance')
    assert np.allclose(canonical_x, np.array([5e5, 1e6]))
    assert metadata['source_units'] == {'x': 'um', 'y': 'absorbance'}
    spectrum = Spectrum.create('test', x, y, x_unit='um', y_unit='absorbance')
    view, _, meta = service.convert(spectrum, 'µm', 'absorbance')
    assert meta == {'source_units': {'x': 'um', 'y': 'absorbance'}}
    assert np.allclose(view, x)


def test_wavenumber_round_trip():
    service = UnitsService()
    x = np.array([2000.0, 1000.0])
    y = np.array([1.0, 0.5])
    canonical_x, canonical_y, metadata = service.to_canonical(x, y, 'cm^-1', 'absorbance')
    assert metadata['source_units'] == {'x': 'cm^-1', 'y': 'absorbance'}
    spectrum = Spectrum.create('wavenumber', x, y, x_unit='cm^-1', y_unit='absorbance')
    view_x, _, meta = service.convert(spectrum, 'cm^-1', 'absorbance')
    assert meta == {'source_units': {'x': 'cm^-1', 'y': 'absorbance'}}
    assert np.allclose(view_x, x)


def test_unicode_wavenumber_aliases():
    service = UnitsService()
    x_nm = np.array([500.0, 1000.0])
    y_abs = np.array([0.1, 0.2])
    display_x, _ = service.from_canonical(x_nm, y_abs, 'cm⁻¹', 'absorbance')
    expected = np.array([1e7 / 500.0, 1e7 / 1000.0])
    assert np.allclose(display_x, expected)

    canonical_x, _, meta = service.to_canonical(np.array([4000.0]), np.array([0.5]), 'cm⁻¹', 'absorbance')
    assert np.allclose(canonical_x, np.array([1e7 / 4000.0]))
    assert meta['source_units']['x'] == 'cm^-1'


def test_wavenumber_zero_maps_to_infinity_without_warning():
    service = UnitsService()
    x_nm = np.array([0.0, 500.0])
    y_abs = np.array([0.0, 0.1])
    converted, _ = service.from_canonical(x_nm, y_abs, 'cm⁻¹', 'absorbance')
    assert np.isinf(converted[0])
    assert np.isclose(converted[1], 1e7 / 500.0)
    back, _, _ = service.to_canonical(np.array([np.inf, 2000.0]), np.array([0.2, 0.3]), 'cm^-1', 'absorbance')
    assert np.isclose(back[0], 0.0)


def test_transmittance_conversion_and_round_trip():
    service = UnitsService()
    x = np.array([400.0])
    y = np.array([0.5])  # fractional transmittance
    canonical_x, canonical_y, metadata = service.to_canonical(x, y, 'nm', 'transmittance')
    assert np.allclose(canonical_y, np.array([0.30103]), atol=1e-6)
    assert metadata['intensity_conversion']['transformation'] == 'T→A10'
    spectrum = Spectrum.create('trans', x, y, x_unit='nm', y_unit='transmittance')
    _, y_view, meta = service.convert(spectrum, 'nm', 'transmittance')
    assert meta == {
        'source_units': {'x': 'nm', 'y': 'transmittance'},
        'intensity_conversion': {'transformation': 'T→A10'},
    }
    assert np.allclose(y_view, y)


def test_percent_transmittance_conversion():
    service = UnitsService()
    x = np.array([400.0])
    y = np.array([50.0])  # percent transmittance
    canonical_x, canonical_y, metadata = service.to_canonical(x, y, 'nm', '%T')
    assert metadata['intensity_conversion']['transformation'] == '%T→A10'
    percent_unit = service.normalise_y_unit('%T')
    spectrum = Spectrum.create('percent', x, y, x_unit='nm', y_unit=percent_unit)
    _, y_view, meta = service.convert(spectrum, 'nm', '%T')
    assert meta == {
        'source_units': {'x': 'nm', 'y': percent_unit},
        'y_conversion': 'percent_transmittance→%t',
        'intensity_conversion': {'transformation': '%T→A10'},
    }
    assert np.allclose(y_view, y)


def test_absorbance_e_conversion():
    service = UnitsService()
    x = np.array([400.0])
    y = np.array([2.303])  # natural log absorbance (Ae)
    canonical_x, canonical_y, metadata = service.to_canonical(x, y, 'nm', 'absorbance_e')
    assert np.allclose(canonical_y, np.array([1.0]))
    assert metadata['intensity_conversion']['transformation'] == 'Ae→A10'
    spectrum = Spectrum.create('ae', x, y, x_unit='nm', y_unit='absorbance_e')
    _, y_view, meta = service.convert(spectrum, 'nm', 'absorbance_e')
    assert meta == {
        'source_units': {'x': 'nm', 'y': 'absorbance_e'},
        'y_conversion': 'absorbance→absorbance_e',
        'intensity_conversion': {'transformation': 'Ae→A10'},
    }
    assert np.allclose(y_view, y)


def test_invalid_units_raise():
    service = UnitsService()
    with pytest.raises(ValueError):
        service.to_canonical(np.array([1.0]), np.array([1.0]), 'foo', 'absorbance')
    with pytest.raises(ValueError):
        service.to_canonical(np.array([1.0]), np.array([1.0]), 'nm', 'bar')
