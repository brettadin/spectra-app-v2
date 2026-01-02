Passband files
==============

- Format: two columns, wavelength_nm and throughput (any linear units), whitespace or comma separated.
- Comments starting with `#` are ignored.
- Filenames should match normalized instrument/band names (see below) so imports can auto-discover them.

Name matching
-------------
We normalize names to lowercase, replace non-alphanumerics with underscores, and strip leading/trailing underscores. Files are searched in this order:
- instrument
- band
- instrument_band
- band_instrument

Examples:
- `kepler_photometer.csv` covers band="Kepler Photometer", instrument="Kepler".
- `tess.csv` covers band or instrument containing "TESS".
- `jwst_nircam_f444w.csv` covers band="F444W" + instrument="NIRCam".

Sample file included: `kepler_photometer.csv` (coarse throughput curve) for testing.
