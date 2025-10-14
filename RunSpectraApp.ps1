[CmdletBinding()]
param(
    [switch]$Reinstall
)

$ErrorActionPreference = 'Stop'

function New-PythonInvoker {
    param(
        [string[]]$PreferredVersions = @('3.12', '3.13', '3.11', '3.10')
    )

    $pyLauncher = Get-Command py -ErrorAction SilentlyContinue
    if ($pyLauncher) {
        foreach ($version in $PreferredVersions) {
            try {
                & $pyLauncher.Path "-$version" '-c' 'import sys' 2>$null | Out-Null
                if ($LASTEXITCODE -eq 0) {
                    return [PSCustomObject]@{
                        Executable    = $pyLauncher.Path
                        PrefixArgs    = @("-$version")
                        DisplayVersion = $version
                    }
                }
            } catch {
                continue
            }
        }
    }

    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCmd) {
        $versionText = (& $pythonCmd.Path '-c' "import sys; print('.'.join(map(str, sys.version_info[:3])))" 2>$null).Trim()
        if ($LASTEXITCODE -ne 0 -or -not $versionText) {
            throw 'Unable to determine Python version. Ensure Python 3.12 is installed.'
        }

        try {
            $parsed = [Version]$versionText
        } catch {
            throw "Unrecognised Python version string: $versionText"
        }

        if ($parsed.Major -ne 3 -or $parsed.Minor -lt 10 -or $parsed.Minor -gt 13) {
            throw "Found Python $versionText, but Spectra currently supports Python 3.10-3.13. Install a supported version and rerun."
        }

        return [PSCustomObject]@{
            Executable    = $pythonCmd.Path
            PrefixArgs    = @()
            DisplayVersion = "{0}.{1}" -f $parsed.Major, $parsed.Minor
        }
    }

    throw "Python 3.12 was not found. Install it from https://www.python.org/downloads/release/python-3120/ and rerun this script."
}

function Invoke-WithPython {
    param(
        [PSCustomObject]$Invoker,
        [string[]]$Args
    )

    & $Invoker.Executable @($Invoker.PrefixArgs + $Args)
}

$scriptPath = $MyInvocation.MyCommand.Path
if (-not $scriptPath) {
    throw 'Unable to determine script path.'
}
$repoRoot = Split-Path -Parent $scriptPath
Set-Location $repoRoot

Write-Host "==> Spectra App quick launcher" -ForegroundColor Cyan

$pythonInvoker = New-PythonInvoker
Write-Host "Using Python $($pythonInvoker.DisplayVersion) at $($pythonInvoker.Executable)" -ForegroundColor Green

$venvPath = Join-Path $repoRoot '.venv'
$pythonExe = Join-Path (Join-Path $venvPath 'Scripts') 'python.exe'

if ($Reinstall -and (Test-Path $venvPath)) {
    Write-Host "Removing existing virtual environment (.venv) because -Reinstall was specified..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force $venvPath
}

if (-not (Test-Path $pythonExe)) {
    Write-Host "Creating virtual environment (.venv)..." -ForegroundColor Cyan
    Invoke-WithPython -Invoker $pythonInvoker -Args @('-m', 'venv', $venvPath)
}

Write-Host "Upgrading pip..." -ForegroundColor Cyan
& $pythonExe -m pip install --upgrade pip | Out-String | Write-Verbose

Write-Host "Installing dependencies from requirements.txt..." -ForegroundColor Cyan
& $pythonExe -m pip install -r (Join-Path $repoRoot 'requirements.txt')

Write-Host "Launching Spectra app..." -ForegroundColor Cyan
& $pythonExe -m app.main
