Solar System sample spectra

This folder contains small, curated CSV samples to demonstrate loading planetary datasets without network access. Each planet has two files:

- A UV–VIS or UV sample (wavelength_nm vs reflectance or brightness_au)
- An IR sample (wavelength_nm vs radiance_w_m2_sr_um or reflectance)

These are tiny, illustrative extracts approximating the ranges of public datasets hosted by NASA PDS or mission archives. They are not intended for scientific analysis. Each CSV includes header comments with a source link for the original archive:

- Mercury: MESSENGER MASCS (UVVS/VIRS)
- Venus: HST WFPC2 (UV), Galileo NIMS (IR)
- Earth: EPOXI HRIV/HRII
- Mars: EPOXI HRIV/HRII
- Jupiter: Cassini UVIS/CIRS
- Saturn: Cassini ISS/CIRS
- Uranus: Voyager 2 UVS/IRIS
- Neptune: Voyager 2 UVS/IRIS
- Pluto: New Horizons ALICE/LEISA

How to import in the app

- In the UI, open the Inspector dock → Remote Data tab and click "Load Solar System Samples" to import all CSVs in this folder.
- Or use File → Open… and browse to an individual CSV.

Notes

- X-axis units are provided in nm for simplicity. IR long-wave samples therefore include values up to tens of microns (e.g., 50,000 nm).
- The CSV importer will infer units and sort ascending if needed; provenance comments are preserved in metadata.
 - Duplicate naming variants like `*_infrared.csv` and `*_uvvis.csv` are ignored in favor of `*_ir.csv`, `*_uv.csv`, and `*_visible.csv` for consistency.

Cleanup duplicates on disk

If you see both `*_infrared.csv`/`*_uvvis.csv` alongside the canonical `*_ir.csv`, `*_uv.csv`, or `*_visible.csv`, you can remove the duplicates safely. A helper script is provided:

1) Preview what would be deleted (dry run):

	- Run `tools/cleanup_solar_system_samples.py --dry-run`

2) Delete duplicates:

	- Run `tools/cleanup_solar_system_samples.py`

Replacing placeholders with authoritative datasets

We plan to replace these sample extracts with real, archived datasets from mission sources. A minimal manifest and fetcher are included:

- `samples/solar_system/manifest.json`: add URLs and citations per planet/band
- `tools/fetch_solar_system_datasets.py`: downloads files into the expected per-planet folders and filenames

Usage:

- Edit `samples/solar_system/manifest.json` to add `url` values for each entry you want to download.
- Optionally filter by planet/band:
  - `tools/fetch_solar_system_datasets.py --only planet=jupiter`
  - `tools/fetch_solar_system_datasets.py --only planet=mars,band=ir`
  - Add `--dry-run` to preview without writing files.
