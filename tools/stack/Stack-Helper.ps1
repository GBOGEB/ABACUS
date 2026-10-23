<#
.SYNOPSIS
  Pick a repo, pick a stacked-PR chain, get the Rebase-Stack.ps1 command (copied to clipboard),
  and optionally run the check / push.

.EXAMPLE
  .\Stack-Helper.ps1                 # full menu: repo -> clone -> stack
.EXAMPLE
  .\Stack-Helper.ps1 -Repo C:\path\to\clone     # skip repo selection
.EXAMPLE
  .\Stack-Helper.ps1 -Rescan         # re-scan the disk for clones (otherwise cached)
#>
param(
    [string]$Repo,          # a local clone path; skips repo/clone selection
    [switch]$Rescan
)

$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$rebase = Join-Path $here 'Rebase-Stack.ps1'
$cache = Join-Path $env:LOCALAPPDATA 'stack-helper\clones.json'
$hdr = @{ 'User-Agent' = 'Stack-Helper' }
if ($env:GITHUB_TOKEN) { $hdr.Authorization = "Bearer $env:GITHUB_TOKEN" }   # optional: higher API limit

function Invoke-Api([string]$Url) {
    try { Invoke-RestMethod $Url -Headers $hdr }
    catch {
        if ($hdr.Authorization -and $_.Exception.Response.StatusCode.value__ -eq 401) {
            Write-Host 'GITHUB_TOKEN rejected; continuing without it.' -ForegroundColor DarkGray
            $hdr.Remove('Authorization'); Invoke-RestMethod $Url -Headers $hdr
        }
        else { throw }
    }
}
function Get-Json([string]$Url) { @((Invoke-Api $Url) | ForEach-Object { $_ }) }
function Get-Slug([string]$Url) {
    if ($Url -match 'github\.com[:/]([^/]+)/([^/]+?)(\.git)?/?$') { "$($Matches[1])/$($Matches[2])".ToLower() }
}
function Read-Choice([string]$Prompt, [int]$Max, [int]$Default = 1) {
    while ($true) {
        $a = Read-Host "$Prompt [1-$Max, Enter=$Default, q=quit]"
        if ($a -eq 'q') { exit }
        if (-not $a) { return $Default }
        if ($a -match '^\d+$' -and [int]$a -ge 1 -and [int]$a -le $Max) { return [int]$a }
    }
}

# ---- 1. find local clones (cached) ------------------------------------------
function Find-Clones {
    $roots = "$HOME", "$HOME\source\repos", "$HOME\PycharmProjects", "$HOME\Documents",
             "$HOME\Clone_FrOM_GITHUB", "$HOME\OneDrive - Studiecentrum voor Kernenergie"
    Write-Host 'Scanning for git clones (cached afterwards; -Rescan to refresh)...' -ForegroundColor DarkGray
    $dirs = foreach ($r in $roots) {
        if (Test-Path $r) {
            Get-ChildItem $r -Directory -Force -Depth 3 -Filter .git -ErrorAction SilentlyContinue |
                ForEach-Object { $_.Parent.FullName }
        }
    }
    $out = foreach ($d in ($dirs | Sort-Object -Unique)) {
        if ($d -match '\\\.(cookiecutters|codex|claude)\\|\\external\\') { continue }
        $slug = Get-Slug (& git.exe -C $d remote get-url origin 2>$null)
        if ($slug) { [pscustomobject]@{ Path = $d; Slug = $slug } }
    }
    New-Item -ItemType Directory -Force (Split-Path $cache) | Out-Null
    $out | ConvertTo-Json | Set-Content $cache -Encoding utf8
    $out
}

if ($Repo) {
    $slug = Get-Slug (& git.exe -C $Repo remote get-url origin)
    if (-not $slug) { throw "$Repo has no GitHub 'origin' remote." }
    $clone = (Resolve-Path $Repo).Path
}
else {
    $clones = if (-not $Rescan -and (Test-Path $cache)) { @(Get-Content $cache -Raw | ConvertFrom-Json) } else { @(Find-Clones) }
    $repos = $clones | Group-Object Slug | Sort-Object Name

    # open-PR counts per repo (1 API call each) so repos with stacks come first
    $rows = foreach ($g in $repos) {
        $open = 0; $stacked = 0
        try {
            $prs = Get-Json "https://api.github.com/repos/$($g.Name)/pulls?state=open&per_page=100"
            $heads = $prs | ForEach-Object { $_.head.ref }
            $open = $prs.Count
            $stacked = @($prs | Where-Object { $heads -contains $_.base.ref }).Count
        } catch { $open = -1 }
        [pscustomobject]@{ Slug = $g.Name; Clones = $g.Group; Open = $open; Stacked = $stacked }
    }
    $rows = @($rows | Sort-Object @{ e = 'Stacked'; Descending = $true }, @{ e = 'Open'; Descending = $true }, Slug)
    Write-Host "`nRepositories" -ForegroundColor Cyan
    for ($i = 0; $i -lt $rows.Count; $i++) {
        $r = $rows[$i]
        $info = if ($r.Open -lt 0) { 'no API access (private?)' } else { "$($r.Open) open PR(s), $($r.Stacked) stacked" }
        Write-Host ("  [{0,2}] {1,-45} {2}  ({3} clone(s))" -f ($i + 1), $r.Slug, $info, $r.Clones.Count)
    }
    $pick = $rows[(Read-Choice 'Repo' $rows.Count) - 1]
    $slug = $pick.Slug

    # ---- 2. pick a clone (clean ones first) --------------------------------------
    $cl = @($pick.Clones | ForEach-Object {
            $dirty = @(& git.exe -C $_.Path status --porcelain --untracked-files=no 2>$null).Count
            $br = (& git.exe -C $_.Path branch --show-current 2>$null)
            [pscustomobject]@{ Path = $_.Path; Dirty = $dirty; Branch = $br }
        } | Sort-Object Dirty, Path)
    if ($cl.Count -eq 1) { $clone = $cl[0].Path }
    else {
        Write-Host "`nClones of $slug (clean ones first; the script needs a clean one)" -ForegroundColor Cyan
        for ($i = 0; $i -lt $cl.Count; $i++) {
            $state = if ($cl[$i].Dirty) { "$($cl[$i].Dirty) uncommitted change(s)" } else { 'clean' }
            Write-Host ("  [{0}] {1}  [{2}, on {3}]" -f ($i + 1), $cl[$i].Path, $state, $cl[$i].Branch)
        }
        $clone = $cl[(Read-Choice 'Clone' $cl.Count) - 1].Path
    }
}

# ---- 3. build stacks from open PRs ---------------------------------------------
$api = "https://api.github.com/repos/$slug"
$default = (Invoke-Api $api).default_branch
$prs = @()
for ($page = 1; $page -le 10; $page++) {
    $b = Get-Json "$api/pulls?state=open&per_page=100&page=$page"; $prs += $b
    if ($b.Count -lt 100) { break }
}
$byBase = @{}; foreach ($p in $prs) { $byBase[$p.base.ref] += @($p) }

$chains = [System.Collections.Generic.List[object]]::new()
function Add-Paths($chain) {
    $kids = $byBase[$chain[-1].head.ref]
    if (-not $kids) { $chains.Add($chain); return }
    foreach ($k in $kids) { Add-Paths (@($chain) + $k) }
}
foreach ($p in $prs | Where-Object { $_.base.ref -eq $default }) { Add-Paths @($p) }
if (-not $chains.Count) { Write-Host "No open PRs in $slug."; exit }

Write-Host "`nChecking conflict state of $($prs.Count) open PR(s) in $slug..." -ForegroundColor DarkGray
$state = @{}
foreach ($p in $prs) {
    try { $state[$p.number] = (Invoke-Api "$api/pulls/$($p.number)").mergeable_state } catch { $state[$p.number] = '?' }
}
$rank = { param($c) if ($c | Where-Object { $state[$_.number] -eq 'dirty' }) { 0 } elseif ($c.Count -gt 1) { 1 } else { 2 } }
$chains = @($chains | Sort-Object { & $rank $_ }, { -$_.Count })

Write-Host "`nStacks in $slug  (base: $default)   dirty = has conflicts" -ForegroundColor Cyan
for ($i = 0; $i -lt $chains.Count; $i++) {
    $c = $chains[$i]
    $flag = if ($c | Where-Object { $state[$_.number] -eq 'dirty' }) { 'CONFLICT' } else { 'ok      ' }
    $line = ($c | ForEach-Object { "#$($_.number)[$($state[$_.number])]" }) -join ' -> '
    Write-Host ("  [{0,2}] {1} {2}" -f ($i + 1), $flag, $line) -ForegroundColor ($(if ($flag -eq 'CONFLICT') { 'Yellow' } else { 'Gray' }))
    Write-Host ("        top: {0}" -f $c[-1].head.ref) -ForegroundColor DarkGray
}
$chain = $chains[(Read-Choice 'Stack' $chains.Count) - 1]

# ---- 4. command, clipboard, run --------------------------------------------------
$branches = ($chain | ForEach-Object { "'$($_.head.ref)'" }) -join ', '
$check = "& '$rebase' -Repo '$clone' -Base '$default' -Branches $branches"
$push = "$check -Push"
Write-Host "`nCheck (no push):" -ForegroundColor Cyan; Write-Host $check
Write-Host "`nPush:" -ForegroundColor Cyan; Write-Host $push
try { Set-Clipboard -Value $check; Write-Host "`n(check command copied to clipboard)" -ForegroundColor DarkGray } catch {}

$a = Read-Host "`nRun the check now? [y/N]"
if ($a -eq 'y') {
    & $rebase -Repo $clone -Base $default -Branches ($chain | ForEach-Object { $_.head.ref })
    $a = Read-Host "`nAll OK and auto: decisions look right? Push now? [y/N]"
    if ($a -eq 'y') { & $rebase -Repo $clone -Base $default -Branches ($chain | ForEach-Object { $_.head.ref }) -Push }
    else { try { Set-Clipboard -Value $push; Write-Host '(push command copied to clipboard)' -ForegroundColor DarkGray } catch {} }
}
