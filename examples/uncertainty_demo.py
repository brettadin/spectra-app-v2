"""Example demonstrating uncertainty propagation and quality flags.

This script shows how to:
1. Create spectra with uncertainty and quality flags
2. Perform mathematical operations with error propagation
3. Analyze and visualize the results
"""

import numpy as np
from app.services import MathService, Spectrum, UnitsService, QualityFlags


def main():
    print("=" * 70)
    print("Uncertainty Propagation and Quality Flags Demo")
    print("=" * 70)
    
    # Create two sample spectra with uncertainties
    print("\n1. Creating sample spectra with uncertainties...")
    
    x = np.linspace(400, 500, 101)  # 400-500 nm, 1 nm resolution
    
    # Spectrum A: smooth baseline with 5% relative uncertainty
    y_a = 1.0 + 0.01 * x
    sigma_a = 0.05 * y_a  # 5% relative error
    
    # Spectrum B: similar but offset, with bad pixels at 425 and 475 nm
    y_b = 1.2 + 0.008 * x
    sigma_b = 0.03 * y_b  # 3% relative error
    
    # Quality flags for spectrum B
    flags_b = np.zeros(len(x), dtype=np.uint8)
    flags_b[25] = QualityFlags.BAD_PIXEL  # At 425 nm
    flags_b[75] = QualityFlags.COSMIC_RAY  # At 475 nm
    
    spec_a = Spectrum.create(
        name="Sample A",
        x=x,
        y=y_a,
        x_unit="nm",
        y_unit="absorbance",
        uncertainty=sigma_a,
    )
    
    spec_b = Spectrum.create(
        name="Sample B",
        x=x,
        y=y_b,
        x_unit="nm",
        y_unit="absorbance",
        uncertainty=sigma_b,
        quality_flags=flags_b,
    )
    
    print(f"  Created '{spec_a.name}': {len(spec_a.x)} points, "
          f"mean σ = {np.mean(spec_a.uncertainty):.4f}")
    print(f"  Created '{spec_b.name}': {len(spec_b.x)} points, "
          f"mean σ = {np.mean(spec_b.uncertainty):.4f}, "
          f"{np.sum(spec_b.quality_flags != 0)} flagged points")
    
    # Perform subtraction with uncertainty propagation
    print("\n2. Performing subtraction: A - B...")
    
    math_service = MathService(units_service=UnitsService())
    diff_spec, meta = math_service.subtract(spec_a, spec_b)
    
    if diff_spec is None:
        print("  Result suppressed (spectra too similar)")
        return
    
    print(f"  Result: '{diff_spec.name}'")
    print(f"  Uncertainty propagated: mean σ = {np.mean(diff_spec.uncertainty):.4f}")
    print(f"  Quality flags combined: {np.sum(diff_spec.quality_flags != 0)} flagged points")
    
    # Analyze uncertainty propagation
    print("\n3. Analyzing uncertainty propagation...")
    
    # Expected combined uncertainty: sqrt(sigma_a^2 + sigma_b^2)
    expected_sigma = np.sqrt(sigma_a**2 + sigma_b**2)
    mean_difference = np.mean(np.abs(diff_spec.uncertainty - expected_sigma))
    
    print(f"  Formula check: σ_diff = √(σ_a² + σ_b²)")
    print(f"  Mean deviation from expected: {mean_difference:.2e} (should be ~0)")
    
    # Show specific examples
    indices = [0, 25, 50, 75, 100]
    print("\n  Sample points:")
    print("  λ (nm)  |  σ_A    σ_B    σ_diff  | Flags")
    print("  " + "-" * 50)
    for i in indices:
        flags_str = "GOOD" if diff_spec.quality_flags[i] == 0 else f"0x{diff_spec.quality_flags[i]:02X}"
        print(f"  {x[i]:6.1f}  | {sigma_a[i]:.4f} {sigma_b[i]:.4f} {diff_spec.uncertainty[i]:.4f} | {flags_str}")
    
    # Perform ratio operation
    print("\n4. Performing ratio: A / B...")
    
    ratio_spec, meta = math_service.ratio(spec_a, spec_b)
    
    print(f"  Result: '{ratio_spec.name}'")
    print(f"  Uncertainty propagated: mean σ = {np.mean(ratio_spec.uncertainty):.4f}")
    
    # Expected ratio uncertainty: |a/b| * sqrt((sigma_a/a)^2 + (sigma_b/b)^2)
    ratio_values = y_a / y_b
    rel_a = sigma_a / np.abs(y_a)
    rel_b = sigma_b / np.abs(y_b)
    expected_ratio_sigma = np.abs(ratio_values) * np.sqrt(rel_a**2 + rel_b**2)
    
    mean_ratio_diff = np.mean(np.abs(ratio_spec.uncertainty - expected_ratio_sigma))
    print(f"  Formula check: σ_ratio = |a/b| × √((σ_a/a)² + (σ_b/b)²)")
    print(f"  Mean deviation from expected: {mean_ratio_diff:.2e} (should be ~0)")
    
    # Test averaging
    print("\n5. Averaging multiple spectra...")
    
    # Create 3 similar spectra with slight variations
    spectra = []
    for i in range(3):
        y_variant = y_a + np.random.normal(0, 0.02, len(x))
        sigma_variant = 0.04 * y_variant
        
        spec = Spectrum.create(
            name=f"Replicate {i+1}",
            x=x,
            y=y_variant,
            x_unit="nm",
            y_unit="absorbance",
            uncertainty=sigma_variant,
        )
        spectra.append(spec)
    
    avg_spec, meta = math_service.average(spectra)
    
    print(f"  Averaged {len(spectra)} spectra")
    print(f"  Result uncertainty: mean σ = {np.mean(avg_spec.uncertainty):.4f}")
    print(f"  Individual uncertainty: mean σ = {np.mean(sigma_variant):.4f}")
    print(f"  Reduction factor: {np.mean(sigma_variant) / np.mean(avg_spec.uncertainty):.2f} "
          f"(expected ~√3 = 1.73)")
    
    # Interpret quality flags
    print("\n6. Quality flag interpretation...")
    
    print(f"  Total flagged points in difference spectrum: "
          f"{np.sum(diff_spec.quality_flags != 0)}")
    
    flag_counts = {
        "BAD_PIXEL": np.sum((diff_spec.quality_flags & QualityFlags.BAD_PIXEL) != 0),
        "COSMIC_RAY": np.sum((diff_spec.quality_flags & QualityFlags.COSMIC_RAY) != 0),
        "SATURATED": np.sum((diff_spec.quality_flags & QualityFlags.SATURATED) != 0),
        "LOW_SNR": np.sum((diff_spec.quality_flags & QualityFlags.LOW_SNR) != 0),
    }
    
    print("  Flag breakdown:")
    for flag_name, count in flag_counts.items():
        if count > 0:
            print(f"    {flag_name}: {count} points")
    
    print("\n" + "=" * 70)
    print("Demo complete! Uncertainty propagation and quality flags working.")
    print("=" * 70)


if __name__ == "__main__":
    main()
