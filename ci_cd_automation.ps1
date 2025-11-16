# CI/CD Automation Script (PowerShell)
# Handles both Continuous Integration (CI) and Continuous Deployment (CD)
# Monitors tests, deployments, and tracks GitHub state

param(
    [Parameter(Mandatory=$false)]
    [int]$PR,
    
    [Parameter(Mandatory=$false)]
    [switch]$Watch,
    
    [Parameter(Mandatory=$false)]
    [switch]$CreateIssues,
    
    [Parameter(Mandatory=$false)]
    [switch]$MonitorCD,
    
    [Parameter(Mandatory=$false)]
    [string]$Environment = "all",
    
    [Parameter(Mandatory=$false)]
    [switch]$Analyze,
    
    [Parameter(Mandatory=$false)]
    [switch]$Track,
    
    [Parameter(Mandatory=$false)]
    [switch]$Report,
    
    [Parameter(Mandatory=$false)]
    [int]$Days = 30
)

# Colors for output
$ErrorColor = "Red"
$SuccessColor = "Green"
$InfoColor = "Cyan"
$WarningColor = "Yellow"

function Write-ColorOutput {
    param(
        [string]$Message,
        [string]$Color = "White"
    )
    Write-Host $Message -ForegroundColor $Color
}

function Test-GitHubAuth {
    Write-ColorOutput "🔐 Checking GitHub authentication..." $InfoColor
    
    try {
        $authStatus = gh auth status 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-ColorOutput "✅ GitHub CLI authenticated" $SuccessColor
            return $true
        }
    }
    catch {
        Write-ColorOutput "❌ GitHub CLI not authenticated" $ErrorColor
        Write-ColorOutput "Please run: gh auth login" $WarningColor
        return $false
    }
    
    return $false
}

function Get-RepositoryInfo {
    Write-ColorOutput "📦 Getting repository information..." $InfoColor
    
    try {
        $remoteUrl = git remote get-url origin 2>&1
        if ($remoteUrl -match "github\.com[:/](.+)/(.+?)(?:\.git)?$") {
            $owner = $matches[1]
            $repo = $matches[2]
            Write-ColorOutput "✅ Repository: $owner/$repo" $SuccessColor
            return @{
                Owner = $owner
                Repo = $repo
                FullName = "$owner/$repo"
            }
        }
    }
    catch {
        Write-ColorOutput "❌ Could not determine repository" $ErrorColor
        return $null
    }
    
    return $null
}

function Start-CIMonitoring {
    param(
        [int]$PRNumber,
        [bool]$WatchMode,
        [bool]$CreateIssuesFlag
    )
    
    Write-ColorOutput "`n🔍 Starting CI Monitoring for PR #$PRNumber..." $InfoColor
    
    $args = @("--pr", $PRNumber)
    
    if ($WatchMode) {
        $args += "--watch"
    }
    
    if ($CreateIssuesFlag) {
        $args += "--create-issues"
    }
    
    python ci_monitor_local.py @args
}

function Start-CDMonitoring {
    param(
        [string]$Env = "all"
    )
    
    Write-ColorOutput "`n📦 Starting CD Monitoring..." $InfoColor
    
    $args = @()
    
    if ($Env -ne "all") {
        $args += "--environment", $Env
    }
    
    $args += "--report"
    
    python cd_monitor.py @args
}

function Start-Tracking {
    param(
        [int]$PRNumber
    )
    
    Write-ColorOutput "`n📊 Starting GitHub Tracking for PR #$PRNumber..." $InfoColor
    
    # Sync PR data
    Write-ColorOutput "  Syncing PR data..." $InfoColor
    python github_tracking_manager.py --sync-pr $PRNumber
    
    # Sync CI runs
    Write-ColorOutput "  Syncing CI runs..." $InfoColor
    python github_tracking_manager.py --sync-ci $PRNumber
    
    Write-ColorOutput "✅ Tracking complete" $SuccessColor
}

function Start-Analysis {
    param(
        [int]$PRNumber,
        [int]$DaysToAnalyze
    )
    
    Write-ColorOutput "`n🔍 Starting Analysis..." $InfoColor
    
    if ($PRNumber -gt 0) {
        # Analyze specific PR
        Write-ColorOutput "  Analyzing PR #$PRNumber for missed opportunities..." $InfoColor
        python github_tracking_manager.py --analyze $PRNumber
    }
    
    # Analyze workflows
    Write-ColorOutput "  Analyzing workflows (last $DaysToAnalyze days)..." $InfoColor
    python workflow_analyzer.py --days $DaysToAnalyze
    
    Write-ColorOutput "✅ Analysis complete" $SuccessColor
}

function Generate-Report {
    param(
        [int]$PRNumber
    )
    
    Write-ColorOutput "`n📊 Generating Reports..." $InfoColor
    
    if ($PRNumber -gt 0) {
        # PR-specific report
        Write-ColorOutput "  Generating PR #$PRNumber report..." $InfoColor
        python github_tracking_manager.py --report --pr $PRNumber
    }
    else {
        # Overall report
        Write-ColorOutput "  Generating overall report..." $InfoColor
        python github_tracking_manager.py --report
    }
    
    # CD report
    Write-ColorOutput "  Generating CD report..." $InfoColor
    python cd_monitor.py --report --save-report cd_report.json
    
    # Workflow analysis report
    Write-ColorOutput "  Generating workflow analysis..." $InfoColor
    python workflow_analyzer.py --save-report workflow_analysis.json
    
    Write-ColorOutput "✅ Reports generated" $SuccessColor
    Write-ColorOutput "`nReport files:" $InfoColor
    Write-ColorOutput "  - github_tracking_state.json" $InfoColor
    Write-ColorOutput "  - github_tracking_state.yaml" $InfoColor
    Write-ColorOutput "  - cd_report.json" $InfoColor
    Write-ColorOutput "  - workflow_analysis.json" $InfoColor
}

function Show-Usage {
    Write-ColorOutput "`n🤖 CI/CD Automation Script" $InfoColor
    Write-ColorOutput "=" * 60
    Write-ColorOutput "`nUsage Examples:" $InfoColor
    Write-ColorOutput "`n  CI Monitoring:" $InfoColor
    Write-ColorOutput "    .\ci_cd_automation.ps1 -PR 15" $SuccessColor
    Write-ColorOutput "    .\ci_cd_automation.ps1 -PR 15 -Watch" $SuccessColor
    Write-ColorOutput "    .\ci_cd_automation.ps1 -PR 15 -CreateIssues" $SuccessColor
    
    Write-ColorOutput "`n  CD Monitoring:" $InfoColor
    Write-ColorOutput "    .\ci_cd_automation.ps1 -MonitorCD" $SuccessColor
    Write-ColorOutput "    .\ci_cd_automation.ps1 -MonitorCD -Environment production" $SuccessColor
    
    Write-ColorOutput "`n  Tracking:" $InfoColor
    Write-ColorOutput "    .\ci_cd_automation.ps1 -PR 15 -Track" $SuccessColor
    
    Write-ColorOutput "`n  Analysis:" $InfoColor
    Write-ColorOutput "    .\ci_cd_automation.ps1 -Analyze" $SuccessColor
    Write-ColorOutput "    .\ci_cd_automation.ps1 -PR 15 -Analyze" $SuccessColor
    Write-ColorOutput "    .\ci_cd_automation.ps1 -Analyze -Days 90" $SuccessColor
    
    Write-ColorOutput "`n  Reports:" $InfoColor
    Write-ColorOutput "    .\ci_cd_automation.ps1 -Report" $SuccessColor
    Write-ColorOutput "    .\ci_cd_automation.ps1 -PR 15 -Report" $SuccessColor
    
    Write-ColorOutput "`n  Combined:" $InfoColor
    Write-ColorOutput "    .\ci_cd_automation.ps1 -PR 15 -Track -Analyze -Report" $SuccessColor
    
    Write-ColorOutput "`nParameters:" $InfoColor
    Write-ColorOutput "  -PR <number>        PR number to monitor/track" $InfoColor
    Write-ColorOutput "  -Watch              Watch CI status continuously" $InfoColor
    Write-ColorOutput "  -CreateIssues       Create issues for CI failures" $InfoColor
    Write-ColorOutput "  -MonitorCD          Monitor CD deployments" $InfoColor
    Write-ColorOutput "  -Environment <env>  Filter CD by environment" $InfoColor
    Write-ColorOutput "  -Track              Track PR lifecycle and CI/CD" $InfoColor
    Write-ColorOutput "  -Analyze            Analyze for missed opportunities" $InfoColor
    Write-ColorOutput "  -Report             Generate comprehensive reports" $InfoColor
    Write-ColorOutput "  -Days <number>      Days to analyze (default: 30)" $InfoColor
    Write-ColorOutput "=" * 60
}

# Main execution
Write-ColorOutput "`n🤖 CI/CD Automation Script" $InfoColor
Write-ColorOutput "=" * 60

# Check authentication
if (-not (Test-GitHubAuth)) {
    exit 1
}

# Get repository info
$repoInfo = Get-RepositoryInfo
if (-not $repoInfo) {
    Write-ColorOutput "❌ Could not determine repository" $ErrorColor
    exit 1
}

# Execute based on parameters
$actionTaken = $false

if ($MonitorCD) {
    Start-CDMonitoring -Env $Environment
    $actionTaken = $true
}

if ($PR -gt 0) {
    if ($Track) {
        Start-Tracking -PRNumber $PR
        $actionTaken = $true
    }
    
    if ($Watch -or $CreateIssues -or (-not $Track -and -not $Analyze -and -not $Report)) {
        Start-CIMonitoring -PRNumber $PR -WatchMode $Watch -CreateIssuesFlag $CreateIssues
        $actionTaken = $true
    }
}

if ($Analyze) {
    Start-Analysis -PRNumber $PR -DaysToAnalyze $Days
    $actionTaken = $true
}

if ($Report) {
    Generate-Report -PRNumber $PR
    $actionTaken = $true
}

if (-not $actionTaken) {
    Show-Usage
}

Write-ColorOutput "`n✅ Script completed" $SuccessColor
