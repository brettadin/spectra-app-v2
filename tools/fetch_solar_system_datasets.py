#!/usr/bin/env python3
"""
Fetch authoritative Solar System spectra listed in samples/solar_system/manifest.json
and place them into the expected per-planet folders with canonical filenames.

This is a minimal downloader that saves CSV files as-is. For non-CSV or
mission-native formats (e.g., FITS, TAB), conversion hooks can be added later.

Usage:
  # Download all entries with a non-empty URL
  python tools/fetch_solar_system_datasets.py

  # Preview only
  python tools/fetch_solar_system_datasets.py --dry-run

  # Filter by planet or band
  python tools/fetch_solar_system_datasets.py --only planet=jupiter
  python tools/fetch_solar_system_datasets.py --only planet=mars,band=ir

Notes:
 - Expects 'requests' to be available (already listed in requirements.txt)
 - Writes to samples/solar_system/<planet>/<filename>
 - Overwrites existing files by default (use --no-overwrite to prevent)
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List

import requests

MANIFEST_RELATIVE = Path("samples/solar_system/manifest.json")


@dataclass
class Entry:
    planet: str
    band: str
    filename: str
    url: str
    fmt: str
    citation: str
    license: str

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "Entry":
        return Entry(
            planet=d["planet"],
            band=d["band"],
            filename=d["filename"],
            url=d.get("url", ""),
            fmt=d.get("format", "csv"),
            citation=d.get("citation", ""),
            license=d.get("license", ""),
        )


def find_repo_root(start: Path) -> Path:
    cur = start.resolve()
    for _ in range(6):
        if (cur / "samples" / "solar_system").exists() and (cur / "app").exists():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    return start.resolve()


def load_manifest(repo_root: Path) -> List[Entry]:
    manifest_path = (repo_root / MANIFEST_RELATIVE).resolve()
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    entries = [Entry.from_dict(e) for e in data.get("entries", [])]
    return entries


def filter_entries(entries: Iterable[Entry], only_filters: Dict[str, str]) -> List[Entry]:
    out: List[Entry] = []
    for e in entries:
        ok = True
        for k, v in only_filters.items():
            if getattr(e, k) != v:
                ok = False
                break
        if ok:
            out.append(e)
    return out


def download_csv(url: str) -> bytes:
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    return resp.content


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fetch Solar System datasets from manifest")
    parser.add_argument("--dry-run", action="store_true", help="Only print what would be fetched")
    parser.add_argument("--only", action="append", default=[], help="Filter like planet=jupiter or band=ir (can be repeated or comma-separated)")
    parser.add_argument("--no-overwrite", action="store_true", help="Do not overwrite existing files")
    args = parser.parse_args(argv)

    # Parse filters
    only: Dict[str, str] = {}
    for item in args.only:
        parts = [p.strip() for p in item.split(",") if p.strip()]
        for kv in parts:
            if "=" in kv:
                k, v = kv.split("=", 1)
                only[k.strip()] = v.strip()

    repo_root = find_repo_root(Path(__file__).parent)
    entries = load_manifest(repo_root)
    if only:
        entries = filter_entries(entries, only)

    if not entries:
        print("No entries to process.")
        return 0

    samples_root = repo_root / "samples" / "solar_system"

    planned: List[Entry] = [e for e in entries if e.url]
    skipped_empty = len(entries) - len(planned)
    if skipped_empty:
        print(f"Skipping {skipped_empty} entries with empty URL.")

    for e in planned:
        planet_dir = samples_root / e.planet
        target = planet_dir / e.filename
        print(f"-> {e.planet}/{e.band} from {e.url}\n   -> {target.relative_to(repo_root)}")
        if args.dry_run:
            continue
        planet_dir.mkdir(parents=True, exist_ok=True)
        if args.no_overwrite and target.exists():
            print(f"   Skipping existing (no-overwrite): {target}")
            continue
        if e.fmt.lower() == "csv":
            try:
                content = download_csv(e.url)
                target.write_bytes(content)
            except Exception as ex:
                print(f"   ERROR: download failed: {ex}")
                continue
        else:
            print(f"   TODO: format '{e.fmt}' not implemented; skipping")
            continue

    if args.dry_run:
        print("Dry run complete. No files written.")
    else:
        print("Fetch complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
