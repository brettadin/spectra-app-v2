# PDS3 Multi-Column Table Import

## Overview

The Spectra app now supports importing PDS3 (Planetary Data System version 3) table files that contain spectral data for multiple targets in a single file. This is common for planetary albedo measurements where each column represents a different solar system object (e.g., Jupiter, Saturn, Uranus).

## How It Works

### File Format

PDS3 datasets consist of two companion files:
- **`.lbl` file**: ASCII label describing the table structure, column definitions, metadata
- **`.tab` file**: Fixed-width ASCII table containing the actual data

Example files in `samples/solar_system/`:
- `1995high.lbl` / `1995high.tab`: Jupiter, Saturn, Uranus albedo (520-995nm)
- `1995low.lbl` / `1995low.tab`: Jupiter, Saturn, Uranus, Neptune, Titan albedo (300-1050nm)

### Import Process

1. **Detection**: When opening a `.tab` file, the CSV importer checks for a companion `.lbl` file
2. **Label Parsing**: `pds_label_parser.py` extracts:
   - Column definitions (names, byte positions, units, data types)
   - Target names from `TARGET_NAME` field
   - Instrument metadata
   - Wavelength column identification
3. **Data Extraction**: Fixed-width column parsing creates separate arrays for each target
4. **Bundle Creation**: Each target becomes a separate `Spectrum` with:
   - Proper name (e.g., "Jupiter (Methane Spectrophotometry of the Jovian)")
   - Wavelength array from shared wavelength column
   - Target-specific albedo/flux values
   - Full PDS metadata preserved in `spectrum.metadata["pds_label"]`

## Usage

### File → Open

1. Navigate to `samples/solar_system/`
2. Select `1995high.tab` or `1995low.tab`
3. All targets are imported automatically as separate spectra
4. Each spectrum appears in the spectra list with its target name

### Metadata Preservation

PDS label metadata is stored in each spectrum:
```python
spectrum.metadata["pds_label"] = {
    "version": "PDS3",
    "targets": ["Jupiter", "Saturn", "Uranus"],
    "instrument": "BOLLER & CHIVENS SPECTROGRAPH",
    "instrument_host": "EUROPEAN SOUTHERN OBSERVATORY",
    "start_time": "1995-07-06",
    "stop_time": "1995-07-10",
    "note": "Full description of observation..."
}
```

## Implementation Details

### New Files

- **`app/services/pds_label_parser.py`**: PDS3 label parser
  - `PDSLabel` dataclass: Complete label metadata
  - `PDSColumn` dataclass: Column definitions
  - `parse_pds_label()`: Main parsing function
  - Helper methods for wavelength/target column identification

- **`tests/test_pds_label_parser.py`**: Parser tests (6 passing)
- **`tests/test_pds_import.py`**: End-to-end import tests (5 passing)

### Modified Files

- **`app/services/importers/csv_importer.py`**:
  - Added `_try_parse_pds_table()` method
  - Checks for `.lbl` companion file before normal CSV parsing
  - Creates bundle format for multi-target data

- **`app/services/data_ingest_service.py`**:
  - Added `.tab` extension to CSV importer registration
  - Extended `_ingest_bundle()` to accept PDS metadata parameter
  - Propagates PDS label metadata to individual spectra
  - Handles `pds3-multi-target` bundle format

## Supported Features

✅ Multi-column tables with shared wavelength column  
✅ Fixed-width column parsing via byte positions  
✅ Target identification from column names  
✅ Wavelength unit detection (nm, µm, Å)  
✅ Metadata preservation (instrument, dates, targets)  
✅ Automatic import of all targets  
✅ Proper spectrum naming (target + product name)  

## Current Limitations

- Only ASCII tables are supported (not binary PDS tables)
- Assumes shared wavelength column for all targets
- No user selection dialog for target filtering (imports all targets automatically)
- Only tested with planetary albedo data format

## Testing

Run the test suite:
```bash
pytest tests/test_pds_label_parser.py -v  # Parser unit tests
pytest tests/test_pds_import.py -v        # Import integration tests
```

All 11 tests passing (6 parser + 5 import).

## Example Data

The `samples/solar_system/` directory contains:
- **1995high.tab** (4750 rows, 0.1nm sampling):
  - Columns: vacuum λ, air λ, CH₄ absorption, Jupiter, Saturn, Uranus albedos
  - Range: 520-995nm
  
- **1995low.tab** (1875 rows, 0.4nm sampling):
  - Columns: vacuum λ, air λ, CH₄ absorption, Jupiter, Saturn, Uranus, Neptune, Titan albedos
  - Range: 300-1050nm

Data source: Karkoschka (1998) ICARUS - Methane, Ammonia, and Temperature Measurements of the Jovian Planets and Titan from CCD-Spectrophotometry

## Future Enhancements

- Binary PDS table support
- Target selection UI for large multi-target files
- PDS4 format support
- Automatic metadata display in Inspector panel
- Enhanced error messages for malformed labels
