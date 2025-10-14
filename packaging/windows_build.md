# Windows Build Instructions

These notes describe the reproducible process for packaging the Spectra application on Windows using PyInstaller.  The process f
ollows the guidelines in `specs/packaging.md` and mirrors the configuration captured in `packaging/spectra_app.spec`.

## Prerequisites

1. Windows 10 or 11 workstation.
2. Python 3.12 (64-bit) installed and added to `PATH`.
3. Microsoft Visual C++ Redistributable (automatically installed with Python 3.12).
4. Git (optional, for cloning the repository).

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt pyinstaller
```

## Build Steps

1. Ensure the working directory is the repository root (`C:\Code\spectra-app-beta`).
2. Run PyInstaller using the provided spec file:

   ```powershell
   pyinstaller --clean --noconfirm packaging\spectra_app.spec
   ```

   The command produces a `dist\SpectraApp` folder containing `SpectraApp.exe`, Qt libraries and bundled samples.

3. (Optional) Create a portable ZIP package:

   ```powershell
   Compress-Archive -Path dist\SpectraApp -DestinationPath dist\SpectraApp-portable.zip
   ```

4. (Optional) Build an MSIX package using the Microsoft MSIX Packaging Tool.  Point the tool at the `dist\SpectraApp` folder and
   reuse the manifest template in `packaging\msix-template.xml` (to be completed in a later milestone).

5. Copy the generated folder or ZIP into `build\windows` for archival.

## Smoke Test

After building, run `SpectraApp.exe`.  Confirm that:

* The application launches without a console window.
* The **Data** tab loads `samples/sample_spectrum.csv` and displays the overlay chart.
* The **Compare** tab performs A − B and A / B calculations without freezing.
* The **Provenance** tab generates a manifest for the loaded spectrum.

## Notes

* Because this milestone was executed in a Linux-based CI container, the executable itself was not produced here.  The spec file
  and dependency locks (see `requirements.txt`) are ready for Windows execution.
* Code signing should be added once a certificate is available; run `signtool.exe sign /fd SHA256 /a SpectraApp.exe` after build.
