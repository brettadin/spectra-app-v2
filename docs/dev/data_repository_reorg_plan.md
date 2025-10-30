# Data Repository Reorganisation Plan

## Current Layout Snapshot
- `downloads/`
  - `_incoming/` – staging area for in-progress remote downloads (e.g., `tmplat5jdey/jupiter__9407171405N_evt.fits`).
  - `files/` – mixed historical downloads without consistent naming.
  - `index.json` – remote catalogue cache.
- `samples/`
  - Root CSV manifests (`sample_manifest.json`, `sample_spectrum.csv`, `sample_transmittance.csv`).
  - Modality-based folders (`fits data/`, `IR data/`, `lamp data/`, `other file types/`, `SUN AND MOON/`).
- `exports/`
  - User-generated CSVs and manifests.
- `app/data/reference/`
  - Static reference JSON assets consumed by the UI.

Pain points:
- Object-specific assets are scattered across `downloads/` and `samples/` with inconsistent naming.
- Staging `_incoming/` directories remain opaque, making it hard to locate completed downloads once they are copied to the cache.
- No single manifest enumerates available curated data for the app to display.

## Target Structure
```
 data/
   solar_system/
     sun/
       imagery/
       spectra/
       metadata.json
     mercury/
       imagery/
       spectra/
       metadata.json
     ...
   stars/
     proxima-centauri/
       imagery/
       spectra/
       metadata.json
   exoplanets/
     trappist-1e/
       lightcurves/
       spectra/
       metadata.json
   samples/
     canonical/
     derived/
 staging/
   incoming/
   quarantine/
```

Key conventions:
- Lowercase, hyphenated directory names for celestial objects.
- Files named `<object>_<instrument>_<yyyymmdd>.<ext>` when acquisition dates exist; fallback to `<object>_<instrument>.<ext>`.
- `metadata.json` summarises provenance (source URL, licence, capture date, instrument) and cross-references brain neurons.
- `staging/` replaces `downloads/_incoming` to make the workflow explicit (incoming → quarantine → promotion).

## Migration Steps
1. **Inventory & Classification**
   - Enumerate existing downloads (`downloads/files`, `_incoming`) and samples to classify by object/instrument.
   - Produce a CSV mapping current path → target path + metadata fields.

2. **Scripted Move**
   - Implement a migration script (`tools/data_migration.py`) that reads the mapping CSV and moves/copies files into the new `data/` hierarchy.
   - Generate stub `metadata.json` files during migration, capturing known provenance fields and marking gaps for manual completion.

3. **Runtime Adjustments**
   - Update `RemoteDataService` to promote completed downloads from `staging/incoming` into the new object directories based on metadata (object name, provider).
   - Modify ingest workflows to read from the structured data repository when presenting curated datasets.
   - Provide a registry file (e.g., `data/index.json`) summarising available datasets for use by the UI and documentation.

4. **Documentation & Tests**
   - Update contributor docs (`README`, `docs/dev/path_notes.md`) with the new layout and naming rules.
   - Add tests to ensure the migration script produces valid metadata and that runtime promotion routes files correctly.

5. **Cleanup**
   - Remove or archive legacy directories (`downloads/files`, modality-based sample folders) once confidence is established.
   - Ensure Git LFS or alternate storage is configured if curated assets exceed repository size limits.

## Open Questions
- How to handle mixed-origin datasets (e.g., composite exports combining lunar and solar data)? Store under a `composite/` namespace or attach multiple object tags?
- Should exports remain separate or also live within the object hierarchy under a `derived/` folder?
- What metadata schema should be standard (Dublin Core subset vs. custom fields)? Alignment with `docs/specs/provenance_schema.md` needs confirmation.

Capture answers in the worklog and update this plan as implementation proceeds.
