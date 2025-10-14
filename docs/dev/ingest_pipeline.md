# Ingest Pipeline Overview

```
      ┌──────────────┐      ┌───────────────┐      ┌──────────────────┐
      │ File chooser │ ---> │ Importer plug │ ---> │ UnitsService      │
      └──────────────┘      │  (CSV/FITS/   │      │ to canonical nm  │
                            │   JCAMP)      │      │ + absorbance     │
                            └───────────────┘      └──────────────────┘
                                     │                         │
                                     ▼                         ▼
                               ┌────────────┐         ┌──────────────────┐
                               │ Spectrum   │ <------ │ Provenance entry │
                               │ (canonical │         │ + LocalStore     │
                               │   nm/A10)  │         └──────────────────┘
```

- Every importer reports the source units. The `UnitsService` normalises the
  wavelength array into **nanometres**; intensities are converted into base-10
  absorbance when possible. Raw units are kept in the metadata under
  `source_units` and `original_flux_unit`.
- The resulting `Spectrum` is immutable. Derived views use unit conversions at
  display time, so toggling units is idempotent and never mutates the stored
  arrays.
- The `LocalStore` copies the raw file to `%APPDATA%/SpectraApp/data` (or the
  platform equivalent) and records a `sha256` checksum alongside unit metadata.
  This makes repeat loads instantaneous and ensures provenance is reproducible.
- Provenance exports call `ProvenanceService.export_bundle`, which writes a
  manifest, a canonical CSV snapshot, and a PNG plot into the selected folder.
