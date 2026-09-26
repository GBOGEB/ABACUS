param(
    [ValidateSet("fast", "full", "gate")]
    [string]$Mode = "fast",
    [switch]$Fix,
    [switch]$All,
    [double]$CoverageFloor = -1
)

$ArgsList = @("scripts/testpilot_preflight.py", "--mode", $Mode)
if ($Fix) { $ArgsList += "--fix" }
if ($All) { $ArgsList += "--all" }
if ($CoverageFloor -ge 0) {
    $ArgsList += @("--coverage-floor", $CoverageFloor.ToString([Globalization.CultureInfo]::InvariantCulture))
}

python @ArgsList
exit $LASTEXITCODE
