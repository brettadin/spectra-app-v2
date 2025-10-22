@echo off
setlocal

REM ---- Project root (adjust if moved) ----
set PROJ_ROOT=%~dp0

REM ---- Use existing venv if present, else create ----
if exist "%PROJ_ROOT%\.venv\Scripts\python.exe" (
  echo Using existing virtual environment at "%PROJ_ROOT%\.venv".
) else (
  echo Creating virtual environment...
  py -3 -m venv "%PROJ_ROOT%\.venv" || (
    echo Failed to create virtual environment.
    exit /b 1
  )
)

set PY_EXE=%PROJ_ROOT%\.venv\Scripts\python.exe
echo Using interpreter "%PY_EXE%".

REM ---- Upgrade pip (optional) ----
"%PY_EXE%" -m pip install --upgrade pip

REM ---- Install numpy first (prefer prebuilt wheel) ----
echo Installing numpy (prefer binary wheel)...
"%PY_EXE%" -m pip install --prefer-binary "numpy>=1.26,<3" || (
  echo Warning: installing numpy wheel failed; will attempt full requirements install next.
)

REM ---- Install deps from requirements.txt ----
echo Installing dependencies from requirements.txt...
set "PIP_NO_BINARY="
set "PIP_ONLY_BINARY=numpy"
set "PIP_PREFER_BINARY=1"
"%PY_EXE%" -m pip install --prefer-binary -r "%PROJ_ROOT%\requirements.txt" || (
  echo Dependency install failed.
  echo If numpy attempts to build from source, install the latest Microsoft C++ Build Tools ^
   or run: "%PY_EXE%" -m pip install --prefer-binary "numpy>=1.26,<3".
  pause
  exit /b 1
)

REM ---- (Optional) force Qt offscreen for headless runs (uncomment if needed) ----
REM set QT_QPA_PLATFORM=offscreen

REM ---- Launch app ----
echo Launching Spectra application...
"%PY_EXE%" -m app.main
set EXITCODE=%ERRORLEVEL%

echo(
echo Spectra exited with error code %EXITCODE%.
pause
exit /b %EXITCODE%
