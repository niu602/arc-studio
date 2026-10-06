# =============================================================================
# ARC Studio - One-click environment setup script (Windows)
# Run in project root (arc-studio/):
#   powershell -ExecutionPolicy Bypass .\setup.ps1
#
# What it does:
#   1) Create venv for backend and install REST service dependencies
#   2) Create venv for built-in ARC compiler (compiler/) and install deps
# =============================================================================

$ErrorActionPreference = "Stop"

$root = $PSScriptRoot
$backend = Join-Path $root "backend"
$compiler = Join-Path $root "compiler"

function New-Venv([string]$path) {
    $venvPath = Join-Path $path ".venv"
    if (Test-Path $venvPath) {
        Write-Host "[skip] $venvPath already exists" -ForegroundColor Yellow
    } else {
        Write-Host "[venv] Creating $venvPath ..." -ForegroundColor Cyan
        python -m venv $venvPath
    }
    return (Join-Path $venvPath "Scripts\python.exe")
}

# ---- 1. backend ----
Write-Host ""
Write-Host "===== 1/2 Backend dependencies =====" -ForegroundColor Green
$pyBackend = New-Venv $backend
& $pyBackend -m pip install --upgrade pip --quiet
& $pyBackend -m pip install -r (Join-Path $backend "requirements.txt")

# ---- 2. compiler ----
Write-Host ""
Write-Host "===== 2/2 ARC compiler dependencies =====" -ForegroundColor Green
$pyCompiler = New-Venv $compiler
& $pyCompiler -m pip install --upgrade pip --quiet
if (Test-Path (Join-Path $compiler "pyproject.toml")) {
    & $pyCompiler -m pip install -e $compiler
} else {
    Write-Host "[warn] compiler/pyproject.toml not found, please check compiler/ directory" -ForegroundColor Red
}

Write-Host ""
Write-Host "===== Done =====" -ForegroundColor Green
Write-Host "Start backend:  cd backend ; .\.venv\Scripts\Activate.ps1 ; uvicorn app.main:app --reload --port 8000"
Write-Host "Start frontend: cd frontend ; npm install ; npm run dev"
