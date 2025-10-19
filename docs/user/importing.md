# Importing Local Spectra

The **File → Open** picker currently filters to comma-separated (`*.csv`,
`*.txt`) datasets. JCAMP-DX still appears once you toggle the OS-provided
"*All files*" view, but FITS ingest requires manually typing or pasting the path
into the filename field until the [GUI filter expansion roadmap
item](../../reports/roadmap.md#gui-file-dialog-filter-expansion) lands. Imported
arrays are normalised into the app's canonical wavelength baseline of
nanometres while the desktop build now copies the raw upload into the local
cache for provenance-aware reuse.

## Supported formats

- **CSV/TXT** – Flexible parser that scans for numeric columns even when prose
  surrounds the table. Units can be provided inline (e.g. `wavelength(nm)`), in
  square brackets, or in the preamble text; otherwise the importer estimates
  sensible defaults from value ranges (e.g. 400–2500 ≈ nanometres).
- **FITS** – 1D binary tables with wavelength and flux columns. The importer
  looks for standard names such as `WAVELENGTH`, `WAVE`, or `FLUX`. Original
  header metadata is preserved in the provenance panel. Install the optional
  `astropy` dependency (`pip install astropy`) to enable FITS ingest on new
  machines; without it the menu item remains but attempting to load FITS files
  will raise a helpful error.
- **JCAMP-DX** – Compact infrared/UV spectral files using `##XYDATA` blocks.

## How to import

1. Choose **File → Open** and select one or more spectra (hold `Ctrl` or `Shift` to pick multiple files in a single pass).
2. Review the detected units shown in the preview banner.
3. Confirm the ingest. The spectrum is normalised in-memory and the
   provenance-aware cache records the canonical units alongside a copy of the
   upload so repeat loads avoid re-parsing.

> **Need datasets?** Consult `docs/link_collection.md` for curated spectroscopy
> portals, lab standards, and instrument handbooks that pair well with the
> importer and remote catalogue workflow.

### Cache persistence controls

The ingest pipeline now writes to the on-disk cache automatically, which keeps
track of canonical units, importer provenance, and SHA256 hashes for deduping.
You can opt out temporarily by setting the environment variable
`SPECTRA_DISABLE_PERSISTENCE=1` before launching the app. When the environment
flag is not set, toggle **File → Enable Persistent Cache** to persist the
preference between sessions.

Imported spectra always appear in canonical units inside the application. Use
 the unit toggle on the toolbar to view alternative axes without mutating the
 underlying data. The raw source file remains untouched in the provenance
 bundle created during export.

### Browsing cached files

Open the **Library** dock (tabified with the Datasets pane) to inspect cached
uploads. Each row lists the stored alias, units, timestamp, provider/importer,
and checksum. Selecting a row now fills the metadata preview beneath the table
with the entry’s provenance, canonical units, byte size, and storage location,
so you can audit the cache without re-opening the file. Use the search bar to
filter by alias, units, provider, or checksum tokens. Double-click an entry to
re-load it without touching the original path—ideal when you want to compare
different normalisations or revisit a session offline. Routine imports no
longer spam the knowledge log with raw file paths; only high-level summaries
remain in `docs/history/KNOWLEDGE_LOG.md` while the library exposes the full
cache index for auditability.

## Intelligent parsing of messy tables

Field notebooks and vendor exports rarely follow a pristine two-column layout.
The CSV/TXT importer now performs several heuristics to recover the intended
trace:

- **Context-aware unit detection** – The reader inspects headers, inline
  parentheses, bracketed annotations, and leading prose for hints like
  “wavenumber (cm⁻¹)” or “Signal: Percent Transmittance”. When absent, it falls
  back to value ranges (for example, medians above 1000 are treated as
  wavenumbers).
- **Numeric block scanning** – Rather than assuming the very first non-comment
  line is a header, the importer searches for the longest contiguous block of
  rows containing at least two numbers. This lets it skip introductory text and
  footnotes while still capturing the core dataset.
- **Column scoring** – Each numeric column is scored for monotonic behaviour
  and variance. The most monotonic column becomes the independent axis, while
  the dependent axis is chosen from the remaining columns with the richest
  variation. Extra metadata such as temperature or annotations are retained in
  the provenance notes but excluded from the plotted trace.
- **Header-unit enforcement** – If column headers only advertise units (for
  example `Value [cm⁻¹]`), the importer trusts those annotations even when the
  labels are generic. Recognised wavelength/wavenumber units always win the X
  axis, while intensity units such as `%`, `a.u.`, or `counts` are kept on the
  Y axis.
- **Value-range awareness** – When the first numeric column is an intensity
  channel (common in vendor exports), the importer checks medians/spans against
  typical wavelength and wavenumber ranges so the axes are not flipped by
  absorbance-first layouts.
- **Header conflict resolution** – After selecting candidate axes, the parser
  double-checks the headers. If the tentative X column looks intensity-like and
  the Y column looks wavelength-like, the importer swaps them and records the
  correction in the provenance metadata so you can audit the decision.
- **Profile-based axis swap** – Even when headers are absent, the importer now
  inspects the numeric profiles. If the provisional X column behaves like an
  intensity series while the Y column sits in a typical wavelength/wavenumber
  range, the axes are swapped and the rationale (`profile-swap`) is written to
  `metadata.column_selection`.
- **Layout memory** – When a particular header/units layout has been seen
  before in the current session, the importer reuses the previously confirmed
  X/Y column order before re-running the heuristics. The cache key and whether
  it was a cache hit appear in `metadata.column_selection.layout_signature`
  and `layout_cache` so you can audit how recurring vendor exports were
  interpreted.
- **Automatic ordering** – Descending wavenumber tables are reversed so the X
  axis is monotonically increasing, matching the expectations of the plotting
  stack and unit conversions.

These behaviours are covered by regression tests in
`tests/test_csv_importer.py` to ensure future tweaks keep messy real-world data
ingestable. The importer also records the selected column indices and the
heuristics it used under `metadata.column_selection` for every ingest so you
can confirm how a particular file was interpreted. The same metadata block now
stores the original X/Y units under `metadata.source_units`; the plot pane reads
those values so newly imported traces appear in the exact scale they were
captured (for example percent transmittance) before you opt into additional
normalisation.

## Appendix — Provenance export bundle

Every export initiated from **File → Export Manifest** writes a timestamped
directory that preserves both the processed spectrum and its origin story. The
bundle contains:

- `manifest.json` — human-readable metadata describing the session, import
  source, applied unit conversions, and any math operations performed.
- `spectra/` — canonicalised arrays in CSV format (`wavelength_nm`,
  `intensity`) for each trace that remains visible in the workspace at export time.
- `sources/` — verbatim copies of the original uploads alongside their SHA256
  hashes so you can independently verify integrity.
- `log.txt` — a chronological history of ingest, analysis, and export actions
  captured by the provenance service.
- Optional extras (if selected in the export dialog):
  - `*_wide.csv` — a paired-column view tagged with `# spectra-wide-v1` comment
    headers so the CSV importer can expand each spectrum back into its own
    trace. This is designed for spreadsheet workflows where keeping values side
    by side is helpful before returning to Spectra.
  - `*_composite.csv` — an averaged intensity profile that records how many
    sources contributed to each wavelength sample. Use this when you want to
    compare a blended envelope against laboratory references without manually
    averaging outside the application.

The top-level CSV now leads with the numeric wavelength/intensity columns and
records provenance fields (`spectrum_id`, `spectrum_name`, units, point index)
to the right. When you re-import this combined CSV—or the wide variant with the
`spectra-wide-v1` header—the ingest pipeline spots the metadata, splits the
file into per-trace bundles, and restores each spectrum individually. You can
also ingest the composite CSV directly; the importer detects the standard
`wavelength_nm,intensity` prefix and ignores the `source_count` bookkeeping
column when choosing axes.

The top-level CSV now leads with the numeric wavelength/intensity columns and
records provenance fields (`spectrum_id`, `spectrum_name`, units, point index)
to the right.  When you re-import this combined CSV the ingest pipeline spots
the `spectrum_id` column, splits the file into per-trace bundles, and restores
each spectrum individually—no more merged axis mistakes or manual splitting of
the export before analysis.

Because the manifest records the units detected during import, round-tripping
through Ångström, micrometre, or wavenumber views does not alter the stored
values. When sharing data with collaborators, distribute the entire export
folder so downstream users can inspect both the canonicalised spectra and the
raw files referenced in the manifest.

## Quick smoke workflow

Run File → Open on `samples/sample_spectrum.csv`, toggle the units toolbar to Ångström/Transmittance, and export a manifest via File → Export Manifest. This mirrors the automated regression in `tests/test_smoke_workflow.py`, ensuring the ingest pipeline and provenance export are healthy.
