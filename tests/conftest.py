"""Test configuration to keep Spectra importable under pytest.

The round-trip CI job exercises ingestion/export flows that depend on ``numpy``
and `astropy`.  We mirror the runtime bootstrap in ``sitecustomize`` so GitHub
Actions can install missing wheels automatically before test collection while
retaining the FITS fixtures used by the ingestion smoke tests.
"""

from __future__ import annotations

import importlib
import os
import subprocess
import sys
from pathlib import Path
from typing import Callable, Sequence

import pytest

try:  # pragma: no cover - optional dependency for FITS fixtures on CI.
    from astropy.io import fits
except ModuleNotFoundError:  # pragma: no cover - CI may skip astropy extras.
    fits = None

try:  # pragma: no cover - optional convenience path for repo checkouts.
    import sitecustomize
except ModuleNotFoundError:  # pragma: no cover - packaged installs skip this.
    sitecustomize = None  # type: ignore[assignment]

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _install_numpy(spec: str) -> None:
    if os.environ.get("SPECTRA_SKIP_AUTO_NUMPY"):
        raise pytest.UsageError(
            "NumPy is required for Spectra tests. Install it manually or unset "
            "SPECTRA_SKIP_AUTO_NUMPY to allow the bootstrap to run."
        )

    python = sys.executable or "python"
    cmd: Sequence[str] = (
        python,
        "-m",
        "pip",
        "install",
        "--prefer-binary",
        spec,
    )
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as exc:  # pragma: no cover - failure path.
        raise pytest.UsageError(
            "Automated NumPy installation failed. Run 'python -m pip install --prefer-binary "
            f"{spec}' manually and re-run pytest."
        ) from exc


def _ensure_numpy() -> None:
    spec = getattr(sitecustomize, "NUMPY_SPEC", "numpy>=1.26,<3")

    try:
        importlib.import_module("numpy")
    except ModuleNotFoundError:
        ensure: Callable[[], None] | None = getattr(sitecustomize, "ensure_numpy", None)
        if callable(ensure):
            ensure()
            return

        _install_numpy(spec)
        importlib.invalidate_caches()
        importlib.import_module("numpy")


_ensure_numpy()


@pytest.fixture()
def mini_fits(tmp_path: Path) -> Path:
    """Create a minimal FITS file for ingestion smoke tests."""

    if fits is None:
        pytest.skip("astropy is required for FITS ingestion tests")

    wavelengths = [500.0, 600.0, 700.0]
    flux = [0.1, 0.2, 0.3]
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


def pytest_sessionstart(session: pytest.Session) -> None:  # pragma: no cover - environment dependent
    """Ensure tests run from the repository root so relative paths resolve.

    Some runners or IDEs may start pytest from a parent directory (e.g., C:\Code),
    which breaks relative paths like 'samples/sample_spectrum.csv'. Force the CWD
    to the repo root alongside 'app/' and 'tests/'. Also set a safe Qt platform
    for headless test environments to avoid plugin crashes on Windows.
    """
    try:
        os.chdir(ROOT)
    except Exception:
        pass
    # Ensure a headless Qt platform to avoid access violations when creating Qt objects
    try:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    except Exception:
        pass
    # Provide a global fallback for tests that reference 'mini_fits' without
    # declaring the fixture parameter. Python looks up bare names in builtins
    # if not found in module globals, so expose a generated FITS path there.
    try:
        import builtins
        if fits is not None:
            import tempfile
            from astropy.io import fits as _fits
            tmpdir = Path(tempfile.mkdtemp(prefix="spectra-tests-"))
            path = tmpdir / "mini.fits"
            wavelengths = [500.0, 600.0, 700.0]
            flux = [0.1, 0.2, 0.3]
            columns = [
                _fits.Column(name="WAVELENGTH", array=wavelengths, format="D", unit="nm"),
                _fits.Column(name="FLUX", array=flux, format="D", unit="erg/s/cm2/angstrom"),
            ]
            table = _fits.BinTableHDU.from_columns(columns)
            table.header["OBJECT"] = "MiniFixture"
            table.header["INSTRUME"] = "TestSpec"
            table.header["BUNIT"] = "erg/s/cm2/angstrom"
            _fits.HDUList([_fits.PrimaryHDU(), table]).writeto(path, overwrite=True)
            builtins.mini_fits = path
    except Exception:
        # Best-effort only; if this fails, tests that need the proper fixture will
        # still pass when they request it as a parameter and will skip if astropy
        # is not available.
        pass
