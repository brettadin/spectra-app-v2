"""Central constants for units, file filters, and common paths.

Low-risk centralization to reduce magic strings. Importers and UI can
adopt these gradually; no behavior changes are implied by this module
existing.
"""
from __future__ import annotations

import os
from pathlib import Path

# ---- Units ---------------------------------------------------------------
# Canonical internal wavelength unit (nm)
CANONICAL_X_UNIT: str = "nm"

# Display units supported by the UI (labels)
DISPLAY_X_UNITS: tuple[str, ...] = ("nm", "Å", "µm", "cm⁻¹")

# Common synonyms used by importers when parsing headers/metadata
X_UNIT_SYNONYMS: dict[str, str] = {
    "nanometer": "nm",
    "nanometre": "nm",
    "nanometers": "nm",
    "nanometres": "nm",
    "angstrom": "Å",
    "angström": "Å",
    "a": "Å",
    "um": "µm",
    "micron": "µm",
    "microns": "µm",
    "micrometer": "µm",
    "micrometre": "µm",
    "wavenumber": "cm⁻¹",
    "cm-1": "cm⁻¹",
}

# ---- File filters --------------------------------------------------------
SPECTRAL_FILE_EXTENSIONS: tuple[str, ...] = (
    ".csv", ".txt", ".dat", ".fits", ".fit", ".fts", ".jdx", ".dx", ".jcamp",
)

NON_SPECTRAL_EXTENSIONS: tuple[str, ...] = (
    ".gif", ".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff",
    ".svg", ".log", ".xml", ".html", ".htm", ".json", ".md",
)

# ---- Providers -----------------------------------------------------------
# Mirror names used in RemoteDataService so other modules can refer to a single source
PROVIDER_MAST: str = "MAST"
PROVIDER_NIST: str = "NIST"
PROVIDER_SOLAR_SYSTEM: str = "Solar System Archive"

# ---- Common paths --------------------------------------------------------
REPO_ROOT: Path = Path(__file__).resolve().parents[1]
DEFAULT_DOWNLOADS_DIR: Path = REPO_ROOT / "downloads"
DEFAULT_EXPORTS_DIR: Path = REPO_ROOT / "exports"
DEFAULT_LOG_DIR: Path = REPO_ROOT / "exports" / "logs"

# Allow overrides via environment variables for headless/packaged runs
STORE_DIR_OVERRIDE: Path | None = Path(os.environ["SPECTRA_STORE_DIR"]) if os.environ.get("SPECTRA_STORE_DIR") else None


def ensure_dir(path: Path) -> Path:
    """Create a directory if missing and return it."""
    path.mkdir(parents=True, exist_ok=True)
    return path
