#!/usr/bin/env python3
"""Helper script to bootstrap and run the Spectra application.

This script will create (or reuse) a virtual environment located at
```.venv``` in the repository root, install the project's dependencies, and
launch the desktop application using that interpreter.  The script is intended
to work on both Windows and POSIX shells.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent
DEFAULT_VENV = REPO_ROOT / ".venv"


class LaunchError(RuntimeError):
    """Raised when bootstrapping or launching the app fails."""


def _run(command: list[str], *, check: bool = True) -> subprocess.CompletedProcess:
    """Run a subprocess command, streaming output to the console."""
    return subprocess.run(command, check=check)


def _venv_python(venv_path: Path) -> Path:
    """Return the path to the python executable inside a virtual environment."""
    if os.name == "nt":
        candidate = venv_path / "Scripts" / "python.exe"
    else:
        candidate = venv_path / "bin" / "python"

    if not candidate.exists():
        raise LaunchError(f"Python executable not found in virtual env: {candidate}")
    return candidate


def ensure_virtualenv(venv_path: Path) -> Path:
    """Create the virtual environment if it is missing and return its python."""
    if not venv_path.exists():
        print(f"Creating virtual environment at {venv_path}...", flush=True)
        _run([sys.executable, "-m", "venv", str(venv_path)])
    else:
        print(f"Using existing virtual environment at {venv_path}.")

    python = _venv_python(venv_path)
    print(f"Using interpreter: {python}")
    return python


def install_dependencies(python: Path) -> None:
    """Install the project's dependencies using pip."""
    print("Upgrading pip...", flush=True)
    _run([str(python), "-m", "pip", "install", "--upgrade", "pip"])

    requirements = REPO_ROOT / "requirements.txt"
    if requirements.exists():
        print(f"Installing dependencies from {requirements}...", flush=True)
        _run([str(python), "-m", "pip", "install", "-r", str(requirements)])
    else:
        print("requirements.txt not found; skipping dependency installation.")


def launch_app(python: Path) -> None:
    """Run the Spectra application."""
    print("Launching Spectra application...", flush=True)
    _run([str(python), "-m", "app.main"], check=False)


def main() -> None:
    try:
        python = ensure_virtualenv(DEFAULT_VENV)
        install_dependencies(python)
        launch_app(python)
    except subprocess.CalledProcessError as exc:
        raise LaunchError(
            f"Command failed with exit code {exc.returncode}: {' '.join(exc.cmd)}"
        ) from exc


if __name__ == "__main__":
    main()
