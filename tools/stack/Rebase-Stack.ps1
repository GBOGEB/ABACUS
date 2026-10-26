<#
.SYNOPSIS
  Rebase a stack of PR branches (bottom -> top) onto the latest base branch.

.DESCRIPTION
  - Starts from the REMOTE state of every branch (what the PRs show).
  - Backs up every original tip to refs/stack-backup/<timestamp>/<branch>.
  - Handles non-linear stacks: if an upper branch was cut from an OLDER copy of the
    branch below it, the stale copied commits (same subject already present below)
    are dropped and only the upper branch's own commits are replayed.
  - Enables git rerere, so a conflict you resolve once is replayed automatically
    the next time the same hunk appears (in this stack or any other).
  - Pauses on a new conflict so you can resolve it in another window.
  - Pushes only with -Push, atomically, with --force-with-lease pinned to the
    original remote SHAs.

.EXAMPLE
  .\Rebase-Stack.ps1 2145
  Any PR number in the stack: the whole stack (bottom -> top) is looked up on GitHub.

.EXAMPLE
  .\Rebase-Stack.ps1 2145 -Push

.EXAMPLE
  .\Rebase-Stack.ps1 -Branches feat/a-bottom, test/b-middle, feat/c-top
#>
param(
    [Parameter(Position = 0)][int]$Pr,           # any PR number in the stack
    [string]$Repo = $env:STACK_REPO,             # default: the clone this script lives in
    [string[]]$Branches,                         # or give branches explicitly, bottom first
    [switch]$Manual,                             # pause on every conflict instead of newest-wins
    [string]$Base = 'main',
    [string]$Remote = 'origin',
    # Auto: Merge if any branch in the stack contains merge commits, else Rebase.
    # Merge mode merges the (updated) branch below into each branch: history kept, no force-push needed.
    [ValidateSet('Auto', 'Rebase', 'Merge')][string]$Mode = 'Auto',
    # Resolve conflicts automatically: per file, the side whose last change (author date) is newer
    # wins every conflicting hunk; non-conflicting hunks from both sides are kept.
    # If the newer change deleted the file, the deletion wins.
    [switch]$NewestWins,
    [switch]$Push,
    # -Push refuses when any conflict was resolved automatically (newest-wins or a replayed rerere
    # resolution); review the listed files, then re-run with -AcceptAuto to push anyway.
    [switch]$AcceptAuto
)
$script:AutoResolved = [ordered]@{}   # "branch: file" -> how it was resolved

$ErrorActionPreference = 'Stop'
if (-not $Repo) { $Repo = (& git.exe -C $PSScriptRoot rev-parse --show-toplevel 2>$null) }
if (-not $Repo) { throw 'No repo: pass -Repo <clone> or set STACK_REPO.' }
$env:GIT_EDITOR = 'true'   # accept existing commit messages, never open Vim
if (-not $Manual) { $NewestWins = $true }   # default rule: added -> keep both, changed/deleted -> newer wins

function Get-StackFromPr([int]$Number) {
    $url = (& git.exe -C $Repo remote get-url $Remote)
    if ($url -notmatch 'github\.com[:/]([^/]+)/(.+?)(\.git)?$') { throw "Remote '$Remote' is not a GitHub URL: $url" }
    $api = "https://api.github.com/repos/$($Matches[1])/$($Matches[2])"
    $h = @{ 'User-Agent' = 'Rebase-Stack' }
    $prs = @()
    for ($page = 1; $page -le 10; $page++) {
        $batch = @((Invoke-RestMethod "$api/pulls?state=open&per_page=100&page=$page" -Headers $h) | ForEach-Object { $_ })
        $prs += $batch
        if ($batch.Count -lt 100) { break }
    }
    $byHead = @{}; $byBase = @{}
    foreach ($p in $prs) { $byHead[$p.head.ref] = $p; $byBase[$p.base.ref] += @($p) }
    $start = $prs | Where-Object { $_.number -eq $Number }
    if (-not $start) { throw "PR #$Number is not an open PR in $api (use a PR number, not the stack ID)." }

    $chain = @($start)
    while ($chain[0].base.ref -ne $Base -and $byHead[$chain[0].base.ref]) { $chain = @($byHead[$chain[0].base.ref]) + $chain }
    if ($chain[0].base.ref -ne $Base) { throw "Bottom PR #$($chain[0].number) targets '$($chain[0].base.ref)', not '$Base'." }
    while ($byBase[$chain[-1].head.ref]) {
        $kids = $byBase[$chain[-1].head.ref]
        if ($kids.Count -gt 1) {
            Write-Host ("Stack splits above #{0} into {1}; stopping there. Run again with one of those PR numbers to include that branch." -f `
                    $chain[-1].number, (($kids | ForEach-Object { "#$($_.number)" }) -join ', ')) -ForegroundColor Yellow
            break
        }
        $chain += $kids[0]
    }
    Write-Host "Stack for #${Number} (bottom -> top):" -ForegroundColor Cyan
    $chain | ForEach-Object { Write-Host ("  #{0}  {1}" -f $_.number, $_.head.ref) }
    @($chain | ForEach-Object { $_.head.ref })
}

if ($Pr) { $Branches = Get-StackFromPr $Pr }
$Branches = @($Branches -split ',' | ForEach-Object Trim | Where-Object { $_ })   # allow "a,b,c"
if (-not $Branches) { throw 'Give a PR number (e.g. .\Rebase-Stack.ps1 2145) or -Branches bottom,...,top.' }

function Invoke-Git {
    $out = & git.exe -C $Repo @args
    if ($LASTEXITCODE -ne 0) { throw "git $($args -join ' ') failed (exit $LASTEXITCODE)" }
    $out
}
function Test-Rebasing {
    foreach ($d in 'rebase-merge', 'rebase-apply') {
        $p = (& git.exe -C $Repo rev-parse --git-path $d)
        if (-not [IO.Path]::IsPathRooted($p)) { $p = Join-Path $Repo $p }
        if (Test-Path $p) { return $true }
    }
    $false
}
function Get-Conflicts { @(& git.exe -C $Repo diff --name-only --diff-filter=U | Where-Object { $_ }) }
function Test-Ancestor($a, $b) { & git.exe -C $Repo merge-base --is-ancestor $a $b; $LASTEXITCODE -eq 0 }

function Get-LastChange([string]$Range, [string]$File) {
    $t = @(& git.exe -C $Repo log -1 --format=%at $Range -- $File)
    if ($t -and $t[0]) { [long]$t[0] } else { 0L }
}

function Test-Syntax([string]$Path) {
    switch -Regex ([IO.Path]::GetExtension($Path).ToLower()) {
        '^\.py$' { & python -c "import ast,sys; ast.parse(open(sys.argv[1],encoding='utf-8').read())" $Path 2>$null; return $LASTEXITCODE -eq 0 }
        '^\.ya?ml$' { & python -c "import yaml,sys; list(yaml.safe_load_all(open(sys.argv[1],encoding='utf-8')))" $Path 2>$null; return $LASTEXITCODE -eq 0 }
        '^\.json$' { try { Get-Content -Raw -LiteralPath $Path | ConvertFrom-Json | Out-Null; return $true } catch { return $false } }
        default { return $true }
    }
}

function Resolve-Newest([string]$TheirsRef) {
    $mb = (& git.exe -C $Repo merge-base HEAD $TheirsRef)
    foreach ($f in Get-Conflicts) {
        $od = Get-LastChange "$mb..HEAD" $f
        $td = Get-LastChange "$mb..$TheirsRef" $f
        $side = if ($td -gt $od) { 'theirs' } else { 'ours' }
        $when = [DateTimeOffset]::FromUnixTimeSeconds([math]::Max($od, $td)).LocalDateTime.ToString('yyyy-MM-dd HH:mm')
        # stage temp files: "<base> <ours> <theirs>\t<path>", '.' = absent
        $line = @(& git.exe -C $Repo checkout-index --stage=all --temp -- $f)[0]
        $tmp = ($line -split "`t")[0] -split ' '
        $abs = { param($n) if ($n -eq '.') { $null } else { Join-Path $Repo $n } }
        $base = & $abs $tmp[0]; $ours = & $abs $tmp[1]; $theirs = & $abs $tmp[2]
        $win = if ($side -eq 'ours') { $ours } else { $theirs }
        $lose = if ($side -eq 'ours') { $theirs } else { $ours }
        $target = Join-Path $Repo $f
        if (-not $win) {
            & git.exe -C $Repo rm -q -- $f | Out-Null
            $what = 'deleted'
        }
        elseif (-not $lose) {
            Copy-Item -LiteralPath $win -Destination $target -Force
            & git.exe -C $Repo add -- $f
            $what = 'kept'
        }
        else {
            # add/add (both sides created the file): competing versions, never glue them together
            $addAdd = -not $base
            if ($addAdd) { $base = Join-Path $Repo ".stack-empty-base"; [IO.File]::WriteAllBytes($base, [byte[]]@()) }
            & git.exe -C $Repo merge-file --diff3 $ours $base $theirs | Out-Null   # writes result into $ours
            if ($LASTEXITCODE -lt 0) {
                Copy-Item -LiteralPath $win -Destination $target -Force          # binary: whole newer file
                $what = 'binary, newer file'
            }
            else {
                $bytes = [IO.File]::ReadAllBytes($ours)
                $bom = $bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF
                $raw = [IO.File]::ReadAllText($ours)
                # "keep both" only for prose/list files; code always takes the newer side
                $ext = [IO.Path]::GetExtension($f).ToLower()
                $unionOk = $ext -in '.md', '.txt', '.rst', '.yml', '.yaml', '.toml', '.cfg', '.ini', '.gitignore'
                $n = @{ both = 0; newer = 0 }
                $rx = '(?ms)^<<<<<<<[^\n]*\n(.*?)^\|\|\|\|\|\|\|[^\n]*\n(.*?)^=======\r?\n(.*?)^>>>>>>>[^\n]*(?:\n|\z)'
                $resolve = { param($allowUnion) $n.both = 0; $n.newer = 0; [regex]::Replace($raw, $rx, {
                        param($m)
                        $o = $m.Groups[1].Value; $b = $m.Groups[2].Value; $t = $m.Groups[3].Value
                        if ($allowUnion -and -not $addAdd -and $b.Trim() -eq '') {
                            # both only ADDED lines here: keep both, but never add text that is already present
                            $n.both++
                            if ($o.Trim() -and $o.Contains($t.Trim())) { return $o }
                            if ($t.Trim() -and $t.Contains($o.Trim())) { return $t }
                            if ($t.Trim() -and $raw.Replace($m.Value, '').Contains($t.Trim())) { return $o }
                            return $o + $t
                        }
                        $n.newer++
                        if ($side -eq 'ours') { $o } else { $t }              # a CHANGE/DELETE: newer side wins
                    }) }
                $text = & $resolve $unionOk
                $enc = New-Object Text.UTF8Encoding($bom)
                [IO.File]::WriteAllText($target, $text, $enc)
                if (-not (Test-Syntax $target)) {
                    $text = & $resolve $false                                  # union broke it: newer side only
                    [IO.File]::WriteAllText($target, $text, $enc)
                    Write-Host "  auto: $f -> 'keep both' gave invalid syntax, used newer side for every hunk" -ForegroundColor Yellow
                }
                if (-not (Test-Syntax $target)) { Write-Host "  WARNING: $f still fails a syntax check - review it" -ForegroundColor Red }
                $what = "$($n.both) hunk(s) both added -> kept both, $($n.newer) changed -> newer side"
            }
            & git.exe -C $Repo add -- $f
        }
        foreach ($t in @($base, $ours, $theirs)) { if ($t -and (Test-Path -LiteralPath $t)) { Remove-Item -LiteralPath $t -Force } }
        Write-Host ("  auto: {0} -> {1} ({2}, {3})" -f $f, $side, $what, $when) -ForegroundColor DarkCyan
        $script:AutoResolved["$(& git.exe -C $Repo branch --show-current): $f"] = "$side, $what"
    }
}

function Save-RerereReplays {
    # files rerere resolved from an earlier recorded resolution never reach Resolve-Newest
    $br = (& git.exe -C $Repo branch --show-current)
    foreach ($f in @(& git.exe -C $Repo rerere status | Where-Object { $_ })) {
        if (-not $script:AutoResolved.Contains("${br}: $f")) { $script:AutoResolved["${br}: $f"] = 'replayed rerere resolution' }
    }
}

function Invoke-RebaseStep([string[]]$RebaseArgs) {
    & git.exe -C $Repo rebase @RebaseArgs
    while (Test-Rebasing) {
        if ($NewestWins -and (Get-Conflicts).Count -gt 0) { Resolve-Newest 'REBASE_HEAD' }
        $conf = Get-Conflicts
        if ($conf.Count -gt 0) {
            $stop = (& git.exe -C $Repo log -1 --format='%h %s' REBASE_HEAD 2>$null)
            Write-Host "`nCONFLICT while applying: $stop" -ForegroundColor Yellow
            $conf | ForEach-Object { Write-Host "  $_" -ForegroundColor Yellow }
            Write-Host "Resolve the files above in another window, then 'git add' them." -ForegroundColor Yellow
            $ans = Read-Host "Press Enter to continue, type 'skip' to DROP this commit, 'a' to abort"
            if ($ans -eq 'a') { & git.exe -C $Repo rebase --abort; throw 'Aborted by user.' }
            if ($ans -eq 'skip') { & git.exe -C $Repo rebase --skip; continue }
            if ((Get-Conflicts).Count -gt 0) { Write-Host 'Still unresolved files, try again.' -ForegroundColor Red; continue }
        }
        else {
            # rerere (autoupdate) already resolved and staged everything
            & git.exe -C $Repo add -u
        }
        Save-RerereReplays
        & git.exe -C $Repo rebase --continue
        if ($LASTEXITCODE -ne 0 -and (Test-Rebasing) -and (Get-Conflicts).Count -eq 0) {
            # commit became empty (already in base): drop it
            Write-Host 'Commit is now empty, skipping it.' -ForegroundColor DarkGray
            & git.exe -C $Repo rebase --skip
        }
    }
}

function Test-Merging {
    $p = (& git.exe -C $Repo rev-parse --git-path MERGE_HEAD)
    if (-not [IO.Path]::IsPathRooted($p)) { $p = Join-Path $Repo $p }
    Test-Path $p
}

function Invoke-MergeStep([string]$From) {
    & git.exe -C $Repo merge --no-edit --no-ff -m "merge: update stack branch with $From" $From
    while (Test-Merging) {
        if ($NewestWins -and (Get-Conflicts).Count -gt 0) { Resolve-Newest 'MERGE_HEAD' }
        $conf = Get-Conflicts
        if ($conf.Count -gt 0) {
            Write-Host "`nCONFLICT merging $From into $(Invoke-Git branch --show-current)" -ForegroundColor Yellow
            $conf | ForEach-Object { Write-Host "  $_" -ForegroundColor Yellow }
            Write-Host "Resolve the files above in another window, then 'git add' them." -ForegroundColor Yellow
            $ans = Read-Host "Press Enter to continue, 'a' to abort"
            if ($ans -eq 'a') { & git.exe -C $Repo merge --abort; throw 'Aborted by user.' }
            if ((Get-Conflicts).Count -gt 0) { Write-Host 'Still unresolved files, try again.' -ForegroundColor Red; continue }
        }
        else { & git.exe -C $Repo add -u }   # rerere already resolved and staged
        Save-RerereReplays
        & git.exe -C $Repo commit --no-edit
    }
}

# ---- preflight --------------------------------------------------------------
if ((Test-Rebasing) -or (Test-Merging)) { throw "A rebase or merge is already in progress in $Repo. Finish or abort it first." }
if (Invoke-Git status --porcelain --untracked-files=no) { throw "Working tree in $Repo has uncommitted changes." }

Invoke-Git config rerere.enabled true | Out-Null
Invoke-Git config rerere.autoUpdate true | Out-Null
Invoke-Git fetch $Remote --prune | Out-Null

$baseRef = "$Remote/$Base"
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$orig = [ordered]@{}
foreach ($b in $Branches) {
    $sha = (& git.exe -C $Repo rev-parse --verify --quiet "refs/remotes/$Remote/$b")
    if (-not $sha) { throw "Branch '$b' not found on $Remote (check the spelling)." }
    $orig[$b] = $sha
    Invoke-Git update-ref "refs/stack-backup/$stamp/$b" $sha | Out-Null
    $local = (& git.exe -C $Repo rev-parse --verify --quiet "refs/heads/$b")
    if ($local -and $local -ne $sha) { Invoke-Git update-ref "refs/stack-backup/$stamp/local/$b" $local | Out-Null }
}
Write-Host "Backups: refs/stack-backup/$stamp/*" -ForegroundColor Cyan

if ($Mode -eq 'Auto') {
    $merges = ($Branches | ForEach-Object { [int](Invoke-Git rev-list --merges --count "$baseRef..$($orig[$_])") } | Measure-Object -Sum).Sum
    $Mode = if ($merges -gt 0) { 'Merge' } else { 'Rebase' }
    if ($merges -gt 0) { Write-Host "Stack contains $merges merge commit(s): using Merge mode (rebasing would flatten them)." -ForegroundColor Cyan }
}

# ---- merge mode: merge the updated branch below into each branch -------------
if ($Mode -eq 'Merge') {
    for ($i = 0; $i -lt $Branches.Count; $i++) {
        $b = $Branches[$i]
        $from = if ($i -eq 0) { $baseRef } else { $Branches[$i - 1] }
        Invoke-Git checkout -q -B $b $orig[$b] | Out-Null
        Write-Host "`n=== $b : merging $from ===" -ForegroundColor Cyan
        Invoke-MergeStep $from
    }
}

# ---- rebase mode: rebase each branch onto the (new) one below it ------------
for ($i = 0; $Mode -eq 'Rebase' -and $i -lt $Branches.Count; $i++) {
    $b = $Branches[$i]
    Invoke-Git checkout -q -B $b $orig[$b] | Out-Null

    if ($i -eq 0) {
        $onto = $baseRef
        $upstream = (Invoke-Git merge-base $orig[$b] $baseRef)
    }
    else {
        $prev = $Branches[$i - 1]
        $prevOld = $orig[$prev]
        $onto = $prev
        if (Test-Ancestor $prevOld $orig[$b]) {
            $upstream = $prevOld                       # normal linear stack
        }
        else {
            # Non-linear: branch was cut from an older copy of $prev.
            $mb = (Invoke-Git merge-base $orig[$b] $prevOld)
            $prevSubjects = @(Invoke-Git log --format=%s "$baseRef..$prev")
            $upstream = $mb
            $dropped = @()
            foreach ($line in @(Invoke-Git log --reverse --format='%H%x09%s' "$mb..$($orig[$b])")) {
                $h, $s = $line -split "`t", 2
                if ($prevSubjects -contains $s) { $upstream = $h; $dropped += "$($h.Substring(0,8)) $s" } else { break }
            }
            Write-Host "`n$b was cut from an older copy of $prev." -ForegroundColor Yellow
            if ($dropped) {
                Write-Host "Dropping $($dropped.Count) stale copied commit(s) already in ${prev}:" -ForegroundColor Yellow
                $dropped | ForEach-Object { Write-Host "  $_" -ForegroundColor DarkGray }
            }
        }
    }

    $own = (Invoke-Git rev-list --count "$upstream..$($orig[$b])")
    Write-Host "`n=== $b : replaying $own commit(s) onto $onto ===" -ForegroundColor Cyan
    if ($i -eq 0) {
        # plain form keeps git's "already applied upstream" detection (skips commits merged into base)
        Invoke-RebaseStep @($baseRef, $b)
    }
    else {
        Invoke-RebaseStep @('--onto', $onto, $upstream, $b)
    }
}

# ---- verify ----------------------------------------------------------------
$ok = $true
for ($i = 0; $i -lt $Branches.Count; $i++) {
    $below = if ($i -eq 0) { $baseRef } else { $Branches[$i - 1] }
    $good = Test-Ancestor $below $Branches[$i]
    $n = (Invoke-Git rev-list --count "$below..$($Branches[$i])")
    Write-Host ("{0,-4} {1}  (+{2} on top of {3})" -f ($(if ($good) { 'OK' } else { 'BAD' })), $Branches[$i], $n, $below) `
        -ForegroundColor ($(if ($good) { 'Green' } else { 'Red' }))
    $ok = $ok -and $good
}
$markers = @(& git.exe -C $Repo grep -l -E '^(<<<<<<<|>>>>>>>) ' $Branches[-1] -- 2>$null)
if ($markers) { Write-Host "Conflict markers left in: $($markers -join ', ')" -ForegroundColor Red; $ok = $false }
foreach ($b in $Branches) {
    # duplicated Markdown headings introduced by the update (typical "kept both" damage)
    foreach ($md in @(& git.exe -C $Repo diff --name-only $orig[$b] $b -- '*.md')) {
        $count = { param($rev) @(& git.exe -C $Repo show "${rev}:$md" 2>$null | Where-Object { $_ -match '^#{1,6} ' } |
                Group-Object | Where-Object Count -gt 1).Count }
        if ((& $count $b) -gt (& $count $orig[$b])) { Write-Host "Duplicated heading added in $md ($b)" -ForegroundColor Red; $ok = $false }
    }
}
if (-not $ok) { throw 'Stack verification failed; nothing pushed.' }
if ($script:AutoResolved.Count) {
    Write-Host "`nAuto-resolved conflicts (check each one keeps BOTH sides' intent):" -ForegroundColor Yellow
    $script:AutoResolved.GetEnumerator() | ForEach-Object { Write-Host "  $($_.Key)  [$($_.Value)]" -ForegroundColor Yellow }
    Write-Host "Review: git -C `"$Repo`" diff <backup-or-other-parent> <branch> -- <file>; bad replay: git rerere forget <file>" -ForegroundColor DarkGray
    if ($Push -and -not $AcceptAuto) {
        Write-Host 'Not pushing: auto-resolved conflicts need review. Re-run with -Push -AcceptAuto once checked.' -ForegroundColor Yellow
        $Push = $false
    }
}
# mark what this script produced, so a later run can tell it apart from hand-made commits on top
foreach ($b in $Branches) { Invoke-Git update-ref "refs/stack-result/$b" "refs/heads/$b" | Out-Null }

# ---- push ------------------------------------------------------------------
$leases = $Branches | ForEach-Object { "--force-with-lease=refs/heads/${_}:$($orig[$_])" }
$refs = $Branches | ForEach-Object { "refs/heads/${_}:refs/heads/${_}" }
if ($Push) {
    Invoke-Git push --atomic @leases $Remote @refs
    Write-Host 'Pushed.' -ForegroundColor Green
}
else {
    Write-Host "`nNot pushed. To push, re-run with -Push, or:" -ForegroundColor Cyan
    Write-Host "git -C `"$Repo`" push --atomic $($leases -join ' ') $Remote $($refs -join ' ')"
}
Write-Host "Undo: git -C `"$Repo`" branch -f <branch> refs/stack-backup/$stamp/<branch>"
