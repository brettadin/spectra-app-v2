"""Tests for uncertainty propagation in math operations."""

import numpy as np
import pytest

from app.services import MathService, Spectrum, UnitsService


@pytest.fixture
def math_service():
    """Create a MathService with standard epsilon."""
    return MathService(units_service=UnitsService())


def test_subtract_with_uncertainties(math_service):
    """Test uncertainty propagation in subtraction: σ_diff = √(σ_a² + σ_b²)."""
    x = np.array([400.0, 450.0, 500.0])
    a_y = np.array([1.0, 2.0, 3.0])
    b_y = np.array([0.5, 1.0, 1.5])
    a_sigma = np.array([0.1, 0.2, 0.15])
    b_sigma = np.array([0.05, 0.1, 0.1])
    
    spec_a = Spectrum.create(
        name="A",
        x=x,
        y=a_y,
        x_unit="nm",
        y_unit="absorbance",
        uncertainty=a_sigma,
    )
    spec_b = Spectrum.create(
        name="B",
        x=x,
        y=b_y,
        x_unit="nm",
        y_unit="absorbance",
        uncertainty=b_sigma,
    )
    
    result, meta = math_service.subtract(spec_a, spec_b)
    
    assert result is not None
    assert meta['status'] == 'ok'
    assert result.uncertainty is not None
    
    # Expected: σ_diff = √(0.1² + 0.05²), √(0.2² + 0.1²), √(0.15² + 0.1²)
    expected_sigma = np.sqrt(a_sigma**2 + b_sigma**2)
    np.testing.assert_allclose(result.uncertainty, expected_sigma, rtol=1e-10)


def test_subtract_with_one_uncertainty(math_service):
    """Test subtraction when only one spectrum has uncertainty."""
    x = np.array([400.0, 450.0, 500.0])
    a_y = np.array([1.0, 2.0, 3.0])
    b_y = np.array([0.5, 1.0, 1.5])
    a_sigma = np.array([0.1, 0.2, 0.15])
    
    spec_a = Spectrum.create(
        name="A",
        x=x,
        y=a_y,
        x_unit="nm",
        y_unit="absorbance",
        uncertainty=a_sigma,
    )
    spec_b = Spectrum.create(
        name="B",
        x=x,
        y=b_y,
        x_unit="nm",
        y_unit="absorbance",
    )
    
    result, meta = math_service.subtract(spec_a, spec_b)
    
    assert result is not None
    assert result.uncertainty is not None
    # When one sigma is zero, result should equal the non-zero sigma
    np.testing.assert_allclose(result.uncertainty, a_sigma, rtol=1e-10)


def test_ratio_with_uncertainties(math_service):
    """Test uncertainty propagation in ratio: σ_ratio = |a/b| * √((σ_a/a)² + (σ_b/b)²)."""
    x = np.array([400.0, 450.0, 500.0])
    a_y = np.array([2.0, 4.0, 6.0])
    b_y = np.array([1.0, 2.0, 3.0])
    a_sigma = np.array([0.2, 0.4, 0.3])
    b_sigma = np.array([0.1, 0.2, 0.15])
    
    spec_a = Spectrum.create(
        name="A",
        x=x,
        y=a_y,
        x_unit="nm",
        y_unit="absorbance",
        uncertainty=a_sigma,
    )
    spec_b = Spectrum.create(
        name="B",
        x=x,
        y=b_y,
        x_unit="nm",
        y_unit="absorbance",
        uncertainty=b_sigma,
    )
    
    result, meta = math_service.ratio(spec_a, spec_b)
    
    assert meta['status'] == 'ok'
    assert result.uncertainty is not None
    
    # Expected: σ_ratio = |a/b| * √((σ_a/a)² + (σ_b/b)²)
    ratio_values = a_y / b_y
    rel_a = a_sigma / np.abs(a_y)
    rel_b = b_sigma / np.abs(b_y)
    expected_sigma = np.abs(ratio_values) * np.sqrt(rel_a**2 + rel_b**2)
    
    np.testing.assert_allclose(result.uncertainty, expected_sigma, rtol=1e-10)


def test_average_with_uncertainties(math_service):
    """Test uncertainty propagation in averaging: σ_avg = σ_individual / √N."""
    x = np.array([400.0, 450.0, 500.0])
    y1 = np.array([1.0, 2.0, 3.0])
    y2 = np.array([1.1, 2.1, 3.1])
    y3 = np.array([0.9, 1.9, 2.9])
    sigma = np.array([0.3, 0.3, 0.3])  # Same uncertainty for all
    
    spectra = [
        Spectrum.create(name=f"Spec{i}", x=x, y=y, x_unit="nm", y_unit="absorbance", uncertainty=sigma)
        for i, y in enumerate([y1, y2, y3], 1)
    ]
    
    result, meta = math_service.average(spectra)
    
    assert meta['status'] == 'ok'
    assert result.uncertainty is not None
    
    # Expected: σ_avg = σ / √3 ≈ σ / 1.732
    expected_sigma = sigma / np.sqrt(3)
    np.testing.assert_allclose(result.uncertainty, expected_sigma, rtol=1e-10)


def test_quality_flags_combine_with_or(math_service):
    """Test that quality flags combine with bitwise OR in operations."""
    x = np.array([400.0, 450.0, 500.0])
    a_y = np.array([1.0, 2.0, 3.0])
    b_y = np.array([0.5, 1.0, 1.5])
    
    # Flags: 0x1 = bad_pixel, 0x2 = cosmic_ray, 0x4 = saturated
    a_flags = np.array([0x1, 0x0, 0x2], dtype=np.uint8)  # bad_pixel at 400nm, cosmic_ray at 500nm
    b_flags = np.array([0x0, 0x4, 0x2], dtype=np.uint8)  # saturated at 450nm, cosmic_ray at 500nm
    
    spec_a = Spectrum.create(
        name="A",
        x=x,
        y=a_y,
        x_unit="nm",
        y_unit="absorbance",
        quality_flags=a_flags,
    )
    spec_b = Spectrum.create(
        name="B",
        x=x,
        y=b_y,
        x_unit="nm",
        y_unit="absorbance",
        quality_flags=b_flags,
    )
    
    result, meta = math_service.subtract(spec_a, spec_b)
    
    assert result is not None
    assert result.quality_flags is not None
    
    # Expected: OR combination
    # [0x1, 0x0, 0x2] | [0x0, 0x4, 0x2] = [0x1, 0x4, 0x2]
    expected_flags = np.array([0x1, 0x4, 0x2], dtype=np.uint8)
    np.testing.assert_array_equal(result.quality_flags, expected_flags)


def test_uncertainty_interpolation_different_ranges(math_service):
    """Test that uncertainties are properly interpolated when spectra have different ranges."""
    x_a = np.array([400.0, 450.0, 500.0])
    x_b = np.array([425.0, 475.0, 525.0])
    
    y_a = np.array([1.0, 2.0, 3.0])
    y_b = np.array([0.5, 1.0, 1.5])
    
    sigma_a = np.array([0.1, 0.2, 0.15])
    sigma_b = np.array([0.05, 0.1, 0.12])
    
    spec_a = Spectrum.create(
        name="A",
        x=x_a,
        y=y_a,
        x_unit="nm",
        y_unit="absorbance",
        uncertainty=sigma_a,
    )
    spec_b = Spectrum.create(
        name="B",
        x=x_b,
        y=y_b,
        x_unit="nm",
        y_unit="absorbance",
        uncertainty=sigma_b,
    )
    
    result, meta = math_service.subtract(spec_a, spec_b)
    
    assert result is not None
    assert result.uncertainty is not None
    # Uncertainty should be interpolated and combined
    assert len(result.uncertainty) == len(result.x)
    # All values should be positive
    assert np.all(result.uncertainty >= 0)


def test_no_uncertainty_propagation_when_none(math_service):
    """Test that operations without uncertainty data don't create spurious uncertainty."""
    x = np.array([400.0, 450.0, 500.0])
    a_y = np.array([1.0, 2.0, 3.0])
    b_y = np.array([0.5, 1.0, 1.5])
    
    spec_a = Spectrum.create(
        name="A",
        x=x,
        y=a_y,
        x_unit="nm",
        y_unit="absorbance",
    )
    spec_b = Spectrum.create(
        name="B",
        x=x,
        y=b_y,
        x_unit="nm",
        y_unit="absorbance",
    )
    
    result, meta = math_service.subtract(spec_a, spec_b)
    
    assert result is not None
    assert result.uncertainty is None
    assert result.quality_flags is None
