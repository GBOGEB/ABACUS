<#
.SYNOPSIS
  Scan a repo for every PR stack with merge conflicts, update each stack bottom -> top
  (rebase or merge, auto-resolve: added -> keep both, changed/deleted -> newer wins),
  validate the result, report, then push the READY stacks after you confirm.

.EXAMPLE
  .\Fix-AllStacks.ps1                      # scan + fix locally + report, then asks before pushing
.EXAMPLE
  .\Fix-AllStacks.ps1 -ListOnly            # only list conflicting stacks, change nothing
.EXAMPLE
  .\Fix-AllStacks.ps1 -Test "python -m pytest -q -p no:cacheprovider tests"   # also run tests per stack
.EXAMPLE
  .\Fix-AllStacks.ps1 -Repo C:\path\to\other\clone
#>
param(
    [string]$Repo = $env:STACK_REPO,   # default: the clone this script lives in
    [switch]$ListOnly,
    [string]$Test,          # optional command run in the repo on each stack's top branch
    [switch]$Yes            # push READY stacks without asking
)

$ErrorActionPreference = 'Stop'
if (-not $Repo) { $Repo = (& git.exe -C $PSScriptRoot rev-parse --show-toplevel 2>$null) }
if (-not $Repo) { throw 'No repo: pass -Repo <clone> or set STACK_REPO.' }
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$rebaseScript = Join-Path $here 'Rebase-Stack.ps1'
$hdr = @{ 'User-Agent' = 'Fix-AllStacks' }
if ($env:GITHUB_TOKEN) { $hdr.Authorization = "Bearer $env:GITHUB_TOKEN" }

function Invoke-Api([string]$Url) {
    try { Invoke-RestMethod $Url -Headers $hdr }
    catch {
        if ($hdr.Authorization -and $_.Exception.Response.StatusCode.value__ -eq 401) {
            $hdr.Remove('Authorization'); Invoke-RestMethod $Url -Headers $hdr
        }
        else { throw }
    }
}
function G { & git.exe -C $Repo @args }

# ---- 1. scan ------------------------------------------------------------------------
$url = G remote get-url origin
if ($url -notmatch 'github\.com[:/]([^/]+)/([^/]+?)(\.git)?/?$') { throw "origin is not a GitHub URL: $url" }
$api = "https://api.github.com/repos/$($Matches[1])/$($Matches[2])"
$default = (Invoke-Api $api).default_branch
$prs = @((Invoke-Api "$api/pulls?state=open&per_page=100") | ForEach-Object { $_ })
Write-Host "Scanning $($prs.Count) open PR(s) in $($Matches[1])/$($Matches[2]) ..." -ForegroundColor DarkGray

$state = @{}
foreach ($p in $prs) {
    for ($try = 0; $try -lt 3; $try++) {          # GitHub computes mergeability lazily
        $s = (Invoke-Api "$api/pulls/$($p.number)").mergeable_state
        if ($s -ne 'unknown') { break }; Start-Sleep -Seconds 2
    }
    $state[$p.number] = $s
}

$byBase = @{}; foreach ($p in $prs) { $byBase[$p.base.ref] += @($p) }
$chains = [System.Collections.Generic.List[object]]::new()
function Add-Paths($chain) {
    $kids = $byBase[$chain[-1].head.ref]
    if (-not $kids) { $chains.Add($chain); return }
    foreach ($k in $kids) { Add-Paths (@($chain) + $k) }
}
foreach ($p in $prs | Where-Object { $_.base.ref -eq $default }) { Add-Paths @($p) }
$dirty = @($chains | Where-Object { $_ | Where-Object { $state[$_.number] -eq 'dirty' } })

Write-Host "`nStacks with conflicts: $($dirty.Count)" -ForegroundColor Cyan
foreach ($c in $dirty) { Write-Host ('  ' + (($c | ForEach-Object { "#$($_.number)[$($state[$_.number])]" }) -join ' -> ')) }
if ($ListOnly -or -not $dirty.Count) { exit }

# ---- 2. fix each stack locally (no push) ---------------------------------------------
G fetch -q origin
$logDir = Join-Path $env:LOCALAPPDATA ("stack-helper\logs\" + (Get-Date -Format 'yyyyMMdd-HHmmss'))
New-Item -ItemType Directory -Force $logDir | Out-Null
$used = @{}
$results = foreach ($c in $dirty) {
    $branches = @($c | ForEach-Object { $_.head.ref })
    $label = ($c | ForEach-Object { "#$($_.number)" }) -join '>'
    $r = [ordered]@{ Stack = $label; Status = ''; Auto = 0; Note = ''; PushCmd = $null; Log = '' }

    # never overwrite unpushed local work, never touch a branch twice in one run
    # (a branch that is exactly what Rebase-Stack produced last time is fine to rebuild)
    $local = $branches | Where-Object {
        (G rev-parse --verify --quiet "refs/heads/$_") -and [int](G rev-list --count "origin/$_..refs/heads/$_") -gt 0 -and
        (G rev-parse "refs/heads/$_") -ne (G rev-parse --verify --quiet "refs/stack-result/$_")
    }
    $shared = $branches | Where-Object { $used[$_] }
    if ($shared) { $r.Status = 'SKIPPED'; $r.Note = "shares $($shared -join ', ') with a stack above; rerun after pushing it"; [pscustomobject]$r; continue }
    if ($local) { $r.Status = 'SKIPPED'; $r.Note = "unpushed local commits on $($local -join ', '); push or reset them first"; [pscustomobject]$r; continue }
    $branches | ForEach-Object { $used[$_] = $true }

    $log = Join-Path $logDir ((($label -replace '[^0-9#>]', '') -replace '[#>]', '_').Trim('_') + '.log')
    $r.Log = $log
    Write-Host "`n=== $label ===" -ForegroundColor Cyan
    $out = & pwsh -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $rebaseScript `
        -Repo $Repo -Base $default -Branches ($branches -join ',') 2>&1 |
        ForEach-Object { "$_" } | Where-Object { $_ -and $_ -ne 'System.Management.Automation.RemoteException' }
    $out | Set-Content $log -Encoding utf8
    $out | Where-Object { $_ -match '^\s+auto:|WARNING|^OK |^BAD|^Exception|mode' } | ForEach-Object { Write-Host "  $_" }

    $r.Auto = @($out | Where-Object { $_ -match '^\s+auto:' }).Count
    $okCount = @($out | Where-Object { $_ -match '^OK ' }).Count
    $warn = @($out | Where-Object { $_ -match '^\s*WARNING|^BAD|^Exception|verification failed|Aborted by user|Read and Prompt|still fails a syntax' })
    $r.PushCmd = ($out | Where-Object { $_ -match '^git -C .* push --atomic' } | Select-Object -First 1)

    $problems = @()
    if ($okCount -ne $branches.Count -or $warn) { $problems += 'did not finish cleanly (see log)' }
    else {
        foreach ($b in $branches) {
            # duplicated Markdown headings introduced by the update
            foreach ($md in @(G diff --name-only "origin/$b" $b -- '*.md')) {
                $before = @(G show "origin/${b}:$md" 2>$null | Where-Object { $_ -match '^#{1,6} ' } | Group-Object | Where-Object Count -gt 1).Count
                $after = @(G show "${b}:$md" | Where-Object { $_ -match '^#{1,6} ' } | Group-Object | Where-Object Count -gt 1).Count
                if ($after -gt $before) { $problems += "duplicated heading in $md ($b)" }
            }
        }
        # code files where the newer side replaced the other side's change in a conflicting spot
        # (workflows/config count as code: a newer side that only bumped versions can wipe real logic changes)
        $dropped = @($out | Where-Object { $_ -match '^\s+auto: (\S+\.(py|ps1|js|ts|cs|java|go|rs|sh|ya?ml|json|toml)) -> .* [1-9]\d* changed' } |
            ForEach-Object { $Matches[1] })
        if ($dropped) { $problems += "code hunks resolved newer-side-only: $(@($dropped | Sort-Object -Unique) -join ', ')" }
        # resolutions replayed from rerere were never re-checked in this run
        $replayed = @($out | Where-Object { $_ -match '^\s+\S+: (\S+)\s+\[replayed rerere resolution\]' } | ForEach-Object { $Matches[1] })
        if ($replayed) { $problems += "rerere replayed old resolutions: $(@($replayed | Sort-Object -Unique) -join ', ')" }
        if ($Test) {
            G checkout -q $branches[-1]
            Push-Location $Repo
            try { $env:PYTHONPATH = $Repo; Invoke-Expression $Test *>> $log; if ($LASTEXITCODE) { $problems += "tests failed (exit $LASTEXITCODE)" } }
            finally { Pop-Location }
        }
    }
    $problems = @($problems | Sort-Object -Unique)
    $r.Status = if ($problems) { 'REVIEW' } else { 'READY' }
    $r.Note = ($problems -join '; ')
    [pscustomobject]$r
}

# ---- 3. report + push ------------------------------------------------------------------
Write-Host "`n================ REPORT ================" -ForegroundColor Cyan
foreach ($r in $results) {
    $col = @{ READY = 'Green'; REVIEW = 'Yellow'; SKIPPED = 'DarkGray' }[$r.Status]
    Write-Host ("{0,-8} {1,-30} auto-resolved files: {2}  {3}" -f $r.Status, $r.Stack, $r.Auto, $r.Note) -ForegroundColor $col
}
Write-Host "Logs: $logDir" -ForegroundColor DarkGray

$ready = @($results | Where-Object { $_.Status -eq 'READY' -and $_.PushCmd })
if (-not $ready.Count) { Write-Host "`nNothing READY to push." ; exit }
$go = $Yes -or ((Read-Host "`nPush the $($ready.Count) READY stack(s)? [y/N]") -eq 'y')
if (-not $go) {
    Write-Host "`nNot pushed. Push commands:" -ForegroundColor Cyan
    $ready | ForEach-Object { Write-Host $_.PushCmd }
    exit
}
foreach ($r in $ready) {
    Write-Host "`nPushing $($r.Stack)" -ForegroundColor Cyan
    & pwsh -NoProfile -Command $r.PushCmd
}
Write-Host "`nDone. REVIEW stacks are fixed locally but not pushed: check them, then push with the command in their log." -ForegroundColor Cyan
