#!/usr/bin/env python
"""Generate the bundled NIST hydrogen line list JSON from ASD."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import astropy.units as u
from astropy.constants import c
from astroquery.nist import Nist


def _value(row: Any, key: str) -> Any:
    """Return column value from an Astroquery row if present."""

    try:
        return row[key]
    except KeyError:
        return None


def _serialize_row(row: Any) -> Dict[str, Any]:
    """Transform an Astroquery row into our JSON line schema."""

    wavelength = _value(row, "Wavelength")
    vacuum_wavelength_nm = wavelength.to(u.nm).value if wavelength is not None else None
    wavenumber = _value(row, "Wavenumber")
    wavenumber_cm = wavenumber.to(u.cm**-1).value if wavenumber is not None else None
    einstein_a = _value(row, "Aki (s^-1)")
    relative_intensity = _value(row, "Rel. Intensity")

    return {
        "id": _value(row, "Spectrum"),
        "species": "H I",
        "series": _value(row, "Transition"),
        "upper_n": _value(row, "Upper level"),
        "lower_n": _value(row, "Lower level"),
        "transition": _value(row, "Transition"),
        "vacuum_wavelength_nm": round(vacuum_wavelength_nm, 6) if vacuum_wavelength_nm is not None else None,
        "air_wavelength_nm": None,
        "wavenumber_cm_1": round(wavenumber_cm, 3) if wavenumber_cm is not None else None,
        "frequency_thz": (
            round((c / (vacuum_wavelength_nm * u.nm)).to(u.THz).value, 3)
            if vacuum_wavelength_nm is not None
            else None
        ),
        "einstein_a_s_1": float(einstein_a) if einstein_a is not None else None,
        "relative_intensity": float(relative_intensity) if relative_intensity is not None else None,
        "uncertainty_nm": None,
        "source_id": "nist_asd",
        "notes": _value(row, "Notes"),
    }


def build_lines(*, wmin_nm: float, wmax_nm: float) -> Dict[str, Any]:
    """Query NIST ASD and return metadata with curated lines."""

    table = Nist.query(
        wmin=wmin_nm * u.nm,
        wmax=wmax_nm * u.nm,
        element="H I",
        output_order="wavelength",
        linename="",
    )
    lines: List[Dict[str, Any]] = []
    for row in table:
        serialized = _serialize_row(row)
        lines.append(serialized)

    retrieval_time = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    metadata = {
        "source_id": "nist_asd",
        "citation": (
            "Y. Ralchenko, A.E. Kramida, J. Reader, and NIST ASD Team (2024). "
            "NIST Atomic Spectra Database (ver. 5.11), National Institute of Standards and Technology, Gaithersburg, MD."
        ),
        "url": "https://physics.nist.gov/asd",
        "retrieved_utc": retrieval_time,
        "notes": (
            "Lines generated directly from NIST ASD query via astroquery.nist. "
            "Vacuum wavelengths converted to nanometres; Rydberg–Ritz consistency retained."
        ),
        "provenance": {
            "generator": "tools/reference_build/build_hydrogen_asd.py",
            "query": {
                "element": "H I",
                "wmin_nm": wmin_nm,
                "wmax_nm": wmax_nm,
            },
            "dependency": "astroquery.nist",
        },
    }

    return {"metadata": metadata, "lines": lines}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="Path to write JSON bundle")
    parser.add_argument("--wmin", type=float, default=90.0, help="Minimum wavelength in nm")
    parser.add_argument("--wmax", type=float, default=1000.0, help="Maximum wavelength in nm")
    args = parser.parse_args()

    bundle = build_lines(wmin_nm=args.wmin, wmax_nm=args.wmax)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(bundle, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
