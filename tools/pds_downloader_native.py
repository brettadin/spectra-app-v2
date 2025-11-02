#!/usr/bin/env python3
"""
Native Python PDS downloader - no external dependencies required.

Recursively downloads files from PDS archives using only requests and urllib.
Replacement for wget-based downloader that works on all platforms without additional installs.
"""

import argparse
import re
import sys
from pathlib import Path
from urllib.parse import urljoin, urlparse
import time

try:
    import requests
except ImportError:
    print("ERROR: requests library required")
    print("Install with: pip install requests")
    sys.exit(1)

# PDS dataset definitions - MASCS optical spectroscopy ONLY
DATASETS = {
    # MESSENGER MASCS - Mercury/Venus OPTICAL SPECTROMETERS ONLY
    "uvvs_cdr": {
        "url": "https://pds-geosciences.wustl.edu/messenger/mess-e_v_h-mascs-3-uvvs-cdr-caldata-v1/messmas_1001/data/cdr/uvvs/",
        "description": "UVVS calibrated radiance (FUV 115-190nm, MUV 160-320nm, VIS 250-600nm)",
        "size_est": "~2 GB",
        "file_types": [".DAT", ".LBL", ".FMT"],
        "required_patterns": ["ufc_", "umc_", "uvc_"],  # UVVS CDR science files only
        "exclude_patterns": ["_hdr.dat", "_eng.dat", "index", "catalog"],  # No headers/engineering
    },
    "virs_cdr": {
        "url": "https://pds-geosciences.wustl.edu/messenger/mess-e_v_h-mascs-3-virs-cdr-caldata-v1/messmas_2001/data/cdr/",
        "description": "VIRS calibrated radiance (VIS 300-1050nm, NIR 850-1450nm)",
        "size_est": "~5 GB",
        "file_types": [".DAT", ".LBL", ".FMT"],
        "required_patterns": ["vnc_", "vvc_"],  # VIRS CDR science files only
        "exclude_patterns": ["_hdr.dat", "_eng.dat", "index", "catalog"],
    },
    "uvvs_ddr": {
        "url": "https://pds-geosciences.wustl.edu/messenger/mess-h-mascs-4-uvvs-ddr-v1/messmas_4001/data/ddr/",
        "description": "UVVS derived surface reflectance (binned, high quality)",
        "size_est": "~500 MB",
        "file_types": [".DAT", ".LBL", ".FMT"],
        "required_patterns": ["uvs_", "uvd_"],  # UVVS DDR science files
        "exclude_patterns": ["_eng.dat", "index", "catalog"],
    },
    "virs_ddr": {
        "url": "https://pds-geosciences.wustl.edu/messenger/mess-h-mascs-4-virs-ddr-v1/messmas_4002/data/ddr/",
        "description": "VIRS derived surface reflectance (high quality)",
        "size_est": "~3 GB",
        "file_types": [".DAT", ".LBL", ".FMT"],
        "required_patterns": ["vnd_", "vvd_"],  # VIRS DDR science files
        "exclude_patterns": ["_eng.dat", "index", "catalog"],
    },
}


class PDSDownloader:
    """Recursive PDS archive downloader using requests - MASCS optical spectroscopy only."""
    
    def __init__(self, base_url: str, output_dir: Path, max_size_gb: float = None, 
                 file_types: list = None, dry_run: bool = False,
                 required_patterns: list = None, exclude_patterns: list = None):
        self.base_url = base_url.rstrip('/')
        self.output_dir = output_dir
        self.max_size_bytes = int(max_size_gb * 1024**3) if max_size_gb else None
        self.file_types = [ft.upper() for ft in file_types] if file_types else None
        self.required_patterns = required_patterns or []
        self.exclude_patterns = exclude_patterns or []
        self.dry_run = dry_run
        
        self.total_downloaded = 0
        self.file_count = 0
        self.skipped_count = 0
        self.filtered_count = 0
        self.visited_urls = set()
    
    def should_download_file(self, filename: str) -> bool:
        """Check if file matches our STRICT criteria."""
        fname_lower = filename.lower()
        
        # Must match file type
        if self.file_types and not any(filename.upper().endswith(ft) for ft in self.file_types):
            return False
        
        # Must match at least one required pattern (MASCS science files only)
        if self.required_patterns:
            if not any(pattern.lower() in fname_lower for pattern in self.required_patterns):
                self.filtered_count += 1
                return False
        
        # Must NOT match any exclude pattern (no engineering/header files)
        if self.exclude_patterns:
            if any(pattern.lower() in fname_lower for pattern in self.exclude_patterns):
                self.filtered_count += 1
                return False
        
        return True
    
    def parse_directory_listing(self, html: str, current_url: str) -> tuple[list[str], list[str]]:
        """Extract file and subdirectory links from Apache-style directory listing."""
        files = []
        dirs = []
        
        # Apache directory listing links: <a href="...">
        link_pattern = re.compile(r'<a\s+href="([^"]+)"[^>]*>([^<]+)</a>', re.IGNORECASE)
        
        for match in link_pattern.finditer(html):
            href = match.group(1)
            text = match.group(2).strip()
            
            # Skip parent directory, query strings, absolute URLs to different domains
            if href in ['../', '../', '/', ''] or href.startswith('?') or href.startswith('http'):
                continue
            if href.startswith('mailto:'):
                continue
                
            # Build full URL
            full_url = urljoin(current_url, href)
            
            # Classify as directory or file
            if href.endswith('/'):
                dirs.append(full_url)
            else:
                files.append(full_url)
        
        return files, dirs
    
    def download_file(self, url: str) -> bool:
        """Download a single file."""
        try:
            # Get relative path from base URL
            rel_path = url.replace(self.base_url, '').lstrip('/')
            output_path = self.output_dir / rel_path
            
            # Check if already exists
            if output_path.exists():
                print(f"  ⏭️  Skip (exists): {rel_path}")
                self.skipped_count += 1
                return True
            
            if self.dry_run:
                print(f"  📄 Would download: {rel_path}")
                self.file_count += 1
                return True
            
            # Make HEAD request to get file size
            head_resp = requests.head(url, allow_redirects=True, timeout=10)
            if head_resp.status_code != 200:
                print(f"  ⚠️  Skip (not found): {rel_path}")
                return False
            
            file_size = int(head_resp.headers.get('content-length', 0))
            
            # Check quota
            if self.max_size_bytes and (self.total_downloaded + file_size) > self.max_size_bytes:
                print(f"  🛑 Quota reached ({self.total_downloaded / 1024**3:.2f} GB)")
                return False
            
            # Download file
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            resp = requests.get(url, stream=True, timeout=30)
            resp.raise_for_status()
            
            with open(output_path, 'wb') as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            self.total_downloaded += file_size
            self.file_count += 1
            size_mb = file_size / 1024**2
            print(f"  ✅ Downloaded: {rel_path} ({size_mb:.2f} MB)")
            return True
            
        except Exception as e:
            print(f"  ❌ Error downloading {url}: {e}")
            return False
    
    def crawl_directory(self, url: str, depth: int = 0) -> bool:
        """Recursively crawl directory and download files."""
        # Avoid infinite loops
        if url in self.visited_urls:
            return True
        self.visited_urls.add(url)
        
        # Check quota
        if self.max_size_bytes and self.total_downloaded >= self.max_size_bytes:
            print(f"  🛑 Quota reached, stopping crawl")
            return False
        
        indent = "  " * depth
        rel_path = url.replace(self.base_url, '').lstrip('/') or '/'
        print(f"{indent}📁 Scanning: {rel_path}")
        
        try:
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            
            files, subdirs = self.parse_directory_listing(resp.text, url)
            
            # Download files in this directory
            for file_url in files:
                filename = file_url.split('/')[-1]
                if self.should_download_file(filename):
                    if not self.download_file(file_url):
                        # Check if quota reached
                        if self.max_size_bytes and self.total_downloaded >= self.max_size_bytes:
                            return False
            
            # Recurse into subdirectories
            for subdir_url in subdirs:
                if not self.crawl_directory(subdir_url, depth + 1):
                    return False  # Quota reached
            
            return True
            
        except Exception as e:
            print(f"{indent}❌ Error scanning {url}: {e}")
            return True  # Continue with other directories
    
    def run(self):
        """Start the download process."""
        print(f"Starting {'DRY RUN' if self.dry_run else 'download'} from: {self.base_url}")
        print(f"Output directory: {self.output_dir}")
        if self.max_size_bytes:
            print(f"Size limit: {self.max_size_bytes / 1024**3:.2f} GB")
        if self.file_types:
            print(f"File types: {', '.join(self.file_types)}")
        print()
        
        start_time = time.time()
        self.crawl_directory(self.base_url)
        elapsed = time.time() - start_time
        
        print()
        print("=" * 60)
        print("DOWNLOAD SUMMARY")
        print("=" * 60)
        print(f"Files downloaded: {self.file_count}")
        print(f"Files skipped (existing): {self.skipped_count}")
        print(f"Files filtered (non-MASCS/engineering): {self.filtered_count}")
        print(f"Total size: {self.total_downloaded / 1024**3:.2f} GB")
        print(f"Time elapsed: {elapsed / 60:.1f} minutes")
        print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Download MESSENGER MASCS data from PDS archives (native Python, no wget required)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download UVVS CDR (limit 2GB)
  python pds_downloader_native.py --dataset uvvs_cdr --output-dir samples/SOLAR_SYSTEM/Mercury_bulk --max-size 2

  # Download VIRS CDR (limit 5GB)
  python pds_downloader_native.py --dataset virs_cdr --output-dir samples/SOLAR_SYSTEM/Mercury_bulk --max-size 5

  # Dry run to preview what would be downloaded
  python pds_downloader_native.py --dataset uvvs_cdr --output-dir test --dry-run

Available datasets: uvvs_cdr, virs_cdr, uvvs_edr, virs_edr
        """
    )
    
    parser.add_argument("--dataset", required=True, choices=list(DATASETS.keys()),
                        help="Dataset to download")
    parser.add_argument("--output-dir", required=True, type=Path,
                        help="Output directory for downloaded files")
    parser.add_argument("--max-size", type=float,
                        help="Maximum download size in GB (e.g., 2 = 2GB)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview what would be downloaded without downloading")
    parser.add_argument("--target", default="mercury",
                        help="Target body (for display only)")
    
    args = parser.parse_args()
    
    # Get dataset info
    dataset_info = DATASETS[args.dataset]
    
    print("=" * 70)
    print("MESSENGER MASCS Native Python Downloader")
    print("=" * 70)
    print(f"Dataset: {args.dataset}")
    print(f"Description: {dataset_info['description']}")
    print(f"Est. size: {dataset_info['size_est']}")
    print(f"URL: {dataset_info['url']}")
    print(f"Output: {args.output_dir}")
    if args.dry_run:
        print("\nDRY RUN - no files will be downloaded")
    print()
    
    # Create downloader and run
    downloader = PDSDownloader(
        base_url=dataset_info['url'],
        output_dir=args.output_dir,
        max_size_gb=args.max_size,
        file_types=dataset_info.get('file_types'),
        required_patterns=dataset_info.get('required_patterns'),
        exclude_patterns=dataset_info.get('exclude_patterns'),
        dry_run=args.dry_run
    )
    
    try:
        downloader.run()
        print("\n✅ Download complete!")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Download interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Download failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
