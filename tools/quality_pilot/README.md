# Code Quality Pilot (open source, report-only)

Goal: **measure** whether static analysis earns its keep on ABACUS before
anything new is gated. Nothing in this pilot can fail a merge.

## What it adds (and what it deliberately does not)

ABACUS already runs CodeQL, Semgrep (`p/python`, `p/owasp-top-ten`, `p/secrets`),
Bandit, Ruff security and Dependabot. The pilot does **not** re-run those. It adds:

| Tool | Gap it closes | Licence |
|---|---|---|
| gitleaks (full history, redacted) | Semgrep `p/secrets` sees the current tree only | MIT |
| pip-audit | Dependabot opens PRs but gives no CVE baseline count | Apache-2.0 |
| mypy on `models` + `DMAIC_V3/core` | no type checking on physics/orchestration core | MIT |
| mypy-focus (burn-in only) | strict scan of `models/` (`--check-untyped-defs --warn-unreachable --strict-equality`) | MIT |
| Opengrep + `rules/ssot.yml` | SSOT / EOS-adapter / patch-counter governance | LGPL-2.1 |
| code-scanning import | precision of the **existing** CodeQL/Semgrep/Bandit alerts | — |

## Cadence

| Phase | When | Extras |
|---|---|---|
| burn-in | first `BURN_IN_RUNS` (=10) **scheduled** runs, **daily** 05:17 UTC (PR/manual runs do not consume it) | focused scan + run-over-run trend |
| steady | afterwards, **Mondays** only (other days skip in ~5 s) | — |
| manual | `workflow_dispatch` or a PR touching pilot files | focused scan + trend |

Change `BURN_IN_RUNS` in the workflow `env:` to extend or shorten burn-in.

## Telemetry (per run, in the `quality-pilot-N` artifact)

- `telemetry.json` — schema `gbogeb-quality-pilot-telemetry/1.0.0`: per tool
  findings, top rules, seconds, exit code, tool version; run number; phase.
- `trend.md` — burn-in table, findings per tool across runs, classified
  `stable` / `falling` / `rising — investigate` / `fluctuating — check determinism`.
- `summary.md` — also posted to the job summary.
- `triage_sample.csv` — 20 findings, stratified per tool, new seed each run.

Scheduled and manual runs also post this digest as a comment on the standing issue
**"Quality pilot — burn-in telemetry"** (created on first scheduled run), so every
burn-in run produces a readable notification. Pilot PRs post no comment: their
token stays read-only and the digest goes to the job summary instead.

Exit codes are recorded honestly (`timed.sh` returns the scanner's own code).
All advisory steps carry `# rex-allow: ADVISORY_EXPLICIT` and pass
`scripts/ci_false_green_lint.py` with zero unguarded findings.

## Protocol (DMAIC)

1. **Define** — scope is the table above; rule excludes are mapped to
   `models/helium_properties/` (EOS adapter) and `**/ssot/**`.
2. **Measure** — burn-in runs 1–10 build the baseline + trend automatically.
3. **Analyze** — triage each run's `triage_sample.csv`: set `verdict`
   (`TP`/`FP`/`NOISE`/`WONTFIX`) and `minutes`, then
   `python tools/quality_pilot/pilot_summary.py score triage_sample.csv`.
4. **Improve** — tune or drop rules the score marks low-precision.
5. **Control** — gate only what earned it:

| Score result | Action |
|---|---|
| gitleaks / pip-audit with ≥1 real hit | gate immediately |
| precision ≥ 50 % | gate **new code only** (ratchet) |
| 20–50 % | stay report-only, tune |
| < 20 % | drop or rewrite the rule |

Thresholds: `GATE_PRECISION`, `TUNE_PRECISION` in `pilot_summary.py`.

## Placement

Pilot lives in ABACUS (System Under Test). After Control, promote to CODEX as a
reusable `workflow_call` (CODEX = automation) and call it from ABACUS and
cryoplant-project.

## Known unverified points

- Opengrep install path and `scan --test` were not executed in the authoring
  sandbox (network-blocked); the PR run of this workflow is the first execution.
- gitleaks uses `:latest` during the pilot; pin a digest before gating.
