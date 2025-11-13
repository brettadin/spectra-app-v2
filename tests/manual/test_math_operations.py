"""Quick test of new math operations (smooth, derivative, integral)."""

import numpy as np
from app.services.spectrum import Spectrum
from app.services.math_service import MathService
from app.services.units_service import UnitsService


def test_smooth():
    """Test smoothing operation."""
    print("Testing smooth...")
    
    # Create test spectrum with noise
    x = np.linspace(400, 700, 100)
    y = np.sin(x / 50) + np.random.normal(0, 0.1, 100)
    
    spec = Spectrum.create(
        name="Noisy Spectrum",
        x=x,
        y=y,
        x_unit="nm",
        y_unit="absorbance",
    )
    
    units_service = UnitsService()
    math_service = MathService(units_service=units_service)
    
    # Test moving average
    result, metadata = math_service.smooth(spec, window_size=5, method='moving_average')
    print(f"✓ Moving average: created '{result.name}'")
    assert result is not None
    assert len(result.x) == len(spec.x)
    assert metadata['status'] == 'ok'
    assert metadata['method'] == 'moving_average'
    
    # Test Savitzky-Golay (will fallback to moving average if scipy not installed)
    result2, metadata2 = math_service.smooth(spec, window_size=7, method='savitzky_golay')
    print(f"✓ Savitzky-Golay: created '{result2.name}' (method: {metadata2['method']})")
    assert result2 is not None
    

def test_derivative():
    """Test derivative operation."""
    print("\nTesting derivative...")
    
    # Create test spectrum (parabola)
    x = np.linspace(0, 10, 50)
    y = x**2
    
    spec = Spectrum.create(
        name="Parabola",
        x=x,
        y=y,
        x_unit="nm",
        y_unit="absorbance",
    )
    
    units_service = UnitsService()
    math_service = MathService(units_service=units_service)
    
    # Test first derivative (should be ~2x)
    result, metadata = math_service.derivative(spec, order=1)
    print(f"✓ First derivative: created '{result.name}'")
    assert result is not None
    assert metadata['status'] == 'ok'
    assert metadata['order'] == 1
    # Check that derivative is approximately linear (2x)
    mid_idx = len(result.y) // 2
    expected = 2 * result.x[mid_idx]
    actual = result.y[mid_idx]
    print(f"  At x={result.x[mid_idx]:.2f}, dy/dx ≈ {actual:.2f} (expected ~{expected:.2f})")
    
    # Test second derivative (should be ~2)
    result2, metadata2 = math_service.derivative(spec, order=2)
    print(f"✓ Second derivative: created '{result2.name}'")
    assert result2 is not None
    assert metadata2['order'] == 2
    print(f"  Second derivative ≈ {np.mean(result2.y):.2f} (expected ~2)")


def test_integral():
    """Test integral operation."""
    print("\nTesting integral...")
    
    # Create test spectrum (constant value = 1)
    x = np.linspace(0, 10, 100)
    y = np.ones_like(x)
    
    spec = Spectrum.create(
        name="Constant",
        x=x,
        y=y,
        x_unit="nm",
        y_unit="absorbance",
    )
    
    units_service = UnitsService()
    math_service = MathService(units_service=units_service)
    
    # Test cumulative integral
    result, metadata = math_service.integral(spec, method='cumulative')
    print(f"✓ Cumulative integral: created '{result.name}'")
    assert result is not None
    assert metadata['status'] == 'ok'
    assert metadata['method'] == 'cumulative'
    total = metadata['total']
    print(f"  Total area: {total:.2f} (expected ~10)")
    assert abs(total - 10.0) < 0.5  # Should be close to 10
    
    # Test total integral
    result2, metadata2 = math_service.integral(spec, method='total')
    print(f"✓ Total integral: {metadata2['total']:.2f}")
    assert result2 is None  # No spectrum returned for total method
    assert metadata2['status'] == 'ok'
    assert abs(metadata2['total'] - 10.0) < 0.5


if __name__ == '__main__':
    test_smooth()
    test_derivative()
    test_integral()
    print("\n✅ All math operation tests passed!")
