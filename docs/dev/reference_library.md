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
up the files without UI changes if they reuse existing keys. Regeneration scripts live under `tools/reference_build/` and
should be used instead of hand-editing JSON.

## JSON schema overview

### `nist_hydrogen_lines.json`

- `metadata`: citation info, source URL, retrieval timestamp, descriptive notes, and a `provenance` block containing the
  build script (`generator`), query window, and curation status (`authoritative`).
- `lines`: array of records with identifiers (`id`), quantum numbers, wavelengths (vacuum/air), wavenumber (cm⁻¹),
  frequency (THz), Einstein *A* (s⁻¹), relative intensity (normalised to Hα), and measurement uncertainty (nm).

- `metadata`: citation, notes, and `provenance.source_file` pointing at the curated CSV/JSON used as input to
  `build_ir_bands.py`.
- `groups`: array of functional group objects with ID, name, wavenumber min/max, qualitative intensity, vibrational modes
  (list), and notes.

### `line_shape_placeholders.json`

- `metadata`: includes `references` (array of citation/url pairs) documenting the spectroscopy literature to consult when
  implementing broadening models.
- `placeholders`: objects with ID, label, status (`todo` for now), description, parameter names, and notes.

### `jwst_targets.json`

- `metadata`: compiled timestamp, STScI citation, and a `provenance` block describing whether the file still contains
  digitised placeholders or fully regenerated MAST products.
- `targets`: array of JWST quick-look entries. Keys:
  - `id`, `name`, `object_type`, `instrument`, `program` (MAST program ID or label).
  - `spectral_range_um`: two-element array `[min_um, max_um]`.
  - `spectral_resolution`: resolving power (dimensionless).
  - `data_units`: string used for column labelling.
  - `data`: list of measurement dicts. Required keys: `wavelength_um` and `value`. Optional uncertainty columns should
    start with `uncertainty_` (e.g. `uncertainty_ppm`, `uncertainty_mjy_sr`).
  - `source`: nested citation info (`citation`, `url`, `notes`).
  - `provenance`: curated metadata describing whether values are `digitized_release_graphic` placeholders, the intended
    `planned_regeneration_uri` in MAST, and any pipeline versions already available.
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
2. Include `metadata.citation`, `metadata.url`, retrieval timestamps, and a `metadata.provenance` object so provenance is
   explicit and auditable.
3. Regenerate assets using the scripts below; do **not** land manual JSON edits for authoritative data.
4. Update `docs/user/reference_data.md` and `docs/user/spectroscopy_primer.md` to document the new dataset and cite its
   source.
5. (Optional) add regression coverage in `tests/test_reference_library.py` to lock in new IDs or expected value ranges.

## Regeneration scripts

The `tools/reference_build` folder contains small utilities that turn external sources into the JSON manifests consumed by
the app:

- `build_hydrogen_asd.py`: queries the NIST Atomic Spectra Database via `astroquery.nist`, converts the hydrogen lines to
  our schema, and records the wavelength window used. Usage:

  ```bash
  python tools/reference_build/build_hydrogen_asd.py --output app/data/reference/nist_hydrogen_lines.json
  ```

- `build_ir_bands.py`: ingests a curated CSV/JSON of IR functional-group ranges (typically transcribed from the NIST
  Chemistry WebBook) and writes the canonical JSON. Usage:

  ```bash
  python tools/reference_build/build_ir_bands.py docs/reference_sources/ir_functional_groups.csv \
      --output app/data/reference/ir_functional_groups.json
  ```

- `build_jwst_quicklook.py`: downloads calibrated JWST spectra using `astroquery.mast`, resamples them to a manageable
  number of points, and emits `jwst_targets.json`. Supply a config manifest listing the desired products (see
  `tools/reference_build/jwst_targets_template.json`). Usage:

  ```bash
  python tools/reference_build/build_jwst_quicklook.py tools/reference_build/jwst_targets.json \
      --output app/data/reference/jwst_targets.json --bins 64
  ```

Each script records its generator path inside `metadata.provenance.generator`, allowing CI to assert that assets were
rebuilt from source instead of hand-edited. Install `astroquery`, `astropy`, and `numpy` in the dev environment before
running the JWST fetcher.

## External references

- NIST Atomic Spectra Database — https://physics.nist.gov/asd
- NIST Chemistry WebBook — https://webbook.nist.gov/chemistry/
- NASA/ESA/CSA JWST releases — https://webbtelescope.org/
- STScI JWST Documentation — https://jwst-docs.stsci.edu/

The JWST data points currently ship as digitised quick-look values for offline use. Their `provenance.curation_status`
flag remains `digitized_release_graphic` until the build script is wired into CI and the assets are regenerated from
MAST/astroquery outputs.
