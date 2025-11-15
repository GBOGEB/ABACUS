# DMAIC V3.0 - PowerShell Setup Script
# Auto-venv activation and dependency management for Windows
# Version: 3.0.0

param(
    [string]$VenvName = ".venv",
    [switch]$Force,
    [switch]$SkipDependencies,
    [switch]$Validate
)

$ErrorActionPreference = "Stop"

# Colors for output
function Write-Success { Write-Host $args -ForegroundColor Green }
function Write-Info { Write-Host $args -ForegroundColor Cyan }
function Write-Warning { Write-Host $args -ForegroundColor Yellow }
function Write-Error { Write-Host $args -ForegroundColor Red }

Write-Host "=" * 80
Write-Host "DMAIC V3.0 - Environment Setup (PowerShell)"
Write-Host "=" * 80
Write-Host ""

# Check Python installation
Write-Info "[1/7] Checking Python installation..."
try {
    $pythonVersion = python --version 2>&1
    Write-Success "  ✓ $pythonVersion"
} catch {
    Write-Error "  ✗ Python not found. Please install Python 3.8 or higher."
    exit 1
}

# Check Python version
$versionMatch = $pythonVersion -match "Python (\d+)\.(\d+)\.(\d+)"
if ($versionMatch) {
    $major = [int]$Matches[1]
    $minor = [int]$Matches[2]
    
    if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 8)) {
        Write-Error "  ✗ Python 3.8 or higher required. Found: $pythonVersion"
        exit 1
    }
    Write-Success "  ✓ Python version meets requirements (>= 3.8)"
} else {
    Write-Warning "  ⚠ Could not parse Python version"
}

# Check if virtual environment exists
Write-Info "[2/7] Checking virtual environment..."
$venvPath = Join-Path $PSScriptRoot $VenvName

if (Test-Path $venvPath) {
    if ($Force) {
        Write-Warning "  ⚠ Removing existing virtual environment..."
        Remove-Item -Recurse -Force $venvPath
        Write-Success "  ✓ Removed existing virtual environment"
    } else {
        Write-Success "  ✓ Virtual environment exists: $venvPath"
    }
}

# Create virtual environment if needed
if (-not (Test-Path $venvPath)) {
    Write-Info "  Creating virtual environment: $venvPath"
    python -m venv $venvPath
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "  ✓ Virtual environment created"
    } else {
        Write-Error "  ✗ Failed to create virtual environment"
        exit 1
    }
}

# Activate virtual environment
Write-Info "[3/7] Activating virtual environment..."
$activateScript = Join-Path $venvPath "Scripts\Activate.ps1"

if (Test-Path $activateScript) {
    & $activateScript
    Write-Success "  ✓ Virtual environment activated"
} else {
    Write-Error "  ✗ Activation script not found: $activateScript"
    exit 1
}

# Upgrade pip
Write-Info "[4/7] Upgrading pip..."
python -m pip install --upgrade pip --quiet
if ($LASTEXITCODE -eq 0) {
    Write-Success "  ✓ pip upgraded"
} else {
    Write-Warning "  ⚠ Could not upgrade pip"
}

# Install/upgrade setuptools and wheel
Write-Info "[5/7] Installing build tools..."
python -m pip install --upgrade setuptools wheel --quiet
if ($LASTEXITCODE -eq 0) {
    Write-Success "  ✓ Build tools installed"
} else {
    Write-Warning "  ⚠ Could not install build tools"
}

# Install dependencies
if (-not $SkipDependencies) {
    Write-Info "[6/7] Installing dependencies..."
    
    # Check for requirements.txt
    $requirementsFiles = @(
        "DMAIC_V3\requirements.txt",
        "requirements.txt"
    )
    
    $requirementsFile = $null
    foreach ($file in $requirementsFiles) {
        $fullPath = Join-Path $PSScriptRoot $file
        if (Test-Path $fullPath) {
            $requirementsFile = $fullPath
            break
        }
    }
    
    if ($requirementsFile) {
        Write-Info "  Installing from: $requirementsFile"
        python -m pip install -r $requirementsFile
        
        if ($LASTEXITCODE -eq 0) {
            Write-Success "  ✓ Dependencies installed"
        } else {
            Write-Error "  ✗ Failed to install dependencies"
            exit 1
        }
    } else {
        Write-Warning "  ⚠ No requirements.txt found"
    }
} else {
    Write-Info "[6/7] Skipping dependency installation (--SkipDependencies)"
}

# Validate installation
Write-Info "[7/7] Validating installation..."

$validationPassed = $true

# Check core packages
$corePackages = @("pip", "setuptools", "wheel")
foreach ($package in $corePackages) {
    $result = python -m pip show $package 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Success "  ✓ $package installed"
    } else {
        Write-Warning "  ⚠ $package not found"
        $validationPassed = $false
    }
}

# Summary
Write-Host ""
Write-Host "=" * 80
Write-Host "SETUP SUMMARY"
Write-Host "=" * 80

if ($validationPassed) {
    Write-Success "✅ Environment setup completed successfully!"
    Write-Host ""
    Write-Info "Virtual environment: $venvPath"
    Write-Info "Python: $(python --version)"
    Write-Info "Pip: $(python -m pip --version)"
    Write-Host ""
    Write-Info "To activate the environment in a new session:"
    Write-Host "  $venvPath\Scripts\Activate.ps1" -ForegroundColor White
    Write-Host ""
    Write-Info "To deactivate:"
    Write-Host "  deactivate" -ForegroundColor White
} else {
    Write-Warning "⚠️  Setup completed with warnings"
}

Write-Host "=" * 80
Write-Host ""

# Run validation if requested
if ($Validate) {
    Write-Info "Running Phase 0 validation..."
    Write-Host ""
    
    $phase0Script = Join-Path $PSScriptRoot "DMAIC_V3\phases\phase0_setup.py"
    if (Test-Path $phase0Script) {
        python $phase0Script
    } else {
        Write-Warning "Phase 0 script not found: $phase0Script"
    }
}

# Create activation helper script
$helperScript = @"
# DMAIC V3.0 - Quick Activation Helper
# Run this script to activate the virtual environment

`$venvPath = Join-Path `$PSScriptRoot "$VenvName"
`$activateScript = Join-Path `$venvPath "Scripts\Activate.ps1"

if (Test-Path `$activateScript) {
    & `$activateScript
    Write-Host "✓ DMAIC V3.0 environment activated" -ForegroundColor Green
} else {
    Write-Host "✗ Virtual environment not found. Run setup_environment.ps1 first." -ForegroundColor Red
}
"@

$helperPath = Join-Path $PSScriptRoot "activate_dmaic.ps1"
$helperScript | Out-File -FilePath $helperPath -Encoding UTF8
Write-Info "Created activation helper: activate_dmaic.ps1"

Write-Success "Setup complete! 🚀"
