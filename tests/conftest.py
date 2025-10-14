"""Test configuration for ensuring the application package is importable."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

try:
    from astropy.io import fits
except ModuleNotFoundError:  # pragma: no cover - optional dep on CI
    fits = None

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture()
def mini_fits(tmp_path: Path) -> Path:
    """Create a minimal FITS file for ingestion smoke tests."""

    if fits is None:
        pytest.skip("astropy is required for FITS ingestion tests")

    wavelengths = np.array([500.0, 600.0, 700.0])
    flux = np.array([0.1, 0.2, 0.3])
    columns = [
        fits.Column(name="WAVELENGTH", array=wavelengths, format="D", unit="nm"),
        fits.Column(name="FLUX", array=flux, format="D", unit="erg/s/cm2/angstrom"),
    ]
    table = fits.BinTableHDU.from_columns(columns)
    table.header["OBJECT"] = "MiniFixture"
    table.header["INSTRUME"] = "TestSpec"
    table.header["BUNIT"] = "erg/s/cm2/angstrom"

    path = tmp_path / "mini.fits"
    fits.HDUList([fits.PrimaryHDU(), table]).writeto(path)
    return path
