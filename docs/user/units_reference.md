# Units & Conversions Reference

Spectra App normalises all spectral axes to nanometres (nm) internally while preserving the original units provided by the data source. This reference explains the available unit options, how conversions are applied, and what guarantees the application provides for round-trip idempotency.

## Supported spectral units

| Label in UI | Physical dimension | Canonical symbol |
|-------------|--------------------|------------------|
| Nanometres  | Wavelength         | nm               |
| Angstroms   | Wavelength         | Å                |
| Micrometres | Wavelength         | µm               |
| Wavenumber  | Reciprocal length  | cm⁻¹             |

All values are stored in nm internally, which keeps the unit canon consistent across the application.

## Conversion guarantees

- **Round-trip idempotency**: Switching between any two supported units and back to the starting unit will yield the original values within floating-point tolerances. Automated regression tests enforce this behaviour.
- **Precision preservation**: Conversions use high-precision constants (e.g., 10 Å = 1 nm, 1000 nm = 1 µm) and avoid cumulative rounding by always converting via the canonical nm representation.
- **Provenance visibility**: Every conversion action is logged to the session manifest so exported bundles retain the original unit context and the canonical nm data.

## Practical guidance

- Prefer capturing raw data in its native units; the importer records both the raw axis metadata and the canonical nm values.
- When scripting automated ingest via the CLI, include unit annotations—omitted units default to nm.
- For wavenumber data (cm⁻¹), the app automatically converts to wavelength by inverting the values before normalising to nm. The inverse operation is applied when switching the UI back to cm⁻¹.
- If you notice unexpected rounding, verify that upstream data is not truncated before import; Spectra App will faithfully preserve precision once the data is inside the store.

## Further reading

- [Quickstart](./quickstart.md) — outlines how to ingest data and toggle units during a session.
- [Importing guide](./importing.md) — details metadata requirements for unit annotations and provenance capture.
- [Atlas: units and signed log transform](../atlas/README.md#units-signed-log-transform)
