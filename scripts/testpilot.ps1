param(
    [ValidateSet("fast", "full", "gate")]
    [string]$Mode = "fast",
    [switch]$Fix,
    [switch]$All,
    [switch]$Floating,
    [double]$CoverageFloor = -1
)

$ArgsList = @("scripts/testpilot_preflight.py", "--mode", $Mode)
if ($Fix) { $ArgsList += "--fix" }
if ($All) { $ArgsList += "--all" }
if ($CoverageFloor -ge 0) {
    $ArgsList += @("--coverage-floor", $CoverageFloor.ToString([Globalization.CultureInfo]::InvariantCulture))
}

python @ArgsList
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if ($Floating) {
    python -m unittest -q tests.test_floating_testflight
    exit $LASTEXITCODE
}
exit 0
