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

# PDS dataset definitions (same as pds_wget_bulk.py)
DATASETS = {
    # MESSENGER MASCS - Mercury/Venus
    "uvvs_ddr_surface": {
        "url": "https://pds-geosciences.wustl.edu/messenger/mess-h-mascs-4-uvvs-ddr/messmas_4001/data/ddr/uvvs_surface/",
        "description": "UVVS Mercury surface reflectance (MUV, binned)",
        "size_est": "~500 MB",
        "file_types": [".DAT", ".LBL", ".FMT"],
    },
    "virs_ddr": {
        "url": "https://pds-geosciences.wustl.edu/messenger/mess-h-mascs-4-virs-ddr/messmas_4002/data/ddr/",
        "description": "VIRS Mercury surface reflectance (VIS+NIR arrays)",
        "size_est": "~8 GB (recommend max-size limit)",
        "file_types": [".DAT", ".LBL", ".FMT"],
    },
    "uvvs_cdr": {
        "url": "https://pds-geosciences.wustl.edu/messenger/mess-h-mascs-3-uvvs-cdr/messmas_3001/data/cdr/uvvs/",
        "description": "UVVS calibrated radiance (FUV/MUV/VIS, per-step)",
        "size_est": "~5 GB (recommend max-size limit)",
        "file_types": [".DAT", ".LBL", ".FMT"],
    },
    "virs_cdr": {
        "url": "https://pds-geosciences.wustl.edu/messenger/mess-h-mascs-3-virs-cdr/messmas_3002/data/cdr/",
        "description": "VIRS calibrated radiance (VIS+NIR arrays)",
        "size_est": "~15 GB (recommend max-size limit)",
        "file_types": [".DAT", ".LBL", ".FMT"],
    },
}


class PDSDownloader:
    """Recursive PDS archive downloader using requests."""
    
    def __init__(self, base_url: str, output_dir: Path, max_size_gb: float = None, 
                 file_types: list = None, dry_run: bool = False):
        self.base_url = base_url.rstrip('/')
        self.output_dir = output_dir
        self.max_size_bytes = int(max_size_gb * 1024**3) if max_size_gb else None
        self.file_types = [ft.upper() for ft in file_types] if file_types else None
        self.dry_run = dry_run
        
        self.total_downloaded = 0
        self.file_count = 0
        self.skipped_count = 0
        self.visited_urls = set()
        
    def should_download_file(self, filename: str) -> bool:
        """Check if file matches our criteria."""
        if not self.file_types:
            return True
        return any(filename.upper().endswith(ft) for ft in self.file_types)
    
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
        print(f"Total size: {self.total_downloaded / 1024**3:.2f} GB")
        print(f"Time elapsed: {elapsed / 60:.1f} minutes")
        print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Download MESSENGER MASCS data from PDS archives (native Python, no wget required)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download Mercury surface reflectance (limit 2GB)
  python pds_downloader_native.py --dataset uvvs_ddr_surface --output-dir samples/SOLAR_SYSTEM/Mercury_bulk --max-size 2

  # Download VIRS DDR (limit 5GB)
  python pds_downloader_native.py --dataset virs_ddr --output-dir samples/SOLAR_SYSTEM/Mercury_bulk --max-size 5

  # Dry run to preview what would be downloaded
  python pds_downloader_native.py --dataset uvvs_ddr_surface --output-dir test --dry-run

Available datasets: uvvs_ddr_surface, virs_ddr, uvvs_cdr, virs_cdr
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
