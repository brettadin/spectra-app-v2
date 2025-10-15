# Reference Data Browser

The **Reference** tab in the Inspector exposes curated spectroscopy datasets that ship with the preview shell. All
entries are stored in `app/data/reference` so they can be browsed without a network connection and reused by agents or
future automation. Each dataset advertises a `provenance` status in the metadata pane so you can distinguish
authoritative NIST assets from digitised JWST placeholders that still need regeneration.

## NIST hydrogen line list

- Data source: [NIST Atomic Spectra Database (ver. 5.11)](https://physics.nist.gov/asd) — Y. Ralchenko, A.E. Kramida,
  J. Reader, and the NIST ASD Team (2024).
- Coverage: Lyman (UV) and Balmer (visible) transitions for neutral hydrogen.
- Fields: series, upper/lower quantum numbers, vacuum/air wavelength, wavenumber, Einstein *A* coefficients, relative
  intensity, uncertainty, and notes describing the Rydberg–Ritz connection.
- Usage: select **NIST Hydrogen Lines (Balmer & Lyman)**, optionally filter by series (e.g. “Balmer”) and copy values for
  overlay markers or import sanity checks. The metadata drawer lists the astroquery build script and retrieval timestamp.

## Infrared functional groups

- Primary reference: [NIST Chemistry WebBook](https://webbook.nist.gov/chemistry/) — P.J. Linstrom and W.G. Mallard
  (2024 update); supplemental ranges from Pavia *et al.*, *Introduction to Spectroscopy*, 5th ed. (2015).
- Contents: characteristic absorption windows (cm⁻¹) for O–H, N–H, aliphatic/aromatic C–H, carbonyl variants, alkynes,
  and carboxylates. Each range is annotated with intensity heuristics and vibrational modes.
- Usage: load **IR Functional Groups**, then filter by mode (“stretch”), functional class (“carbonyl”), or a wavenumber
  value to shortlist plausible assignments during import QA. The dataset provenance links back to the staging CSV stored
  under `docs/reference_sources/`.

## Line-shape placeholders

- References: B.W. Mangum & S. Shirley (2015) PASP 127, 266–298; G. Herzberg (1950) *Spectra of Diatomic Molecules*.
- Purpose: captures TODO scaffolding for Doppler shifts, pressure/Stark broadening, and instrumental resolution so the
  feature backlog is visible to users and agents.
- Usage: select **Line-shape Placeholders** to review planned parameters before integrating physics models. Each entry
  is marked with a status flag (currently `todo`).

## JWST quick-look spectra

The JWST entries now ship with resampled, calibrated spectra for Jupiter sourced directly from MAST using
`build_jwst_quicklook.py`. Each record includes the authoritative `mast_product_uri`, the pipeline version reported in the
FITS header, and an automated retrieval timestamp so you can audit when the cache was last refreshed. Additional planets and
targets remain on the backlog until their calibrated products are harvested.

| Target | Instrument | Program | Spectral range (µm) | Units | Provenance |
| ------ | ---------- | ------- | ------------------- | ----- | ---------- |
| Jupiter reflectance | NIRSpec IFU (G140H/F100LP) | CAR 1022 | 0.97–1.89 | Flux density (Jy) | Calibrated Level-3 `jw01022-o013_t001_nirspec_g140h-f100lp_x1d.fits` (pipeline 1.19.1). |
| Jupiter mid-IR brightness | MIRI MRS (Channel 2 Short) | CAR 1022 | 7.5–8.8 | Flux density (Jy) | Calibrated Level-3 `jw01022-o018_t001_miri_ch2-short_x1d.fits` (pipeline 1.19.1). |

Both spectra originate from JWST Program 1022 (PI: J. A. Stansberry) "CAR FGS-017 Straylight for Moving Targets". Their
metadata panes link to the STScI program description and record the exact MAST product URIs used for regeneration. Remaining
targets (WASP-96 b, Mars, Neptune, HD 84406, etc.) stay flagged in the workplan until matching calibrated products are
ingested.

### Workflow tips

1. Select a JWST dataset to preview the stored values. The measurement column adapts to the stored units and displays
   per-point uncertainties when available.
2. Use the Inspector filter bar to narrow down to wavelength windows (e.g. enter `1.4` to isolate WASP-96 b’s water
   absorption peak).
3. Click the citation link in the metadata pane to open the original release or follow the planned MAST URI when the
   mission archive can be accessed.

## Roadmap hooks

- Doppler, Stark, and pressure broadening models are placeholders awaiting velocity/thermodynamic metadata capture.
- JWST records include spectral resolution fields so future convolution or instrument-matching steps can pick up the
  stored resolving power.
- Additional species (He I, O III, Fe II, etc.) can extend the NIST catalogue by dropping JSON manifests into
  `app/data/reference` — regenerate via a companion build script and the Reference tab will ingest the new files after
  service refresh.
