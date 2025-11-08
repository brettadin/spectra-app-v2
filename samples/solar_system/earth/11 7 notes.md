Here’s a full, structured “state of the union” so you can see exactly what we changed, what’s fragile, and the safest path forward. Then I’ll answer your “should we roll back?” and “other data sources?” questions directly.

## 1. What We’ve Done (Chronological / Thematic)

### A. NIST Overlay Behavior
- Refactor intent: Make NIST line collections behave like normal overlays so you can pin/unpin and they disappear cleanly.
- Current issue: The runtime log still shows `overlay_service.add({ ... dict ... })` — meaning in `_on_nist_fetch_clicked` we’re still passing a raw `dict` instead of a `Spectrum` (or your new overlay wrapper). That causes the `AttributeError: 'dict' object has no attribute 'id'`.
- Status: Partially refactored; needs a finishing pass to wrap NIST line sets in a proper Spectrum-like object (or add a branch inside `OverlayService.add`).

### B. MODIS HDF4 Data Integration
- Implemented `ModisHdfImporter` with:
  - Band list: sur_refl_b01..b07
  - Scaling 0.0001
  - Mask invalid values (<0 or >10000)
  - Median aggregation across pixels → a 7‑point “discrete spectrum”.
- Registered `.hdf` extension in ingest service.
- Added optional dependency note for `pyhdf` (later corrected version in requirements.txt).
- Provided CSV fallback sample (so you can test the UI without native libs).
- Added extraction helper script to guide user via GDAL/h5py or Panoply manual export.

### C. Windows Binary Library Challenge
- Root cause: PyPI `pyhdf` lacks bundled HDF4 DLLs on Windows.
- Solution implemented: Use conda to install `pyhdf` (and it pulled in `hdf4`, `mkl`, etc.).
- Verified `from pyhdf.SD import SD` works under conda base.

### D. Environment & Launch Changes
- Switched VS Code interpreter to conda’s Python (3.13).
- Edited launch.json to pin `python` path and set `PYTHONPATH`.
- Added settings.json for default interpreter.
- Updated `RunSpectraApp_Conda.cmd` to export `PYTHONPATH` and (optionally) `QT_DEBUG_PLUGINS`.

### E. Dependency Adjustments
- requirements.txt: Changed `pyhdf>=0.12.2` (non-existent) → `pyhdf>=0.11.6` with clarifying comment.
- Installed GUI / science stack (`PySide6`, `pyqtgraph`, `astropy`, `astroquery`, `pandas`, etc.)

### F. Diagnostics Around Crash
- Full app hard-crashes (native exit code) with `SpectraMainWindow()` under Python 3.13 + PySide6 6.10.0.
- Minimal Qt test and a `PlotPane` instantiation succeed (so base Qt + pyqtgraph is fine).
- Crash occurs *during* the large window initialization (dock/widget forest).
- No Python stack trace → likely a binary compatibility or PySide6 edge case.
- We have not yet bisected the exact constructor step (instrumentation not applied yet).

### G. Documentation & Developer Notes
- Added MODIS Windows install guidance doc.
- Added dev notes file for ingest (band mapping, scaling, QA future plan).
- Provided user-level extraction instructions (Panoply, CSV, or conda route).

### H. Utility / Test Additions
- Added `test_qt_simple.py` to confirm GUI baseline.
- Confirmed pyhdf import path works independently.

## 2. What’s Currently Broken / At Risk

| Area | Problem | Risk Level | Fix Effort |
|------|---------|------------|-----------|
| App launch (full window) | Native crash under PySide6 6.10 + Python 3.13 | High | Moderate (env downgrade) |
| NIST overlay removal | Still adding raw dict to overlay service | Medium | Low (wrap / convert) |
| MODIS importer runtime | Blocked until app launches normally | Medium | Low (once app runs) |
| Requirements reproducibility | Using base (root) conda env; not isolated | Medium | Low (create env) |
| Future QA / band expansions | Not yet implemented (QA flags, ROI) | Low | Planned enhancement |

## 3. Should We Roll Back?

I don’t think you need to roll everything back. The changes are *incremental and modular* (importer, docs, config). The real blocker is the binary/toolchain combination:

- PySide6 6.10.0 + Python 3.13 is relatively fresh; GUI frameworks often stabilize slower than core Python.
- Moving to a **Python 3.12 conda environment** (isolated) is the cleanest, lowest-risk step.  
- Rolling back code won’t solve a native ABI mismatch if that’s the underlying crash.

Recommendation: Don’t revert code; instead, create a stable environment and then finish the NIST refactor + test the MODIS importer.

## 4. Immediate Action Plan (Safe Path)

1. Create isolated env (Python 3.12):
   ```
   conda create -n spectra312 python=3.12 -c conda-forge
   conda activate spectra312
   conda install -c conda-forge pyhdf pyqtgraph pyside6 numpy pandas astropy astroquery requests
   pip install pytest  # if not pulled automatically
   ```
2. Point VS Code interpreter to `.../miniconda3/envs/spectra312/python.exe`.
3. Run F5 → confirm window opens.
4. Patch `_on_nist_fetch_clicked` to construct a small `Spectrum` object (or dedicated `LineOverlay` wrapper) instead of passing a dict.
5. Re-test ingest with:
   - CSV sample
   - Your HDF MODIS file (should now succeed, producing 7 points).
6. Add a tiny test for MODIS importer (already partly exists) plus a smoke test launching main window offscreen (set `QT_QPA_PLATFORM=offscreen` in CI later).
7. Commit.

If the crash persists *even* on Python 3.12, then we instrument the constructor with staged guards to isolate the failing block (create → add plot → add first dock → etc.).

## 5. Where Else Can You Get the Data? (Alternate Sources / Easier Formats)

If your goal is “Earth surface reflectance at a handful of wavelengths for comparative spectral analysis”, you have options:

### Direct MODIS Alternatives
- NASA LAADS DAAC (https://ladsweb.modaps.eosdis.nasa.gov/): Can request subsets in **GeoTIFF** or **netCDF4** (easier to parse than HDF4). Use subset tool or LAADS API + “format=GTiff”.
- NASA Earthdata CMR API + `earthaccess` Python client: Query “MOD09GA” granules then request conversions.
- NASA AppEEARS (https://appeears.earthdatacloud.nasa.gov/): Lets you pick coordinates/area, outputs CSV or GeoTIFF; eliminates HDF4 parsing locally.

### Other Sensors with Similar Reflectance Bands
- VIIRS Surface Reflectance (VNP09) – netCDF4/HDF5 (not HDF4) → easier ingestion (h5py).
- Sentinel-2 L2A (MSI) via Copernicus / AWS – 13 bands (more spectral richness); can downsample to your target wavelengths or pick closest.
- Harmonized Landsat-Sentinel (HLS) “HLSS30 / HLSL30” – surface reflectance, consistent formatting, Cloud-Optimized GeoTIFF.
- USGS Landsat Collection 2 Surface Reflectance (GeoTIFF) – stable, widely supported by rasterio/GDAL.

### Simplest Immediate “No Binary Pain” Path
Use AppEEARS or LAADS subset to export a **CSV** of per-band reflectance for a chosen AOI/date. Then our existing CSV ingestion path works unchanged.

### If You Want a More Continuous Spectrum
Your current approach yields only 7 discrete MODIS SR points. If your scientific goal is *spectral shape* over continuous wavelengths:
- Consider hyperspectral public samples: e.g. USGS Spectral Library, ECOSTRESS spectral library (already continuous), ASTER spectral libraries.
- In that case, the MODIS importer is a “discrete multi-band point series” adapter, not a full spectrum—keep expectations clear in the UI (label as “MODIS Multiband Sample” maybe).

## 6. Understanding Your Intent (Restated)

What you want (condensed):
- A robust desktop spectral exploration tool that can ingest heterogeneous planetary/remote sensing and lab spectra, unify wavelength units, normalize/combine, compare, and annotate with line libraries (NIST/IR line shapes).
- Extend it to planetary & Earth observation datasets seamlessly without users wrestling with obscure binary dependencies.
- Provide provenance + history + exportable bundles.
- Gradually add math ops (difference, ratios, normalized diff), calibration, overlays, and remote fetching.

We’ve aligned most infrastructure (ingest abstraction, overlay service, normalization pipeline, UI docks). The friction now is environment stability and finalizing the overlay/NIST adaptation.

## 7. Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Native crash from PySide6 on 3.13 | Use Python 3.12 env; pin versions in `environment.yml` |
| Future dependency drift | Add locked `conda env export > environment.yml` |
| NIST overlay partial refactor leads to regressions | Finish wrapper object + add unit test calling `_on_nist_fetch_clicked` in offscreen mode |
| User confusion over discrete vs continuous spectra | Label MODIS result as “7-band reflectance (discrete)” in name field |
| HDF4 dependency friction for casual users | Provide “Fetch via AppEEARS (CSV)” button in future; keep CSV fallback path prominent |

## 8. Concrete Next Steps (Priority Order)

1. Create `spectra312` environment (as above).
2. Update launch.json to point to new env (already structured for override).
3. Run app; if OK, proceed; if still crash, we instrument constructor.
4. Patch NIST fetch method to build a `Spectrum` (id like `nist::<element>::<range>::<counter>`) with x=lines, y=zeros, metadata={"type":"nist_lines"} and maybe set a special trace style (vertical markers).
5. Add test: run minimal offscreen window + call the fetch function with mocked line results (don’t hit network).
6. Add optional “MODIS (CSV) importer” doc snippet pointing to LAADS/AppEEARS for novice users.
7. Commit and tag a checkpoint (e.g. `checkpoint_modis_integration`).

## 9. Rollback Strategy (If You Insist)

If you decide to revert:
- Use `git log --oneline` to identify the last known-good commit before MODIS changes.
- Create a branch `experiment/modis` retaining current work.
- `git reset --hard <good_commit>` on `main` (only if you’re comfortable losing the new commits locally—otherwise merge selectively).
- Reintroduce only the CSV sample + doc first; delay HDF4 importer until environment is finalized.

I don’t recommend rollback because the code separation is clean and the remaining blockers are environment + small refactor completion.

## 10. Your Options for Data Path Right Now

| Goal | Fastest Path | Notes |
|------|--------------|-------|
| Get real MODIS reflectance into app today | Use AppEEARS/LAADS to export band values → CSV → ingest | Zero extra binary libs |
| Keep using full MODIS HDF pipeline | Fix environment (Python 3.12) + existing importer | Already coded |
| Expand to richer spectral resolution | Pull USGS/ASTER continuous spectral libraries (already textual) | Show continuous curves |
| Multi-sensor comparison (MODIS vs Sentinel) | Add additional simple CSV adapters first | Avoid binary complexity early |

## 11. My Recommendation (Direct Answer)

- Do **not** throw away the work. Proceed with a clean Python 3.12 env to eliminate the PySide6 crash variable.
- Finish the NIST overlay refactor and add a small test so this doesn’t regress silently.
- For everyday MODIS/Earth data, encourage CSV exports or AppEEARS while leaving HDF4 importer as an “advanced / enabled when pyhdf present” path.
- Then iterate on QA flags / uncertainty handling in MODIS importer once launch stability is confirmed.

## 12. Let Me Know Your Choice

Reply with one of:
- “Go with Python 3.12 env” → I’ll give exact condensed commands and patch an `environment.yml`.
- “Instrument constructor” → I’ll patch main_window.py with staged debug prints / early returns to isolate the crash.
- “Prefer CSV-only path for now” → I’ll mark HDF importer optional and improve docs/labels.
- “Rollback” → I’ll outline selective revert commands.

Just tell me which route you want and I’ll execute the next steps.

(And yes—I fully grasp what you’re building; we’re on a good trajectory. The crash is an environment/version kink, not architectural failure.)