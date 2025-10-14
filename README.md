# Spectra App - Spectroscopy Toolkit for Exoplanet Characterization

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![Platform: Windows](https://img.shields.io/badge/platform-Windows-lightgrey.svg)](https://www.microsoft.com/windows)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Code style: Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

A modern, modular **Windows desktop application** for spectroscopic analysis of stellar, planetary, and exoplanet data. Built with PySide6/Qt for performance and reliability, featuring clean UI, robust provenance tracking, and offline-first caching.

## 🎯 Project Overview

This repository represents the complete rewrite of the Spectra-App into a modern, modular desktop application. The redesign addresses legacy limitations while preserving all existing functionality:

- **Clean Architecture**: Modular service-based design for maintainability
- **Scientific Accuracy**: Rigorous unit handling and provenance tracking
- **Performance Focus**: Optimized for large datasets (1M+ points)
- **Docs-First Development**: Comprehensive documentation for users and developers

### Legacy Reference
- Original application: https://github.com/brettadin/spectra-app
- This repository: Complete PySide6 rewrite with enhanced architecture

## ✨ Key Features

### Data Ingestion & Management
- **Multi-format Support**: CSV/TXT, FITS 1D, JCAMP-DX with intelligent header detection
- **Remote Data Integration**: NASA/MAST API for JWST spectra, NIST Atomic Spectra Database
- **Offline-First Cache**: All data persists locally with SHA256 deduplication
- **Provenance Tracking**: Complete audit trail for all data operations

### Analysis & Processing
- **Unit Canon System**: Store raw data in nanometers; display-time conversions (nm/Å/µm/cm⁻¹)
- **Mathematical Operations**: A−B, A/B (epsilon-guarded), baseline removal, Savitzky-Golay smoothing
- **Spectral Analysis**: Gaussian fitting, peak detection, continuum subtraction
- **Reference Overlays**: NIST atomic line lists with interactive redshift controls

### User Experience
- **High-Performance Plotting**: PyQtGraph with LOD optimization for 1M+ point datasets
- **Clean, Intuitive UI**: Logical control grouping with progressive disclosure
- **Comprehensive Inspector**: Spectrum metadata, math operations, style controls, provenance viewer
- **Export Capabilities**: PNG, CSV with complete manifest.json provenance

## 📁 Repository Structure

```
spectra-app-beta/
├── app/                    # PySide6 application core
│   ├── ui/                # Windows, actions, plot pane, inspectors
│   ├── services/          # Business logic services
│   │   ├── ingest_*       # Data import handlers
│   │   ├── fetch_*        # Remote data fetchers
│   │   ├── units/         # Unit conversion system
│   │   ├── math/          # Analysis operations
│   │   ├── provenance/    # Audit trail management
│   │   └── store/         # Local cache management
│   └── main.py           # Application entry point
├── docs/                  # Comprehensive documentation
│   ├── user/             # Quickstart guides & tutorials
│   ├── dev/              # Architecture & API references
│   ├── edu/              # Spectroscopy educational content
│   ├── patch_notes/      # Version-specific release notes
│   └── ai_log/           # AI development history
├── specs/                # Technical specifications
│   ├── architecture/     # System design decisions
│   ├── ui_contract/      # UI component specifications
│   └── provenance/       # Data provenance schema
├── tests/                # Pytest test suite
│   ├── unit/            # Service-level tests
│   ├── integration/      # Cross-module tests
│   └── performance/      # Performance benchmarks
├── samples/              # Example datasets & manifests
├── reports/              # Audit reports & planning documents
└── packaging/            # Distribution & deployment
```

## 🚀 Quick Start

### Windows Quick Launch (Recommended)

Double-click `RunSpectraApp.cmd` or run from terminal:

```powershell
# Quick launch with automatic environment setup
RunSpectraApp.cmd

# Force clean environment rebuild
RunSpectraApp.cmd -Reinstall
```

The launcher script automatically:
- Detects available Python versions (3.11+ preferred)
- Creates/updates virtual environment
- Installs all dependencies
- Launches the application

### Manual Installation

1. **Create Virtual Environment**:
   ```bash
   py -3.11 -m venv .venv
   .\.venv\Scripts\activate
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Launch Application**:
   ```bash
   # From repository root directory
   python -m app.main
   ```

   > **Important**: Always run from repository root, not from within `app/` directory.

### Testing the Installation

Verify everything works by running the test suite:

```bash
pytest
```

Explore the `samples/` directory for example datasets and provenance manifests.

## 🔬 Scientific Mission

The Spectra App is designed for rigorous spectroscopic analysis with particular focus on:

- **Exoplanet Characterization**: Atmospheric composition, temperature profiles
- **Stellar Spectroscopy**: Elemental abundances, radial velocity measurements  
- **Planetary Science**: Surface composition, atmospheric studies
- **Laboratory Spectroscopy**: Reference data comparison, calibration validation

### Core Scientific Principles

- **Unit Integrity**: Canonical nanometer storage with mathematically sound conversions
- **Provenance Everywhere**: Complete data lineage from acquisition to export
- **Reference-Grade Accuracy**: NIST-validated line lists and JWST data integration
- **Transparent Processing**: All transformations documented and reversible

## 🛠 Development & Contribution

### For Users
- **Documentation**: Start with `docs/user/quickstart.md`
- **Tutorials**: See `docs/edu/` for spectroscopy fundamentals
- **Support**: Check `docs/user/faq.md` for common questions

### For Developers
- **Architecture**: Review `specs/architecture/system_design.md`
- **API Reference**: See `docs/dev/api/` for service contracts
- **Testing**: Add tests for all new features in `tests/`
- **Style Guide**: Follow coding conventions in `docs/dev/coding_standards.md`

### Documentation roadmap
- Track planned and in-progress documentation work in the [Documentation Inventory](docs/reviews/doc_inventory_2025-10-14.md).

### Building Distributables

```bash
# Build Windows executable
cd packaging
python -m PyInstaller spectra_app.spec
```

## 📚 Documentation Index

### User Documentation
- `docs/user/quickstart.md` - Getting started guide
- `docs/user/file_types.md` - Supported formats and import procedures
- `docs/user/units_conversions.md` - Unit system explanation
- `docs/user/analysis_tools.md` - Mathematical operations guide
- `docs/user/export_guide.md` - Export formats and provenance

### Developer Resources
- `docs/dev/architecture.md` - System architecture overview
- `docs/dev/data_pipeline.md` - Ingestion and processing flow
- `docs/dev/ui_contract.md` - UI component specifications
- `docs/dev/testing_guide.md` - Test development procedures

### Educational Content
- `docs/edu/spectroscopy_basics.md` - Fundamental concepts
- `docs/edu/atomic_spectra.md` - NIST ASD and line identification
- `docs/edu/jwst_data.md` - Working with JWST observations
- `docs/edu/analysis_techniques.md` - Scientific analysis methods

## 🎯 Roadmap & Status

### Current Phase: Core Implementation
- [x] Application skeleton and service architecture
- [x] Unit conversion system and provenance tracking
- [x] Basic plotting and UI framework
- [ ] Data ingestion pipeline (CSV, FITS, JCAMP-DX)
- [ ] Remote fetchers (NIST ASD, MAST/JWST)
- [ ] Mathematical operations and analysis tools

### Upcoming Features
- Advanced spectral fitting and modeling
- Plugin system for custom analysis
- Multi-instrument calibration tools
- Collaborative analysis features

## 🤝 Contributing

We welcome contributions from scientists, developers, and spectroscopy enthusiasts! Please:

1. Review the feature parity matrix in `reports/feature_parity_matrix.md`
2. Follow the docs-first development process
3. Add tests for all new functionality
4. Update relevant documentation
5. Submit PRs with clear descriptions and rationale

See `docs/contributing.md` for detailed guidelines.

## 📄 License

MIT License - see LICENSE file for details.

## 🔗 References & Data Sources

- **NASA MAST API**: JWST and Hubble spectral data
- **NIST Atomic Spectra Database**: Reference line lists
- **Astropy/Specutils**: Spectral data containers and operations
- **SpecViz**: UI/UX inspiration and compatibility targets

---

**Spectra App** - Advancing spectroscopic analysis through modern software engineering and scientific rigor.