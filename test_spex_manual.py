"""Manual SpeX FITS helper (relocated to tests/manual/manual_spex.py).

This stub avoids pytest auto-collection while preserving a simple entry point.
Run manually with: `python -m tests.manual.manual_spex` from repo root.
"""

from tests.manual.manual_spex import test_spex_file as _run


if __name__ == "__main__":
    import sys

    success = _run()
    sys.exit(0 if success else 1)
