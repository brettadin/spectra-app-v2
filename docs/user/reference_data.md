# Reference Data Browser

The **Reference** tab in the Inspector exposes curated spectroscopy datasets that ship with the preview shell. All
entries are stored in `app/data/reference` so they can be browsed without a network connection and reused by agents or
future automation.

## NIST hydrogen line list

- Data source: [NIST Atomic Spectra Database (ver. 5.11)](https://physics.nist.gov/asd) — Y. Ralchenko, A.E. Kramida,
  J. Reader, and the NIST ASD Team (2024).
- Coverage: Lyman (UV) and Balmer (visible) transitions for neutral hydrogen.
- Fields: series, upper/lower quantum numbers, vacuum/air wavelength, wavenumber, Einstein *A* coefficients, relative
  intensity, uncertainty, and notes describing the Rydberg–Ritz connection.
- Usage: select **NIST Hydrogen Lines (Balmer & Lyman)**, optionally filter by series (e.g. “Balmer”) and copy values for
  overlay markers or import sanity checks.

## Infrared functional groups

- Primary reference: [NIST Chemistry WebBook](https://webbook.nist.gov/chemistry/) — P.J. Linstrom and W.G. Mallard
  (2024 update); supplemental ranges from Pavia *et al.*, *Introduction to Spectroscopy*, 5th ed. (2015).
- Contents: characteristic absorption windows (cm⁻¹) for O–H, N–H, aliphatic/aromatic C–H, carbonyl variants, alkynes,
  and carboxylates. Each range is annotated with intensity heuristics and vibrational modes.
- Usage: load **IR Functional Groups**, then filter by mode (“stretch”), functional class (“carbonyl”), or a wavenumber
  value to shortlist plausible assignments during import QA.

## Line-shape placeholders

- References: B.W. Mangum & S. Shirley (2015) PASP 127, 266–298; G. Herzberg (1950) *Spectra of Diatomic Molecules*.
- Purpose: captures TODO scaffolding for Doppler shifts, pressure/Stark broadening, and instrumental resolution so the
  feature backlog is visible to users and agents.
- Usage: select **Line-shape Placeholders** to review planned parameters before integrating physics models. Each entry
  is marked with a status flag (currently `todo`).

## JWST quick-look spectra

The JWST entries bundle down-sampled spectra digitised from public NASA/ESA/CSA/STSci releases so the preview can
illustrate multi-instrument datasets without contacting MAST. Each record cites its release page and records the
approximate resolving power.

| Target | Instrument | Program | Spectral range (µm) | Units | Notes |
| ------ | ---------- | ------- | ------------------- | ----- | ----- |
| WASP-96 b transmission | NIRSpec PRISM | ERS 1324 | 0.6–2.8 | Transit depth (ppm) | Water vapour feature from 2022 release graphic. |
| Jupiter mid-IR brightness | MIRI MRS | ERS 1373 | 7.6–12.8 | Radiance (MJy·sr⁻¹) | Auroral emission snapshot, digitised from Webb release. |
| Mars reflectance | NIRSpec PRISM | DD-2759 | 0.7–3.0 | I/F reflectance | Scaled from the 2022 Webb Mars press kit. |
| Neptune NIRCam brightness | NIRCam F444W/F356W | ERS 2282 | 1.6–4.4 | Radiance (MJy·sr⁻¹) | Photometry from STScI release imagery. |
| HD 84406 calibration | NIRCam imaging | Commissioning | 0.9–2.2 | Flux density (Jy) | Rounded photometry from wavefront sensing docs. |
| Earth observation | — | — | — | — | JWST cannot observe Earth; entry retained for completeness. |

### Workflow tips

1. Select a JWST dataset to preview the stored values. The measurement column adapts to the stored units and displays
   per-point uncertainties when available.
2. Use the Inspector filter bar to narrow down to wavelength windows (e.g. enter `1.4` to isolate WASP-96 b’s water
   absorption peak).
3. Click the citation link in the metadata pane to open the original release for deeper context or to pull the full FITS
   data products when the mission archive can be accessed.

## Roadmap hooks

- Doppler, Stark, and pressure broadening models are placeholders awaiting velocity/thermodynamic metadata capture.
- JWST records include spectral resolution fields so future convolution or instrument-matching steps can pick up the
  stored resolving power.
- Additional species (He I, O III, Fe II, etc.) can extend the NIST catalogue by dropping JSON manifests into
  `app/data/reference` — the Reference tab will ingest any new files after service refresh.
