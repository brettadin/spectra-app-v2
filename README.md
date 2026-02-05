# Spectra App

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![Platform: Windows](https://img.shields.io/badge/platform-Windows-lightgrey.svg)](https://www.microsoft.com/windows)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![PySide6](https://img.shields.io/badge/Qt-PySide6-green.svg)](https://doc.qt.io/qtforpython/)

A modern **Windows desktop application** for spectroscopic analysis of stellar, planetary, and exoplanet data. Built with PySide6/Qt for performance and reliability.

---

## Features

### Remote Data Access
- **MAST Archive Integration**: Search and download calibrated spectra from NASA MAST (JWST, HST, and more)
- **Responsive UI**: Searches run in a subprocess - the interface never freezes
- **One-click downloads**: Select results and download FITS files directly
- **Targets**: Solar system objects, stars, exoplanets (Jupiter, Vega, WASP-39 b, TRAPPIST-1, etc.)

### Data Management
- **Multi-format support**: CSV, FITS, JCAMP-DX, HDF5, with intelligent header detection
- **Automatic grouping**: Datasets organized by source (Uploaded, Remote, Spectral Lines)
- **Group management**: Create, rename, delete groups; move datasets via right-click menu
- **Persistent library**: All imported data stays organized for future access
- **Offline-first cache**: Data persists locally with SHA256 deduplication

### Analysis Tools
- **Unit conversions**: Display in nm, Angstrom, um, or cm-1 (data stored canonically in nm)
- **Math operations**: Subtract (A-B), Ratio (A/B), Average multiple spectra
- **Normalization**: Max, Area, or Global modes with linear/log/asinh Y-scaling
- **Calibration**: FWHM blurring and radial-velocity shifts (non-destructive, display-time)
- **NIST line overlays**: Atomic spectral line references with caching
- **IR functional groups**: 50+ functional groups for FTIR/ATR analysis
- **Annotations**: Add persistent notes to plots - saved automatically with datasets
- **Quick Actions toolbar**: Icon-based shortcuts for common tasks (import, export, autoscale, etc.)

### Visualization
- **High-performance plotting**: PyQtGraph with LOD optimization for 1M+ point datasets
- **Customizable display**: Adjustable font sizes, themes (light/dark/midnight), color palettes
- **Modern UI**: Professional sci-fi aesthetic with resizable, tabbable panels
- **Live cursor readout**: Real-time coordinates in monospace font status bar
- **Inline metadata**: Dataset names show wavelength ranges and point counts at a glance
- **Robust FITS handling**: NaN/Inf values handled gracefully

---

## Quick Start

### Windows (Recommended)

Double-click `RunSpectraApp.cmd` or run:

```powershell
RunSpectraApp.cmd
```

The launcher automatically sets up Python, creates a virtual environment, and installs dependencies.

### Manual Installation

```bash
# Create virtual environment (Python 3.11+ required)
py -3.11 -m venv .venv
.\.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Launch (from repository root)
python -m app.main
```

### Conda Environment

```bash
conda env create -f environment.yml
conda activate spectra312
python -m app.main
```

> **Note**: Always run from the repository root directory, not from within `app/`.

---

## Repository Structure

```
spectra-app-v2/
+-- app/                      # Application source code
|   +-- main.py              # Entry point
|   +-- ui/                  # Qt windows and panels
|   +-- services/            # Business logic
|   +-- workers/             # Background processes
+-- docs/                    # Documentation
|   +-- INDEX.md            # Documentation hub
|   +-- user/               # User guides
|   +-- history/            # Patch notes and change log
+-- storage/                 # Local data storage
|   +-- samples/            # Example datasets
|   +-- annotations/        # Saved plot annotations
|   +-- cache/              # Downloaded remote data
+-- tests/                   # Test suite
+-- packaging/               # Distribution files
+-- IMPROVEMENTS_SUMMARY.md  # Recent UI improvements log
```

---

## Documentation

Start at **[docs/INDEX.md](docs/INDEX.md)** for the complete documentation map.

### User Guides
| Guide | Description |
|-------|-------------|
| [Quickstart](docs/user/quickstart.md) | Basic workflow walkthrough |
| [Remote Data](docs/user/remote_data.md) | Fetching spectra from MAST |
| [Plot Tools](docs/user/plot_tools.md) | Visualization features |
| [Importing](docs/user/importing.md) | Supported formats |

### Developer Resources
| Resource | Description |
|----------|-------------|
| [Improvements Summary](IMPROVEMENTS_SUMMARY.md) | Recent UI/UX improvements (Feb 2026) |
| [Patch Notes](docs/history/PATCH_NOTES.md) | Complete change history |
| [Knowledge Log](docs/history/KNOWLEDGE_LOG.md) | Architecture decisions |
| [START_HERE.md](START_HERE.md) | Development onboarding |

---

## Requirements

| Package | Version | Purpose |
|---------|---------|---------|
| Python | 3.11+ | Runtime |
| PySide6 | 6.8+ | Qt GUI framework |
| numpy | 1.26+ | Numerical operations |
| astropy | 7.1+ | FITS handling |
| astroquery | 0.4+ | MAST API access |
| pyqtgraph | 0.13+ | High-performance plotting |
| pandas | 2.2+ | Data manipulation |

**Optional:**
- `h5py` - HDF5/JWST Eureka pipeline support
- `pyhdf` - MODIS HDF4 support

---

## Testing

```bash
pytest
```

---

## Contributing

1. Read [CONTRIBUTING.md](CONTRIBUTING.md)
2. Check [docs/history/PATCH_NOTES.md](docs/history/PATCH_NOTES.md) for recent changes
3. Follow the docs-first development process
4. Add tests for new functionality

---

## License

MIT License - see [LICENSE](LICENSE) for details.

---

## Data Sources

- [NASA MAST](https://mast.stsci.edu/) - JWST, HST spectral archives
- [NIST Atomic Spectra Database](https://www.nist.gov/pml/atomic-spectra-database) - Reference line lists
- [Astropy](https://www.astropy.org/) - FITS and spectral data handling

---

**Spectra App** - Modern spectroscopic analysis for researchers and enthusiasts.