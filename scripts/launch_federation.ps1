<#
.SYNOPSIS
    DELTA_1 federation launcher (PowerShell) for GBOGEB/CODEX, GBOGEB/ABACUS and
    GBOGEB/cryoplant-project.

.DESCRIPTION
    Locates the three federation repos under configurable local roots (default
    C:/repos and C:/DEV), runs each repo's entry points (shared bridge status +
    native smoke), and optionally opens the HTML portals. Read-only / smoke only;
    never mutates governed SSOT.

.PARAMETER Roots
    One or more local root folders to search. Default: C:/repos, C:/DEV.

.PARAMETER OpenHtml
    Also open each repo's HTML portals in the default browser.

.PARAMETER NoSmoke
    Skip running the native smoke entry points.

.EXAMPLE
    ./launch_federation.ps1
    ./launch_federation.ps1 -Roots 'C:/repos','C:/DEV','D:/work' -OpenHtml
#>
param(
    [string[]]$Roots = @('C:/repos', 'C:/DEV'),
    [switch]$OpenHtml,
    [switch]$NoSmoke
)

$ErrorActionPreference = 'Continue'
$repos = @('CODEX', 'ABACUS', 'cryoplant-project')

function Find-Repo {
    param([string]$Name)
    foreach ($root in $Roots) {
        if ([string]::IsNullOrWhiteSpace($root)) { continue }
        $candidate = Join-Path $root $Name
        if (Test-Path $candidate) { return $candidate }
    }
    return $null
}

Write-Host '== DELTA_1 federation launcher ==' -ForegroundColor Cyan
Write-Host ("roots: " + ($Roots -join ', '))

foreach ($repo in $repos) {
    Write-Host ''
    Write-Host "---- $repo ----" -ForegroundColor Yellow
    $path = Find-Repo -Name $repo
    if (-not $path) {
        Write-Host '  NOT FOUND under roots (adjust -Roots)' -ForegroundColor Red
        continue
    }
    Write-Host "  path: $path"
    Push-Location $path
    try {
        python -c 'import delta1_bridge' 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host '  [bridge] status:'
            python -m delta1_bridge status --repo-root .
        } else {
            Write-Host '  [bridge] delta1_bridge not importable here (vendor it or set PYTHONPATH)'
        }

        if (-not $NoSmoke) {
            switch ($repo) {
                'ABACUS' {
                    Write-Host '  [smoke] DMAIC_V3 self-smoke:'
                    python -m DMAIC_V3 self-smoke *> $null
                    if ($LASTEXITCODE -eq 0) { Write-Host '    OK' } else { Write-Host '    (needs deps)' }
                }
                'cryoplant-project' {
                    Write-Host '  [smoke] federation_smoke.py:'
                    python scripts/federation_smoke.py *> $null
                    if ($LASTEXITCODE -eq 0) { Write-Host '    OK' } else { Write-Host '    (needs deps)' }
                }
                'CODEX' {
                    Write-Host '  [smoke] pca_engine tests:'
                    Push-Location pca_engine
                    python -m pytest -q *> $null
                    if ($LASTEXITCODE -eq 0) { Write-Host '    OK' } else { Write-Host '    (needs deps)' }
                    Pop-Location
                }
            }
        }

        if ($OpenHtml) {
            foreach ($html in @('docs/index.html', 'docs/bridge_overview.html', 'qps/engineering_hub/site/index.html')) {
                if (Test-Path $html) {
                    Write-Host "  [html] opening $html"
                    Start-Process (Resolve-Path $html)
                }
            }
        }
    }
    finally {
        Pop-Location
    }
}

Write-Host ''
Write-Host 'done.' -ForegroundColor Green
