@echo off
REM Launch Spectra App using conda env (spectra312)
setlocal
cd /d "%~dp0"
set PROJ_ROOT=%CD%
echo Starting Spectra App (conda env: spectra312)...
REM Ensure project is importable as a package
set PYTHONPATH=%PROJ_ROOT%
REM Optional diagnostics: uncomment for verbose Qt plugin loading
REM set QT_DEBUG_PLUGINS=1

set PY_EXE=C:\Users\brett\miniconda3\envs\spectra312\python.exe
if not exist "%PY_EXE%" (
	echo Could not find interpreter at "%PY_EXE%".
	echo Please create the environment with:
	echo   conda env create -f %PROJ_ROOT%\environment.yml
	pause
	exit /b 1
)

"%PY_EXE%" -X faulthandler -m app.main
set EXITCODE=%ERRORLEVEL%
echo.
echo (Exit code %EXITCODE%)
pause
endlocal
