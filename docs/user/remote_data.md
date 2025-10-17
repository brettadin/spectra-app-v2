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
2. Pick a catalogue from the *Catalogue* selector. The desktop shell currently
   ships with:
   - **NIST ASD** (line lists via the Atomic Spectra Database)
   - **MAST** (MAST data products via `astroquery.mast`)
3. Enter a keyword, element symbol, or target name in the search field and click
   **Search**. Provider-specific tokens are supported:
   - NIST treats free text as an element/ion string. Use `element:Fe II`,
     `wavelength_min:250`, `wavelength_max:260` to constrain the query.
   - MAST maps free text to `target_name`. Additional filters like `obsid:12345`
     or `instrument:NIRSpec` route directly to `Observations.query_criteria`.

The results table displays identifiers, titles, and the source URI for each
match. Selecting a row shows the raw metadata payload in the preview panel so
you can confirm provenance before downloading.

## Downloading and importing spectra

1. Select one or more rows in the results table.
2. Click **Download & Import** to fetch the source files and pipe them through
   the normal ingestion pipeline.

Behind the scenes the application:

* Streams the remote file through the appropriate client. NIST requests use the
  shared `requests.Session`, while MAST downloads are handled via
  `astroquery.mast.Observations.download_file` so `mast:` URIs resolve
  correctly.
* Copies the artefact into the `LocalStore`, recording the provider, URI,
  checksum, and fetch timestamp in the cache index.
* Hands the stored path to `DataIngestService` so the file benefits from the
  existing importer registry, unit normalisation, and provenance hooks.

Imported spectra appear in the dataset tree immediately. They behave exactly
like manual imports: overlays update, the data table refreshes, and the Library
dock lists the cached artefact so you can re-ingest it later without touching
disk.

## Offline behaviour and caching

Every download is associated with its remote URI. If you request the same file
again the dialog reuses the cached copy instead of issuing another network
request. This makes it safe to build collections during limited connectivity:
the cache stores the raw download alongside canonical units so future sessions
can ingest the files instantly.

If persistent caching is disabled in **File → Enable Persistent Cache**, remote
fetches are stored in a temporary data directory for the current session. The
dialog will still reuse results within that session, but the artefacts are
discarded once the preview shell closes and the Library dock remains empty. The
Knowledge Log now stays focused on higher-level insights—routine remote imports
surface in the Library instead of logging raw file paths.
