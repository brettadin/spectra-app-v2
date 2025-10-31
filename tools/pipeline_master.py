#!/usr/bin/env python3
"""
Master pipeline orchestrator for planetary spectral data acquisition.

This script automates the entire workflow:
1. Download bulk data from PDS
2. Convert binary files to CSV
3. Rank by quality
4. Merge best spectra
5. Copy to solar_system sample folder

Usage:
  # Mercury surface reflectance (complete pipeline)
  python tools/pipeline_master.py --target mercury --auto
  
  # Venus with custom settings
  python tools/pipeline_master.py --target venus --dataset virs_cdr --top-n 10
  
  # Dry run (show what would happen)
  python tools/pipeline_master.py --target mercury --dry-run
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path


def run_command(cmd: list[str], description: str, dry_run: bool = False) -> int:
    """Run a command and print status."""
    print("\n" + "=" * 70)
    print(f"STEP: {description}")
    print("=" * 70)
    print(f"Command: {' '.join(cmd)}")
    
    if dry_run:
        print("[DRY RUN - not executing]")
        return 0
    
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print(f"\n⚠️  Command failed with exit code {result.returncode}")
    return result.returncode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Master pipeline for planetary spectral data acquisition"
    )
    parser.add_argument(
        "--target",
        choices=["mercury", "venus"],
        required=True,
        help="Target planet",
    )
    parser.add_argument(
        "--dataset",
        default="auto",
        help="Dataset to download (auto=best for target)",
    )
    parser.add_argument(
        "--download-dir",
        type=Path,
        help="Download directory (auto-generated if not specified)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Final output directory (defaults to samples/solar_system/<target>)",
    )
    parser.add_argument(
        "--max-size",
        default="2G",
        help="Maximum download size (default: 2G)",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=5,
        help="Number of best spectra per range to merge (default: 5)",
    )
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Skip download step (use existing data)",
    )
    parser.add_argument(
        "--skip-parse",
        action="store_true",
        help="Skip CSV conversion (use existing CSVs)",
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        help="Run all steps automatically with defaults",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without executing",
    )
    
    args = parser.parse_args(argv)
    
    # Set defaults
    if args.download_dir is None:
        args.download_dir = Path(f"samples/SOLAR SYSTEM/{args.target.capitalize()}_bulk")
    
    if args.output_dir is None:
        args.output_dir = Path(f"samples/solar_system/{args.target}")
    
    # Select best dataset for target
    if args.dataset == "auto":
        if args.target == "mercury":
            datasets = ["uvvs_ddr_surface", "virs_ddr"]
        else:  # venus
            datasets = ["virs_cdr"]
    else:
        datasets = [args.dataset]
    
    print("=" * 70)
    print("PLANETARY SPECTRAL DATA PIPELINE")
    print("=" * 70)
    print(f"Target: {args.target.upper()}")
    print(f"Datasets: {', '.join(datasets)}")
    print(f"Download to: {args.download_dir}")
    print(f"Output to: {args.output_dir}")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")
    print()
    
    if not args.auto and not args.dry_run:
        response = input("Continue? [y/N]: ")
        if response.lower() != 'y':
            print("Aborted")
            return 1
    
    # Step 1: Download
    if not args.skip_download:
        for dataset in datasets:
            cmd = [
                "python", "tools/pds_downloader_native.py",
                "--dataset", dataset,
                "--target", args.target,
                "--output-dir", str(args.download_dir),
                "--max-size", args.max_size.rstrip('G'),  # Native downloader expects just the number
            ]
            if args.dry_run:
                cmd.append("--dry-run")
            
            result = run_command(
                cmd,
                f"Downloading {dataset}",
                dry_run=False,  # pds_downloader_native.py has its own dry-run
            )
            if result != 0:
                return result
    else:
        print("\n⏭️  Skipping download (using existing data)")
    
    # Step 2: Parse to CSV
    if not args.skip_parse:
        cmd = [
            "python", "tools/parse_messenger_mascs.py",
            str(args.download_dir),
            "--batch",
        ]
        result = run_command(
            cmd,
            "Converting binary files to CSV",
            dry_run=args.dry_run,
        )
        if result != 0 and not args.dry_run:
            return result
    else:
        print("\n⏭️  Skipping CSV conversion (using existing CSVs)")
    
    # Step 3: Rank and select best
    cmd = [
        "python", "tools/mascs_quality_filter.py",
        "--input", str(args.download_dir),
        "--rank",
    ]
    result = run_command(
        cmd,
        "Ranking spectra by quality",
        dry_run=args.dry_run,
    )
    if result != 0 and not args.dry_run:
        return result
    
    # Step 4: Merge best spectra
    composite_path = args.output_dir / f"{args.target}_composite.csv"
    cmd = [
        "python", "tools/mascs_quality_filter.py",
        "--input", str(args.download_dir),
        "--select-best", str(args.top_n),
        "--merge",
        "--output", str(composite_path),
    ]
    result = run_command(
        cmd,
        f"Merging top {args.top_n} spectra per range",
        dry_run=args.dry_run,
    )
    if result != 0 and not args.dry_run:
        return result
    
    # Step 5: Copy to solar_system folder
    if not args.dry_run:
        print("\n" + "=" * 70)
        print("STEP: Copying to solar_system folder")
        print("=" * 70)
        
        args.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Find best individual spectra by detector
        csv_files = list(args.download_dir.rglob("*_sci.csv"))
        
        # Copy composite as visible
        if composite_path.exists():
            dest = args.output_dir / f"{args.target}_visible.csv"
            shutil.copy2(composite_path, dest)
            print(f"✓ Copied composite to {dest}")
        
        # Find and copy best VIRS IR spectrum
        virs_files = [f for f in csv_files if 'virsnd' in f.name.lower()]
        if virs_files:
            # Use first one (already sorted by quality in previous step)
            src = virs_files[0]
            dest = args.output_dir / f"{args.target}_ir.csv"
            shutil.copy2(src, dest)
            print(f"✓ Copied IR spectrum to {dest}")
        
        # Find and copy best UVVS UV spectrum
        uvvs_files = [f for f in csv_files if any(x in f.name.lower() for x in ['ufc', 'umc', 'uvc'])]
        if uvvs_files:
            src = uvvs_files[0]
            dest = args.output_dir / f"{args.target}_uv.csv"
            shutil.copy2(src, dest)
            print(f"✓ Copied UV spectrum to {dest}")
    
    print("\n" + "=" * 70)
    print("✅ PIPELINE COMPLETE")
    print("=" * 70)
    print(f"\nFinal spectra saved to: {args.output_dir}")
    print("\nYou can now:")
    print("  1. Load spectra in your app: 'Load Solar System Samples' button")
    print(f"  2. View raw data: {args.download_dir}")
    print(f"  3. Run custom analysis on CSVs in {args.download_dir}")
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
