@echo off
REM Launch Spectra App using Miniconda Python
setlocal
cd /d "%~dp0"
echo Starting Spectra App...
REM Ensure project is importable as a package
set PYTHONPATH=%CD%
REM Optional: uncomment for verbose Qt plugin diagnostics
REM set QT_DEBUG_PLUGINS=1
"C:\Users\brett\miniconda3\python.exe" -m app.main
echo.
echo (Exit code %ERRORLEVEL%)
pause
endlocal
