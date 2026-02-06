@echo off
REM Development helper script for Windows

if "%1"=="" goto help
if "%1"=="help" goto help
if "%1"=="install" goto install
if "%1"=="install-dev" goto install-dev
if "%1"=="test" goto test
if "%1"=="lint" goto lint
if "%1"=="format" goto format
if "%1"=="check" goto check
if "%1"=="clean" goto clean
if "%1"=="run" goto run
goto help

:help
echo Spectra App - Development Commands
echo ====================================
echo dev install       Install production dependencies
echo dev install-dev   Install dev dependencies (linters, formatters)
echo dev test          Run test suite
echo dev lint          Run linters (pylint, flake8, mypy)
echo dev format        Format code (black, isort)
echo dev check         Run format check without modifying files
echo dev clean         Remove cache and temporary files
echo dev run           Launch the application
goto :eof

:install
pip install -e .
goto :eof

:install-dev
pip install -e ".[dev]"
pre-commit install
goto :eof

:test
pytest tests/ -v
goto :eof

:lint
echo Running pylint...
pylint app/
echo.
echo Running flake8...
flake8 app/ tests/
echo.
echo Running mypy...
mypy app/
goto :eof

:format
echo Running black...
black app/ tests/
echo Running isort...
isort app/ tests/
goto :eof

:check
echo Checking format with black...
black --check app/ tests/
echo Checking imports with isort...
isort --check-only app/ tests/
goto :eof

:clean
echo Cleaning cache and temporary files...
for /d /r . %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d"
for /r . %%f in (*.pyc) do @if exist "%%f" del "%%f"
del /s /q tmpclaude-* 2>nul
goto :eof

:run
python -m app.main
goto :eof
