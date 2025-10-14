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
    spectrum = Spectrum.create('test', canonical_x, canonical_y)
    view, _, _ = service.convert(spectrum, 'µm', 'absorbance')
    assert np.allclose(view, x)


def test_wavenumber_round_trip():
    service = UnitsService()
    x = np.array([2000.0, 1000.0])
    y = np.array([1.0, 0.5])
    canonical_x, canonical_y, _ = service.to_canonical(x, y, 'cm^-1', 'absorbance')
    spectrum = Spectrum.create('wavenumber', canonical_x, canonical_y)
    view_x, _, _ = service.convert(spectrum, 'cm^-1', 'absorbance')
    assert np.allclose(view_x, x)


def test_transmittance_conversion_and_round_trip():
    service = UnitsService()
    x = np.array([400.0])
    y = np.array([0.5])  # fractional transmittance
    canonical_x, canonical_y, metadata = service.to_canonical(x, y, 'nm', 'transmittance')
    assert np.allclose(canonical_y, np.array([0.30103]), atol=1e-6)
    spectrum = Spectrum.create('trans', canonical_x, canonical_y)
    _, y_view, _ = service.convert(spectrum, 'nm', 'transmittance')
    assert np.allclose(y_view, y)


def test_percent_transmittance_conversion():
    service = UnitsService()
    x = np.array([400.0])
    y = np.array([50.0])  # percent transmittance
    canonical_x, canonical_y, metadata = service.to_canonical(x, y, 'nm', '%T')
    assert metadata['intensity_conversion']['transformation'] == '%T→A10'
    spectrum = Spectrum.create('percent', canonical_x, canonical_y)
    _, y_view, _ = service.convert(spectrum, 'nm', '%T')
    assert np.allclose(y_view, y)


def test_absorbance_e_conversion():
    service = UnitsService()
    x = np.array([400.0])
    y = np.array([2.303])  # natural log absorbance (Ae)
    canonical_x, canonical_y, _ = service.to_canonical(x, y, 'nm', 'absorbance_e')
    assert np.allclose(canonical_y, np.array([1.0]))
    spectrum = Spectrum.create('ae', canonical_x, canonical_y)
    _, y_view, _ = service.convert(spectrum, 'nm', 'absorbance_e')
    assert np.allclose(y_view, y)


def test_invalid_units_raise():
    service = UnitsService()
    with pytest.raises(ValueError):
        service.to_canonical(np.array([1.0]), np.array([1.0]), 'foo', 'absorbance')
    with pytest.raises(ValueError):
        service.to_canonical(np.array([1.0]), np.array([1.0]), 'nm', 'bar')
