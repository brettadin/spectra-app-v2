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
3. Enter a keyword, element symbol, or target name in the search field (or pick
   one of the curated **Examples…** entries) and click **Search**. The dialog
   blocks empty submissions so you always send provider-specific filters rather
   than unbounded catalogue sweeps.

### Provider-specific search tips

- **NIST ASD** – The query box maps to the catalogue’s `spectra` filter. Enter
  an element/ion (e.g. `Fe II`) or a transition label (`H-alpha`). The examples
  menu includes Fe II, Ca II K, and Hα shortcuts you can select instead of
  typing the query manually.
- **MAST** – Free-text input is rewritten to `target_name` before invoking
  `astroquery.mast.Observations.query_criteria`, and the adapter injects
  `dataproduct_type="spectrum"`, `intentType="SCIENCE"`, and
  `calib_level=[2, 3]` filters automatically. Supply JWST target names or
  instrument identifiers (e.g. `WASP-96 b`, `NIRSpec grism`). The examples menu
  preloads spectroscopy-friendly targets such as WASP‑96 b, WASP‑39 b, and
  HD 189733 so you can trigger a query without retyping common names.

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
  checksum, and fetch timestamp in the cache index.
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
