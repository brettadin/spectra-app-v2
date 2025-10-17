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
   **Search**. The placeholder text and hint banner update when you change
   providers—NIST expects a species label (for example `Fe II`), while MAST
   accepts full target names such as `WASP-96 b` or proposal identifiers.

The results table displays identifiers, titles, and the source URI for each
match. Selecting a row shows the raw metadata payload in the preview panel so
you can confirm provenance before downloading. Provider-specific hints remain
visible beneath the status banner to remind you which criteria each catalogue
understands.

## Downloading and importing spectra

1. Select one or more rows in the results table.
2. Click **Download & Import** to fetch the source files and pipe them through
   the normal ingestion pipeline.

Behind the scenes the application:

* Streams the remote file through the appropriate client—`requests` for HTTP
  catalogues such as NIST and `astroquery.mast.Observations.download_file` for
  MAST data URIs—and writes it to a temporary location.
* Copies the artefact into the `LocalStore`, recording the provider, URI,
  checksum, and fetch timestamp in the cache index.
* Hands the stored path to `DataIngestService` so the file benefits from the
  existing importer registry, unit normalisation, and provenance hooks.

Imported spectra appear in the dataset tree immediately. They behave exactly
like manual imports: overlays update and the data table refreshes. Routine
downloads no longer append verbose entries to the knowledge log—the Library
dock described below now tracks cached artefacts explicitly.

## Library dock

Remote downloads (and any local ingests recorded to the cache) are listed in the
**Library** dock on the left-hand side of the window. Use the filter box to
search by alias, provider, timestamp, checksum prefix, or unit metadata. Double
clicking an entry loads the cached file through the ingestion pipeline without
touching the knowledge log, and the detail pane renders the full cache record so
you can inspect provenance at a glance.

## Offline behaviour and caching

Every download is associated with its remote URI. If you request the same file
again the dialog reuses the cached copy instead of issuing another network
request. This makes it safe to build collections during limited connectivity:
the cache stores the raw download alongside canonical units so future sessions
can ingest the files instantly. The Library dock exposes these cached entries so
you can reload them even when the remote catalogue is offline.

If persistent caching is disabled in **File → Enable Persistent Cache**, remote
fetches are stored in a temporary data directory for the current session. The
dialog will still reuse results within that session, but the artefacts are
discarded once the preview shell closes.
