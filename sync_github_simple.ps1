# ABACUS v2.1 - Simple GitHub Sync Script
# Run this to push your deployment package to GitHub

Write-Host "╔══════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║        ABACUS v2.1 - GitHub Sync (Simplified)               ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Add deployment files
Write-Host "[1/3] Adding deployment files..." -ForegroundColor Yellow
git add ABACUS_V21_DEPLOYMENT_PACKAGE/
git add POWERSHELL_GITHUB_AZURE_GUIDE.md
git add DEPLOYMENT_READY_SUMMARY.md
git add QUICK_START.txt
git add sync_github_simple.ps1
git add github_azure_deployment_helper.py

# Commit
Write-Host "[2/3] Committing changes..." -ForegroundColor Yellow
git commit -m "Add ABACUS v2.1 deployment package - $(Get-Date -Format 'yyyy-MM-dd HH:mm')"

# Push
Write-Host "[3/3] Pushing to GitHub..." -ForegroundColor Yellow
git push origin main

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✅ SUCCESS! Deployment package pushed to GitHub!" -ForegroundColor Green
    Write-Host ""
    Write-Host "📊 View at: https://github.com/GBOGEB/ABACUS" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "🚀 Next: Deploy to Azure (see QUICK_START.txt)" -ForegroundColor Yellow
} else {
    Write-Host ""
    Write-Host "❌ Push failed. Check error above." -ForegroundColor Red
    Write-Host "   Try: git pull origin main --no-rebase" -ForegroundColor Yellow
    Write-Host "   Then run this script again" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Press any key to exit..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
