#!/usr/bin/env python3
"""
Worklog helper: prints today's suggested worklog filename (America/New_York),
current timestamps in local ET and UTC, and a header stub for the next entry.

Usage:
  python tools/worklog_helper.py

Notes:
- No external dependencies.
- Safe to run on Windows/macOS/Linux.
"""
from __future__ import annotations

from datetime import UTC, datetime
import os
import sys

try:
    import zoneinfo  # Python 3.9+
except Exception:  # pragma: no cover
    zoneinfo = None  # type: ignore


def _now_et() -> datetime:
    if zoneinfo is None:
        # Fallback: assume system local time approximates ET
        return datetime.now()
    ny = zoneinfo.ZoneInfo("America/New_York")
    return datetime.now(ny)


def main() -> int:
    now_et = _now_et()
    now_utc = datetime.now(UTC)

    date_et = now_et.strftime("%Y-%m-%d")
    time_et = now_et.strftime("%H:%M")
    time_utc = now_utc.strftime("%H:%MZ")

    worklog_rel = os.path.join("docs", "dev", "worklog", f"{date_et}.md")

    header = (
        f"## [Entry #N] {time_et} (Local ET) / {time_utc} (UTC) — Agent: <name>\n\n"
        f"### Summary\n- ...\n\n### Changes\n- ...\n"
    )

    print("Worklog helper")
    print("---------------")
    print(f"Suggested worklog file (ET): {worklog_rel}")
    print(f"Local ET time: {time_et}")
    print(f"UTC time:      {time_utc}")
    print("\nEntry header stub:\n")
    print(header)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
