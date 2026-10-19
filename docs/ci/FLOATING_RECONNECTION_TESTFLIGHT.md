# ABACUS floating-code local testflight

Status: candidate testflight, not merge or engineering authority.

This lane extends existing TestPilot and DAB/W104 source discovery.
It never treats path matches as runtime reachability or orphan proof.

## Preconfiguration on Windows

Install the existing developer environment and pre-commit hooks:

```powershell
python -m pip install -r requirements-dev.txt
pre-commit install
.\scripts\testpilot.ps1 -Mode fast -Floating
```

The `-Floating` switch runs the existing fast TestPilot first.
It then invokes the new, standard-library unittest control suite.
Any failing stage remains nonzero. Existing gate floors are untouched.

The pre-commit hook `abacus-floating-staging-testflight` runs when
floating-method or matching test files are staged. It runs without
using a network service and does not write source fixes.

## Frozen forecast before running the selected tests

Commit the source under test before generating a source-bound forecast.
Do not label a dirty worktree's uncommitted bytes with HEAD.

```powershell
$head = (git rev-parse HEAD).Trim()
New-Item -ItemType Directory -Force .testpilot/floating | Out-Null
python tools/triage/floating_testflight.py forecast `
  --head $head --pulse 1 `
  --out .testpilot/floating/forecast.json
```

The forecast file is created exclusively; an existing one is not
overwritten. The seal and UTC issue time are checked on read.

Without a prior qualified observation, forecasts are UNKNOWN.
A previous observation permits persistence estimates, not
statistical certification.

## Scoped staging test and evidence collection

Run selected tests with measured branch coverage:

```powershell
python -m pytest -q -o addopts= `
  tests/test_coverage_dab_census.py `
  tests/test_floating_evidence_join.py `
  tests/test_mip_pulse_rollup.py `
  tests/test_floating_testflight.py `
  --cov=scripts.coverage_dab_census `
  --cov=tools.triage.floating_evidence_join `
  --cov=tools.triage.mip_pulse_rollup `
  --cov=tools.triage.floating_testflight `
  --cov-branch `
  --cov-report=json:.testpilot/floating/coverage.json `
  --junitxml=.testpilot/floating/junit.xml
```

Regardless of the test result, record the observed state:

```powershell
python tools/triage/floating_testflight.py observe `
  --forecast .testpilot/floating/forecast.json `
  --junit .testpilot/floating/junit.xml `
  --coverage .testpilot/floating/coverage.json `
  --out .testpilot/floating/observation.json

python tools/triage/floating_testflight.py review `
  --forecast .testpilot/floating/forecast.json `
  --observation .testpilot/floating/observation.json `
  --out .testpilot/floating/review.md
```

Local observations have UNKNOWN native job and artifact IDs.
They cannot independently establish completed GitHub CI runs.

## GitHub native pulse and reviewer package

The workflow `floating-reconnection-testflight.yml` validates an
exact checkout. It publishes the frozen forecast artifact before
running the focused suite. It subsequently publishes JUnit, scoped
coverage, observation, control status, toolchain and review summary.

The GitHub job summary is reviewable without extra write tokens.
Artifact size reported by GitHub is not ZIP CRC/member verification.

The existing `testpilot-preflight.yml` remains independent,
alongside canonical B0, quality, Safety, A10 and review controls.
The method never changes those required gates.

## Rolling decision and second-phase quiet mode

One GitHub run/attempt counts at most once. Rereading a run is not
a new pulse. Repeated local tests in one runner are not independent
native attempts.

- A RED restarts first-red attribution before adding tests.
- A changed source population or instrumentor requires rebaselining.
- Matched positive coverage gains continue the ranked test campaign.
- Three matched transitions with uncovered opportunities cause
  reranking rather than a false success declaration.
- Four distinct, terminal, same-scope native runs with zero skips,
  no RED and 100% focused statement and branch coverage may become
  `QUIET_WATCH_CANDIDATE`.

Quiet mode stops unnecessary *local* intensive retesting only after
independent admission evaluation. The scheduled read-only watch
continues and restarts on source changes, drift, new consumers,
first-red regressions or coverage loss.

A quiet candidate does not mean full-repository 100% coverage,
independent review, security waiver, root closure or release readiness.

## Source-bound evidence boundaries

The workflow's branch/statement denominators apply only to its
four selected source modules. Match source file hashes, eligible
opportunities, tool version and test selection before interpreting
coverage movement. Do not pool this scope with W46, main B0,
a QPS module or a federation census.

M1 remains partial; M2, M3, PCA and Bradley-Terry release
qualification remain on HOLD until independent populations and
sufficient longitudinal evidence are available.


## Instrumentor census rule

The targeted suite instruments the entire `tools/triage` source directory,
not only modules imported during test collection. This intentionally
exposes unused code and test-support files, which increase the eligible
measurement population. Coverage never silently drops the
`mip_pulse_rollup.py` module merely because it was pre-imported by
the test harness. The explicit CI guard requires four core modules plus
`floating_anchor_census.py` to be present and executed; other measured
files remain visible as separate candidates and are not silently removed.
A scope change creates a new baseline; avoid naive percentage comparisons.
