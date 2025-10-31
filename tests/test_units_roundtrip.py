"""Unit canon regression tests for wavelength/intensity toggles."""

from pathlib import Path

import numpy as np

from app.services.spectrum import Spectrum
from app.services.units_service import UnitsService


FIXTURE_CSV = Path("tests/data/mini.csv")


def load_fixture_spectrum() -> Spectrum:
    data = np.loadtxt(FIXTURE_CSV, delimiter=",", skiprows=1)
    wavelengths = data[:, 0]
    absorbance = data[:, 1]
    return Spectrum.create("mini", wavelengths, absorbance, x_unit="nm", y_unit="absorbance")


def test_roundtrip_nm_to_angstrom_and_back():
    service = UnitsService()
    spectrum = load_fixture_spectrum()

    x_view, y_view, meta = service.convert(spectrum, "Å", "absorbance")

    assert meta == {"x_conversion": "nm→angstrom", "source_units": {"x": "nm", "y": "absorbance"}}
    assert not np.shares_memory(x_view, spectrum.x)

    canonical_x, canonical_y, metadata = service.to_canonical(x_view, y_view, "Å", "absorbance")
    assert np.allclose(canonical_x, spectrum.x)
    assert np.allclose(canonical_y, spectrum.y)
    assert metadata["source_units"] == {"x": "angstrom", "y": "absorbance"}


def test_roundtrip_nm_to_wavenumber_to_percent_transmittance():
    service = UnitsService()
    spectrum = load_fixture_spectrum()

    x_view, y_view, meta = service.convert(spectrum, "cm^-1", "%T")
    assert meta["x_conversion"] == "nm→cm^-1"
    assert meta["y_conversion"] == "absorbance→%t"
    assert meta["source_units"] == {"x": "nm", "y": "absorbance"}
    assert np.allclose(y_view, 10 ** (-spectrum.y) * 100.0)

    canonical_x, canonical_y, metadata = service.to_canonical(x_view, y_view, "cm^-1", "%T")
    assert np.allclose(canonical_x, spectrum.x)
    assert np.allclose(canonical_y, spectrum.y)
    assert metadata["source_units"] == {"x": "cm^-1", "y": "%t"}
