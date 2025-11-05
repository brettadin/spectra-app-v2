import numpy as np
from numpy.typing import NDArray

from app.utils.analysis import (
    find_local_maxima,
    peak_near,
    centroid,
    fwhm,
    noise_sigma,
    snr,
)


def _gaussian(x: NDArray[np.floating], mu: float, sigma: float, amp: float = 1.0) -> NDArray[np.floating]:
    return amp * np.exp(-0.5 * ((x - mu) / sigma) ** 2)


def test_peak_near_centroid_fwhm_and_snr_on_gaussian():
    rng = np.random.default_rng(0)
    x = np.linspace(500.0, 600.0, 2001)
    mu = 550.0
    sigma = 2.0
    amp = 1.0
    y_clean = _gaussian(x, mu, sigma, amp)
    noise = rng.normal(0.0, 0.02, size=x.size)
    y = y_clean + noise

    # Peak near 550 within ±5 nm
    idx, xp, yp = peak_near(x, y, mu, window=5.0)
    assert idx >= 0
    assert abs(xp - mu) < 0.3
    assert yp == y[idx]

    # Centroid over ±3*sigma window should be near mu
    wmask = (x >= mu - 3 * sigma) & (x <= mu + 3 * sigma)
    xc = centroid(x[wmask], y[wmask])
    assert abs(xc - mu) < 0.3

    # FWHM approximates 2.355*sigma (allow small tolerance)
    width = fwhm(x, y, idx)
    expected = 2.35482 * sigma
    assert np.isfinite(width)
    assert abs(width - expected) < 0.5

    # SNR around expected amplitude vs MAD noise estimate
    sig = noise_sigma(y, method="mad")
    s = snr(max(yp, 1e-9), sig)
    # With 0.02 noise, SNR should be reasonably high
    assert np.isfinite(sig) and sig > 0
    assert np.isfinite(s) and 20.0 < s < 200.0


def test_find_local_maxima_basic():
    y = np.array([0, 1, 0, 2, 0, 1, 0], dtype=float)
    m = find_local_maxima(y, window=1)
    idxs = np.nonzero(m)[0]
    # Expect peaks at positions 1, 3, 5
    assert list(idxs) == [1, 3, 5]
