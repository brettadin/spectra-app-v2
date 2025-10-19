# Reference Data Browser

The **Reference** tab in the Inspector exposes curated spectroscopy datasets that ship with the preview shell. All
entries are stored in `app/data/reference` so they can be browsed without a network connection and reused by agents or
future automation. Each dataset advertises a `provenance` status in the metadata pane so you can distinguish
authoritative NIST assets from digitised JWST placeholders that still need regeneration. For additional leads (UV/VIS,
IR, mass spectrometry, elemental standards, instrument handbooks), consult `docs/link_collection.md`—it tracks
spectroscopy-focused resources that align with the app’s analytical goals.

## NIST spectral line queries

- Source: [NIST Atomic Spectra Database (ver. 5.11)](https://physics.nist.gov/asd) — Y. Ralchenko, A.E. Kramida,
  J. Reader, and the NIST ASD Team (2024).
- Controls: the **Spectral lines** tab exposes element, ion stage (Roman or numeric), wavelength bounds, a vacuum/air
  selector, and a “Prefer Ritz wavelengths” toggle. Enter an element symbol (e.g. `Fe`), refine the bounds to the region of
  interest, and press **Fetch lines**. Example presets (Hydrogen I, Helium II, Iron II) pre-populate the fields when you
  need a quick sanity check.
- Results: the table lists the observed and Ritz wavelengths (nm), relative and normalised intensities, lower/upper energy
  levels, and transition type. Metadata on the right records the astroquery provenance, wavelength medium, and retrieval
  timestamp so notebook and CI runs can reference identical queries.
- Overlay: the preview plot renders each transition as a bar scaled by the normalised intensity. Enabling **Overlay on plot**
  projects those markers into the main workspace in the current unit system, letting you compare laboratory lines against
  imported spectra without re-parsing JSON manifests.

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
- Purpose: captures Doppler shifts, pressure and Stark broadening, instrumental resolution, and other scaffolding so the
  feature backlog is visible to users and agents.
- Models marked `ready` (Doppler shift, pressure broadening, Stark broadening) now include physical units and example
  parameters pulled from those references. Highlighting a row renders a normalised sample profile and records Doppler
  factors, Lorentzian kernel widths, or Stark wing scaling derived from the seeded inputs.
- Usage: select **Line-shape Placeholders** and click a row to refresh the preview plot. The **Overlay on plot** toggle
  projects the simulated profile into the main workspace, letting you compare the seeded broadening or velocity shift
  against active spectra before wiring real metadata into the pipeline.

### Workflow tips

1. Choose the appropriate tab (Spectral lines, IR groups, or Line-shape models). For NIST queries, press **Fetch lines** after
   configuring the element and bounds; IR and line-shape data load instantly.
2. Use the filter field below the tabs to narrow long tables by wavelength, functional group, or parameter name.
3. Enable **Overlay on plot** to project the preview into the main workspace. Spectral lines respect their relative intensities
   in the current unit system, IR bands shade their ranges with clustered labels, and line-shape previews overlay simulated
   profiles returned by `app/services/line_shapes.py`.
4. The metadata drawer captures citations, astroquery parameters, and retrieval timestamps so exported manifests can trace the
   exact reference dataset used during analysis.

## Roadmap hooks

- Doppler, Stark, and pressure broadening models are placeholders awaiting velocity/thermodynamic metadata capture.
- JWST records include spectral resolution fields so future convolution or instrument-matching steps can pick up the
  stored resolving power.
- Additional species (He I, O III, Fe II, etc.) can be fetched live via the NIST form today; a persistent catalogue export can
  still be generated under `app/data/reference/` for offline snapshots.
- Remote catalogue tooling now rewrites provider-specific queries and downloads via astroquery so agents should focus on
  spectroscopic targets (UV/VIS, IR, mass-spec benchmarks) when wiring new data sources.
- JWST quick-look placeholders have been retired from the Reference tab until calibrated spectra are regenerated from MAST; see
  the workplan for the outstanding ingestion task.
