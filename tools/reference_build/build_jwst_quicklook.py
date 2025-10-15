#!/usr/bin/env python
"""Fetch JWST spectra via MAST and resample for in-app quick-look tables."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from astroquery.mast import Observations
from astropy.io import fits
import numpy as np


def _download_product(product_uri: str, cache_dir: Path) -> Path:
    cache_dir.mkdir(parents=True, exist_ok=True)
    manifest = Observations.download_products(product_uri, download_dir=str(cache_dir))
    if not manifest:
        raise RuntimeError(f"MAST returned no products for {product_uri}")
    first = manifest[0]
    path = Path(first["Local Path"])
    if not path.exists():
        raise FileNotFoundError(path)
    return path


def _resample_fits(path: Path, *, bins: int) -> List[Dict[str, float]]:
    with fits.open(path) as hdul:
        data = hdul[1].data
        wavelength = np.array(data["WAVELENGTH"])
        flux = np.array(data["FLUX"])
    if len(wavelength) == 0:
        raise ValueError(f"No wavelength column in {path}")
    indices = np.linspace(0, len(wavelength) - 1, bins, dtype=int)
    result: List[Dict[str, float]] = []
    for idx in indices:
        result.append({
            "wavelength_um": float(wavelength[idx]),
            "value": float(flux[idx]),
        })
    return result


def build_targets(config_path: Path, *, cache_dir: Path, bins: int) -> Dict[str, Any]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    targets: List[Dict[str, Any]] = []
    for entry in config["targets"]:
        product_uri = entry["mast_product_uri"]
        fits_path = _download_product(product_uri, cache_dir)
        data_rows = _resample_fits(fits_path, bins=bins)
        min_wave = min(row["wavelength_um"] for row in data_rows)
        max_wave = max(row["wavelength_um"] for row in data_rows)
        targets.append(
            {
                "id": entry["id"],
                "name": entry["name"],
                "object_type": entry.get("object_type"),
                "instrument": entry.get("instrument"),
                "program": entry.get("program"),
                "spectral_range_um": [min_wave, max_wave],
                "spectral_resolution": entry.get("spectral_resolution"),
                "data_units": entry.get("data_units"),
                "data": data_rows,
                "provenance": {
                    "mast_product_uri": product_uri,
                    "pipeline_version": entry.get("pipeline_version"),
                    "retrieved_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                },
                "source": entry.get("source"),
            }
        )
    metadata = {
        "compiled_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "notes": "Quick-look spectra resampled from calibrated JWST products via astroquery.mast.",
        "provenance": {
            "generator": "tools/reference_build/build_jwst_quicklook.py",
            "bins": bins,
            "cache_dir": str(cache_dir),
        },
    }
    return {"metadata": metadata, "targets": targets}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path, help="JSON manifest enumerating JWST products to resample")
    parser.add_argument("--output", type=Path, required=True, help="Path to write JSON bundle")
    parser.add_argument("--cache-dir", type=Path, default=Path(".cache/jwst"), help="Download directory for FITS products")
    parser.add_argument("--bins", type=int, default=64, help="Number of points to resample per spectrum")
    args = parser.parse_args()

    bundle = build_targets(args.config, cache_dir=args.cache_dir, bins=args.bins)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(bundle, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
