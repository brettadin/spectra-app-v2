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
   - **MAST** (MAST data products via `astroquery.mast`)
   - **MAST ExoSystems** (NExScI exoplanet metadata cross-matched with MAST missions and Exo.MAST curated spectra)
   
   > **Note**: NIST spectral line lookups now live in the Inspector’s **Reference → Spectral lines** tab, where you can pin
   > multiple element/ion queries and manage colour palettes directly within the preview plot.
3. Enter a keyword, element symbol, or target name in the search field (or pick
   one of the curated **Examples…** entries) and click **Search**. The dialog
   blocks empty submissions so you always send provider-specific filters rather
   than unbounded catalogue sweeps. While the remote service responds the main
   controls are temporarily disabled, a spinner appears beside the status
   banner, and rows stream into the table as soon as each record is processed.
   The examples highlight solar-system benchmarks (e.g. Jupiter),
   representative stellar standards (HD 189733), and exoplanet hosts such as
   TRAPPIST‑1 that are pre-indexed by the Exo.MAST catalogue.

### Streaming search results

Remote catalogue lookups now run on a worker thread, so the dialog stays
responsive even when the provider takes a few seconds to answer. The spinner in
the status area starts as soon as the query is dispatched, the record counter
increments while results arrive, and the preview pane updates dynamically if the
first result changes mid-stream. Pressing **Cancel** (or closing the dialog)
signals the worker to stop and clears any partial rows; errors surface in the
status banner instead of blocking the interface with modal message boxes.

### Provider-specific search tips

- **MAST / Exo.MAST** – Free-text input is rewritten to `target_name` before
  invoking `astroquery.mast.Observations.query_criteria`, and the adapter injects
  `dataproduct_type="spectrum"`, `intentType="SCIENCE"`, and
  `calib_level=[2, 3]` filters automatically. When available, Exo.MAST augments
  each record with NASA Exoplanet Archive host/planet parameters so the dialog
  can summarise orbital periods, discovery methods, and stellar temperatures.
  Supply JWST target names, instrument identifiers, or planet hosts (e.g.
  `Jupiter`, `TRAPPIST-1`, `WASP-96 b`). Tick **Include imaging** to relax the
  product filter so calibrated imaging results appear alongside spectra.

The hint banner beneath the results table updates as you switch providers and
also surfaces dependency warnings when optional clients are missing.

### Reading the expanded results table

The table now surfaces richer provenance for each match:

* **ID / Title** – Stable identifiers and mission-provided labels.
* **Target / Host** – Planet names, host stars, or solar-system bodies derived
  from Exo.MAST metadata.
* **Telescope / Mission** – Observatory names, programmes, and proposal IDs.
* **Instrument / Mode** – Instrument configuration and observing mode.
* **Product Type** – Spectroscopic vs. imaging products plus calibration level.
* **Download** – Clickable hyperlinks (MAST URIs are rewritten to
  `https://mast.stsci.edu/portal/Download/...` so they open in a browser).
* **Preview / Citation** – Thumbnail links and mission citations when provided
  by MAST or the Exoplanet Archive.

Selecting a row displays a narrative summary in the preview pane (planet/host,
mission, instrument, and citation) followed by the full JSON payload. The status
bar beneath the table also echoes the host/planet summary so you can scan for
relevant targets without opening the preview pane.

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

Imported spectra appear in the dataset tree immediately. They behave exactly
like manual imports: overlays update, the data table refreshes, and the history
dock records a "Remote Import" entry noting the provider. File-level metadata
now lives in the Library tab inside the Data dock so the consolidated knowledge
log stays focused on high-level insights.

### Exo.MAST and NASA Exoplanet Archive workflow

MAST queries for exoplanet systems automatically request Exo.MAST augmentations
so the dialog includes discovery metadata and host-star parameters alongside the
instrument context. Typical flow:

1. Enter an exoplanet or host star (e.g. `WASP-96 b`, `TRAPPIST-1`,
   `HD 189733`).
2. Exo.MAST enriches the response with orbital period, stellar temperature,
   discovery method, and citation strings from the NASA Exoplanet Archive.
3. The results table displays those fields in the **Target / Host** and
   **Preview / Citation** columns, while the status banner summarises the host
   system (e.g. `WASP-96 b around WASP-96 • Discovery: Transit • Period: 3.42 d`).
4. Download and ingest the calibrated JWST/HST spectrum as usual.

Use the narrative preview to capture citation details for reports or to confirm
the observing programme before importing data into Spectra.

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
