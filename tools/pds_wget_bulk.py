#!/usr/bin/env python3
"""
Practical bulk downloader for MESSENGER MASCS data from PDS archives.

Uses wget to recursively download entire dataset directories from PDS.
This is the fastest way to get hundreds/thousands of spectra at once.

Usage:
  # Download all Mercury UVVS surface reflectance (DDR)
  python tools/pds_wget_bulk.py --dataset uvvs_ddr_surface --target mercury
  
  # Download Venus flyby VIRS calibrated data
  python tools/pds_wget_bulk.py --dataset virs_cdr --target venus
  
  # Custom download with filters
  python tools/pds_wget_bulk.py --dataset uvvs_cdr --filter "*/muv/*" --max-size 500M
"""
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path
from typing import List


# PDS MESSENGER MASCS Archive URLs
PDS_MESSENGER_BASE = "https://pds-geosciences.wustl.edu/messenger"

DATASETS = {
    # UVVS (Ultraviolet/Visible Spectrometer)
    "uvvs_edr": {
        "url": f"{PDS_MESSENGER_BASE}/mess-h-mascs-2-uvvs-edr/messmas_2001/data/",
        "desc": "UVVS raw data (uncalibrated)",
        "size_est": "~2 GB",
    },
    "uvvs_cdr": {
        "url": f"{PDS_MESSENGER_BASE}/mess-h-mascs-3-uvvs-cdr/messmas_3001/data/",
        "desc": "UVVS calibrated radiance (FUV/MUV/VIS)",
        "size_est": "~5 GB",
    },
    "uvvs_ddr_surface": {
        "url": f"{PDS_MESSENGER_BASE}/mess-h-mascs-4-uvvs-ddr/messmas_4001/data/ddr/uvvs_surface/",
        "desc": "UVVS Mercury surface reflectance (MUV, binned)",
        "size_est": "~500 MB",
    },
    "uvvs_ddr_atmosphere": {
        "url": f"{PDS_MESSENGER_BASE}/mess-h-mascs-4-uvvs-ddr/messmas_4001/data/ddr/uvvs_atmosphere/",
        "desc": "UVVS Mercury atmosphere (Na, Ca, Mg emission)",
        "size_est": "~200 MB",
    },
    
    # VIRS (Visible/Infrared Spectrometer)
    "virs_edr": {
        "url": f"{PDS_MESSENGER_BASE}/mess-h-mascs-2-virs-edr/messmas_2002/data/",
        "desc": "VIRS raw data (uncalibrated)",
        "size_est": "~10 GB",
    },
    "virs_cdr": {
        "url": f"{PDS_MESSENGER_BASE}/mess-h-mascs-3-virs-cdr/messmas_3002/data/",
        "desc": "VIRS calibrated radiance (VIS 300-1050nm, NIR 300-1450nm)",
        "size_est": "~15 GB",
    },
    "virs_ddr": {
        "url": f"{PDS_MESSENGER_BASE}/mess-h-mascs-4-virs-ddr/messmas_4002/data/ddr/",
        "desc": "VIRS Mercury surface reflectance (full spectrum)",
        "size_est": "~8 GB",
    },
}


def run_wget(
    url: str,
    output_dir: Path,
    accept_pattern: str | None = None,
    reject_pattern: str | None = None,
    max_size: str | None = None,
    dry_run: bool = False,
) -> int:
    """Run wget to recursively download from PDS."""
    
    cmd: List[str] = [
        "wget",
        "-r",  # Recursive
        "-np",  # No parent directories
        "-nH",  # No host directory
        "--cut-dirs=3",  # Remove path prefix
        "-R", "index.html*",  # Reject index files
        "--no-check-certificate",  # Some PDS certs are old
        "-P", str(output_dir),  # Output directory
    ]
    
    # File filters
    if accept_pattern:
        cmd.extend(["-A", accept_pattern])
    if reject_pattern:
        cmd.extend(["-R", reject_pattern])
    
    # Size limit
    if max_size:
        cmd.extend(["--quota", max_size])
    
    # Dry run (show what would be downloaded)
    if dry_run:
        cmd.append("--spider")
    
    cmd.append(url)
    
    print("Running command:")
    print(" ".join(cmd))
    print()
    
    try:
        result = subprocess.run(cmd, check=False)
        return result.returncode
    except FileNotFoundError:
        print("ERROR: wget not found")
        print("Install wget:")
        print("  Windows: choco install wget  OR  download from https://eternallybored.org/misc/wget/")
        print("  Linux: apt install wget / yum install wget")
        print("  Mac: brew install wget")
        return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Bulk download MESSENGER MASCS data using wget",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download all Mercury surface reflectance (best for science)
  python tools/pds_wget_bulk.py --dataset uvvs_ddr_surface
  
  # Download VIRS NIR spectra only
  python tools/pds_wget_bulk.py --dataset virs_ddr --accept "*/nir/*.dat,*.lbl"
  
  # Dry run (see what would download)
  python tools/pds_wget_bulk.py --dataset uvvs_cdr --dry-run
  
  # Limit download size
  python tools/pds_wget_bulk.py --dataset virs_cdr --max-size 1G
""",
    )
    
    parser.add_argument(
        "--dataset",
        choices=list(DATASETS.keys()),
        required=True,
        help="Dataset to download",
    )
    parser.add_argument(
        "--target",
        choices=["mercury", "venus", "earth"],
        default="mercury",
        help="Target body (note: most data is Mercury orbit)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("samples/SOLAR SYSTEM/Mercury_bulk"),
        help="Output directory",
    )
    parser.add_argument(
        "--accept",
        help="File patterns to accept (comma-separated, e.g., '*.dat,*.lbl')",
    )
    parser.add_argument(
        "--reject",
        help="File patterns to reject (comma-separated)",
    )
    parser.add_argument(
        "--max-size",
        help="Maximum download size (e.g., 500M, 2G)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be downloaded without downloading",
    )
    
    args = parser.parse_args(argv)
    
    dataset = DATASETS[args.dataset]
    
    print("=" * 70)
    print("MESSENGER MASCS Bulk Downloader (wget)")
    print("=" * 70)
    print(f"Dataset: {args.dataset}")
    print(f"Description: {dataset['desc']}")
    print(f"Est. size: {dataset['size_est']}")
    print(f"URL: {dataset['url']}")
    print(f"Output: {args.output_dir}")
    print()
    
    if args.dry_run:
        print("DRY RUN - no files will be downloaded")
        print()
    
    # Create output directory
    args.output_dir.mkdir(parents=True, exist_ok=True)
    
    # Run wget
    result = run_wget(
        url=dataset["url"],
        output_dir=args.output_dir,
        accept_pattern=args.accept,
        reject_pattern=args.reject,
        max_size=args.max_size,
        dry_run=args.dry_run,
    )
    
    if result == 0:
        print("\n✓ Download complete!")
        print(f"Files saved to: {args.output_dir}")
        print("\nNext steps:")
        print("  1. Run parse_messenger_mascs.py --batch to convert to CSV")
        print("  2. Use quality filter script to select best spectra")
        print("  3. Merge into composite high-resolution datasets")
    else:
        print("\n⚠️  Download failed or incomplete")
    
    return result


if __name__ == "__main__":
    raise SystemExit(main())
