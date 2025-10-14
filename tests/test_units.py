import numpy as np
import pytest

from app.services.units_service import UnitError, UnitsService


def test_wavelength_round_trip():
    service = UnitsService()
    wavelengths = np.linspace(400, 800, 5)
    microns = service.convert_wavelength(wavelengths, "nm", "µm")
    back_to_nm = service.convert_wavelength(microns, "µm", "nm")
    assert np.allclose(back_to_nm, wavelengths)

    wavenumber = service.convert_wavelength(wavelengths, "nm", "cm^-1")
    restored = service.convert_wavelength(wavenumber, "cm^-1", "nm")
    assert np.allclose(restored, wavelengths)


def test_flux_round_trip_transmittance():
    service = UnitsService()
    trans = np.array([0.2, 0.5, 0.9])
    absorbance = service.convert_flux(trans, "transmittance", "absorbance", context={})
    restored = service.convert_flux(absorbance, "absorbance", "transmittance", context={})
    assert np.allclose(restored, trans)


def test_percent_transmittance():
    service = UnitsService()
    percent = np.array([80.0, 50.0])
    absorbance = service.convert_flux(percent, "percent_transmittance", "absorbance", context={})
    assert pytest.approx(absorbance[0], rel=1e-6) == -np.log10(0.8)
    restored = service.convert_flux(absorbance, "absorbance", "percent_transmittance", context={})
    assert np.allclose(restored, percent)


def test_absorption_coefficient_requires_context():
    service = UnitsService()
    alpha = np.array([1.2])
    with pytest.raises(UnitError):
        service.convert_flux(alpha, "absorption_coefficient", "absorbance", context={})
    absorbance = service.convert_flux(
        alpha,
        "absorption_coefficient",
        "absorbance",
        context={"path_length_m": 0.01, "mole_fraction": 0.5, "absorption_base": "10"},
    )
    restored = service.convert_flux(
        absorbance,
        "absorbance",
        "absorption_coefficient",
        context={"path_length_m": 0.01, "mole_fraction": 0.5, "absorption_base": "10"},
    )
    assert np.allclose(restored, alpha)
