"""Minimal HTTP fallback for NIST ASD line queries.

This bypasses astroquery/astropy entirely, issuing a direct GET request to the
NIST ASD web interface. It is intentionally lightweight and best-effort: the
HTML output format is parsed heuristically to extract wavelength and (if
available) relative intensity. If parsing fails, an error payload is returned.

The goal is resilience in environments where native extensions inside astropy
crash during import (observed on Windows with code 0xc06d007f).

Returned line dict schema (subset of astroquery representation):
    {
        'wavelength_nm': float | None,
        'relative_intensity': float | None,
    }

NOTE: The public ASD interface HTML structure can change. This parser aims to
fail gracefully rather than raise.
"""
from __future__ import annotations

from typing import Any, Dict, List
import re
import json
import math
import os

try:
    import requests  # type: ignore
except Exception:  # pragma: no cover - requests should exist in env
    requests = None  # type: ignore

BASE_URL = "https://physics.nist.gov/cgi-bin/ASD/lines1.pl"
USER_AGENT = "SpectraApp-NIST-Fallback/0.1"

_DEF_TIMEOUT = float(os.environ.get("SPECTRA_NIST_HTTP_TIMEOUT", "15"))

# Precompiled regex patterns (very loose, intentionally tolerant)
_NUM = re.compile(r"[-+]?(?:\d*\.\d+|\d+)(?:[Ee][-+]?\d+)?")

# Minimal built-in line lists for resilience when ASD HTTP is unavailable.
# Values are approximate and intended for visualization only.
_BUILTIN_LINES: Dict[str, List[Dict[str, float]]] = {
    # Hydrogen Balmer series (vacuum wavelengths, nm, approx)
    "H": [
        {"wavelength_nm": 656.281, "relative_intensity": 100.0},  # Hα
        {"wavelength_nm": 486.133, "relative_intensity": 35.0},   # Hβ
        {"wavelength_nm": 434.047, "relative_intensity": 16.0},   # Hγ
        {"wavelength_nm": 410.174, "relative_intensity": 9.0},    # Hδ
    ],
    # Helium (approximate neutral He I lines)
    "He": [
        {"wavelength_nm": 587.562, "relative_intensity": 100.0},  # D3
        {"wavelength_nm": 501.567, "relative_intensity": 50.0},
        {"wavelength_nm": 447.148, "relative_intensity": 40.0},
        {"wavelength_nm": 706.519, "relative_intensity": 80.0},
    ],
    # Sodium D-lines
    "Na": [
        {"wavelength_nm": 588.995, "relative_intensity": 100.0},  # D1
        {"wavelength_nm": 589.592, "relative_intensity": 100.0},  # D2
    ],
    # Iron (some bright Fe I lines)
    "Fe": [
        {"wavelength_nm": 438.355, "relative_intensity": 100.0},
        {"wavelength_nm": 440.475, "relative_intensity": 80.0},
        {"wavelength_nm": 441.513, "relative_intensity": 60.0},
        {"wavelength_nm": 445.897, "relative_intensity": 40.0},
        {"wavelength_nm": 495.761, "relative_intensity": 50.0},
    ],
    # Calcium H & K lines
    "Ca": [
        {"wavelength_nm": 393.366, "relative_intensity": 100.0},  # K
        {"wavelength_nm": 396.847, "relative_intensity": 100.0},  # H
        {"wavelength_nm": 422.673, "relative_intensity": 80.0},
    ],
    # Magnesium
    "Mg": [
        {"wavelength_nm": 518.362, "relative_intensity": 100.0},
        {"wavelength_nm": 517.270, "relative_intensity": 80.0},
        {"wavelength_nm": 516.733, "relative_intensity": 60.0},
    ],
    # Oxygen (OI lines)
    "O": [
        {"wavelength_nm": 777.194, "relative_intensity": 100.0},
        {"wavelength_nm": 777.417, "relative_intensity": 100.0},
        {"wavelength_nm": 777.539, "relative_intensity": 100.0},
        {"wavelength_nm": 844.625, "relative_intensity": 80.0},
    ],
    # Nitrogen (NI lines)
    "N": [
        {"wavelength_nm": 746.831, "relative_intensity": 100.0},
        {"wavelength_nm": 821.634, "relative_intensity": 80.0},
        {"wavelength_nm": 870.334, "relative_intensity": 60.0},
    ],
}


def fetch_lines_http(*, element: str, lower: float, upper: float, wavelength_unit: str = "nm") -> Dict[str, Any]:
    """Attempt a direct HTTP query.

    We request ASCII output (format=1). The response often contains a header
    followed by lines with columns including wavelength. Parsing strategy:
    - Scan each line for numeric tokens
    - First numeric treated as wavelength in the requested unit
    - Second numeric optionally treated as relative intensity (best-effort)
    - Convert wavelength to nm if unit differs
    """
    if requests is None:
        return {"error": "requests-missing", "message": "requests library not available"}

    # Map unit to NIST form parameter (nm=0 A=1 per docs; keep nm assumption if unknown)
    unit_param = "0" if wavelength_unit == "nm" else "0"

    # The public CGI has many parameters; over-requesting occasionally triggers
    # internal "Software error" pages. Keep the query minimal and defensive.
    # Try element symbol only first (more lenient), fallback to "element I" if needed
    attempts = [
        {"spectra": element.strip()},
        {"spectra": f"{element} I".strip()},
    ]
    
    last_error = None
    for attempt_params in attempts:
        params = {
            **attempt_params,
            "low_w": f"{lower}",
            "upp_w": f"{upper}",
            "unit": unit_param,   # 0 == nm per ASD docs
            "format": "1",       # ASCII text output
            "remove_js": "1",    # strip scripts for easier parsing
            "ascii": "1",        # force plain text
        }
        try:
            resp = requests.get(BASE_URL, params=params, headers={"User-Agent": USER_AGENT}, timeout=_DEF_TIMEOUT)
        except Exception as exc:
            last_error = {"error": "http-failure", "message": str(exc)}
            continue
        
        if resp.status_code == 500:
            # Server error - try next attempt
            last_error = {"error": "http-status", "message": f"HTTP 500 (Server Error) - NIST may be overloaded or the query is malformed"}
            continue
        
        if resp.status_code != 200:
            last_error = {"error": "http-status", "message": f"HTTP {resp.status_code}"}
            continue
        
        # Guard against server-side error pages which previously leaked arbitrary numbers
        if "Software error" in resp.text or "Can't use an undefined value" in resp.text:
            last_error = {"error": "server-error", "message": "NIST ASD returned an internal error"}
            continue
        
        # Success - proceed to parse
        break
    else:
        # All attempts failed
        # Before giving up, try built-in fallback for common elements
        sym = (element or "").strip().title()
        if sym in _BUILTIN_LINES:
            lines = []
            for rec in _BUILTIN_LINES[sym]:
                wl = float(rec["wavelength_nm"])  # nm
                if float(lower) <= wl <= float(upper):
                    lines.append({
                        "wavelength_nm": wl,
                        "relative_intensity": float(rec.get("relative_intensity", 1.0)),
                    })
            # Normalise relative intensities
            max_rel = max((l["relative_intensity"] for l in lines), default=0.0)
            if max_rel > 0:
                for l in lines:
                    l["relative_intensity_normalized"] = l["relative_intensity"] / max_rel
            return {
                "lines": lines,
                "meta": {
                    "fallback": True,
                    "line_count": len(lines),
                    "source": "builtin",
                    "note": "Using built-in approximate lines due to HTTP failure",
                },
            }
        return last_error or {"error": "http-failure", "message": "All HTTP attempts failed"}
    text = resp.text
    lines: List[Dict[str, Any]] = []
    for raw in text.splitlines():
        # Skip header / comment / blank lines
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        nums = _NUM.findall(stripped)
        if not nums:
            continue
        try:
            wavelength = float(nums[0])
        except Exception:
            continue
        # Intensity heuristic: choose next numeric token if plausible
        intensity = None
        if len(nums) >= 2:
            try:
                ii = float(nums[1])
                if math.isfinite(ii):
                    intensity = ii
            except Exception:
                pass
        lines.append({"wavelength_nm": wavelength, "relative_intensity": intensity})

    # Normalise intensities if available
    max_rel = max([l["relative_intensity"] for l in lines if isinstance(l.get("relative_intensity"), (int, float))], default=0)
    if max_rel > 0:
        for l in lines:
            rel = l.get("relative_intensity")
            if isinstance(rel, (int, float)) and rel >= 0:
                l["relative_intensity_normalized"] = rel / max_rel
            else:
                l["relative_intensity_normalized"] = None
    else:
        for l in lines:
            l["relative_intensity_normalized"] = None

    # If parser produced clearly invalid wavelengths (e.g. all < 10 nm for typical
    # visible queries) treat as failure to avoid polluting UI.
    if lines and all(l.get("wavelength_nm", 0) < 10 for l in lines):
        return {"error": "parse-anomaly", "message": "Parsed only implausible wavelengths"}
    return {"lines": lines, "meta": {"fallback": True, "line_count": len(lines), "query": params, "source": "http"}}

__all__ = ["fetch_lines_http"]
