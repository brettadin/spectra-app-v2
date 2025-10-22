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


def _install_numpy() -> None:
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
        "numpy>=1.26,<3",
    )
    subprocess.run(cmd, check=True)


def _ensure_numpy() -> None:
    try:
        importlib.import_module("numpy")
    except ModuleNotFoundError:
        _install_numpy()
        importlib.invalidate_caches()
        importlib.import_module("numpy")


_ensure_numpy()

