# Spectra App Quickstart

This walkthrough gets you from launch to a complete provenance export using only the files bundled with the Spectra App. It assumes you are running on Windows with Python 3.11+ available.

## 1. Launch the application

1. Open the repository folder in Explorer.
2. Double-click **RunSpectraApp.cmd**. The helper script builds/updates the virtual environment if needed and starts the desktop UI.
3. Wait for the main window to appear. The plot pane will be empty until you ingest data.

> **Troubleshooting**
> - If the script cannot find Python 3.11+, install it from [python.org](https://www.python.org/downloads/).
> - To force a clean environment rebuild, run `RunSpectraApp.cmd -Reinstall` from PowerShell.

## 2. Load the bundled sample spectrum

1. Choose **File → Open…**.
2. Navigate to the repository's `samples` directory.
3. Select `sample_spectrum.csv` and click **Open**.
4. Confirm the detected units in the preview banner. The importer normalises the axis to nanometres while keeping the source file untouched in the cache directory.

Once the ingest completes, the spectrum appears in the plot pane and in the spectra list on the left-hand sidebar.

## 3. Explore unit toggles

1. Locate the **Units** toolbar dropdown above the plot.
2. Switch the wavelength axis to Ångström, micrometre, or wavenumber (cm⁻¹).
3. Observe that the plot updates instantly without mutating the stored data. You can toggle back to nanometres at any time—unit conversions are idempotent and guaranteed by automated regression tests (`tests/test_units_roundtrip.py`).

## 4. Inspect metadata and provenance

1. Select the ingested spectrum in the spectra list.
2. Open the **Inspector** panel (View → Inspector) if it is not already visible.
3. Review the **Metadata** and **Provenance** tabs for acquisition details, detected units, and file locations.

## 5. Export a provenance bundle

1. Choose **File → Export → Manifest Bundle…**.
2. Pick an empty directory (for example, `Desktop\spectra-export-test`).
3. After export completes, inspect the folder. It contains:
   - The canonicalised CSV representing the current plot view.
   - `manifest.json` with hashes, ingest timestamps, units, and source metadata.
   - `provenance/` with the untouched raw source file.

This mirrors the automated smoke workflow in `tests/test_smoke_workflow.py`. Run that test any time you need to verify the ingest → unit toggle → export pipeline.

## 6. Next steps

- Continue exploring the `samples/` directory for additional datasets.
- Review [docs/user/importing.md](importing.md) for deeper coverage of supported formats.
- Consult the [Units & Conversions Reference](units_reference.md) for detailed information on idempotent toggles and canonical storage.
- Track upcoming documentation deliverables in [docs/reviews/doc_inventory_2025-10-14.md](../reviews/doc_inventory_2025-10-14.md).
