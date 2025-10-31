#!/usr/bin/env python3
"""
Bulk download MESSENGER MASCS data from NASA PDS archives.

Downloads calibrated (CDR) and derived (DDR) spectral data for Mercury and Venus
from the Planetary Data System (PDS) via ODE (Orbital Data Explorer) API.

Usage:
  # Download all Mercury surface reflectance spectra
  python tools/pds_mascs_bulk_download.py --target mercury --product-type ddr --output-dir "samples/SOLAR SYSTEM/Mercury"
  
  # Download Venus flyby data
  python tools/pds_mascs_bulk_download.py --target venus --mission-phase VF1,VF2 --max-files 100
  
  # Download specific instrument/detector
  python tools/pds_mascs_bulk_download.py --target mercury --detector MUV --product-type cdr
"""
from __future__ import annotations

import argparse
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import urlencode

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


@dataclass
class MASCSProduct:
    """Metadata for a MASCS data product."""
    product_id: str
    target: str
    detector: str  # UVVS or VIRS
    product_type: str  # EDR, CDR, DDR
    mission_phase: str
    start_time: str
    stop_time: str
    label_url: str
    data_url: str
    file_size: int | None = None


class PDSMASCSDownloader:
    """Download MASCS data from PDS ODE."""
    
    # PDS ODE API base (Washington University in St. Louis)
    ODE_BASE = "https://ode.rsl.wustl.edu/mars/api"
    
    # MESSENGER MASCS dataset IDs
    DATASETS = {
        "uvvs_edr": "MESS-E/V/H-MASCS-2-UVVS-EDR-V1.0",
        "uvvs_cdr": "MESS-E/V/H-MASCS-3-UVVS-CDR-CALDATA-V1.0",
        "uvvs_ddr": "MESS-E/V/H-MASCS-4-UVVS-DDR-V1.0",
        "virs_edr": "MESS-E/V/H-MASCS-2-VIRS-EDR-V1.0",
        "virs_cdr": "MESS-E/V/H-MASCS-3-VIRS-CDR-CALDATA-V1.0",
        "virs_ddr": "MESS-E/V/H-MASCS-4-VIRS-DDR-V1.0",
    }
    
    def __init__(self, max_workers: int = 4):
        self.session = self._create_session()
        self.max_workers = max_workers
    
    def _create_session(self) -> requests.Session:
        """Create requests session with retry logic."""
        session = requests.Session()
        retry = Retry(
            total=5,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session
    
    def search_products(
        self,
        target: str = "mercury",
        product_type: str = "ddr",
        detector: str | None = None,
        mission_phase: List[str] | None = None,
        max_results: int = 1000,
    ) -> List[MASCSProduct]:
        """
        Search for MASCS products via PDS ODE.
        
        Note: ODE interface for MESSENGER is limited. For production use,
        consider direct PDS Node access or using pds4_tools library.
        """
        products: List[MASCSProduct] = []
        
        # For now, we'll use a simplified search approach
        # In production, you'd query the PDS directly via their API
        # or use the pds4_tools Python library
        
        print(f"Searching PDS for {target.upper()} MASCS {product_type.upper()} data...")
        print("Note: Using fallback mode - for bulk downloads, use direct PDS access")
        
        # Placeholder for direct PDS query implementation
        # This would involve:
        # 1. Query PDS MASCS dataset catalog
        # 2. Filter by target, product type, detector
        # 3. Build download URLs from PDS directory structure
        
        return products
    
    def download_product(
        self,
        product: MASCSProduct,
        output_dir: Path,
        skip_existing: bool = True,
    ) -> Path | None:
        """Download a single MASCS product (label + data file)."""
        
        # Create output subdirectory
        subdir = output_dir / product.detector.lower() / product.product_type.lower()
        subdir.mkdir(parents=True, exist_ok=True)
        
        label_file = subdir / f"{product.product_id.lower()}.lbl"
        data_file = subdir / f"{product.product_id.lower()}.dat"
        
        # Skip if already downloaded
        if skip_existing and label_file.exists() and data_file.exists():
            print(f"  Skipping {product.product_id} (already exists)")
            return data_file
        
        try:
            # Download label
            print(f"  Downloading {product.product_id} label...")
            resp = self.session.get(product.label_url, timeout=30)
            resp.raise_for_status()
            label_file.write_bytes(resp.content)
            
            # Download data file
            print(f"  Downloading {product.product_id} data...")
            resp = self.session.get(product.data_url, timeout=120, stream=True)
            resp.raise_for_status()
            
            with data_file.open("wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            print(f"  ✓ {product.product_id}")
            return data_file
            
        except Exception as e:
            print(f"  ERROR downloading {product.product_id}: {e}")
            return None
    
    def download_batch(
        self,
        products: List[MASCSProduct],
        output_dir: Path,
        skip_existing: bool = True,
    ) -> List[Path]:
        """Download multiple products in parallel."""
        
        downloaded: List[Path] = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(
                    self.download_product,
                    product,
                    output_dir,
                    skip_existing,
                ): product
                for product in products
            }
            
            for future in as_completed(futures):
                result = future.result()
                if result:
                    downloaded.append(result)
        
        return downloaded


def build_pds_url_list(
    target: str,
    product_type: str,
    detector: str | None = None,
) -> List[MASCSProduct]:
    """
    Build list of MASCS product URLs from known PDS directory structure.
    
    This is a simplified version - for production, you'd parse PDS index files.
    """
    products: List[MASCSProduct] = []
    
    # PDS MESSENGER MASCS data is hosted at:
    # https://pds-geosciences.wustl.edu/messenger/mess-h-mascs-[3/4]-[cdr/ddr]/
    
    # Example structure for surface DDR:
    # mess-h-mascs-4-uvvs-ddr/messmas_4001/data/ddr/uvvs_surface/
    
    # For bulk access, you'd:
    # 1. Download and parse the index.tab file from the dataset
    # 2. Extract all product IDs and build URLs
    # 3. Filter by criteria
    
    print("Building product list from PDS structure...")
    print("For full implementation, parse index.tab files from:")
    print("  https://pds-geosciences.wustl.edu/messenger/")
    
    return products


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Bulk download MESSENGER MASCS spectral data from PDS"
    )
    parser.add_argument(
        "--target",
        choices=["mercury", "venus", "earth"],
        default="mercury",
        help="Target body",
    )
    parser.add_argument(
        "--product-type",
        choices=["edr", "cdr", "ddr", "all"],
        default="ddr",
        help="Data product level",
    )
    parser.add_argument(
        "--detector",
        choices=["uvvs", "virs", "all"],
        default="all",
        help="Instrument detector",
    )
    parser.add_argument(
        "--mission-phase",
        help="Comma-separated mission phases (e.g., ORB,OB2)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("samples/SOLAR SYSTEM/bulk_downloads"),
        help="Output directory",
    )
    parser.add_argument(
        "--max-files",
        type=int,
        default=0,
        help="Maximum files to download (0 = unlimited)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Number of parallel download workers",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        default=True,
        help="Skip already downloaded files",
    )
    
    args = parser.parse_args(argv)
    
    print("=" * 60)
    print("MESSENGER MASCS Bulk Downloader")
    print("=" * 60)
    print(f"Target: {args.target.upper()}")
    print(f"Product type: {args.product_type.upper()}")
    print(f"Output: {args.output_dir}")
    print()
    
    # Create downloader
    downloader = PDSMASCSDownloader(max_workers=args.workers)
    
    # Search for products
    products = build_pds_url_list(
        target=args.target,
        product_type=args.product_type,
        detector=args.detector,
    )
    
    if not products:
        print("\n⚠️  No products found with current search.")
        print("\nNOTE: This is a template script.")
        print("For production use, implement one of these approaches:")
        print("  1. Parse PDS index.tab files directly")
        print("  2. Use the pds4_tools Python library")
        print("  3. Use PDS Imaging Node's REST API")
        print("  4. Download entire dataset volumes via wget")
        print("\nExample wget command for full dataset:")
        print("  wget -r -np -nH --cut-dirs=2 -R 'index.html*' \\")
        print("    https://pds-geosciences.wustl.edu/messenger/mess-h-mascs-4-uvvs-ddr/")
        return 1
    
    # Limit results
    if args.max_files > 0:
        products = products[:args.max_files]
    
    print(f"Found {len(products)} products to download")
    
    # Download
    args.output_dir.mkdir(parents=True, exist_ok=True)
    downloaded = downloader.download_batch(
        products,
        args.output_dir,
        skip_existing=args.skip_existing,
    )
    
    print(f"\n✓ Downloaded {len(downloaded)} files to {args.output_dir}")
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
