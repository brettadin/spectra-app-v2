"""Fetch and plot a TESS light curve by target/TIC using astroquery.mast.

Usage:
    python -m examples.time_series_fetch_tess TIC123456789
    python -m examples.time_series_fetch_tess "WASP-18"

This downloads the first available TESS light-curve product to a cache
(subdirectory `.timeseries_cache`) and plots it with pyqtgraph.
"""

from __future__ import annotations

import sys
from pathlib import Path

import argparse
import numpy as np
import pyqtgraph as pg
from astroquery.mast import Observations
from PySide6 import QtWidgets

from app.services.importers.time_series_fits_importer import TimeSeriesFitsImporter
from .time_series_demo import apply_binning, apply_normalization, apply_quality_mask

CACHE_DIR = Path(".timeseries_cache")


def fetch_tess_lightcurve(target: str) -> Path:
    CACHE_DIR.mkdir(exist_ok=True)
    obs = Observations.query_object(target, radius="0.02 deg", project="TESS")
    if len(obs) == 0:
        raise RuntimeError(f"No TESS observations found for {target}")
    products = Observations.get_product_list(obs)
    lc_products = Observations.filter_products(products, productSubGroupDescription="LC")
    if len(lc_products) == 0:
        raise RuntimeError(f"No TESS light-curve products found for {target}")
    manifest = Observations.download_products(lc_products[:1], download_dir=str(CACHE_DIR), mrp_only=False)
    local_path = manifest["Local Path"][0]
    if not local_path:
        raise RuntimeError("Download failed: no local path returned")
    return Path(local_path)


def plot_timeseries(ts):
    app = QtWidgets.QApplication(sys.argv)
    win = pg.plot(title=ts.name)
    win.showGrid(x=True, y=True)
    win.setLabel("bottom", f"Time ({ts.time_unit})")
    win.setLabel("left", f"Flux ({ts.value_unit})")
    pen = pg.mkPen(color=(0, 220, 120), width=2)
    win.plot(ts.time, ts.values, pen=pen, symbol="o", symbolSize=5, symbolBrush=(0, 220, 120, 90))
    if ts.errors is not None:
        err = pg.ErrorBarItem(x=ts.time, y=ts.values, height=2 * np.asarray(ts.errors), pen=pen)
        win.addItem(err)
    win.setWindowTitle(f"TESS Light Curve - {ts.name}")
    return app.exec()


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Fetch and plot TESS light curve")
    parser.add_argument("target", help="Target name or TIC ID")
    parser.add_argument("--normalize", action="store_true", help="Divide flux by median")
    parser.add_argument("--mask-quality", action="store_true", help="Drop points with QUALITY != 0")
    parser.add_argument("--bin", type=int, default=1, help="Bin size")
    args = parser.parse_args(argv[1:])

    path = fetch_tess_lightcurve(args.target)
    ts = TimeSeriesFitsImporter().read(path)
    if args.mask_quality:
        ts = apply_quality_mask(ts)
    if args.normalize:
        ts = apply_normalization(ts)
    if args.bin and args.bin > 1:
        ts = apply_binning(ts, args.bin)
    return plot_timeseries(ts)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
