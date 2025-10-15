#!/usr/bin/env python
"""Regenerate IR functional group ranges from a CSV or JSON source."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List


def _load_rows(path: Path) -> Iterable[Dict[str, Any]]:
    if path.suffix.lower() == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        rows = payload.get("rows", payload)
        for row in rows:
            yield row
        return

    with path.open("r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            yield row


def build_groups(source_path: Path) -> Dict[str, Any]:
    groups: List[Dict[str, Any]] = []
    for raw in _load_rows(source_path):
        try:
            wmin = float(raw["wavenumber_min_cm_1"])
            wmax = float(raw["wavenumber_max_cm_1"])
        except (TypeError, ValueError, KeyError) as exc:
            raise ValueError(f"Invalid wavenumber bounds in row: {raw}") from exc

        groups.append(
            {
                "id": raw.get("id") or raw.get("group", "").lower().replace(" ", "_"),
                "group": raw.get("group"),
                "wavenumber_cm_1_min": wmin,
                "wavenumber_cm_1_max": wmax,
                "intensity": raw.get("intensity"),
                "associated_modes": json.loads(raw.get("associated_modes", "[]"))
                if isinstance(raw.get("associated_modes"), str)
                else raw.get("associated_modes", []),
                "notes": raw.get("notes"),
                "source_id": raw.get("source_id", "nist_webbook"),
            }
        )

    retrieval_time = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    metadata = {
        "source_id": "nist_webbook",
        "citation": (
            "P.J. Linstrom and W.G. Mallard (eds.), NIST Chemistry WebBook, NIST SRD Number 69."
        ),
        "url": "https://webbook.nist.gov/chemistry/",
        "retrieved_utc": retrieval_time,
        "notes": "Ranges parsed from curated CSV; see source for uncertainty context.",
        "provenance": {
            "generator": "tools/reference_build/build_ir_bands.py",
            "source_file": str(source_path),
        },
    }
    return {"metadata": metadata, "groups": groups}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="CSV/JSON table containing IR ranges")
    parser.add_argument("--output", type=Path, required=True, help="Path to write JSON bundle")
    args = parser.parse_args()

    bundle = build_groups(args.source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(bundle, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
