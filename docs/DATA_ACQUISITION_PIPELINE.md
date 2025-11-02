# Planetary Spectral Data Acquisition Pipeline

Complete workflow for downloading, processing, and analyzing hundreds of MESSENGER MASCS spectra for Mercury and Venus.

## 🚀 Quick Start

### 1. Bulk Download Mercury Surface Spectra

```bash
# Download all Mercury surface reflectance data (~500 MB)
python tools/pds_wget_bulk.py --dataset uvvs_ddr_surface

# Or download VIRS infrared data (~8 GB)
python tools/pds_wget_bulk.py --dataset virs_ddr --max-size 1G
```

### 2. Convert Binary Files to CSV

```bash
# Batch process all .dat files to clean CSVs
python tools/parse_messenger_mascs.py "samples/SOLAR SYSTEM/Mercury_bulk" --batch
```

### 3. Filter and Merge Best Spectra

```bash
# Rank all spectra by quality
python tools/mascs_quality_filter.py --input "samples/SOLAR SYSTEM/Mercury_bulk" --rank

# Select best 5 spectra per wavelength range and merge
python tools/mascs_quality_filter.py --input "samples/SOLAR SYSTEM/Mercury_bulk" --select-best 5 --merge --output mercury_composite.csv
```

---

## 📦 Available Datasets

### UVVS (Ultraviolet/Visible Spectrometer)

| Dataset | Description | Size | Wavelength Range | Best For |
|---------|-------------|------|------------------|----------|
| `uvvs_ddr_surface` | **Mercury surface reflectance** | ~500 MB | 210-320 nm (MUV) | Science, best quality |
| `uvvs_ddr_atmosphere` | Mercury exosphere emissions | ~200 MB | Na/Ca/Mg lines | Atmosphere studies |
| `uvvs_cdr` | Calibrated radiance | ~5 GB | 115-600 nm | Full spectral coverage |
| `uvvs_edr` | Raw uncalibrated data | ~2 GB | All | Low-level processing |

### VIRS (Visible/Infrared Spectrometer)

| Dataset | Description | Size | Wavelength Range | Best For |
|---------|-------------|------|------------------|----------|
| `virs_ddr` | **Mercury surface reflectance** | ~8 GB | 300-1450 nm | Best IR coverage |
| `virs_cdr` | Calibrated radiance | ~15 GB | 300-1450 nm | Full dataset |
| `virs_edr` | Raw uncalibrated data | ~10 GB | All | Low-level processing |

**Recommendation:** Start with DDR (Derived Data Records) - these are science-ready reflectance spectra.

---

## 🔧 Detailed Workflow

### Step 1: Install wget (if needed)

**Windows:**
```powershell
choco install wget
# Or download from: https://eternallybored.org/misc/wget/
```

**Linux/Mac:**
```bash
# Linux
sudo apt install wget

# Mac
brew install wget
```

### Step 2: Download Data

#### Option A: Surface Reflectance (Recommended)

Best quality, science-ready data:

```bash
# Mercury surface (MUV, 210-320 nm, binned to ~1 nm resolution)
python tools/pds_wget_bulk.py --dataset uvvs_ddr_surface

# Mercury surface (VIS/NIR, 300-1450 nm, full resolution)
python tools/pds_wget_bulk.py --dataset virs_ddr
```

#### Option B: Calibrated Radiance (More Data)

Higher spectral resolution, but requires more processing:

```bash
# All UVVS calibrated data (FUV/MUV/VIS)
python tools/pds_wget_bulk.py --dataset uvvs_cdr --max-size 2G

# VIRS calibrated (limit to NIR only)
python tools/pds_wget_bulk.py --dataset virs_cdr --accept "*/nir/*.dat,*/nir/*.lbl" --max-size 3G
```

#### Option C: Custom Filters

Download specific subsets:

```bash
# Only MUV surface observations from 2013
python tools/pds_wget_bulk.py --dataset uvvs_ddr_surface --accept "*/mascs2013*/*.dat,*/mascs2013*/*.lbl"

# First 100 files (dry run preview)
python tools/pds_wget_bulk.py --dataset virs_ddr --dry-run
```

### Step 3: Convert to CSV

Process all binary `.dat` files:

```bash
# Batch convert everything in the download directory
python tools/parse_messenger_mascs.py "samples/SOLAR SYSTEM/Mercury_bulk" --batch

# Or process a specific subdirectory
python tools/parse_messenger_mascs.py "samples/SOLAR SYSTEM/Mercury_bulk/uvvs_surface" --batch
```

**This will:**
- Read PDS labels (`.lbl` files)
- Parse binary data tables (`.dat` files)
- Extract wavelength + flux/reflectance
- Handle zigzag grating scans (bin and average)
- Output clean CSV with metadata headers

### Step 4: Quality Ranking

Analyze all spectra and rank by:
- Wavelength coverage
- Signal-to-noise ratio
- Observation geometry
- Data completeness

```bash
# Rank all spectra (shows top 10)
python tools/mascs_quality_filter.py --input "samples/SOLAR SYSTEM/Mercury_bulk" --rank

# Filter by detector
python tools/mascs_quality_filter.py --input "samples/SOLAR SYSTEM/Mercury_bulk" --detector VIRS --rank
```

### Step 5: Merge Best Spectra

Create high-resolution composite spectra:

```bash
# Merge top 5 spectra per wavelength range into single file
python tools/mascs_quality_filter.py \
    --input "samples/SOLAR SYSTEM/Mercury_bulk" \
    --select-best 5 \
    --merge \
    --output samples/solar_system/mercury/mercury_composite.csv

# Merge only VIRS infrared data
python tools/mascs_quality_filter.py \
    --input "samples/SOLAR SYSTEM/Mercury_bulk" \
    --detector VIRS \
    --select-best 10 \
    --merge \
    --output samples/solar_system/mercury/mercury_ir_high_res.csv
```

---

## 🪐 Venus Data

Same workflow works for Venus! MESSENGER made two Venus flybys:

```bash
# Download Venus flyby VIRS data
python tools/pds_wget_bulk.py --dataset virs_cdr --target venus

# Process
python tools/parse_messenger_mascs.py "samples/SOLAR SYSTEM/Venus_bulk" --batch

# Merge
python tools/mascs_quality_filter.py \
    --input "samples/SOLAR SYSTEM/Venus_bulk" \
    --select-best 3 \
    --merge \
    --output samples/solar_system/venus/venus_composite.csv
```

---

## 📊 Expected Output

After running the full pipeline, you'll have:

### Directory Structure
```
samples/solar_system/mercury/
├── mercury_uv.csv              # Best UV spectrum (single observation)
├── mercury_visible.csv         # Best visible spectrum
├── mercury_ir.csv              # Best IR spectrum
└── mercury_composite.csv       # Merged high-resolution composite
```

### Spectrum Files

Each CSV contains:
```csv
# Source: MESSENGER MASCS UVVS/VIRS
# Product: UMD_OB2_49_13044_005906_SCI_DAT
# Type: DDR
# Target: MERCURY
# Observation: 2013-02-13T00:59:08 to 2013-02-13T00:59:14
# Units: wavelength_nm=dimensionless
#
wavelength_nm,reflectance
210.0000,5.124222e-03
212.0000,5.963074e-03
...
```

### Quality Metrics

Quality ranking output:
```
Rank   Product ID                          Detector Points   Range (nm)          Score
--------------------------------------------------------------------------------------------------
1      umd_ob2_49_13044_005906_sci        UVVS     46       210-320             85.3
2      virsnd_ob2_12094_055036_sci        VIRS     256      300-1450            82.1
3      umc_ob5_65_15094_211347_sci        UVVS     134      160-320             78.9
...
```

---

## 🎯 Use Cases

### For Your App

Copy the best merged spectra to your sample folder:

```bash
# These will auto-load with "Load Solar System Samples" button
cp mercury_composite.csv samples/solar_system/mercury/mercury_visible.csv
cp mercury_ir_high_res.csv samples/solar_system/mercury/mercury_ir.csv
```

### For Science Analysis

- **Spectral feature identification**: Find absorption bands, emission lines
- **Surface composition**: Compare to mineral spectra libraries
- **Time-series**: Track changes across different mission phases
- **Spatial mapping**: Compare disk-integrated vs. regional observations

### For Multi-Planet Comparison

Build composites for all planets and overlay in your app to compare:
- Albedo differences
- Spectral slopes
- Absorption features
- UV/IR ratios

---

## 🔄 Extending to Other Missions

### Cassini (Saturn)

PDS also hosts Cassini UVIS and VIMS data:
```bash
# Similar wget approach:
wget -r -np -nH --cut-dirs=3 -R 'index.html*' \
  https://pds-rings.seti.org/vol/COUVIS_0xxx/
```

### New Horizons (Pluto)

```bash
wget -r -np -nH --cut-dirs=3 -R 'index.html*' \
  https://pds-smallbodies.astro.umd.edu/holdings/nh-p-alice/
```

### HST STIS (Many Targets)

Use MAST API:
```python
# astroquery.mast for Hubble spectra
from astroquery.mast import Observations
obs = Observations.query_criteria(target_name="Mercury", obs_collection="HST")
```

---

## 📝 Notes

- **Data Volume**: DDR datasets are manageable (500MB-8GB). CDR/EDR are larger (5-15GB).
- **Processing Time**: Parsing 1000 spectra takes ~5-10 minutes.
- **Quality**: DDR (Derived) data is best - already calibrated, binned, and validated.
- **Coverage**: MESSENGER orbited Mercury 2011-2015, collected >10,000 MASCS observations.

---

## 🐛 Troubleshooting

### wget not found
Install wget (see Step 1 above).

### Download interrupted
wget automatically resumes - just run the command again.

### Binary parsing errors
Some old PDS files have format issues. The parser skips bad files and continues.

### Out of memory
Process in smaller batches:
```bash
# Limit to first 100 files
python tools/pds_wget_bulk.py --dataset virs_ddr --max-size 500M
```

---

## 🚀 Future Enhancements

- [ ] Direct PDS API integration (avoid wget dependency)
- [ ] FITS file support for other missions
- [ ] Automated spectral line identification
- [ ] Interactive quality browser UI
- [ ] Multi-mission stitching (combine MESSENGER + Mariner + ground-based)
- [ ] Database backend for metadata search

---

**Questions?** Check the PDS MESSENGER MASCS archive documentation:
- https://pds-geosciences.wustl.edu/messenger/
- https://pds-geosciences.wustl.edu/missions/messenger/mascs.htm
