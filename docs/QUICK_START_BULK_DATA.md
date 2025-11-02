# 🚀 Quick Start: Bulk Planetary Data Pipeline

Get hundreds of high-quality Mercury/Venus spectra in 3 commands!

## One-Line Master Pipeline

```bash
# Complete automated pipeline for Mercury (downloads, processes, merges)
python tools/pipeline_master.py --target mercury --auto

# Preview what it would do first (dry run)
python tools/pipeline_master.py --target mercury --dry-run
```

**This will:**
1. ⬇️ Download ~2GB of Mercury MASCS data from PDS
2. 🔄 Convert all binary files to clean CSVs
3. 📊 Rank by quality (coverage, SNR, geometry)
4. ✨ Merge top 5 spectra per wavelength range
5. 📁 Copy best spectra to `samples/solar_system/mercury/`

**Result:** High-resolution Mercury spectrum (100-1500nm) ready to load in your app!

---

## Manual Step-by-Step (More Control)

### 1. Download (~5 minutes, requires wget)

```bash
# Mercury surface reflectance (best quality)
python tools/pds_wget_bulk.py --dataset uvvs_ddr_surface

# Mercury infrared
python tools/pds_wget_bulk.py --dataset virs_ddr --max-size 1G
```

### 2. Convert to CSV (~5-10 minutes)

```bash
python tools/parse_messenger_mascs.py "samples/SOLAR SYSTEM/Mercury_bulk" --batch
```

### 3. Merge Best Spectra (~1 minute)

```bash
python tools/mascs_quality_filter.py \
    --input "samples/SOLAR SYSTEM/Mercury_bulk" \
    --select-best 5 \
    --merge \
    --output samples/solar_system/mercury/mercury_composite.csv
```

---

## Venus Data

Same pipeline, different target:

```bash
python tools/pipeline_master.py --target venus --auto
```

---

## Output Files

After pipeline completes:

```
samples/solar_system/mercury/
├── mercury_uv.csv          # 115-320 nm (UVVS)
├── mercury_visible.csv     # 200-600 nm (merged)
├── mercury_ir.csv          # 300-1450 nm (VIRS)
└── mercury_composite.csv   # Full range, high-res
```

**Load in app:** Click "Load Solar System Samples" button → all files imported!

---

## Requirements

- **Python 3.8+** (already have ✓)
- **wget** (for downloads)
  - Windows: `choco install wget`
  - Mac: `brew install wget`
  - Linux: `apt install wget`
- **pandas** (for quality filtering, optional)

---

## Troubleshooting

**wget not found?**  
Install wget (see above) or download files manually from:  
https://pds-geosciences.wustl.edu/messenger/

**Out of disk space?**  
Limit download size: `--max-size 500M`

**Want more resolution?**  
Increase merge count: `--top-n 10` (merges 10 spectra per range instead of 5)

---

## Next Steps

1. **Run the pipeline** for Mercury
2. **Load in your app** to visualize
3. **Repeat for Venus** (and other planets as you get data)
4. **Extend the pipeline** for Cassini (Saturn), New Horizons (Pluto), HST (many targets)

---

Full documentation: `docs/DATA_ACQUISITION_PIPELINE.md`
