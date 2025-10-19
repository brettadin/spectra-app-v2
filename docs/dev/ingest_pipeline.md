# Ingest Pipeline Overview

```
      ┌──────────────┐      ┌───────────────┐      ┌──────────────────┐
      │ File chooser │ ---> │ Importer plug │ ---> │ UnitsService      │
      └──────────────┘      │  (CSV/FITS/   │      │ to canonical nm  │
                            │   JCAMP)      │      │ + absorbance     │
                            └───────────────┘      └──────────────────┘
                                     │
                                     ▼
                               ┌────────────┐
                               │ Spectrum   │
                               │ (canonical │
                               │   nm/A10)  │
                               └────────────┘
                                     │
                                     ▼
                               ┌──────────────────┐
                               │ Provenance entry │
                               └──────────────────┘
```

- Every importer reports the source units. The `UnitsService` normalises the
  wavelength array into **nanometres**; intensities are converted into base-10
  absorbance when possible. Raw units are kept in the metadata under
  `source_units` and `original_flux_unit`.
- The resulting `Spectrum` is immutable. Derived views use unit conversions at
  display time, so toggling units is idempotent and never mutates the stored
  arrays.
- Provenance exports call `ProvenanceService.export_bundle`, which writes a
  manifest, a canonical CSV snapshot, and a PNG plot into the selected folder.

> **Next steps**: Integrate the `LocalStore` cache so imported files are copied
> into the managed data directory with SHA256 deduplication. This is tracked in
> the [GUI filter expansion roadmap
> entry](../../reports/roadmap.md#gui-file-dialog-filter-expansion), which also
> covers expanding the File → Open filters beyond CSV/TXT.

## Smoke validation

An automated smoke test (`tests/test_smoke_workflow.py`) spins up the preview shell, ingests the sample CSV and a generated FITS file, toggles units through `UnitsService`, and runs `ProvenanceService.export_bundle`. This guards the end-to-end ingest pipeline and manifest export behaviour without manual UI clicks.
