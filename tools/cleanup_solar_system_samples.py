#!/usr/bin/env python3
"""
Remove duplicate sample files under samples/solar_system that don't conform to the
canonical naming scheme. Keeps only *_uv.csv, *_visible.csv, and *_ir.csv variants.

Usage:
  - Dry run (show what would be deleted):
      python tools/cleanup_solar_system_samples.py --dry-run
  - Execute deletion:
      python tools/cleanup_solar_system_samples.py

This script is safe to run multiple times.
"""
from __future__ import annotations

import argparse
from pathlib import Path

CANONICAL_SUFFIXES = {"_uv.csv", "_visible.csv", "_ir.csv"}


def find_repo_root(start: Path) -> Path:
    cur = start.resolve()
    for _ in range(6):
        if (cur / "samples" / "solar_system").exists() and (cur / "app").exists():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    # Fallback to start
    return start.resolve()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Cleanup duplicate solar system samples")
    parser.add_argument("--dry-run", action="store_true", help="Only print actions, do not delete")
    args = parser.parse_args(argv)

    repo_root = find_repo_root(Path(__file__).parent)
    samples_root = repo_root / "samples" / "solar_system"
    if not samples_root.exists():
        print(f"Samples folder not found: {samples_root}")
        return 1

    to_delete: list[Path] = []
    for planet_dir in samples_root.iterdir():
        if not planet_dir.is_dir():
            continue
        for p in planet_dir.glob("*.csv"):
            name = p.name
            # Keep canonical; delete specific duplicate variants
            if any(name.endswith(sfx) for sfx in CANONICAL_SUFFIXES):
                continue
            if name.endswith("_infrared.csv") or name.endswith("_uvvis.csv"):
                to_delete.append(p)

    if not to_delete:
        print("No duplicate files found.")
        return 0

    print(f"Found {len(to_delete)} duplicate files:")
    for p in to_delete:
        print(f" - {p.relative_to(repo_root)}")

    if args.dry_run:
        print("Dry run: no files deleted.")
        return 0

    for p in to_delete:
        try:
            p.unlink()
        except Exception as e:
            print(f"Failed to delete {p}: {e}")
            return 2

    print("Duplicates removed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
