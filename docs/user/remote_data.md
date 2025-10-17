# Remote data catalogue workflow

The **Remote Data** dialog lets you browse curated catalogues without leaving the
desktop preview. Searches are routed through provider-specific adapters and the
downloads are cached in your local Spectra data directory so you can re-open
them even when offline. The workflow prioritises calibrated spectroscopic data
(UV/VIS, IR, emission line cubes, etc.) so imported targets can be compared
directly against laboratory references.

> **Optional dependencies**
>
> Remote catalogues rely on third-party clients. The NIST adapter requires the
> [`requests`](https://docs.python-requests.org/) package, while MAST lookups
> also need [`astroquery`](https://astroquery.readthedocs.io/). If either
> dependency is missing the dialog will list the provider as unavailable and the
> search controls remain disabled until the package is installed.

## Opening the dialog

1. Choose **File → Fetch Remote Data…** (or press `Ctrl+Shift+R`).
2. Pick a catalogue from the *Catalogue* selector. The initial release ships
   with:
   - **NIST ASD** (line lists via the Atomic Spectra Database)
   - **MAST** (MAST data products via `astroquery.mast`)
3. Enter a keyword, element symbol, or target name in the search field and click
   **Search**. The dialog adapts the criteria to the selected provider before it
   reaches the service layer:
   - **NIST ASD** maps the text to the `spectra` parameter that powers the
     Atomic Spectra Database line search.
   - **MAST** converts free-form text into a `target_name`, or you can provide
     comma-separated `key=value` pairs for supported `astroquery.mast`
     parameters (for example `instrument_name=NIRSpec, dataproduct_type=spectrum`).
4. Reference the hint banner below the buttons for provider-specific examples.
   The dialog surfaces the mapping so you know when NIST expects an element/ion
   such as `Fe II`, and when MAST accepts target names or comma-separated
   arguments like `instrument_name=NIRSpec`.

When you switch between catalogues the banner updates in real time:

* **NIST ASD** highlights that searches revolve around element symbols or ion
  designations and reminds you that wavelength filters live in the advanced
  toolbar.
* **MAST** clarifies that the free-text box becomes a `target_name` by default
  and that you can provide comma-separated `key=value` pairs for supported
  `astroquery.mast.Observations.query_criteria` arguments (for example
  `obs_collection=JWST`, `proposal_id=1076`, or numerical sky positions via
  `s_ra`, `s_dec`, and `radius`).

### Provider-specific search tips

- **NIST ASD** – The query box maps to the catalogue’s `spectra` filter. Enter
  an element/ion (e.g. `Fe II`) or a transition label (`H-alpha`) to retrieve
  laboratory line lists that align with the bundled reference overlays.
- **MAST** – Free-text input is rewritten to `target_name` before invoking
  `astroquery.mast.Observations.query_criteria`, and the adapter injects
  `dataproduct_type="spectrum"`, `intentType="SCIENCE"`, and
  `calib_level=[2, 3]` filters automatically. Supply JWST target names or
  instrument identifiers (e.g. `WASP-96 b`, `NIRSpec grism`) to favour
  calibrated spectroscopic products (IFS cubes, slit/grism/prism extractions)
  instead of broad-band imaging or photometric light curves.

The hint banner beneath the results table updates as you switch providers and
also surfaces dependency warnings when optional clients are missing.

### Provider-specific search tips

- **NIST ASD** – The query box maps to the catalogue’s `spectra` filter. Enter
  an element/ion (e.g. `Fe II`) or a transition label (`H-alpha`) to retrieve
  laboratory line lists that align with the bundled reference overlays.
- **MAST** – Free-text input is rewritten to `target_name` before invoking
  `astroquery.mast.Observations.query_criteria`, and the adapter injects
  `dataproduct_type="spectrum"`, `intentType="SCIENCE"`, and
  `calib_level=[2, 3]` filters automatically. Supply JWST target names or
  instrument identifiers (e.g. `WASP-96 b`, `NIRSpec grism`) to favour
  calibrated spectroscopic products (IFS cubes, slit/grism/prism extractions)
  instead of broad-band imaging or photometric light curves.

The hint banner beneath the results table updates as you switch providers and
also surfaces dependency warnings when optional clients are missing.

The results table displays identifiers, titles, and the source URI for each
match. Selecting a row shows the raw metadata payload in the preview panel so
you can confirm provenance before downloading.

## Downloading and importing spectra

1. Select one or more rows in the results table.
2. Click **Download & Import** to fetch the source files and pipe them through
   the normal ingestion pipeline.

Behind the scenes the application:

* Streams the remote file through the HTTP/MAST client and writes it to a
  temporary location (`requests.Session.get` for HTTP URLs and
  `astroquery.mast.Observations.download_file` for `mast:` products, which keeps
  the MAST token/auth flow intact).
* Copies the artefact into the `LocalStore`, recording the provider, URI,
  checksum, and fetch timestamp in the cache index. MAST downloads normalise the
  returned astroquery path before copying so cached imports are reused even when
  the original file lives in the astroquery cache.
* Hands the stored path to `DataIngestService` so the file benefits from the
  existing importer registry, unit normalisation, and provenance hooks.

Imported spectra appear in the dataset tree immediately. They behave exactly
like manual imports: overlays update, the data table refreshes, and the history
dock records a "Remote Import" entry noting the provider. File-level metadata
now lives in the Library dock so the consolidated knowledge log stays focused
on high-level insights.

### Working with cached downloads

The **Library** dock (tabified with the Datasets view) lists every cached
artefact recorded by `LocalStore`. Use the filter box to search by alias,
provider, or units. Double-clicking an entry re-ingests the stored file without
touching the original download location—handy when reviewing spectra offline or
comparing multiple normalisations. The table mirrors cache metadata (provider,
checksum, timestamps) so you can audit provenance without sifting through raw
log entries.

## Offline behaviour and caching

Every download is associated with its remote URI. If you request the same file
again the dialog reuses the cached copy instead of issuing another network
request. This makes it safe to build collections during limited connectivity:
the cache stores the raw download alongside canonical units so future sessions
can ingest the files instantly.

If persistent caching is disabled in **File → Enable Persistent Cache**, remote
fetches are stored in a temporary data directory for the current session. The
dialog will still reuse results within that session, but the artefacts are
discarded once the preview shell closes.

See `docs/link_collection.md` for a curated index of spectroscopy catalogues,
laboratory references, and instrument handbooks you can target with the remote
workflow.
