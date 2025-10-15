# Reference Library Implementation Notes

The reference datasets are stored as JSON assets under `app/data/reference` and are loaded by
`app/services/reference_library.ReferenceLibrary`. This file explains the schema so agents can extend or consume the
library.

## Directory layout

```
app/data/reference/
├── ir_functional_groups.json
├── jwst_targets.json
├── line_shape_placeholders.json
└── nist_hydrogen_lines.json
```

Future additions should drop new JSON manifests into this directory; the `ReferenceLibrary` class will automatically pick
up the files without UI changes if they reuse existing keys.

## JSON schema overview

### `nist_hydrogen_lines.json`

- `metadata`: citation info, source URL, retrieval timestamp, descriptive notes.
- `lines`: array of records with identifiers (`id`), quantum numbers, wavelengths (vacuum/air), wavenumber (cm⁻¹),
  frequency (THz), Einstein *A* (s⁻¹), relative intensity (normalised to Hα), and measurement uncertainty (nm).

### `ir_functional_groups.json`

- `metadata`: citation and notes.
- `groups`: array of functional group objects with ID, name, wavenumber min/max, qualitative intensity, vibrational modes
  (list), and notes.

### `line_shape_placeholders.json`

- `metadata`: includes `references` (array of citation/url pairs) documenting the spectroscopy literature to consult when
  implementing broadening models.
- `placeholders`: objects with ID, label, status (`todo` for now), description, parameter names, and notes.

### `jwst_targets.json`

- `metadata`: compiled timestamp and high-level STScI citation.
- `targets`: array of JWST quick-look entries. Keys:
  - `id`, `name`, `object_type`, `instrument`, `program` (MAST program ID or label).
  - `spectral_range_um`: two-element array `[min_um, max_um]`.
  - `spectral_resolution`: resolving power (dimensionless).
  - `data_units`: string used for column labelling.
  - `data`: list of measurement dicts. Required keys: `wavelength_um` and `value`. Optional uncertainty columns should
    start with `uncertainty_` (e.g. `uncertainty_ppm`, `uncertainty_mjy_sr`).
  - `source`: nested citation info (`citation`, `url`, `notes`).
  - Optional `status` (e.g. `not_observed`) when data are placeholders.

## Consuming the library

```python
from app.services.reference_library import ReferenceLibrary

library = ReferenceLibrary()
for line in library.spectral_lines(series="Balmer"):
    print(line["vacuum_wavelength_nm"], line["einstein_a_s_1"])

wasp96 = library.jwst_target("jwst_wasp96b_nirspec_prism")
if wasp96:
    data = wasp96["data"]
```

The `ReferenceLibrary.flatten_entry()` helper returns a list of string tokens for ad-hoc filtering and is used by the UI.

## Adding new datasets

1. Create a JSON file matching one of the patterns above, or extend the schema with similar keys.
2. Include `metadata.citation` and `metadata.url` so provenance is explicit.
3. Update `docs/user/reference_data.md` and `docs/user/spectroscopy_primer.md` to document the new dataset and cite its
   source.
4. (Optional) add regression coverage in `tests/test_reference_library.py` to lock in new IDs or expected value ranges.

## External references

- NIST Atomic Spectra Database — https://physics.nist.gov/asd
- NIST Chemistry WebBook — https://webbook.nist.gov/chemistry/
- NASA/ESA/CSA JWST releases — https://webbtelescope.org/
- STScI JWST Documentation — https://jwst-docs.stsci.edu/

The JWST data points currently ship as digitised quick-look values for offline use. Replace them with official FITS
products once the ingestion pipeline can fetch and cache the relevant calibrated files.
