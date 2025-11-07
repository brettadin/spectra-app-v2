import numpy as np

from app.services import MathService, Spectrum, UnitsService


def make_spectrum(name: str, flux: np.ndarray) -> Spectrum:
    x = np.linspace(400.0, 500.0, flux.size)
    return Spectrum.create(name, x, flux, x_unit="nm", y_unit="absorbance")


def test_difference_suppression():
    math = MathService(UnitsService(), epsilon=1e-9)
    a = make_spectrum("A", np.array([0.1, 0.2, 0.3]))
    b = make_spectrum("B", np.array([0.1, 0.2, 0.3]))
    result, info = math.subtract(a, b)
    assert result is None
    assert info["status"] == "suppressed_trivial"


def test_difference_result():
    math = MathService(UnitsService(), epsilon=1e-9)
    a = make_spectrum("A", np.array([0.2, 0.4, 0.6]))
    b = make_spectrum("B", np.array([0.1, 0.2, 0.3]))
    result, info = math.subtract(a, b)
    assert result is not None
    assert info["operation"] == "subtract"
    assert np.allclose(result.y, np.array([0.1, 0.2, 0.3]))


def test_ratio_with_zero_guard():
    math = MathService(UnitsService(), epsilon=1e-6)
    a = make_spectrum("A", np.array([1.0, 2.0, 3.0]))
    b = make_spectrum("B", np.array([1.0, 0.0, 3.0]))
    result, info = math.ratio(a, b)
    assert info["operation"] == "ratio"
    assert info["masked_points"] == 1
    assert np.isclose(result.y[0], 1.0)
    assert np.isnan(result.y[1])


def test_math_with_different_ranges():
    """Test that math operations work with non-overlapping ranges via interpolation."""
    math = MathService(UnitsService(), epsilon=1e-9)
    
    # Spectrum A: 400-500 nm
    x_a = np.linspace(400.0, 500.0, 11)
    y_a = np.ones(11) * 2.0
    a = Spectrum.create("A", x_a, y_a, x_unit="nm", y_unit="absorbance")
    
    # Spectrum B: 450-550 nm (partial overlap)
    x_b = np.linspace(450.0, 550.0, 11)
    y_b = np.ones(11) * 1.0
    b = Spectrum.create("B", x_b, y_b, x_unit="nm", y_unit="absorbance")
    
    # Subtract: should work on overlapping range (450-500 nm)
    result_sub, info_sub = math.subtract(a, b)
    assert result_sub is not None
    assert info_sub["status"] == "ok"
    # Result should be in overlapping range
    assert np.nanmin(result_sub.x) >= 450.0
    assert np.nanmax(result_sub.x) <= 500.0
    # Values should be ~1.0 (2.0 - 1.0)
    assert np.allclose(result_sub.y, 1.0, atol=0.01)
    
    # Ratio: should work on overlapping range
    result_ratio, info_ratio = math.ratio(a, b)
    assert result_ratio is not None
    assert info_ratio["status"] == "ok"
    # Values should be ~2.0 (2.0 / 1.0)
    assert np.allclose(result_ratio.y, 2.0, atol=0.01)


def test_math_with_different_grid_densities():
    """Test that interpolation chooses the finer grid."""
    math = MathService(UnitsService(), epsilon=1e-9)
    
    # Coarse spectrum: 10 points
    x_coarse = np.linspace(400.0, 500.0, 10)
    y_coarse = np.ones(10) * 2.0
    coarse = Spectrum.create("Coarse", x_coarse, y_coarse, x_unit="nm", y_unit="absorbance")
    
    # Fine spectrum: 100 points
    x_fine = np.linspace(400.0, 500.0, 100)
    y_fine = np.ones(100) * 1.0
    fine = Spectrum.create("Fine", x_fine, y_fine, x_unit="nm", y_unit="absorbance")
    
    # Result should use the finer grid
    result, info = math.subtract(coarse, fine)
    assert result is not None
    # Should have ~100 points (the finer grid)
    assert result.x.size > 50

