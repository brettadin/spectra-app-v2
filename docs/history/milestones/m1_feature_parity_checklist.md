# Feature Parity Checklist – Milestone 1

| Legacy Capability | Status in Desktop Shell | Notes |
|---|---|---|
| CSV/TXT ingest with metadata retention | ✅ Implemented via `DataIngestService` + `CsvImporter`; canonical units preserved. |
| Provenance manifest export | ✅ `ProvenanceService` writes schema-aligned manifest with checksums and timestamps. |
| Unit conversions (nm/µm/Å/cm⁻¹ + absorbance/transmittance) | ✅ Canonical baseline with reversible conversions and tests. |
| Overlay multiple spectra | ✅ Overlay service returns per-trace views; UI tab lists combined data. Plotting deferred. |
| Differential subtract & ratio ops | ✅ Math service with epsilon guard and trivial-result suppression. |
| Sample datasets for feature exercise | ✅ Two CSV samples bundled; UI auto-loads for demo. |
| Windows packaging pathway | ✅ PyInstaller spec and Windows build instructions provided. |
| Knowledge log integration | ⏳ Not implemented; planned in later milestone. |
| External providers / ML features | ⏳ Deferred; requires plugin framework extension. |
