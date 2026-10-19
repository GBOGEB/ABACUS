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
    python -m unittest -q tests.test_floating_testflight tests.test_mip_v3_frontier tests.test_mip_v3_temporal tests.test_floating_accelerator_receiver tests.test_floating_rollup_adversarial
    exit $LASTEXITCODE
}
exit 0
