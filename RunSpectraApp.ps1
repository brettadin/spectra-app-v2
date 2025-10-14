[CmdletBinding()]
param(
    [switch]$Reinstall
)

$ErrorActionPreference = 'Stop'

$scriptPath = $MyInvocation.MyCommand.Path
if (-not $scriptPath) {
    throw 'Unable to determine script path.'
}
$repoRoot = Split-Path -Parent $scriptPath
Set-Location $repoRoot

Write-Host "==> Spectra App quick launcher" -ForegroundColor Cyan

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    throw "Python is required but was not found in PATH. Install Python 3.12 or later and re-run."
}

$venvPath = Join-Path $repoRoot '.venv'
$pythonExe = Join-Path (Join-Path $venvPath 'Scripts') 'python.exe'

if ($Reinstall -and (Test-Path $venvPath)) {
    Write-Host "Removing existing virtual environment (.venv) because -Reinstall was specified..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force $venvPath
}

if (-not (Test-Path $pythonExe)) {
    Write-Host "Creating virtual environment (.venv)..." -ForegroundColor Cyan
    & $python.Path -m venv $venvPath
}

Write-Host "Upgrading pip..." -ForegroundColor Cyan
& $pythonExe -m pip install --upgrade pip | Out-String | Write-Verbose

Write-Host "Installing dependencies from requirements.txt..." -ForegroundColor Cyan
& $pythonExe -m pip install -r (Join-Path $repoRoot 'requirements.txt')

Write-Host "Launching Spectra app..." -ForegroundColor Cyan
& $pythonExe -m app.main
