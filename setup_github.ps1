# GitHub Setup Script for Windows
# This script helps set up Git-GitHub integration

param(
    [Parameter(Mandatory=$false)]
    [string]$RepoUrl,
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipGitignore,
    
    [Parameter(Mandatory=$false)]
    [switch]$DryRun
)

Write-Host "=== GitHub Setup Script ===" -ForegroundColor Cyan
Write-Host ""

# Check if git is installed
try {
    $gitVersion = git --version
    Write-Host "✓ Git installed: $gitVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ Git is not installed. Please install Git first." -ForegroundColor Red
    Write-Host "  Download from: https://git-scm.com/download/win" -ForegroundColor Yellow
    exit 1
}

# Check current git status
Write-Host ""
Write-Host "Current Git Status:" -ForegroundColor Cyan
git status --short

# Check if remote exists
$remoteExists = git remote get-url origin 2>$null
if ($remoteExists) {
    Write-Host ""
    Write-Host "✓ Remote 'origin' already configured:" -ForegroundColor Green
    Write-Host "  $remoteExists" -ForegroundColor White
    
    $response = Read-Host "Do you want to update it? (y/N)"
    if ($response -eq 'y' -or $response -eq 'Y') {
        if (-not $DryRun) {
            git remote remove origin
            Write-Host "✓ Removed existing remote" -ForegroundColor Green
        }
    } else {
        Write-Host "Keeping existing remote configuration" -ForegroundColor Yellow
        exit 0
    }
}

# Get repository URL if not provided
if (-not $RepoUrl) {
    Write-Host ""
    Write-Host "Please create a GitHub repository first:" -ForegroundColor Yellow
    Write-Host "  1. Go to https://github.com/new" -ForegroundColor White
    Write-Host "  2. Create repository (DO NOT initialize with README)" -ForegroundColor White
    Write-Host "  3. Copy the repository URL" -ForegroundColor White
    Write-Host ""
    $RepoUrl = Read-Host "Enter your GitHub repository URL (e.g., https://github.com/username/repo.git)"
}

if (-not $RepoUrl) {
    Write-Host "✗ Repository URL is required" -ForegroundColor Red
    exit 1
}

# Validate URL format
if ($RepoUrl -notmatch '^https://github\.com/[\w-]+/[\w-]+\.git$' -and 
    $RepoUrl -notmatch '^git@github\.com:[\w-]+/[\w-]+\.git$') {
    Write-Host "⚠ Warning: URL format may be incorrect" -ForegroundColor Yellow
    Write-Host "  Expected: https://github.com/username/repo.git" -ForegroundColor White
    Write-Host "  Got: $RepoUrl" -ForegroundColor White
    $continue = Read-Host "Continue anyway? (y/N)"
    if ($continue -ne 'y' -and $continue -ne 'Y') {
        exit 1
    }
}

# Add remote
Write-Host ""
Write-Host "Adding remote 'origin'..." -ForegroundColor Cyan
if (-not $DryRun) {
    try {
        git remote add origin $RepoUrl
        Write-Host "✓ Remote added successfully" -ForegroundColor Green
    } catch {
        Write-Host "✗ Failed to add remote: $_" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "[DRY RUN] Would execute: git remote add origin $RepoUrl" -ForegroundColor Yellow
}

# Verify remote
Write-Host ""
Write-Host "Verifying remote configuration:" -ForegroundColor Cyan
git remote -v

# Create/update .gitignore
if (-not $SkipGitignore) {
    Write-Host ""
    Write-Host "Checking .gitignore..." -ForegroundColor Cyan
    if (Test-Path ".gitignore") {
        Write-Host "✓ .gitignore already exists" -ForegroundColor Green
    } else {
        Write-Host "⚠ .gitignore not found" -ForegroundColor Yellow
        Write-Host "  Please create .gitignore before committing" -ForegroundColor White
    }
}

# Show next steps
Write-Host ""
Write-Host "=== Next Steps ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Review and stage your changes:" -ForegroundColor White
Write-Host "   git status" -ForegroundColor Gray
Write-Host "   git add DMAIC_V3/ deployment/ .gitignore" -ForegroundColor Gray
Write-Host ""
Write-Host "2. Commit your changes:" -ForegroundColor White
Write-Host "   git commit -m 'feat: Add DOW integration and deployment'" -ForegroundColor Gray
Write-Host ""
Write-Host "3. Push to GitHub:" -ForegroundColor White
Write-Host "   git push -u origin feature/dow-integration" -ForegroundColor Gray
Write-Host ""
Write-Host "4. Create Pull Request on GitHub:" -ForegroundColor White
Write-Host "   Visit: $($RepoUrl -replace '\.git$', '')/pulls" -ForegroundColor Gray
Write-Host ""

# Optional: Check if gh CLI is installed
$ghInstalled = Get-Command gh -ErrorAction SilentlyContinue
if ($ghInstalled) {
    Write-Host "✓ GitHub CLI (gh) is installed" -ForegroundColor Green
    Write-Host "  You can use: gh pr create" -ForegroundColor White
} else {
    Write-Host "ℹ GitHub CLI (gh) not installed" -ForegroundColor Blue
    Write-Host "  Install for easier PR management: winget install GitHub.cli" -ForegroundColor White
}

Write-Host ""
Write-Host "Setup complete! 🚀" -ForegroundColor Green
