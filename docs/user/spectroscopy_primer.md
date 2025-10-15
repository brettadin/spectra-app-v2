# Spectroscopy Primer

This primer summarises shared terminology and workflows used throughout the Spectra app so both users and agents can
interpret bundled datasets consistently.

## Coordinate systems and units

- **Wavelength vs. wavenumber**: The importer normalises *x* data to nanometres internally while preserving the source
  unit in provenance metadata. Use the units toolbar or `UnitsService` helpers to convert between nm, Å, µm, and cm⁻¹.
- **Intensity conventions**: The preview shell expects dimensionless transmission/absorbance or relative intensity by
  default. JWST quick-look spectra stored in `app/data/reference` include radiance (MJy·sr⁻¹), flux density (Jy), or
  transit depth (ppm); consult the metadata pane before combining data.
- **Resolution tracking**: Reference datasets capture the resolving power (R = λ/Δλ) when published. Retain this field
  when adding new libraries so future line-spread functions can honour instrument limitations.

## Spectral series and transitions

- Hydrogen line IDs follow the NIST Atomic Spectra Database naming convention (e.g. `H_Balmer_alpha`). Each entry records
  upper/lower quantum numbers and Einstein *A* coefficients for traceability.
- The Rydberg–Ritz combination principle relates the recorded wavenumbers to energy level differences using
  R∞ = 109 737 31.568 160 m⁻¹. When deriving new lines, recompute wavenumbers from vacuum wavelengths to avoid rounding
  drift.

## Infrared functional groups

- The IR catalogue provides broad ranges intended for quick hypothesis building, not final assignments.
- Intensities are qualitative (“strong”, “medium”, “variable”) and should be paired with importer provenance to confirm
  sample preparation (solid vs. solution, hydrogen bonding, etc.).
- When the importer encounters free-text headers mentioning “carbonyl” or “ester”, the heuristics in
  `CsvImporter` can use these ranges to validate axis guesses.

## Broadening and shift placeholders

The `line_shape_placeholders.json` scaffold enumerates future physics modules:

- **Doppler shift**: requires radial velocity inputs (km·s⁻¹) alongside rest wavelengths. Ideal for stellar or laboratory
  calibration sources.
- **Pressure/Lorentzian broadening**: needs collisional half-widths (γₗ) and perturber densities; relevant for gas cell
  experiments and planetary atmospheres.
- **Stark broadening**: targetting hydrogen Balmer wings; depends on electron density and temperature.
- **Instrumental LSF**: stores resolving power and convolution kernels for spectrograph-specific response functions.

Populate these entries (status → `ready`) once the corresponding services exist so agents can wire new buttons or math
operations without digging through historical specs.

## JWST datasets

- Quick-look spectra for WASP-96 b, Jupiter, Mars, Neptune, and HD 84406 are digitised from NASA/ESA/CSA/STSci releases
  to avoid repeated archive calls.
- Each entry records program IDs and instrument modes so agents can fetch the full `*.fits` data from MAST when a
  pipeline module is added.
- The “Earth Observation” row documents JWST’s field-of-regard constraint; future simulated Earth spectra should cite the
  synthetic model or mission planning docs used.

## Library references for agents

- **NIST Atomic Spectra Database** — https://physics.nist.gov/asd (API and citation guidance).
- **NIST Chemistry WebBook** — https://webbook.nist.gov/chemistry/ (vibrational band tables).
- **JWST mission documentation** — https://jwst-docs.stsci.edu/ (instrument handbooks, wavefront sensing notes).
- **STScI GitHub (JWST)** — https://github.com/spacetelescope (open notebooks, calibration tools, sample data).

Store new references alongside code changes in `docs/dev/reference_library.md` (see below) to keep provenance transparent.
