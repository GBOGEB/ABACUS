#requires -Version 7.0
<#
.SYNOPSIS
  Audit all open ABACUS PR heads and optionally rerun failed GitHub Actions jobs
  with native GitHub debug logging. Default: Plan (read-only).
.EXAMPLE
  pwsh -File ./scripts/Invoke-AbacusPrDebug.ps1
.EXAMPLE
  pwsh -File ./scripts/Invoke-AbacusPrDebug.ps1 -Mode Apply -Policy AllFailed -Yes -MaxReruns 12
.EXAMPLE
  pwsh -File ./scripts/Invoke-AbacusPrDebug.ps1 -Mode Refresh -DashboardReceipts ./ledger/dashboard.json
.NOTES
  Requires authenticated GitHub CLI (gh auth login), Python 3.9+ and PowerShell 7.
  No merge, review, required-check or security waiver capability is implemented.
#>
[CmdletBinding()]
param(
    [ValidateSet('Plan', 'Apply', 'Refresh')]
    [string]$Mode = 'Plan',
    [ValidateSet('Retryable', 'AllFailed')]
    [string]$Policy = 'Retryable',
    [string]$Repo = 'GBOGEB/ABACUS',
    [int]$MaxReruns = 8,
    [int]$MaxPRs = 0,
    [int]$MaxPages = 5,
    [int]$DelaySeconds = 20,
    [int]$CooldownMinutes = 45,
    [int]$LagThresholdMinutes = 30,
    [int[]]$OnlyPR,
    [switch]$ExcludeDrafts,
    [switch]$Yes,
    [switch]$NoDebug,
    [string]$AuditDir,
    [string]$Baseline,
    [string]$AgentReceipts,
    [string]$DashboardReceipts,
    [string]$Python = 'python',
    [string]$Gh = 'gh'
)

$ErrorActionPreference = 'Stop'
$scriptPath = Join-Path $PSScriptRoot 'abacus_pr_rerun_audit.py'
$repoRoot = Split-Path -Parent $PSScriptRoot
if (-not $AuditDir) {
    $AuditDir = Join-Path $repoRoot '.artifacts/abacus-pr-debug'
}
if (-not (Test-Path -LiteralPath $scriptPath)) {
    throw "Missing ABACUS rerun controller: $scriptPath"
}
if ($Mode -eq 'Apply' -and -not $Yes) {
    throw 'Apply requires -Yes. Plan first to inspect all exact-head failures.'
}

$argv = @(
    $scriptPath,
    '--mode', $Mode.ToLowerInvariant(),
    '--policy', $(if ($Policy -eq 'AllFailed') { 'all-failed' } else { 'retryable' }),
    '--repo', $Repo,
    '--max-reruns', [string]$MaxReruns,
    '--max-prs', [string]$MaxPRs,
    '--max-pages', [string]$MaxPages,
    '--delay-seconds', [string]$DelaySeconds,
    '--cooldown-minutes', [string]$CooldownMinutes,
    '--lag-threshold-minutes', [string]$LagThresholdMinutes,
    '--audit-dir', $AuditDir,
    '--gh', $Gh
)
if ($Yes) { $argv += '--yes' }
if ($NoDebug) { $argv += '--no-debug' }
if ($ExcludeDrafts) { $argv += '--exclude-drafts' }
foreach ($pr in $OnlyPR) { $argv += @('--only-pr', [string]$pr) }
if ($Baseline) { $argv += @('--baseline', $Baseline) }
if ($AgentReceipts) { $argv += @('--agent-receipts', $AgentReceipts) }
if ($DashboardReceipts) { $argv += @('--dashboard-receipts', $DashboardReceipts) }

# Native external process exit codes are surfaced, not interpreted as CI success.
& $Python @argv
exit $LASTEXITCODE
