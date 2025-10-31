#!/usr/bin/env python3
"""
Quality filter and merge tool for MASCS spectral data.

After bulk downloading hundreds of MASCS observations, this tool:
1. Ranks spectra by quality metrics (SNR, coverage, geometry)
2. Selects best observations per wavelength range
3. Merges multiple spectra into high-resolution composites
4. Stitches FUV+MUV+VIS+NIR into full 100-1500nm coverage

Usage:
  # Rank all Mercury surface spectra
  python tools/mascs_quality_filter.py --input "samples/SOLAR SYSTEM/Mercury_bulk" --rank
  
  # Select best 10 spectra per detector
  python tools/mascs_quality_filter.py --input "samples/SOLAR SYSTEM/Mercury_bulk" --select-best 10
  
  # Create merged high-res spectrum
  python tools/mascs_quality_filter.py --input "samples/SOLAR SYSTEM/Mercury_bulk" --merge --output mercury_composite.csv
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

import numpy as np
import pandas as pd


@dataclass
class SpectrumQuality:
    """Quality metrics for a MASCS spectrum."""
    csv_path: Path
    product_id: str
    detector: str
    product_type: str
    
    # Coverage
    num_points: int = 0
    wavelength_range: tuple[float, float] = (0.0, 0.0)
    wavelength_span: float = 0.0
    
    # Signal quality
    mean_value: float = 0.0
    snr_estimate: float = 0.0
    
    # Geometry (from metadata if available)
    incidence_angle: float | None = None
    emission_angle: float | None = None
    phase_angle: float | None = None
    
    # Composite score
    quality_score: float = 0.0
    
    def compute_score(self) -> float:
        """Compute overall quality score (0-100)."""
        score = 0.0
        
        # Coverage: more points = better (up to 30 points)
        score += min(30, self.num_points / 10)
        
        # Range: wider = better (up to 20 points)
        # Normalize to typical MASCS ranges
        if self.wavelength_span > 0:
            if self.detector == "VIRS":
                score += min(20, (self.wavelength_span / 1200) * 20)  # VIRS: 300-1450nm
            else:
                score += min(20, (self.wavelength_span / 400) * 20)  # UVVS: ~400nm typical
        
        # SNR: higher = better (up to 30 points)
        if self.snr_estimate > 0:
            score += min(30, np.log10(self.snr_estimate + 1) * 10)
        
        # Geometry: favor nadir/low phase (up to 20 points)
        if self.phase_angle is not None:
            # Prefer phase angles 30-60° (good for surface detail)
            geom_score = 20 * (1 - abs(self.phase_angle - 45) / 90)
            score += max(0, geom_score)
        else:
            score += 10  # Default if no geometry info
        
        self.quality_score = score
        return score


def load_spectrum_csv(csv_path: Path) -> tuple[np.ndarray, np.ndarray] | None:
    """Load wavelength and flux from CSV."""
    try:
        df = pd.read_csv(csv_path, comment='#')
        wl = df.iloc[:, 0].values
        flux = df.iloc[:, 1].values
        return wl, flux
    except Exception:
        return None


def analyze_spectrum(csv_path: Path) -> SpectrumQuality | None:
    """Analyze a single spectrum and compute quality metrics."""
    
    # Parse filename for metadata
    name = csv_path.stem
    parts = name.split('_')
    
    detector = "UNKNOWN"
    if name.startswith('ufc') or name.startswith('umc') or name.startswith('uvc'):
        detector = "UVVS"
    elif name.startswith('virsn') or name.startswith('virsv'):
        detector = "VIRS"
    
    product_type = "CDR" if '_cdr' in name.lower() or 'c_' in name else "DDR"
    
    quality = SpectrumQuality(
        csv_path=csv_path,
        product_id=name,
        detector=detector,
        product_type=product_type,
    )
    
    # Load spectrum
    result = load_spectrum_csv(csv_path)
    if result is None:
        return None
    
    wl, flux = result
    
    # Filter valid data
    valid = (flux > 0) & np.isfinite(flux)
    if valid.sum() < 5:
        return None
    
    wl_valid = wl[valid]
    flux_valid = flux[valid]
    
    # Coverage metrics
    quality.num_points = len(wl_valid)
    quality.wavelength_range = (float(wl_valid.min()), float(wl_valid.max()))
    quality.wavelength_span = float(wl_valid.max() - wl_valid.min())
    
    # Signal metrics
    quality.mean_value = float(np.mean(flux_valid))
    
    # Estimate SNR from variability
    if len(flux_valid) > 10:
        # Use median absolute deviation as noise estimate
        median_flux = np.median(flux_valid)
        mad = np.median(np.abs(flux_valid - median_flux))
        if mad > 0:
            quality.snr_estimate = float(median_flux / (1.4826 * mad))
    
    # TODO: Parse geometry from label file if available
    
    # Compute score
    quality.compute_score()
    
    return quality


def rank_spectra(csv_files: List[Path], verbose: bool = True) -> List[SpectrumQuality]:
    """Analyze and rank all spectra by quality."""
    
    print(f"Analyzing {len(csv_files)} spectra...")
    
    qualities: List[SpectrumQuality] = []
    for csv_file in csv_files:
        quality = analyze_spectrum(csv_file)
        if quality:
            qualities.append(quality)
    
    # Sort by score (descending)
    qualities.sort(key=lambda q: q.quality_score, reverse=True)
    
    if verbose:
        print(f"\nAnalyzed {len(qualities)} valid spectra")
        print("\nTop 10 spectra:")
        print("-" * 100)
        print(f"{'Rank':<6} {'Product ID':<35} {'Detector':<8} {'Points':<8} {'Range (nm)':<20} {'Score':<8}")
        print("-" * 100)
        for i, q in enumerate(qualities[:10], 1):
            wl_range = f"{q.wavelength_range[0]:.0f}-{q.wavelength_range[1]:.0f}"
            print(f"{i:<6} {q.product_id:<35} {q.detector:<8} {q.num_points:<8} {wl_range:<20} {q.quality_score:<8.1f}")
    
    return qualities


def select_best_by_range(
    qualities: List[SpectrumQuality],
    detector: str | None = None,
    n_per_range: int = 3,
) -> List[SpectrumQuality]:
    """Select best spectra covering different wavelength ranges."""
    
    # Filter by detector if specified
    if detector:
        qualities = [q for q in qualities if q.detector == detector]
    
    # Group by wavelength range (binned)
    range_groups: dict[str, List[SpectrumQuality]] = {}
    
    for q in qualities:
        # Bin into 100nm ranges
        min_wl = int(q.wavelength_range[0] / 100) * 100
        range_key = f"{min_wl}-{min_wl+100}"
        
        if range_key not in range_groups:
            range_groups[range_key] = []
        range_groups[range_key].append(q)
    
    # Select top N from each range
    selected: List[SpectrumQuality] = []
    for range_key, group in sorted(range_groups.items()):
        group.sort(key=lambda q: q.quality_score, reverse=True)
        selected.extend(group[:n_per_range])
    
    return selected


def merge_spectra(
    qualities: List[SpectrumQuality],
    output_path: Path,
    wavelength_grid: np.ndarray | None = None,
) -> None:
    """Merge multiple spectra into a single high-resolution composite."""
    
    print(f"\nMerging {len(qualities)} spectra...")
    
    # Load all spectra
    all_wl: List[np.ndarray] = []
    all_flux: List[np.ndarray] = []
    
    for q in qualities:
        result = load_spectrum_csv(q.csv_path)
        if result:
            wl, flux = result
            valid = (flux > 0) & np.isfinite(flux)
            all_wl.append(wl[valid])
            all_flux.append(flux[valid])
    
    # Determine wavelength grid
    if wavelength_grid is None:
        min_wl = min(wl.min() for wl in all_wl)
        max_wl = max(wl.max() for wl in all_wl)
        # 0.5 nm resolution
        wavelength_grid = np.arange(min_wl, max_wl + 0.5, 0.5)
    
    # Interpolate and average all spectra onto common grid
    merged_flux = np.zeros_like(wavelength_grid)
    counts = np.zeros_like(wavelength_grid)
    
    for wl, flux in zip(all_wl, all_flux):
        # Interpolate onto grid
        interp_flux = np.interp(wavelength_grid, wl, flux, left=np.nan, right=np.nan)
        valid = np.isfinite(interp_flux)
        merged_flux[valid] += interp_flux[valid]
        counts[valid] += 1
    
    # Average
    valid = counts > 0
    merged_flux[valid] /= counts[valid]
    
    # Write output
    with output_path.open('w') as f:
        f.write("# Merged MESSENGER MASCS composite spectrum\n")
        f.write(f"# Created from {len(qualities)} observations\n")
        f.write("# Units: wavelength_nm, reflectance_or_radiance\n")
        f.write("#\n")
        f.write("wavelength_nm,flux\n")
        
        for wl, flux in zip(wavelength_grid[valid], merged_flux[valid]):
            f.write(f"{wl:.2f},{flux:.6e}\n")
    
    print(f"✓ Merged spectrum saved to {output_path}")
    print(f"  Wavelength range: {wavelength_grid[valid].min():.1f}-{wavelength_grid[valid].max():.1f} nm")
    print(f"  Total points: {valid.sum()}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Quality filter and merge MASCS spectra")
    parser.add_argument("--input", type=Path, required=True, help="Directory with CSV spectra")
    parser.add_argument("--rank", action="store_true", help="Rank all spectra by quality")
    parser.add_argument("--select-best", type=int, metavar="N", help="Select best N spectra per range")
    parser.add_argument("--detector", choices=["UVVS", "VIRS"], help="Filter by detector")
    parser.add_argument("--merge", action="store_true", help="Merge selected spectra")
    parser.add_argument("--output", type=Path, default=Path("merged_spectrum.csv"), help="Output file for merge")
    
    args = parser.parse_args(argv)
    
    # Find all CSV files
    csv_files = list(args.input.rglob("*_sci.csv"))
    
    if not csv_files:
        print(f"No CSV files found in {args.input}")
        print("Run parse_messenger_mascs.py --batch first")
        return 1
    
    print(f"Found {len(csv_files)} CSV files")
    
    # Rank all spectra
    qualities = rank_spectra(csv_files, verbose=args.rank)
    
    # Select best if requested
    if args.select_best:
        selected = select_best_by_range(qualities, detector=args.detector, n_per_range=args.select_best)
        print(f"\nSelected {len(selected)} best spectra")
        qualities = selected
    
    # Merge if requested
    if args.merge:
        if not qualities:
            print("No spectra to merge")
            return 1
        merge_spectra(qualities, args.output)
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
