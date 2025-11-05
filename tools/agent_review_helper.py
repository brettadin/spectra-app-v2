from __future__ import annotations

from datetime import UTC, datetime
import os

try:
    import zoneinfo  # Python 3.9+
except Exception:  # pragma: no cover
    zoneinfo = None


def now_et_iso() -> str:
    if zoneinfo is None:
        # Fallback: print local time if zoneinfo missing
        return datetime.now().isoformat()
    ny = zoneinfo.ZoneInfo("America/New_York")
    return datetime.now(ny).isoformat()


def now_utc_iso() -> str:
    return datetime.now(UTC).isoformat()


def suggested_path() -> str:
    # Use ET calendar date for filename, as per process
    if zoneinfo is None:
        date_et = datetime.now().date().isoformat()
    else:
        ny = zoneinfo.ZoneInfo("America/New_York")
        date_et = datetime.now(ny).date().isoformat()
    return os.path.join("docs", "dev", "agent_reviews", f"{date_et}.md")


def main() -> int:
    et = now_et_iso()
    utc = now_utc_iso()
    path = suggested_path()
    print("Suggested file path (ET calendar date):")
    print(path)
    print()
    print("Copy this header into the file:")
    print()
    print("# Fresh Eyes Review — "+path.split(os.sep)[-1].removesuffix('.md'))
    print()
    print("## Timestamps")
    print(f"- Local ET: {et}")
    print(f"- UTC: {utc}")
    print()
    print("Template: docs/dev/AGENT_REVIEW_TEMPLATE.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
