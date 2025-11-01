# 🚀 Quick Start: Bulk Planetary Data Pipeline

Get hundreds of high-quality Mercury/Venus spectra in 3 commands!

> Status note (2025‑11‑01)
> - Our previous bulk downloader followed the wrong PDS branch (GRNS/GRS, not MASCS).
> - MASCS UVVS/VIRS URLs used in the native downloader returned 404.
> - Until MASCS URL mapping is re-verified, use DRY RUN first and prefer curated/manual downloads.

## One-Line Master Pipeline

```bash
# Complete automated pipeline for Mercury (downloads, processes, merges)
python tools/pipeline_master.py --target mercury --auto

# Preview what it would do first (dry run)
python tools/pipeline_master.py --target mercury --dry-run
```

**This will:**
1. ⬇️ Download Mercury data from PDS (instrument filters in place; verify via dry-run output)
2. 🔄 Convert all binary files to clean CSVs
3. 📊 Rank by quality (coverage, SNR, geometry)
4. ✨ Merge top N spectra per wavelength range
5. 📁 Copy best spectra to `samples/solar_system/mercury/`

> Important
> - Always run `--dry-run` first and confirm URLs point to MASCS (UVVS/VIRS), not GRNS/GRS.
> - If URLs show `...messgrs_...` or `...grs_eng...`, cancel with Ctrl+C and switch to the manual workflow below.

---

## Manual Step-by-Step (More Control)

### 1. Curated download (recommended for now)

Use PDS search (Image/Atmospheres/Cartography nodes) filtered by:
- Target: Mercury
- Instrument Host: MESSENGER
- Instrument: MASCS UVVS / MASCS VIRS
- Product Type: CDR/DDR (science), exclude engineering/INDEX
- File types: .DAT/.IMG + .LBL

Download:
- UVVS: 10–30 science files across day/night and multiple orbits
  - Prefer calibrated (CDR/DDR)
  - Include label files (.LBL)
- VIRS: 10–20 calibrated scenes spanning 0.3–1.45 µm

Save under:
```
samples/SOLAR SYSTEM/Mercury_bulk/
```

### 2. Convert to CSV (~5–10 min)

```bash
python tools/parse_messenger_mascs.py "samples/SOLAR SYSTEM/Mercury_bulk" --batch
```

### 3. Merge best spectra (~1 min)

```bash
python tools/mascs_quality_filter.py ^
  --input "samples/SOLAR SYSTEM/Mercury_bulk" ^
  --select-best 5 ^
  --merge ^
  --output samples/solar_system/mercury/mercury_composite.csv
```

---

## Venus Data

Same pipeline, different target:

```bash
python tools/pipeline_master.py --target venus --auto
```

> Tip
> - Prefer Venus Express VIRTIS (UV/Vis/IR) and Akatsuki (UVI/IR2) for Venus reflectance/thermal windows.
> - See “Planet Data Playbook” for exact filters and file patterns.

---

## Output Files

After pipeline completes:

```
samples/solar_system/mercury/
├── mercury_uv.csv          # 115–320 nm (UVVS)
├── mercury_visible.csv     # 200–600 nm (merged)
├── mercury_ir.csv          # 300–1450 nm (VIRS)
└── mercury_composite.csv   # Full range, high-res
```

---

## Requirements

- Python 3.8+
- wget (for downloads)
  - Windows: `choco install wget`
- pandas (optional, for quality filtering)

---

## Troubleshooting

- Always dry-run first: `--dry-run`
- Wrong instrument in URLs? Cancel and switch to curated download.
- Limit size: `--max-size 500M`
- Increase resolution: `--select-best 10`

---

## Next Steps

1. Use curated downloads for Mercury until MASCS URLs are re-verified
2. Load results in the app to visualize
3. Use the Planet Data Playbook to expand to Venus and beyond

Full documentation: `docs/PLANET_DATA_PLAYBOOK.md`