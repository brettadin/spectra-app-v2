# Reference Data Build Pipeline

This guide walks through the helper scripts under `tools/reference_build/` so future agents can regenerate the bundled
reference datasets from authoritative sources without manual editing.

## Prerequisites

Install the optional tooling into your virtual environment:

```bash
.\.venv\Scripts\python -m pip install astroquery astropy numpy
```

The scripts rely on:

- [`astroquery.nist`](https://astroquery.readthedocs.io/en/latest/nist/nist.html) for NIST ASD hydrogen line queries.
- [`astroquery.mast`](https://astroquery.readthedocs.io/en/latest/mast/mast.html) for JWST product discovery/downloads.
- [`astropy`](https://docs.astropy.org/en/stable/) for unit handling and FITS IO.
- [`numpy`](https://numpy.org/doc/stable/) for quick resampling operations.

## Hydrogen line list

```
python tools/reference_build/build_hydrogen_asd.py --output app/data/reference/nist_hydrogen_lines.json
```

Arguments:

- `--wmin` / `--wmax`: wavelength window in nanometres (defaults 90–1000 nm).
- `--output`: destination JSON path.

The script calls `astroquery.nist.Nist.query`, converts the table to the Spectra schema, records the retrieval timestamp,
and embeds the wavelength window inside `metadata.provenance.query` for auditability.

## IR functional groups

```
python tools/reference_build/build_ir_bands.py docs/reference_sources/ir_functional_groups.csv \
    --output app/data/reference/ir_functional_groups.json
```

Arguments:

- `source`: CSV/JSON table of IR ranges curated from the NIST Chemistry WebBook or equivalent handbook. Use columns
  `group`, `wavenumber_min_cm_1`, `wavenumber_max_cm_1`, `intensity`, `associated_modes`, and optional `notes`.
- `--output`: destination JSON path.

The script embeds the source file path within `metadata.provenance.source_file` so reviewers can verify updates.

## JWST quick-look spectra

```
python tools/reference_build/build_jwst_quicklook.py tools/reference_build/jwst_targets.json \
    --output app/data/reference/jwst_targets.json --cache-dir .cache/jwst --bins 64
```

Arguments:

- `config`: JSON manifest describing target products. See `tools/reference_build/jwst_targets_template.json` for the
  expected structure (`mast_product_uri`, `pipeline_version`, etc.).
- `--bins`: number of resampled points per spectrum (default 64). Lower counts keep the bundled file lightweight while
  preserving broad spectral structure.
- `--cache-dir`: where downloaded FITS products are stored.
- `--output`: destination JSON path.

The script downloads the requested calibrated products via `astroquery.mast.Observations.download_products`, performs an
index-based resampling to `bins` points, and writes the final JSON bundle. Each entry receives a `provenance` block with
`mast_product_uri`, `pipeline_version`, and retrieval timestamp. Downstream UI components render these fields so users can
judge data quality.

## Verification checklist

After regenerating any dataset:

1. Run `pytest -q` to ensure regression coverage still passes.
2. Inspect the diff for large numeric swings and confirm the provenance metadata reflects the new build.
3. Update `docs/user/reference_data.md` and `docs/history/PATCH_NOTES.md` with a summary of the refresh, including source
   DOIs or URLs.
4. Record any new upstream dependencies or credentials (MAST tokens) inside `docs/dev/reference_build.md` if needed.

Document each regeneration in the workplan QA log with timestamps (UTC) so future agents know which assets were refreshed
and why.
