# Spectra App – Feature Review and Implementation Checklist

*Source document: [Branch · Debugging application launch.pdf](Branch · Debugging application launch.pdf)*

## File Type Support
- The legacy application includes dedicated ingestion modules for ASCII/CSV/TXT, FITS, and JCAMP-DX files that normalize units, deduplicate wavelengths, and build multiple downsample tiers for performant viewing.
- Remote fetchers integrate external archives (NIST ASD, ESO X-Shooter, SDSS DR17, NIST Quant IR) to pull spectral datasets, convert them into canonical units, and expose metadata for import.

### Key Recommendations
- Implement an ingestion layer in the beta that routes by extension to CSV, FITS, or JCAMP parsers and adds dependency guards for optional scientific libraries.
- Integrate remote fetchers into a dedicated **Data → Download** experience with search workflows per service and metadata previews prior to import.

### Open Risks
- Remote archive connectors remain absent from the UI, leaving external data sourcing unsupported.
- JCAMP and FITS parsing (including IR unit conversions) are not yet available, preventing parity with the original ingestion suite.

### Cited Sources
- [1](https://github.com/brettadin/spectra-app/blob/main/app/server/ingest_ascii.py), [2](https://github.com/brettadin/spectra-app/blob/main/app/server/ingest_fits.py), [4](https://raw.githubusercontent.com/brettadin/spectra-app/main/app/server/ir_units.py), [5](https://raw.githubusercontent.com/brettadin/spectra-app/main/app/server/fetchers/nist.py), [6](https://raw.githubusercontent.com/brettadin/spectra-app/main/app/server/fetchers/eso.py), [7](https://raw.githubusercontent.com/brettadin/spectra-app/main/app/server/fetchers/sdss.py), [8](https://raw.githubusercontent.com/brettadin/spectra-app/main/app/server/fetchers/nist_quant_ir.py)

## Data Operations
- Original math utilities resample spectra onto a shared grid before subtraction or ratio operations, apply epsilon-guarded arithmetic, and generate multi-tier downsample sets via LTTB and min–max envelope algorithms.
- Unit conversion pipelines transform wavelength and flux metadata (including IR helper logic) while tracking provenance about every transformation.
- Beta UI toggles for normalization and smoothing exist but lack functioning implementations, and metadata/provenance panels are placeholders.

### Key Recommendations
- Port resampling, subtraction, and ratio logic so users can perform math operations with overlapping wavelength safeguards and epsilon handling.
- Replace the current simple downsampler with tiered downsampling and ensure unit conversions plus provenance tracking are executed during ingestion.
- Activate normalization and smoothing controls using numerical routines (e.g., `numpy.interp`, `scipy.signal.savgol_filter`).

### Open Risks
- Without shared-grid resampling and epsilon handling, subtraction/division will yield inaccurate results or fail on mismatched spectra.
- Lack of provenance logging obscures transformations, complicating reproducibility and auditing.

### Cited Sources
- [9](https://raw.githubusercontent.com/brettadin/spectra-app/main/app/server/differential.py), [10](https://raw.githubusercontent.com/brettadin/spectra-app/main/app/server/differential.py), [11](https://raw.githubusercontent.com/brettadin/spectra-app/main/app/utils/downsample.py), [13](https://raw.githubusercontent.com/brettadin/spectra-app/main/app/utils/downsample.py)

## User Interface & Workflow
- The beta app already provides a dataset browser, multi-trace plotting with crosshair readouts, and tab placeholders for Info, Math, Style, and Provenance, but they lack dynamic LOD refresh, grouping, and populated metadata controls.
- Original expectations include overlays of spectral line lists, drag-and-drop import with progress feedback, remote fetcher dialogs, comprehensive export workflows, and richer keyboard shortcuts.

### Key Recommendations
- Populate Info/Provenance/Style tabs with metadata, transformation histories, and styling controls that update traces immediately.
- Expand import/export capabilities, including drag-and-drop multi-format support and CSV/JSON exports with provenance manifests.
- Implement overlay markers for fetched line lists and enhance dataset tree context menus for rename/duplicate/delete actions.

### Open Risks
- Absent remote fetcher UI and overlays will block workflows dependent on curated archives and line identification.
- Limited export options hinder sharing results or preserving derived traces with metadata.

## Libraries & Dependencies
- Parity requires scientific libraries such as Astropy, Pandas, Astroquery, Requests, BeautifulSoup, NumPy/SciPy, and PyQtGraph, with graceful handling when optional packages are missing.

### Key Recommendations
- Declare required dependencies in `requirements.txt`, add optional import guards, and surface clear user messaging when libraries are unavailable.

### Open Risks
- Missing dependency management could break ingestion or remote fetching, degrading user trust in the beta build.

### Cited Sources
- [2](https://github.com/brettadin/spectra-app/blob/main/app/server/ingest_fits.py), [3](https://github.com/brettadin/spectra-app/main/app/server/fetchers/nist.py), [5](https://raw.githubusercontent.com/brettadin/spectra-app/main/app/server/fetchers/nist.py), [6](https://raw.githubusercontent.com/brettadin/spectra-app/main/app/server/fetchers/eso.py), [8](https://raw.githubusercontent.com/brettadin/spectra-app/main/app/server/fetchers/nist_quant_ir.py), [14](https://raw.githubusercontent.com/brettadin/spectra-app/main/app/server/fetchers/nist.py), [15](https://raw.githubusercontent.com/brettadin/spectra-app/main/app/server/fetchers/eso.py)

## Implementation Checklist
- The roadmap enumerates tasks across ingestion routing, parser parity, metadata capture, remote fetchers, math/resampling, downsampling tiers, UI population, export tooling, error handling, and testing.

### Key Recommendations
- Sequence work by standing up the ingestion layer, then remote fetchers, followed by math/resampling, downsampling, UI population, export/persistence, error handling, and testing automation.
- Cache remote downloads with checksums and timestamps, preserve high-resolution data for analytics, and ensure UI responsiveness with million-point datasets.

### Open Risks
- Delayed testing and error handling could allow regressions or poor user messaging during complex ingestion/fetch scenarios.

### Cited Sources
- [9](https://raw.githubusercontent.com/brettadin/spectra-app/main/app/server/differential.py), [11](https://raw.githubusercontent.com/brettadin/spectra-app/main/app/utils/downsample.py), [13](https://raw.githubusercontent.com/brettadin/spectra-app/main/app/utils/downsample.py)

## References
1. [spectra-app/app/server/ingest_ascii.py at main · brettadin/spectra-app · GitHub](https://github.com/brettadin/spectra-app/blob/main/app/server/ingest_ascii.py)
2. [spectra-app/app/server/ingest_fits.py at main · brettadin/spectra-app · GitHub](https://github.com/brettadin/spectra-app/blob/main/app/server/ingest_fits.py)
3. [spectra-app/app/server/fetchers/nist.py at main · brettadin/spectra-app · GitHub](https://github.com/brettadin/spectra-app/blob/main/app/server/fetchers/nist.py)
4. [raw.githubusercontent.com/brettadin/spectra-app/main/app/server/ir_units.py](https://raw.githubusercontent.com/brettadin/spectra-app/main/app/server/ir_units.py)
5. [raw.githubusercontent.com/brettadin/spectra-app/main/app/server/fetchers/nist.py](https://raw.githubusercontent.com/brettadin/spectra-app/main/app/server/fetchers/nist.py)
6. [raw.githubusercontent.com/brettadin/spectra-app/main/app/server/fetchers/eso.py](https://raw.githubusercontent.com/brettadin/spectra-app/main/app/server/fetchers/eso.py)
7. [raw.githubusercontent.com/brettadin/spectra-app/main/app/server/fetchers/sdss.py](https://raw.githubusercontent.com/brettadin/spectra-app/main/app/server/fetchers/sdss.py)
8. [raw.githubusercontent.com/brettadin/spectra-app/main/app/server/fetchers/nist_quant_ir.py](https://raw.githubusercontent.com/brettadin/spectra-app/main/app/server/fetchers/nist_quant_ir.py)
9. [raw.githubusercontent.com/brettadin/spectra-app/main/app/server/differential.py](https://raw.githubusercontent.com/brettadin/spectra-app/main/app/server/differential.py)
10. [raw.githubusercontent.com/brettadin/spectra-app/main/app/server/differential.py](https://raw.githubusercontent.com/brettadin/spectra-app/main/app/server/differential.py)
11. [raw.githubusercontent.com/brettadin/spectra-app/main/app/utils/downsample.py](https://raw.githubusercontent.com/brettadin/spectra-app/main/app/utils/downsample.py)
12. [spectra-app/app/server/ingest_ascii.py at main · brettadin/spectra-app · GitHub](https://github.com/brettadin/spectra-app/blob/main/app/server/ingest_ascii.py)
13. [raw.githubusercontent.com/brettadin/spectra-app/main/app/utils/downsample.py](https://raw.githubusercontent.com/brettadin/spectra-app/main/app/utils/downsample.py)
14. [raw.githubusercontent.com/brettadin/spectra-app/main/app/server/fetchers/nist.py](https://raw.githubusercontent.com/brettadin/spectra-app/main/app/server/fetchers/nist.py)
15. [raw.githubusercontent.com/brettadin/spectra-app/main/app/server/fetchers/eso.py](https://raw.githubusercontent.com/brettadin/spectra-app/main/app/server/fetchers/eso.py)
