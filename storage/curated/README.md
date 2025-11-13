# Curated Datasets

This directory contains richer, larger datasets preserved for teaching, exploration, and manual testing. Use these when you need depth beyond the tiny samples.

How to use in the app:
- File → Open… and navigate into `storage/curated/...`
- Or drag files from here into the app

Contents overview:
- laboratory/
  - IR/
    - CO2/CSV, CO2/Raw — CO₂ spectra at multiple pressures/conditions
    - H2O/CSV, H2O/Raw — H₂O spectra at multiple conditions
    - Lab/CSV, Lab/Raw — instrument exports as recorded
  - Lamps/
    - new_set/CSV, JSON — cleaned lamp lines (H, He, Hg, Ne, Xe, etc.)
    - old_set/CSV — earlier lamp set for provenance
    - from_phys_dpt/CSV — donor spectra (Krypton, Iodine)
  - SunMoon/
    - CSV, JSON, PNG, TXT — sun/moon collections, merges, and logs
- fits_data/
  - spex_library/ — SpeX stellar/standard FITS library (dozens of files)

Notes:
- Canonical unit storage remains nm in-app; conversions happen at display time.
- These files are optional — basic tests and demos work from `samples/`.
- If you reorganize curated data, update this README and docs/INDEX.md.
