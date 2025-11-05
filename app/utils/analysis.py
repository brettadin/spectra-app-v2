"""
Lightweight analysis utilities for spectra.

Contracts (inputs/outputs):
- Arrays are 1D numpy-like; NaNs are handled gracefully.
- X is monotonic for width/centroid operations.
- Functions avoid heavy deps (NumPy only) to keep footprint small.

Functions:
- find_local_maxima(y, window): boolean mask of local maxima
- peak_near(x, y, x0, window): (idx, x_peak, y_peak) near x0 within window
- centroid(x, y): weighted centroid over provided window arrays
- fwhm(x, y, i0): approximate FWHM around a peak index
- noise_sigma(y, method): estimate noise sigma (mad|std)
- snr(peak_height, sigma): compute SNR value
"""
from __future__ import annotations

from typing import Tuple

import numpy as np


def _as_float_array(a: np.ndarray | list | Tuple) -> np.ndarray:
    arr = np.asarray(a, dtype=float)
    return arr


def find_local_maxima(y: np.ndarray, window: int = 1, prominence: float | None = None) -> np.ndarray:
    """Return a boolean mask marking local maxima.

    - window=1 compares each point to 1 neighbor on each side.
    - prominence, if provided, requires y[i] - max(y[i-1], y[i+1]) >= prominence.
    """
    y = _as_float_array(y)
    n = y.shape[0]
    if n < 3:
        return np.zeros(n, dtype=bool)
    w = max(1, int(window))
    mask = np.zeros(n, dtype=bool)
    # Simple local maxima: y[i] greater than neighbors within window
    for i in range(w, n - w):
        left = y[i - w : i]
        right = y[i + 1 : i + 1 + w]
        if not (np.all(np.isfinite(left)) and np.all(np.isfinite(right)) and np.isfinite(y[i])):
            continue
        if y[i] > np.max(left) and y[i] >= np.max(right):
            if prominence is not None:
                prom = y[i] - max(y[i - 1], y[i + 1])
                if prom < prominence:
                    continue
            mask[i] = True
    return mask


def peak_near(x: np.ndarray, y: np.ndarray, x0: float, window: float) -> Tuple[int, float, float]:
    """Find a peak near x0 within +/- window in x-units.

    Returns (idx, x_peak, y_peak). If no local maxima found, returns argmax in the window.
    If the window is empty, returns the global argmax.
    """
    x = _as_float_array(x)
    y = _as_float_array(y)
    if x.shape[0] != y.shape[0] or x.shape[0] == 0:
        return -1, np.nan, np.nan
    # Constrain to window
    sel = np.nonzero((x >= x0 - window) & (x <= x0 + window))[0]
    if sel.size == 0:
        idx = int(np.nanargmax(y)) if y.size else -1
        return (idx, float(x[idx]) if idx >= 0 else np.nan, float(y[idx]) if idx >= 0 else np.nan)
    yy = y[sel]
    # Robust choice: pick the highest point in the window (noise-safe)
    cand = sel[int(np.argmax(yy))]
    return int(cand), float(x[cand]), float(y[cand])


def centroid(x: np.ndarray, y: np.ndarray) -> float:
    """Compute intensity-weighted centroid for given window arrays.

    Ignores NaNs and negative weights. Returns mid-x if sum of weights is 0.
    """
    x = _as_float_array(x)
    y = _as_float_array(y)
    m = np.isfinite(x) & np.isfinite(y)
    if not np.any(m):
        return float(np.nan)
    xw = x[m]
    yw = y[m]
    yw = np.where(yw > 0, yw, 0.0)
    s = np.sum(yw)
    if s <= 0:
        return float(0.5 * (np.nanmin(xw) + np.nanmax(xw)))
    return float(np.sum(xw * yw) / s)


def _interp_crossing(xl: float, yl: float, xr: float, yr: float, yhalf: float) -> float:
    # Linear interpolation for y= yhalf between (xl,yl) and (xr,yr)
    if xr == xl or not np.isfinite(yl) or not np.isfinite(yr):
        return float(np.nan)
    t = (yhalf - yl) / (yr - yl)
    return float(xl + t * (xr - xl))


def fwhm(x: np.ndarray, y: np.ndarray, i0: int) -> float:
    """Approximate FWHM around a peak index i0 using linear interpolation.

    Returns width in x-units, or NaN if crossings not found.
    """
    x = _as_float_array(x)
    y = _as_float_array(y)
    n = y.size
    if n == 0 or i0 < 0 or i0 >= n:
        return float(np.nan)
    ymax = y[i0]
    if not np.isfinite(ymax):
        return float(np.nan)
    yhalf = ymax * 0.5
    # Search left
    xl = xr = np.nan
    # Left side: find last index where y < yhalf transitioning from peak
    for i in range(i0 - 1, 0, -1):
        if np.isfinite(y[i]) and np.isfinite(y[i + 1]) and ((y[i] <= yhalf and y[i + 1] >= yhalf) or (y[i] >= yhalf and y[i + 1] <= yhalf)):
            xl = _interp_crossing(x[i], y[i], x[i + 1], y[i + 1], yhalf)
            break
    # Right side
    for j in range(i0 + 1, n - 1):
        if np.isfinite(y[j]) and np.isfinite(y[j + 1]) and ((y[j] <= yhalf and y[j + 1] >= yhalf) or (y[j] >= yhalf and y[j + 1] <= yhalf)):
            xr = _interp_crossing(x[j], y[j], x[j + 1], y[j + 1], yhalf)
            break
    if not (np.isfinite(xl) and np.isfinite(xr)):
        return float(np.nan)
    return float(xr - xl)


def noise_sigma(y: np.ndarray, method: str = "mad") -> float:
    """Estimate noise sigma of y.

    - mad: 1.4826 * median(|y - median(y)|)
    - std: standard deviation (finite values only)
    """
    y = _as_float_array(y)
    if y.size == 0:
        return float(np.nan)
    m = np.isfinite(y)
    if not np.any(m):
        return float(np.nan)
    yy = y[m]
    if method == "std":
        return float(np.std(yy))
    med = np.median(yy)
    mad = np.median(np.abs(yy - med))
    return float(1.4826 * mad)


def snr(peak_height: float, sigma: float) -> float:
    """Simple SNR as peak_height / sigma. Returns NaN if sigma <= 0."""
    if not np.isfinite(peak_height) or not np.isfinite(sigma) or sigma <= 0:
        return float(np.nan)
    return float(peak_height / sigma)
