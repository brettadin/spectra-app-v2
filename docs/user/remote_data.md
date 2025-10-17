# Remote data catalogue workflow

The **Remote Data** dialog lets you browse curated catalogues without leaving the
desktop preview. Searches are routed through provider-specific adapters and the
downloads are cached in your local Spectra data directory so you can re-open
them even when offline.

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

The results table displays identifiers, titles, and the source URI for each
match. Selecting a row shows the raw metadata payload in the preview panel so
you can confirm provenance before downloading.

## Downloading and importing spectra

1. Select one or more rows in the results table.
2. Click **Download & Import** to fetch the source files and pipe them through
   the normal ingestion pipeline.

Behind the scenes the application:

* Streams HTTP/HTTPS downloads through the bundled `requests` session, or uses
  `astroquery.mast.Observations.download_file` directly when a MAST record is
  selected so provenance matches the upstream archive and the raw HTTP session
  stays idle.
* Copies the artefact into the `LocalStore`, recording the provider, URI,
  checksum, and fetch timestamp in the cache index. MAST downloads normalise the
  returned astroquery path before copying so cached imports are reused even when
  the original file lives in the astroquery cache.
* Hands the stored path to `DataIngestService` so the file benefits from the
  existing importer registry, unit normalisation, and provenance hooks.

Imported spectra appear in the dataset tree immediately. They behave exactly
like manual imports: overlays update, the data table refreshes, and the history
dock records a "Remote Import" entry with the provider URI and cache checksum.

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
