"""Targeted tests for :mod:`app.services.units_service`."""

import numpy as np

from app.services.units_service import UnitsService


def test_from_canonical_wavenumber_accepts_superscript_minus():
    """Ensure Unicode minus wavenumbers normalise to ``cm^-1``."""

    service = UnitsService()
    x_nm = np.array([5000.0, 10000.0])
    y_absorbance = np.array([0.1, 0.2])

    wavenumber, returned_y = service.from_canonical(x_nm, y_absorbance, "cm⁻¹", "absorbance")

    expected = np.array([2000.0, 1000.0])
    assert np.all(np.isfinite(wavenumber))
    assert np.allclose(wavenumber, expected)
    assert np.allclose(returned_y, y_absorbance)
