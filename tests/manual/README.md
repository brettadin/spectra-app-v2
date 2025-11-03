# Manual Tests

These scripts are for quick, human-in-the-loop checks that aren’t part of the automated pytest suite. They won’t be auto-collected by pytest.

Available scripts:
- manual_exoplanet.py — Load curated exoplanet CSV tables and print summary info
- manual_spex.py — Ingest a SpeX FITS spectrum and verify wavelength conversion

How to run (from the repo root):

PowerShell (Windows):

# Exoplanet CSVs
python -m tests.manual.manual_exoplanet

# SpeX FITS sample
python -m tests.manual.manual_spex

Notes:
- Scripts print ✓/✗ results and exit codes (manual_spex) for quick feedback.
- They rely on bundled samples under samples/; no network is required.
- If imports fail, ensure you’re running from the repository root so that the app package is importable.
