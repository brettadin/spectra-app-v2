# Windows Build Instructions

These steps package the Spectra desktop shell into a distributable Windows build using PyInstaller, following the packaging strategy described in `specs/packaging.md`.

1. **Optional quick launch:** To verify the app before packaging, run
   `RunSpectraApp.cmd`. It will locate a supported Python interpreter (preferring
   `py -3.12`), provision `.venv`, install dependencies, and start the UI. Close
   the app when satisfied, then continue.

2. **Create a virtual environment** (recommended):
   ```powershell
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   ```
3. **Install dependencies** (use `python -m pip` to ensure the active
   interpreter installs the packages):
   ```powershell
   python -m pip install -r requirements.txt
   python -m pip install pyinstaller
   ```
4. **Run the PyInstaller build** using the provided spec file:
   ```powershell
   pyinstaller --clean --noconfirm packaging\spectra_app.spec
   ```
   The packaged app is written to `dist\SpectraApp`.  The folder contains `SpectraApp.exe`, Qt runtime DLLs, and bundled assets (sample spectra and documentation for provenance history).
5. **Test the build** by launching the executable:
   ```powershell
   dist\SpectraApp\SpectraApp.exe
   ```
   The app should open with the sample spectra already loaded.  Verify file import, overlay refresh, math operations, and manifest export.
6. **Create a portable zip** (optional):
   ```powershell
   Compress-Archive -Path dist\SpectraApp\* -DestinationPath dist\SpectraApp_portable.zip
   ```

For MSIX or MSI packaging, follow the workflow in `specs/packaging.md` after verifying the PyInstaller output.
