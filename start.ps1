#!/usr/bin/env pwsh
# ============================================================================
# AsysAuti Quick Start for Windows PowerShell
# ============================================================================
# Usage: .\start.ps1

param(
    [int]$BackendPort = 5001,
    [int]$FrontendPort = 5173,
    [string]$Host = "127.0.0.1",
    [string]$VenvDir = "asysauti"
)

$ErrorActionPreference = "Stop"

# Colors
function Write-Info {
    Write-Host "ℹ️  $args" -ForegroundColor Cyan
}

function Write-Success {
    Write-Host "✅ $args" -ForegroundColor Green
}

function Write-Warning {
    Write-Host "⚠️  $args" -ForegroundColor Yellow
}

# ============================================================================
# MAIN
# ============================================================================

Clear-Host
Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║           🚀 AsysAuti - Full Stack Developer Mode         ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Create virtual environment if needed
if (-not (Test-Path $VenvDir)) {
    Write-Info "Creating virtual environment at $VenvDir..."
    & python -m venv $VenvDir
    Write-Success "Virtual environment created"
}

# Activate virtual environment
Write-Info "Activating virtual environment..."
$venvScript = Join-Path $VenvDir "Scripts\Activate.ps1"
& $venvScript
Write-Success "Virtual environment activated"

# Install backend dependencies
Write-Info "Installing backend dependencies..."
& pip install -q -r requirements.txt 2>$null
if ($LASTEXITCODE -ne 0) {
    & pip install -r requirements.txt
}
Write-Success "Backend dependencies ready"

# Install frontend dependencies
Write-Info "Installing frontend dependencies..."
Push-Location frontend
& npm install --quiet 2>$null
if ($LASTEXITCODE -ne 0) {
    & npm install
}
Pop-Location
Write-Success "Frontend dependencies ready"

Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║                   Starting Services                        ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Start backend
Write-Info "Starting Backend (port $BackendPort)..."
$backendCode = @"
from backend.web.app_factory import create_app
import logging
app = create_app()
print('Backend running at http://${Host}:${BackendPort}')
app.run(host='$Host', port=$BackendPort, debug=True)
"@

$backendJob = Start-Job -ScriptBlock {
    param($backendCode)
    python -c $using:backendCode
} -ArgumentList $backendCode

Write-Success "Backend started"

# Wait for backend
Start-Sleep -Seconds 2

# Start frontend
Write-Info "Starting Frontend (port $FrontendPort)..."
$frontendJob = Start-Job -ScriptBlock {
    cd frontend
    npm run dev
} -WorkingDirectory (Get-Location).Path

Write-Success "Frontend started"

Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║                    ✅ BOTH SERVICES READY                 ║" -ForegroundColor Green
Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""
Write-Host "📍 Backend:  http://${Host}:${BackendPort}" -ForegroundColor Cyan
Write-Host "🎨 Frontend: http://${Host}:${FrontendPort}" -ForegroundColor Cyan
Write-Host ""
Write-Host "⏸️  Press Ctrl+C to stop services" -ForegroundColor Yellow
Write-Host ""

# Wait for services
try {
    Wait-Job -Job $backendJob, $frontendJob
}
catch {
    Write-Warning "Services stopped"
}
finally {
    Stop-Job -Job $backendJob, $frontendJob -ErrorAction SilentlyContinue
    Remove-Job -Job $backendJob, $frontendJob -ErrorAction SilentlyContinue
}
