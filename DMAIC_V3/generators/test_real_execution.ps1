# DMAIC V3 Generators - Test Script (PowerShell)
# Version: 3.1.0
# Last Updated: 2025-11-10

$ErrorActionPreference = "Stop"

Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "DMAIC V3 GENERATORS - REAL EXECUTION TEST (POWERSHELL)" -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "Version: 3.1.0"
Write-Host "DMAIC Version: V3"
Write-Host "Integration Mode: BIDIRECTIONAL"
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Check Python version
Write-Host "Step 1: Checking Python version..." -ForegroundColor Yellow
python --version
Write-Host ""

# Step 2: Create virtual environment
Write-Host "Step 2: Creating virtual environment..." -ForegroundColor Yellow
if (Test-Path "venv_dmaic_v3") {
    Write-Host "  Virtual environment already exists. Removing..." -ForegroundColor Gray
    Remove-Item -Recurse -Force venv_dmaic_v3
}
python -m venv venv_dmaic_v3
Write-Host "  ✓ Virtual environment created" -ForegroundColor Green
Write-Host ""

# Step 3: Activate virtual environment
Write-Host "Step 3: Activating virtual environment..." -ForegroundColor Yellow
& "venv_dmaic_v3\Scripts\Activate.ps1"
Write-Host "  ✓ Virtual environment activated" -ForegroundColor Green
Write-Host ""

# Step 4: Install requirements
Write-Host "Step 4: Installing requirements..." -ForegroundColor Yellow
python -m pip install --upgrade pip
python -m pip install -r DMAIC_V3/generators/requirements.txt
Write-Host "  ✓ Requirements installed" -ForegroundColor Green
Write-Host ""

# Step 5: Run execution tracker
Write-Host "Step 5: Running execution tracker..." -ForegroundColor Yellow
python -m DMAIC_V3.generators execute --root master_document_system --timeout 30
Write-Host ""

# Step 6: Run documentation aligner
Write-Host "Step 6: Running documentation aligner..." -ForegroundColor Yellow
python -m DMAIC_V3.generators align-docs --docs-dir master_document_system
Write-Host ""

# Step 7: Check victory conditions
Write-Host "Step 7: Checking victory conditions..." -ForegroundColor Yellow
python -m DMAIC_V3.generators version
Write-Host ""

# Step 8: Deactivate virtual environment
Write-Host "Step 8: Deactivating virtual environment..." -ForegroundColor Yellow
deactivate
Write-Host "  ✓ Virtual environment deactivated" -ForegroundColor Green
Write-Host ""

Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "TEST COMPLETE" -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "Check output/execution_reports/ for detailed results"
Write-Host "================================================================================" -ForegroundColor Cyan
