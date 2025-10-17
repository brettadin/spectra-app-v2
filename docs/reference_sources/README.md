# Reference Source Staging

Place intermediate tables and manifests used by the reference build scripts in this directory. For example:

- `ir_functional_groups.csv` — curated wavenumber ranges transcribed from the NIST Chemistry WebBook with citation column.
- `jwst_targets.json` — configuration passed to `build_jwst_quicklook.py` enumerating MAST product URIs and metadata.

These files should not ship sensitive data or large binaries; commit only lightweight tables needed to reproduce the bundled
reference assets. Update `docs/dev/reference_build.md` when adding new source files.

See `docs/link_collection.md` for an expanded index of external archives and primers that complement the staged sources. Keep the
link collection in sync when new assets or build scripts land so future contributors can trace each dataset back to its
provenance.
