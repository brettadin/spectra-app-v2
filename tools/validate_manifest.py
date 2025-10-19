#!/usr/bin/env python3
"""
Validate a Spectra App provenance manifest against the v1.2.0 schema
and a few extra logical rules (weights ~ 1.0, ET timezone hint, etc.)
"""

import argparse
import json
import math
import os
import sys
from pathlib import Path

from jsonschema import Draft202012Validator, exceptions as js_exceptions

ET_OFFSETS = ("-04:00", "-05:00")  # DST-aware hint; we only warn if missing.

def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def warn(msg: str):
    print(f"[WARN] {msg}", file=sys.stderr)

def fail(msg: str):
    print(f"[FAIL] {msg}", file=sys.stderr)
    sys.exit(1)

def approx_equal(a: float, b: float, eps: float = 1e-6) -> bool:
    return abs(a - b) <= eps

def logical_checks(manifest: dict) -> None:
    # 1) created_at_et looks like ET offset (warn only).
    ts = manifest.get("created_at_et", "")
    if not any(ts.endswith(off) for off in ET_OFFSETS):
        warn("created_at_et does not end with an ET offset (-04:00 or -05:00). "
             "Ensure times are America/New_York when writing manifests.")

    # 2) identification weights sum ~ 1.0 when present.
    ident = manifest.get("identification")
    if ident and isinstance(ident, dict):
        weights = ident.get("weights") or {}
        if all(k in weights for k in ("peaks", "xcorr", "consistency")):
            s = sum(float(weights[k]) for k in ("peaks", "xcorr", "consistency"))
            if not approx_equal(s, 1.0, eps=1e-3):
                warn(f"identification.weights sum to {s:.6f} (expected ~1.0).")

        # Components in 0..1 range (schema already enforces), add a cross-check against total.
        total = ident.get("score")
        components = ident.get("components") or {}
        if total is not None and components:
            comp_sum = sum(float(components.get(k, 0.0)) * float(weights.get(k, 0.0))
                           for k in ("peaks", "xcorr", "consistency"))
            if total is not None and abs(float(total) - comp_sum) > 0.05:
                warn(f"identification.score ({total}) deviates from weighted components ({comp_sum:.3f}) > 0.05")

    # 3) transforms convolve_down_only guidance
    for t in manifest.get("transforms", []):
        if t.get("kind") == "lsf_convolve":
            params = t.get("params", {})
            if "convolve_down_only" in params and params["convolve_down_only"] is False:
                warn("lsf_convolve.convolve_down_only is False; Atlas recommends avoiding sharpening.")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--schema", required=True, help="Path to provenance_schema.json")
    ap.add_argument("--manifest", required=True, help="Path to manifest.json to validate")
    args = ap.parse_args()

    schema_path = Path(args.schema)
    manifest_path = Path(args.manifest)

    if not schema_path.is_file():
        fail(f"Schema not found: {schema_path}")
    if not manifest_path.is_file():
        fail(f"Manifest not found: {manifest_path}")

    schema = load_json(schema_path)
    manifest = load_json(manifest_path)

    try:
        Draft202012Validator.check_schema(schema)
    except js_exceptions.SchemaError as e:
        fail(f"Schema invalid: {e}")

    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(manifest), key=lambda e: e.path)

    if errors:
        print("[ERROR] Manifest failed JSON Schema validation:\n", file=sys.stderr)
        for err in errors:
            loc = "/".join(str(p) for p in err.path) or "(root)"
            print(f" - at {loc}: {err.message}", file=sys.stderr)
        sys.exit(2)

    logical_checks(manifest)

    print("OK: manifest is valid against schema v1.2.0")
    sys.exit(0)

if __name__ == "__main__":
    main()
