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
  overlay markers or import sanity checks. The plot canvas renders each transition with its relative intensity and the
  **Overlay on plot** toggle projects those bars into the main workspace without normalising them against active traces.
  The metadata drawer lists the astroquery build script and retrieval timestamp.

## Infrared functional groups

- Primary reference: [NIST Chemistry WebBook](https://webbook.nist.gov/chemistry/) — P.J. Linstrom and W.G. Mallard
  (2024 update); supplemental ranges from Pavia *et al.*, *Introduction to Spectroscopy*, 5th ed. (2015).
- Contents: characteristic absorption windows (cm⁻¹) for O–H, N–H, aliphatic/aromatic C–H, carbonyl variants, alkynes,
  and carboxylates. Each range is annotated with intensity heuristics and vibrational modes.
- Usage: load **IR Functional Groups**, then filter by mode (“stretch”), functional class (“carbonyl”), or a wavenumber
  value to shortlist plausible assignments during import QA. Each band now renders as a filled, labelled lane that anchors
  itself to the active trace’s intensity span, keeping the annotation inside the plotted data rather than floating above it.
  Bands automatically stack their labels on discrete rows within the filled region so overlapping annotations remain legible
  even when multiple functional classes share a range. The dataset provenance links back to the staging CSV stored under
  `docs/reference_sources/`.

## Line-shape placeholders

- References: B.W. Mangum & S. Shirley (2015) PASP 127, 266–298; G. Herzberg (1950) *Spectra of Diatomic Molecules*.
- Purpose: captures TODO scaffolding for Doppler shifts, pressure/Stark broadening, and instrumental resolution so the
  feature backlog is visible to users and agents.
- Usage: select **Line-shape Placeholders** to review planned parameters before integrating physics models. Each entry
  is marked with a status flag (currently `todo`).

## JWST quick-look spectra

The JWST entries currently bundle down-sampled spectra digitised from public NASA/ESA/CSA/STSci releases so the preview can
illustrate multi-instrument datasets without contacting MAST. The metadata drawer calls out `curation_status:
digitized_release_graphic` and the planned MAST product URI that will replace the placeholder once the astroquery build
pipeline is wired into CI. Each record cites its release page and records the approximate resolving power.

| Target | Instrument | Program | Spectral range (µm) | Units | Provenance status | Notes |
| ------ | ---------- | ------- | ------------------- | ----- | ----------------- | ----- |
| WASP-96 b transmission | NIRSpec PRISM | ERS 1324 | 0.6–2.8 | Transit depth (ppm) | digitized_release_graphic → mast:JWST/product/jw01324-o001_s00002_nirspec_prism_clear_prism_x1d.fits | Water vapour feature from 2022 release graphic. |
| Jupiter mid-IR brightness | MIRI MRS | ERS 1373 | 7.6–12.8 | Radiance (MJy·sr⁻¹) | digitized_release_graphic → mast:JWST/product/jw01373-o002_t001_miri_ch1-shortmediumlong_s3d.fits | Auroral emission snapshot from Webb release. |
| Mars reflectance | NIRSpec PRISM | DD-2759 | 0.7–3.0 | I/F reflectance | digitized_release_graphic → mast:JWST/product/jw02759-o001_t001_nirspec_prism_s1600a3_x1d.fits | Scaled from the 2022 Mars press kit. |
| Neptune NIRCam brightness | NIRCam F444W/F356W | ERS 2282 | 1.6–4.4 | Radiance (MJy·sr⁻¹) | digitized_release_graphic → mast:JWST/product/jw02282-o001_t001_nircam_f444w_i2d.fits | Photometry from STScI release imagery. |
| HD 84406 calibration | NIRCam imaging | Commissioning | 0.9–2.2 | Flux density (Jy) | digitized_release_graphic → mast:JWST/product/jw01107-o001_t001_nircam_f200w_calints.fits | Rounded photometry from wavefront sensing docs. |
| Earth observation | — | — | — | — | operations_restriction | JWST cannot observe Earth; entry retained for completeness. |

### Workflow tips

1. Select a dataset from the combo box; the Reference plot updates immediately without forcing the selection back to the
   first entry, and the metadata pane refreshes with provenance and citation details.
2. Enable **Overlay on plot** to add the previewed dataset to the main graph. Hydrogen lines respect their relative
   intensities, IR bands anchor their shaded lanes within the current intensity envelope with label spacing safeguards verified
   by `tests/test_reference_ui.py::test_ir_overlay_label_stacking`, and JWST spectra draw as standard curves with optional
   uncertainty envelopes. Switching the combo box while the overlay toggle is enabled automatically swaps the projected
   reference so the main plot always mirrors the active dataset.
3. Use the Inspector filter bar to narrow down to wavelength windows (e.g. enter `1.4` to isolate WASP-96 b’s water
   absorption peak) and click citation links in the metadata pane to open the underlying source documentation.
4. If the plot toolbar is hidden, use **View → Plot Toolbar** to reveal the unit and normalization controls before deciding
   whether to overlay the reference data on raw or normalized traces.

## Roadmap hooks

- Doppler, Stark, and pressure broadening models are placeholders awaiting velocity/thermodynamic metadata capture.
- JWST records include spectral resolution fields so future convolution or instrument-matching steps can pick up the
  stored resolving power.
- Additional species (He I, O III, Fe II, etc.) can extend the NIST catalogue by dropping JSON manifests into
  `app/data/reference` — regenerate via a companion build script and the Reference tab will ingest the new files after
  service refresh.
