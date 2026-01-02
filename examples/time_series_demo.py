"""Minimal time-series viewer using PySide6 + pyqtgraph.

Usage examples:
    python -m examples.time_series_demo                      # bundled sample
    python -m examples.time_series_demo path/to/lc.fits      # FITS light curve
    python -m examples.time_series_demo path/to/lc.csv --normalize --mask-quality --bin 5
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pyqtgraph as pg
from PySide6 import QtWidgets

from app.services.importers.time_series_csv_importer import TimeSeriesCsvImporter
from app.services.importers.time_series_fits_importer import TimeSeriesFitsImporter


def load_timeseries(path: Path):
    suffix = path.suffix.lower()
    if suffix in {".csv", ".txt", ".dat"}:
        return TimeSeriesCsvImporter().read(path)
    if suffix in {".fits", ".fit", ".fts", ".h5", ".hdf5"}:
        return TimeSeriesFitsImporter().read(path)
    raise ValueError(f"Unsupported time-series file extension: {suffix}")


def apply_quality_mask(ts):
    if ts.quality is None:
        return ts
    mask = ts.quality == 0
    return ts.__class__(
        name=ts.name,
        time=ts.time[mask],
        values=ts.values[mask],
        time_unit=ts.time_unit,
        value_unit=ts.value_unit,
        errors=ts.errors[mask] if ts.errors is not None else None,
        quality=ts.quality[mask] if ts.quality is not None else None,
        metadata=ts.metadata,
        source_path=ts.source_path,
    )


def apply_normalization(ts):
    med = float(np.nanmedian(ts.values)) if ts.values.size else 1.0
    if med == 0 or not np.isfinite(med):
        return ts
    return ts.__class__(
        name=ts.name,
        time=ts.time,
        values=ts.values / med,
        time_unit=ts.time_unit,
        value_unit=ts.value_unit,
        errors=ts.errors / med if ts.errors is not None else None,
        quality=ts.quality,
        metadata=ts.metadata,
        source_path=ts.source_path,
    )


def apply_binning(ts, bin_size: int):
    if bin_size <= 1:
        return ts
    n = len(ts.time)
    if n == 0:
        return ts
    bins = n // bin_size
    if bins == 0:
        return ts
    t = ts.time[: bins * bin_size].reshape(bins, bin_size).mean(axis=1)
    v = ts.values[: bins * bin_size].reshape(bins, bin_size).mean(axis=1)
    e = None
    if ts.errors is not None:
        e = ts.errors[: bins * bin_size].reshape(bins, bin_size)
        e = np.sqrt((e**2).mean(axis=1))
    q = None
    if ts.quality is not None:
        q = ts.quality[: bins * bin_size].reshape(bins, bin_size)
        q = q.max(axis=1)
    return ts.__class__(
        name=ts.name,
        time=t,
        values=v,
        time_unit=ts.time_unit,
        value_unit=ts.value_unit,
        errors=e,
        quality=q,
        metadata=ts.metadata,
        source_path=ts.source_path,
    )


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Time series viewer (CSV/FITS)")
    parser.add_argument("path", nargs="?", help="Path to CSV/FITS light curve (defaults to bundled sample)")
    parser.add_argument("--normalize", action="store_true", help="Divide flux by median")
    parser.add_argument("--mask-quality", action="store_true", help="Drop points with QUALITY != 0")
    parser.add_argument("--bin", type=int, default=1, help="Bin size (integer)")
    args = parser.parse_args(argv[1:])

    if args.path:
        path = Path(args.path).expanduser()
    else:
        path = Path(__file__).resolve().parent.parent / "samples" / "exoplanets" / "time_series_sample.csv"
    if not path.exists():
        print(f"Time series file not found: {path}")
        return 1

    ts = load_timeseries(path)
    if args.mask_quality:
        ts = apply_quality_mask(ts)
    if args.normalize:
        ts = apply_normalization(ts)
    if args.bin and args.bin > 1:
        ts = apply_binning(ts, args.bin)

    app = QtWidgets.QApplication(sys.argv)
    win = pg.plot(title=ts.name)
    win.showGrid(x=True, y=True)
    win.setLabel("bottom", f"Time ({ts.time_unit})")
    win.setLabel("left", f"Flux ({ts.value_unit})")
    pen = pg.mkPen(color=(0, 180, 255), width=2)
    win.plot(ts.time, ts.values, pen=pen, symbol="o", symbolSize=6, symbolBrush=(0, 180, 255, 120))

    if ts.errors is not None:
        err = pg.ErrorBarItem(x=ts.time, y=ts.values, height=2 * np.asarray(ts.errors), pen=pen)
        win.addItem(err)

    win.setWindowTitle(f"Time Series Viewer - {ts.name}")
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
