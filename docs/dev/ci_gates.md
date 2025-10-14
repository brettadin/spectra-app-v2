# CI Gate Snapshot — 2025-10-15

The current branch (`improve-2025-10-15-b2-ci-scan`) was validated locally with
the standard CI commands:

| Command | Result | Notes |
| --- | --- | --- |
| `ruff check app tests` | Pass | No lint issues reported. |
| `mypy app --ignore-missing-imports` | Pass | Static typing clean across 18 modules. |
| `pytest -q --maxfail=1 --disable-warnings --cov=app --cov-report=term-missing` | Warning | Coverage plugin absent in the harness (`pytest` reports unrecognised `--cov` flags). |
| `pytest -q --maxfail=1 --disable-warnings` | Pass | All suites green; FITS smoke tests skip automatically when `astropy` is unavailable. |

Install `pytest-cov` (or vendor the plugin) if full coverage output is required
in CI. Otherwise, continue to run the reduced pytest invocation above to confirm
the functional suite.
