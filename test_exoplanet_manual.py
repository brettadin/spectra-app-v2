"""Manual exoplanet loader helper (relocated to tests/manual/manual_exoplanet.py).

This stub avoids pytest auto-collection while keeping a convenient entry point.
Run manually with: `python -m tests.manual.manual_exoplanet` from repo root.
"""

import pytest

# Ensure pytest won't try to collect/execute this manual runner
pytestmark = pytest.mark.skip(reason="Manual runner moved to tests/manual; invoke via python -m tests.manual.manual_exoplanet")

from tests.manual.manual_exoplanet import test_exoplanet_csv as _run


if __name__ == "__main__":
    _run()
