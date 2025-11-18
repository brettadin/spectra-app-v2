# Feature Parity Checklist (Milestone 1)

| Legacy Behaviour | Status | Notes |
| --- | --- | --- |
| Load CSV spectra into workspace | ✅ Implemented | `DataIngestService` + `CsvImporter` handle canonical conversion with metadata preservation. |
| Support JCAMP-DX / FITS ingestion | ⏳ Pending | Interfaces prepared; plugins will be added in Milestone 2. |
| Unit conversion (nm/µm/Å/cm⁻¹; transmittance/absorbance) | ✅ Implemented | `UnitsService` covers reversible conversions with pytest coverage. |
| Provenance manifest export | ✅ Implemented | `ProvenanceService` emits machine-readable manifests including checksums and operations. |
| Overlay multiple spectra without mutation | ✅ Implemented | `OverlayService` stores immutable `Spectrum` instances; UI chart renders overlays. |
| Differential math operations (A−B, A/B) | ✅ Implemented | `MathService` performs aligned subtraction/ratio with epsilon handling and suppression logging. |
| Normalised difference, smoothing, similarity search | ⏳ Pending | Planned for later milestones per system design spec. |
| Provenance/History tab UI | ✅ Implemented (basic) | Manifest viewer available; knowledge log integration scheduled later. |
| Knowledge log updates on actions | ⏳ Pending | Service stub to be added with history tab enhancements. |
| Windows packaging workflow | ✅ Implemented (docs/spec) | PyInstaller spec and build guide prepared; execution deferred to native Windows host. |
