@echo off
setlocal

rem Resolve repository root relative to this script
set "SCRIPT_DIR=%~dp0"
if "%SCRIPT_DIR%"=="" set "SCRIPT_DIR=.\"
cd /d "%SCRIPT_DIR%"

set "VENV_DIR=%SCRIPT_DIR%.venv"
set "PYTHON_EXE=%VENV_DIR%\Scripts\python.exe"

if exist "%PYTHON_EXE%" (
    echo Using existing virtual environment at "%VENV_DIR%".
) else (
    echo Creating virtual environment at "%VENV_DIR%"...
    set "PY_LAUNCHER="
    if exist "%SystemRoot%\py.exe" set "PY_LAUNCHER=%SystemRoot%\py.exe"
    if not defined PY_LAUNCHER (
        where py >nul 2>nul && set "PY_LAUNCHER=py"
    )
    if not defined PY_LAUNCHER (
        where python >nul 2>nul && set "PY_LAUNCHER=python"
    )
    if not defined PY_LAUNCHER (
        echo Could not locate a Python interpreter or py launcher on PATH.
        goto :fail
    )
    "%PY_LAUNCHER%" -3 -m venv "%VENV_DIR%"
    if errorlevel 1 goto :fail
)

echo Using interpreter "%PYTHON_EXE%".
"%PYTHON_EXE%" -m pip install --upgrade pip
if errorlevel 1 goto :fail

if exist "%SCRIPT_DIR%requirements.txt" (
    echo Installing dependencies from requirements.txt...
    "%PYTHON_EXE%" -m pip install -r "%SCRIPT_DIR%requirements.txt"
    if errorlevel 1 goto :fail
) else (
    echo requirements.txt not found; skipping dependency installation.
)

echo Launching Spectra application...
"%PYTHON_EXE%" -m app.main
set "APP_EXIT=%ERRORLEVEL%"

if "%APP_EXIT%"=="0" (
    echo.
    echo Spectra closed successfully.
) else (
    echo.
    echo Spectra exited with error code %APP_EXIT%.
)

pause
exit /b %APP_EXIT%

:fail
echo.
echo Bootstrap failed with error level %ERRORLEVEL%.
pause
exit /b %ERRORLEVEL%
