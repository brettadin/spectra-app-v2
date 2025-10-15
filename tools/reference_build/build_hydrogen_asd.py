#!/usr/bin/env python
"""Generate the bundled NIST hydrogen line list JSON from ASD."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

import astropy.units as u
from astropy.constants import c
from astroquery.nist import Nist


def _value(row: Any, key: str) -> Any:
    """Return column value from an Astroquery row if present."""

    try:
        return row[key]
    except KeyError:
        return None


def _serialize_row(row: Any, *, source_id: str) -> Dict[str, Any]:
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
        "source_id": source_id,
        "notes": _value(row, "Notes"),
    }


def _find_version_from_headers(headers: Mapping[str, str]) -> Optional[str]:
    """Extract a version token from ASD response headers if possible."""

    version_hints: List[str] = []
    for key, value in headers.items():
        key_lower = key.lower()
        value_text = str(value)
        value_lower = value_text.lower()
        if "version" in key_lower and ("asd" in key_lower or "atomic" in key_lower):
            version_hints.append(value_text)
        elif "asd" in key_lower and ("release" in key_lower or "version" in key_lower):
            version_hints.append(value_text)
        elif "version" in value_lower and "asd" in value_lower:
            version_hints.append(value_text)

    for hint in version_hints:
        match = re.search(r"(\d+(?:[._]\d+)+)", hint)
        if match:
            return match.group(1)

    for hint in version_hints:
        sanitized = re.sub(r"[^0-9A-Za-z]+", "_", hint).strip("_")
        if sanitized:
            return sanitized

    date_header = headers.get("date")
    if date_header:
        try:
            parsed_date = datetime.strptime(date_header, "%a, %d %b %Y %H:%M:%S %Z")
        except ValueError:
            parsed_date = None
        if parsed_date:
            return parsed_date.strftime("%Y%m%d")

    return None


def _compose_source_id(base: str, *, version_tag: Optional[str]) -> str:
    """Return a source identifier that incorporates a version tag."""

    if not version_tag:
        return base

    sanitized = re.sub(r"[^0-9A-Za-z]+", "_", version_tag).strip("_")
    if not sanitized:
        return base

    if sanitized.lower() in base.lower():
        return base

    return f"{base}_{sanitized}"


def build_lines(
    *,
    wmin_nm: float,
    wmax_nm: float,
    source_id: str,
    detect_source_version: bool = True,
) -> Dict[str, Any]:
    """Query NIST ASD and return metadata with curated lines."""

    table = Nist.query(
        wmin_nm * u.nm,
        wmax_nm * u.nm,
        linename="H I",
        output_order="wavelength",
    )

    version_tag: Optional[str] = None
    if detect_source_version:
        response = None
        query_obj = getattr(Nist, "_last_query", None)
        session = getattr(Nist, "_session", None)
        if query_obj is not None and session is not None:
            try:
                response = query_obj.request(session)
            except Exception:
                response = None
        if response is not None:
            version_tag = _find_version_from_headers(response.headers)

    final_source_id = _compose_source_id(source_id, version_tag=version_tag)
    lines: List[Dict[str, Any]] = []
    for row in table:
        serialized = _serialize_row(row, source_id=final_source_id)
        lines.append(serialized)

    retrieval_time = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    metadata = {
        "source_id": final_source_id,
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

    if version_tag:
        metadata["provenance"]["asd_version_tag"] = version_tag

    return {"metadata": metadata, "lines": lines}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="Path to write JSON bundle")
    parser.add_argument("--wmin", type=float, default=90.0, help="Minimum wavelength in nm")
    parser.add_argument("--wmax", type=float, default=1000.0, help="Maximum wavelength in nm")
    parser.add_argument(
        "--source-id",
        type=str,
        default="nist_asd_2024",
        help="Identifier to stamp onto metadata and individual lines.",
    )
    parser.add_argument(
        "--no-detect-source-version",
        action="store_true",
        help="Skip trying to infer an ASD version tag from HTTP response headers.",
    )
    args = parser.parse_args()

    bundle = build_lines(
        wmin_nm=args.wmin,
        wmax_nm=args.wmax,
        source_id=args.source_id,
        detect_source_version=not args.no_detect_source_version,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(bundle, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
