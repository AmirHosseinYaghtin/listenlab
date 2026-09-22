# Runs the backend test suite, then frontend lint + build.
# Usage:  .\scripts\test.ps1

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

$venvPython = Join-Path $root ".venv\Scripts\python.exe"
$python = if (Test-Path $venvPython) { $venvPython } else { "python" }

$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONPATH = Join-Path $root "backend"

Write-Host "=== Backend tests (pytest) ===" -ForegroundColor Cyan
Push-Location (Join-Path $root "backend")
& $python -m pytest
$pytestExit = $LASTEXITCODE
Pop-Location

Write-Host "`n=== Frontend lint ===" -ForegroundColor Cyan
Push-Location (Join-Path $root "frontend")
npm run lint
$lintExit = $LASTEXITCODE

Write-Host "`n=== Frontend typecheck + build ===" -ForegroundColor Cyan
npm run build
$buildExit = $LASTEXITCODE
Pop-Location

if ($pytestExit -or $lintExit -or $buildExit) {
    Write-Host "`nFAILED (pytest=$pytestExit lint=$lintExit build=$buildExit)" -ForegroundColor Red
    exit 1
}
Write-Host "`nAll checks passed." -ForegroundColor Green
