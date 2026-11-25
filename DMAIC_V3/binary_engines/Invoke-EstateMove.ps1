<#
.SYNOPSIS
  Apply inventory\MOVE_PLAN.csv. Dry run unless -Execute. Moves only rows with action=MOVE.
  Re-checks sha256, Office lock and destination before each move and writes an undo log.
.EXAMPLE
  Set-Location "<ABACUS checkout>"
  .\DMAIC_V3\binary_engines\Invoke-EstateMove.ps1              # dry run, prints the summary
  .\DMAIC_V3\binary_engines\Invoke-EstateMove.ps1 -Execute     # moves, writes <ESTATE_HOME>\inventory\UNDO_<stamp>.csv
  .\DMAIC_V3\binary_engines\Invoke-EstateMove.ps1 -Undo "$env:ESTATE_HOME\inventory\UNDO_<stamp>.csv"
#>
[CmdletBinding()]
param([switch]$Execute, [string]$Undo, [string[]]$Types, [string]$RootId = 'MI')
$ErrorActionPreference = 'Stop'
# data home, same rule as estate_spec.ESTATE: ESTATE_HOME, else ~/.binary_estate (never inside the repository)
$estate = if ($env:ESTATE_HOME) { $env:ESTATE_HOME } else { Join-Path $HOME '.binary_estate' }
# same rule as estate_spec.inv_dir: MI -> inventory, others -> roots/<id>/inventory; the root path comes from the inventory itself
$inv  = if ($RootId -eq 'MI') { Join-Path $estate 'inventory' } else { Join-Path (Join-Path (Join-Path $estate 'roots') $RootId) 'inventory' }
$root = (Get-Content -LiteralPath (Join-Path $inv 'root_inventory.json') -Raw | ConvertFrom-Json).root

if ($Undo) {
  $log = Import-Csv -LiteralPath $Undo
  [array]::Reverse($log)
  foreach ($r in $log) {
    $from = Join-Path $root $r.dest; $to = Join-Path $root $r.src
    if ((Test-Path -LiteralPath $from) -and -not (Test-Path -LiteralPath $to)) { Move-Item -LiteralPath $from -Destination $to }
    else { Write-Warning "undo skipped: $($r.dest)" }
  }
  return
}

$plan = Import-Csv -LiteralPath (Join-Path $inv 'MOVE_PLAN.csv') | Where-Object { $_.action -eq 'MOVE' }
if ($Types) { $plan = $plan | Where-Object { $Types -contains $_.type } }
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$undoLog = Join-Path $inv "UNDO_$stamp.csv"
$done = New-Object System.Collections.Generic.List[object]
$skip = @{}
foreach ($r in $plan) {
  $src = Join-Path $root $r.src; $dst = Join-Path $root $r.dest
  $why = $null
  if (-not (Test-Path -LiteralPath $src)) { $why = 'missing' }
  elseif (Test-Path -LiteralPath $dst) { $why = 'dest_exists' }
  elseif ((Test-Path -LiteralPath (Join-Path $root ('~$' + $r.src))) -or (Test-Path -LiteralPath (Join-Path $root ('~$' + $r.src.Substring([Math]::Min(2, $r.src.Length)))))) { $why = 'locked' }
  elseif ($r.sha256 -and (Get-FileHash -LiteralPath $src -Algorithm SHA256).Hash.ToLower() -ne $r.sha256) { $why = 'changed_since_inventory' }
  if ($why) { $skip[$why] = 1 + [int]$skip[$why]; continue }
  $row = [pscustomobject]@{ src = $r.src; dest = $r.dest; sha256 = $r.sha256 }
  if ($Execute) {
    try {
      New-Item -ItemType Directory -Force -Path (Split-Path $dst) | Out-Null
      Move-Item -LiteralPath $src -Destination $dst -ErrorAction Stop
    } catch [System.IO.IOException] {
      $skip['in_use'] = 1 + [int]$skip['in_use']; continue   # held by another process (open app, sync, preview)
    }
    # log each move the moment it happens: an interrupted run is always undoable
    $row | Export-Csv -LiteralPath $undoLog -NoTypeInformation -Encoding UTF8 -Append
  }
  $done.Add($row)
}
"{0}: {1} files {2}; skipped {3}" -f ($(if ($Execute) {'EXECUTE'} else {'DRY RUN'})), $done.Count,
  ($(if ($Execute) {"moved, undo log $undoLog"} else {'would move'})), (($skip.GetEnumerator() | ForEach-Object { "$($_.Key)=$($_.Value)" }) -join ', ')
