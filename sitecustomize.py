"""Test environment bootstrap ensuring numpy availability.

This module is imported automatically by Python during startup if it lives on
``sys.path``. We use it to guarantee ``numpy`` is importable on CI runners that
install the project without optional binary wheels. If numpy is missing we
perform a focused, prefer-binary pip installation before proceeding.
"""

from __future__ import annotations

import importlib
import os
import subprocess
import sys
from typing import Sequence


NUMPY_SPEC = "numpy>=1.26,<3"
"""Pinned numpy spec shared with the test bootstrap."""


def _install_numpy(spec: str = NUMPY_SPEC) -> None:
    """Install numpy if it is missing.

    We intentionally keep the dependency pin aligned with ``requirements.txt``
    (``>=1.26,<3``) and request binary wheels to avoid slow source builds.
    ``PIP_ONLY_BINARY`` mirrors the guidance in ``AGENTS.md`` so local
    developers can opt out by setting ``SPECTRA_SKIP_AUTO_NUMPY=1`` when they
    manage environments manually.
    """

    if os.environ.get("SPECTRA_SKIP_AUTO_NUMPY"):
        return

    python = sys.executable or "python"
    cmd: Sequence[str] = (
        python,
        "-m",
        "pip",
        "install",
        "--prefer-binary",
        spec,
    )
    subprocess.run(cmd, check=True)


def ensure_numpy() -> None:
    """Guarantee ``numpy`` is importable for Spectra runtime/tests."""

    try:
        importlib.import_module("numpy")
    except ModuleNotFoundError:
        _install_numpy()
        importlib.invalidate_caches()
        importlib.import_module("numpy")


_ensure_numpy = ensure_numpy  # Backwards compatibility for older imports.


ensure_numpy()

