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

### Accessing Real Spectral Data
- **Remote Data Dialog**: Fetch calibrated spectra directly from NASA MAST archives
  - **Solar System quick-picks**: Mercury, Venus, Earth, Mars, Jupiter, Saturn, Uranus, Neptune, Pluto (JWST, HST, Cassini, New Horizons)
  - **Stars**: Vega (A0V CALSPEC standard), Tau Ceti (solar analog), HD 189733 (active K-dwarf host)
  - **Exoplanets & systems**: HD 189733 b, WASP-39 b, TRAPPIST-1 system (JWST transmission/emission spectra)
  - Access via **File → Fetch Remote Data** (Ctrl+Shift+R)
  - All data from credible sources: MAST, Exo.MAST, NASA Exoplanet Archive
  - Wavelength coverage: UV, visible, near-IR, mid-IR (0.1–30 µm depending on instrument)

> **Note**: Bundled reference data (JWST targets JSON) contains example-only digitized values for demonstration purposes. For scientific analysis, always use the Remote Data dialog to fetch real calibrated observations from MAST.

### Data Ingestion & Management
- **Multi-format Support**: CSV/TXT, FITS 1D, JCAMP-DX with intelligent header detection
- **Remote Data Integration**: NASA/MAST API for JWST spectra, NIST Atomic Spectra Database, NASA Exoplanet Archive
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
│   ├── history/          # MASTER_PROMPT, RUNNER_PROMPT, PATCH_NOTES, KNOWLEDGE_LOG
│   ├── reviews/          # Workplan, pass dossiers, documentation inventory
│   ├── user/             # Quickstart guides, importing reference, remote data docs
│   ├── dev/              # Developer guides (CI gates, ingest pipeline, reference build)
│   ├── brains/           # Timestamped architecture decisions
│   ├── atlas/            # Legacy Atlas materials retained for provenance
│   └── reference_sources/  # Curated spectroscopy references linked from the knowledge base
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

Prefer a guided walkthrough? Follow the step-by-step [Spectra App Quickstart](docs/user/quickstart.md) to launch the app, ingest sample data, toggle units, and export provenance bundles.

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

### Optional remote providers

MAST (JWST/HST) support requires the `astroquery` package. If you want the
`File → Fetch Remote Data…` dialog to enable MAST searches, install the
dependency in your virtualenv:

```bash
pip install astroquery
```

The Remote Data dialog will list available providers and annotate any missing
dependencies (e.g. `MAST (dependencies missing)`). The Search button is only
enabled when the provider's optional dependencies are present.

### Knowledge Log

The consolidated knowledge log (operational patch history, architecture notes,
and agent entries) lives at `docs/history/KNOWLEDGE_LOG.md`. Append entries
there when you make cross-cutting changes so future contributors can trace the
rationale.

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
- **Tutorials**: Explore `docs/user/spectroscopy_primer.md` and `docs/user/plot_tools.md`
- **Support**: Review the index in `docs/user/README.md` for topic-specific guides

- **Architecture**: Review `specs/architecture.md`
- **Pipelines**: See `docs/dev/ingest_pipeline.md` and `docs/dev/reference_build.md`
- **Testing**: Add tests for all new features in `tests/` and consult `specs/testing.md`
- **Documentation & Logging**: Update `docs/history/PATCH_NOTES.md` and `docs/history/KNOWLEDGE_LOG.md` with every change

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
- `docs/user/quickstart.md` - Getting started walkthrough from launch to export
- `docs/user/importing.md` - Supported formats and ingest workflow details
- `docs/user/plot_tools.md` - Plot interactions, crosshair usage, and LOD behaviour
- `docs/user/units_reference.md` - Unit system guarantees and toggle guidance

### Developer Resources
- `specs/architecture.md` - System architecture overview
- `specs/ui_contract.md` - UI component specifications and expectations
- `specs/testing.md` - Testing strategy and validation matrix
- `docs/dev/ingest_pipeline.md` - Ingestion and processing flow
- `docs/dev/reference_build.md` - Reference build instructions and packaging notes
- `docs/dev/ci_gates.md` - Local and CI validation gates

### Spectroscopy & Reference Material
- `docs/user/spectroscopy_primer.md` - Spectroscopy fundamentals for new contributors
- `docs/reference_sources/` - Curated reference datasets and literature links
- `docs/link_collection.md` - External resources to cite when sourcing new data

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