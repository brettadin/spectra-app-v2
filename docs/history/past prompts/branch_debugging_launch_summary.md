# "Branch · Debugging application launch" — Summary

> Source: [Branch · Debugging application launch.pdf](./Branch · Debugging application launch.pdf)

## Overview

The historical review contrasts the legacy `spectra-app` implementation with the current `spectra-app-beta`
preview, outlining the ingestion, processing, and user-interface capabilities required to reach and exceed
feature parity. It emphasises the original application's breadth of importer coverage, downsampling
infrastructure, remote archive integrations, and provenance tracking to guide ongoing beta development.

## Key Gaps Identified

- **Importer breadth:** The legacy application auto-detected wavelength/flux columns across ASCII, FITS, and
  JCAMP-DX formats, converting units via `astropy.units` and producing multi-tier downsample caches, whereas the
  beta build only ingests curated CSV samples without heuristics or tier generation.
- **Remote archive access:** Production code exposed NIST, ESO, SDSS, and NIST Quant IR fetchers with
  astroquery/requests clients, but the beta UI provides no remote download workflow or dependency guards.
- **Mathematical operations:** Original helpers resampled spectra onto shared grids before subtraction/ratio,
  recorded provenance, and surfaced results in dedicated Inspector tabs; the beta implementation lacks the math
  UI and resampling safeguards entirely.
- **UI instrumentation:** Legacy inspectors populated metadata, provenance logs, and style editors while the beta
  panes are mostly placeholders, omitting overlays, contextual menus, and responsive data tables tied to the
  active trace selection.

## Recommended Actions from the Review

- Build a routed ingestion layer that dispatches to CSV, FITS, and JCAMP parsers, preserves source units and
  provenance, and regenerates downsample tiers per zoom level.
- Introduce a "Remote Data" dialog that fronts the archived fetchers, caches downloads with checksums, and
  surfaces informative errors when optional dependencies such as `astroquery` are missing.
- Flesh out the Inspector by wiring metadata/provenance views, math operations, style controls, and data-table
  exports aligned with the active selection.
- Enable normalization and smoothing controls using NumPy/SciPy primitives while recording each transformation
  in the provenance log.

## Dependency and Testing Notes

- Documented production dependencies include `astropy`, `pandas`, `astroquery`, `requests`, `beautifulsoup4`,
  `numpy`, `scipy`, and `pyqtgraph`; the beta build must declare these with graceful fallbacks for absent
  packages.
- The review calls for ingestion unit tests, remote fetcher contract tests against known identifiers, math
  operation regression suites, and responsiveness checks with million-point spectra to confirm performance.

## Usage in Current Planning

This summary surfaces the historical checklist so modern planning documents (e.g., the Batch 14 workplan and
roadmap) can reference the original expectations while prioritising the importer, remote-fetch, and provenance
milestones still outstanding.
