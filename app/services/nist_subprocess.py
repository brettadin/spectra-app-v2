"""Isolated NIST ASD fetch in a subprocess to avoid native crashes.

Usage:
    from app.services import nist_subprocess
    payload = nist_subprocess.safe_fetch(identifier="Fe", lower=400, upper=500)

If astroquery/astropy import or query triggers a native crash, the main
process survives and an error dictionary is returned.
"""
from __future__ import annotations

import json
import sys
import subprocess
import textwrap
from typing import Any, Dict


def _build_driver(identifier: str, element: str | None, lower: float, upper: float, wavelength_unit: str, wavelength_type: str, use_ritz: bool) -> str:
    """Build the Python source executed in the isolated subprocess.

    We avoid an f-string for the bulk of the script so that braces used in
    dictionary literals and comprehensions are not treated as formatting
    placeholders. Only a small header segment is interpolated.
    """
    header = textwrap.dedent(
        f"""
        identifier = {identifier!r}
        element = {element!r}
        lower = float({lower})
        upper = float({upper})
        wavelength_unit = {wavelength_unit!r}
        wavelength_type = {wavelength_type!r}
        use_ritz = bool({use_ritz!r})
        """
    )
    body = """
import json, math
try:
    import astropy.units as u  # type: ignore
    from astroquery.nist import Nist  # type: ignore
except Exception as exc:  # Dependency/import failure
    print(json.dumps({'error': 'import-failure', 'message': str(exc)}))
    raise SystemExit(0)

# User-specified search window
if lower > upper:
    lower, upper = upper, lower
try:
    min_w = u.Quantity(lower, wavelength_unit)
    max_w = u.Quantity(upper, wavelength_unit)
    table = Nist.query(min_w, max_w, linename=identifier, wavelength_type=wavelength_type)
except Exception as exc:
    print(json.dumps({'error': 'query-failure', 'message': str(exc)}))
    raise SystemExit(0)

lines = []
max_rel = 0.0

def _to_float(val):
    try:
        return float(val)
    except Exception:
        return None

if table is not None:
    cols = getattr(table, 'colnames', []) or []
    for row in table:
        if not isinstance(row, dict):
            # Table rows behave like a mapping; build a plain dict copy
            row_map = {col_name: row[col_name] for col_name in cols}
        else:
            row_map = row
        obs = _to_float(row_map.get('Observed'))
        ritz = _to_float(row_map.get('Ritz'))
        chosen = ritz if use_ritz and ritz is not None else (obs if obs is not None else ritz)
        if chosen is None:
            continue
        rel = _to_float(row_map.get('Rel.'))
        if rel is not None and rel > max_rel:
            max_rel = rel
        lines.append({
            'wavelength_nm': chosen,
            'observed_wavelength_nm': obs,
            'ritz_wavelength_nm': ritz,
            'relative_intensity': rel,
        })

for line in lines:
    rel = line.get('relative_intensity')
    if rel is not None and max_rel > 0:
        line['relative_intensity_normalized'] = rel / max_rel
    else:
        line['relative_intensity_normalized'] = None

print(json.dumps({'lines': lines, 'meta': {'subprocess': True, 'line_count': len(lines)}}))
"""
    return header + body


def safe_fetch(*, identifier: str, element: str | None = None, lower: float, upper: float, wavelength_unit: str = "nm", wavelength_type: str = "vacuum", use_ritz: bool = True, timeout: float = 45.0) -> Dict[str, Any]:
    """Fetch lines using a subprocess; never raises on native crash.

    Returns a payload dict on success or {'error': <code>, 'message': ..., 'meta': {...}} on failure.
    """
    driver = _build_driver(identifier, element, lower, upper, wavelength_unit, wavelength_type, use_ritz)
    try:
        # Enable faulthandler in the child for better diagnostics on native crashes
        proc = subprocess.run([sys.executable, "-X", "faulthandler", "-c", driver], capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"error": "timeout", "message": f"NIST subprocess exceeded {timeout}s"}
    except Exception as exc:  # pragma: no cover
        return {"error": "spawn-failure", "message": str(exc)}
    stdout = (proc.stdout or "").strip()
    if not stdout:
        return {"error": "empty-output", "message": "No data returned from NIST subprocess", "stderr": (proc.stderr or "").strip(), "returncode": int(proc.returncode)}
    try:
        payload = json.loads(stdout.splitlines()[-1])
    except Exception as exc:
        return {"error": "parse-failure", "message": f"Could not parse subprocess JSON: {exc}", "raw": stdout[:5000], "stderr": (proc.stderr or "").strip(), "returncode": int(proc.returncode)}
    return payload

__all__ = ["safe_fetch"]
