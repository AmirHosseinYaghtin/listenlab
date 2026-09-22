# Starts the API (127.0.0.1:8000) and the Vite dev server (localhost:5173).
# Usage:  .\scripts\dev.ps1
# Stop with Ctrl+C (both processes exit).

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

# Prefer a local .venv, then whatever python is on PATH.
$pythonCandidates = @(
    (Join-Path $root ".venv\Scripts\python.exe"),
    "python"
)
$python = $null
foreach ($candidate in $pythonCandidates) {
    if ($candidate -eq "python") {
        $python = "python"
        break
    }
    if (Test-Path $candidate) {
        $python = $candidate
        break
    }
}
if (-not $python) { Write-Error "Python not found. Edit scripts\dev.ps1."; exit 1 }

Write-Host "Using Python: $python" -ForegroundColor Cyan

$env:PYTHONPATH = Join-Path $root "backend"
$env:PYTHONIOENCODING = "utf-8"

# Seed databases/podcasts if needed (idempotent).
& $python -m app.services.seed
if ($LASTEXITCODE -ne 0) { Write-Warning "Seed reported problems; continuing anyway." }

$uvicornArgs = @("-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000", "--reload")
$backend = Start-Process -FilePath $python -ArgumentList $uvicornArgs `
    -WorkingDirectory (Join-Path $root "backend") -PassThru -NoNewWindow

Push-Location (Join-Path $root "frontend")
try {
    Write-Host "`nAPI   → http://127.0.0.1:8000  (docs at /docs)" -ForegroundColor Green
    Write-Host "App   → http://localhost:5173`n" -ForegroundColor Green
    npm run dev
}
finally {
    Pop-Location
    if ($backend -and -not $backend.HasExited) {
        Stop-Process -Id $backend.Id -Force -ErrorAction SilentlyContinue
    }
}
