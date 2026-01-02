"""Passband utilities for deriving effective wavelengths from filter curves.

The expected passband file format is simple two-column text (wavelength_nm,
throughput), with whitespace or comma delimiters. Wavelengths are assumed to be
nanometres; throughputs are arbitrary linear weights. Comments starting with
"#" are ignored.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional
import urllib.request

import numpy as np


PASSBAND_DIR = Path(__file__).resolve().parents[3] / "storage" / "passbands"

# Known public passband sources keyed by normalized names.
# Kepler: official Kepler response curve (nm vs. throughput)
# TESS: STScI TESS full-system transmission (wavelength in microns, converted later by callers)
KNOWN_PASSBANDS = {
    "kepler_photometer": "https://keplergo.arc.nasa.gov/KeplerResponse.txt",
    "kepler": "https://keplergo.arc.nasa.gov/KeplerResponse.txt",
    "tess": "https://archive.stsci.edu/missions/tess/models/TESS_Transmission_20181119.csv",
}


def _normalize_name(text: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in text).strip("_")


def find_passband_file(band: Optional[str], instrument: Optional[str]) -> Optional[Path]:
    """Locate a passband file under PASSBAND_DIR using band/instrument hints."""
    candidates: list[str] = []
    if instrument:
        candidates.append(_normalize_name(instrument))
    if band:
        candidates.append(_normalize_name(band))
    if instrument and band:
        candidates.append(_normalize_name(f"{instrument}_{band}"))
        candidates.append(_normalize_name(f"{band}_{instrument}"))

    tried = set()
    for stem in candidates:
        if not stem or stem in tried:
            continue
        tried.add(stem)
        for ext in ("csv", "txt", "dat", "tsv"):  # common plain-text options
            path = PASSBAND_DIR / f"{stem}.{ext}"
            if path.exists():
                return path
    return None


def _download_url(url: str, dest: Path) -> bool:
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(url) as resp, dest.open("wb") as fh:
            fh.write(resp.read())
        return True
    except Exception:
        try:
            if dest.exists():
                dest.unlink()
        except Exception:
            pass
        return False


def ensure_passband_file(band: Optional[str], instrument: Optional[str]) -> Optional[Path]:
    """Find or download a passband file using known sources and naming rules."""
    existing = find_passband_file(band, instrument)
    if existing is not None:
        return existing

    candidates: list[str] = []
    if instrument:
        candidates.append(_normalize_name(instrument))
    if band:
        candidates.append(_normalize_name(band))
    if instrument and band:
        candidates.append(_normalize_name(f"{instrument}_{band}"))
        candidates.append(_normalize_name(f"{band}_{instrument}"))

    for stem in candidates:
        if not stem:
            continue
        url = KNOWN_PASSBANDS.get(stem)
        if url:
            # Use URL extension when possible; fall back to .csv
            ext = Path(url).suffix or ".csv"
            dest = PASSBAND_DIR / f"{stem}{ext}"
            if _download_url(url, dest):
                return dest
    return None


def effective_wavelength_from_passband(path: Path) -> Optional[float]:
    """Compute effective wavelength (nm) from a passband throughput file."""
    if not path.exists():
        return None

    def _load(delim: Optional[str]) -> Optional[np.ndarray]:
        try:
            data = np.genfromtxt(path, comments="#", delimiter=delim)
            return data
        except Exception:
            return None

    data = _load(None)
    if data is None or data.size == 0:
        data = _load(",")
    if data is None or data.size == 0:
        return None

    data = np.asarray(data, dtype=float)
    if data.ndim == 1 and data.shape[0] >= 2:
        data = data.reshape(1, -1)
    if data.ndim != 2 or data.shape[1] < 2:
        return None

    wavelength = data[:, 0]
    throughput = data[:, 1]
    mask = np.isfinite(wavelength) & np.isfinite(throughput)
    wavelength = wavelength[mask]
    throughput = throughput[mask]
    if throughput.size == 0:
        return None
    weights = throughput
    total = float(np.sum(weights))
    if total == 0.0:
        return None
    eff = float(np.sum(wavelength * weights) / total)
    return eff
