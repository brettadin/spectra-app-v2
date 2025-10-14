import numpy as np

from app.services import MathService, Spectrum


def make_spectrum(name: str, flux: np.ndarray) -> Spectrum:
    return Spectrum.create(
        name=name,
        wavelength_nm=np.linspace(400, 500, flux.size),
        flux=flux,
    )


def test_difference_suppression():
    math = MathService(epsilon=1e-9)
    a = make_spectrum("A", np.array([0.1, 0.2, 0.3]))
    b = make_spectrum("B", np.array([0.1, 0.2, 0.3]))
    result = math.difference(a, b)
    assert result.suppressed
    assert result.spectrum is None


def test_difference_result():
    math = MathService(epsilon=1e-9)
    a = make_spectrum("A", np.array([0.2, 0.4, 0.6]))
    b = make_spectrum("B", np.array([0.1, 0.2, 0.3]))
    result = math.difference(a, b)
    assert not result.suppressed
    assert np.allclose(result.spectrum.flux, np.array([0.1, 0.2, 0.3]))


def test_ratio_with_zero_guard():
    math = MathService(epsilon=1e-6)
    a = make_spectrum("A", np.array([1.0, 2.0, 3.0]))
    b = make_spectrum("B", np.array([1.0, 0.0, 3.0]))
    result = math.ratio(a, b)
    assert not result.suppressed
    assert result.spectrum.metadata["epsilon_mask_count"] == 1
    assert np.isclose(result.spectrum.flux[0], 1.0)
    assert result.spectrum.flux[1] == 0.0
