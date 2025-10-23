# Atlas: Remote Data Flow

High-level map of how remote catalogues integrate into Spectra.

Nodes
- UI (Remote Data dialog)
- RemoteDataService
- Importers (CSV/FITS/JCAMP)
- UnitsService
- LocalStore
- Plot/OverlayService

Flow (text diagram)

UI::Search --> RemoteDataService::search(provider, query)
    --> records[]
UI::Filter/Preview(records)
UI::Download(selected) --> RemoteDataService::download(record)
    --> (MAST) astroquery.mast download to temp-dir
        [if empty] --> direct HTTP fallback (MAST Download API)
    --> LocalStore.record(source)
    --> DataIngestService.ingest(path)
        --> Importer.read(path) -> arrays + units
        --> UnitsService.to_canonical(...)
        --> Spectrum.create(...)
UI::Plot(OverlayService.add(spectrum))

Reliability
- Worker threads with QTimer-based cleanup
- Non-spectral file skip during bulk ingest
- Direct HTTP fallback when astroquery stalls

See also: ../brains/remote_data_pipeline.md
