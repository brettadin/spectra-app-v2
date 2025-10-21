# Remote data catalogue workflow

The **Remote Data** dialog lets you browse curated catalogues without leaving the
desktop preview. Searches are routed through provider-specific adapters and the
downloads are cached in your local Spectra data directory so you can re-open
them even when offline. The workflow prioritises calibrated spectroscopic data
(UV/VIS, IR, emission line cubes, etc.) so imported targets can be compared
directly against laboratory references.

> **Optional dependencies**
>
> Remote catalogues rely on third-party clients. Install the following Python
> packages before launching Spectra to ensure both providers are available:
>
> ```bash
> pip install -r requirements.txt
> ```
>
> This pulls in [`requests`](https://docs.python-requests.org/) for HTTP
> downloads, plus [`astroquery`](https://astroquery.readthedocs.io/) and
> [`pandas`](https://pandas.pydata.org/) for MAST queries. When any dependency
> is missing the dialog lists the provider as unavailable and disables the
> corresponding search controls until installation is complete.

## Opening the dialog

1. Choose **File → Fetch Remote Data…** (or press `Ctrl+Shift+R`).
2. Pick a catalogue from the *Catalogue* selector. The current build focuses on:
   - **NIST ASD** (atomic line lists via `astroquery.nist`)
   - **MAST** (MAST data products via `astroquery.mast`)

   > **Tip**: The Inspector’s **Reference → Spectral lines** tab still exposes the full pinned-workflow for NIST queries. Use the
   > Remote Data dialog when you want a quick CSV download to compare against live spectra, then pin the results from the
   > inspector if you need persistent overlays and palette controls.
3. Enter a keyword, element symbol, or target name in the search field (or pick
   one of the curated **Examples…** entries) and click **Search**. The dialog
   blocks empty submissions so you always send provider-specific filters rather
   than unbounded catalogue sweeps.

### Provider-specific search tips

- **NIST ASD** – Provide an element/ion identifier (e.g. `Fe II`, `O III`). Optional clauses such as `keyword=nebula` or
  `keyword=aurora` refine the transition list without widening the wavelength bounds. The dialog automatically forwards the
  element/keyword pair and ion-stage tokens (e.g. `ion=III`) to the remote service so cached CSV exports record the full query
  context.
- **MAST** – Free-text input is rewritten to `target_name` before invoking
  `astroquery.mast.Observations.query_criteria`, and the adapter injects
  `dataproduct_type="spectrum"`, `intentType="SCIENCE"`, and
  `calib_level=[2, 3]` filters automatically. Supply JWST target names or
  instrument identifiers (e.g. `WASP-96 b`, `NIRSpec grism`). The examples menu
  preloads spectroscopy-friendly targets including all major solar system planets
  (Mercury, Venus, Earth/Moon, Mars, Jupiter, Saturn, Uranus, Neptune), exoplanets
  such as WASP‑96 b and WASP‑39 b, and stellar standards like Vega, so you can
  trigger a query without retyping common names. Tick
  **Include imaging** to relax the product filter so calibrated imaging results
  appear alongside spectra.

The hint banner beneath the results table updates as you switch providers and
also surfaces dependency warnings when optional clients are missing.

The results table now surfaces a richer snapshot for each match—identifier,
target, mission, instrument, product type, plus quick links for preview and
download. Selecting a row shows the raw metadata payload in the preview panel so
you can confirm provenance before downloading, and the preview/download links
open in your default browser when you want to inspect the provider portal
directly.

> **Background execution**
>
> Searches and downloads now run on background threads. A compact progress bar
> beside the status banner lights up while work is in flight, and the
> search/download buttons remain disabled. This keeps the main window
> responsive—even long JWST queries no longer freeze the shell—and any warnings
> from the background worker are surfaced once the operation completes.

## Downloading and importing spectra

1. Select one or more rows in the results table.
2. Click **Download & Import** to fetch the source files and pipe them through
   the normal ingestion pipeline. The same status spinner appears while
   downloads run, the action buttons are disabled, and the banner reports how
   many products were imported (plus any failures) once the worker finishes.

Behind the scenes the application:

* For providers that expose downloadable artefacts, streams the remote file
  through the appropriate client (`requests.Session.get` for HTTP URLs and
  `astroquery.mast.Observations.download_file` for `mast:` products, which keeps
  the MAST token/auth flow intact).
* Copies the artefact into the `LocalStore`, recording the provider, URI,
  checksum, and fetch timestamp in the cache index.
* Hands the stored path to `DataIngestService` so the file benefits from the
  existing importer registry, unit normalisation, and provenance hooks.

If any downloads fail mid-batch, the worker aggregates those messages and shows
a single warning dialog when the import completes so you can review the
identifiers that need attention without dismissing multiple pop-ups.

Imported spectra appear in the dataset tree immediately. They behave exactly
like manual imports: overlays update, the data table refreshes, and the history
dock records a "Remote Import" entry noting the provider. File-level metadata
now lives in the Library tab inside the Data dock so the consolidated knowledge
log stays focused on high-level insights.

### Working with cached downloads

The **Library** tab in the **Data** dock lists every cached artefact recorded by
`LocalStore`. Use the filter box to search by alias, provider, or units.
Double-clicking an entry re-ingests the stored file without touching the
original download location—handy when reviewing spectra offline or comparing
multiple normalisations. The table mirrors cache metadata (provider, checksum,
timestamps) while the detail panel on the right renders provenance and storage
paths so you can audit downloads without sifting through raw log entries.

## Offline behaviour and caching

Every download is associated with its remote URI. If you request the same file
again the dialog reuses the cached copy instead of issuing another network
request. This makes it safe to build collections during limited connectivity:
the cache stores the raw download alongside canonical units so future sessions
can ingest the files instantly. NIST line lists now embed the full query
parameters (element, ion stage, wavelength bounds, Ritz preference) in their
pseudo URI, so distinct searches produce unique cache entries instead of
colliding on a shared label.

If persistent caching is disabled in **File → Enable Persistent Cache**, remote
fetches are stored in a temporary data directory for the current session. The
dialog will still reuse results within that session, but the artefacts are
discarded once the preview shell closes.

See `docs/link_collection.md` for a curated index of spectroscopy catalogues,
laboratory references, and instrument handbooks you can target with the remote
workflow.
