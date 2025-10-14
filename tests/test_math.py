import numpy as np

from app.services import MathService, Spectrum


def make_spectrum(name: str, flux: np.ndarray) -> Spectrum:
    x = np.linspace(400.0, 500.0, flux.size)
    return Spectrum.create(name, x, flux)


def test_difference_suppression():
    math = MathService(epsilon=1e-9)
    a = make_spectrum("A", np.array([0.1, 0.2, 0.3]))
    b = make_spectrum("B", np.array([0.1, 0.2, 0.3]))
    result, info = math.subtract(a, b)
    assert result is None
    assert info["status"] == "suppressed_trivial"


def test_difference_result():
    math = MathService(epsilon=1e-9)
    a = make_spectrum("A", np.array([0.2, 0.4, 0.6]))
    b = make_spectrum("B", np.array([0.1, 0.2, 0.3]))
    result, info = math.subtract(a, b)
    assert result is not None
    assert info["operation"] == "subtract"
    assert np.allclose(result.y, np.array([0.1, 0.2, 0.3]))


def test_ratio_with_zero_guard():
    math = MathService(epsilon=1e-6)
    a = make_spectrum("A", np.array([1.0, 2.0, 3.0]))
    b = make_spectrum("B", np.array([1.0, 0.0, 3.0]))
    result, info = math.ratio(a, b)
    assert info["operation"] == "ratio"
    assert info["masked_points"] == 1
    assert np.isclose(result.y[0], 1.0)
    assert np.isnan(result.y[1])
