# CODE PURPLE MIP M1–M3 statistical admission

This is a **read-only diagnostic producer**, not merge or worker authority.

## Seven series families

| Family | Native metric | Backtest target |
| --- | --- | --- |
| ci_reliability | Failed / terminal workflows | Red incidence |
| bd_burndown | Verified root transitions | Net root backlog |
| coverage | Covered / eligible | Covered delta |
| debug_ldab | Matched / accepted sessions | Linkage precision |
| evidence_quality | Valid / required receipts | Missing/stale rate |
| repair_effectiveness | Accepted / evaluated fixes | Reopen incidence |
| throughput | Closures / native worker-hours | Closures per hour |

For ci_reliability, recovery duration requires start and end timestamps.
For bd_burndown, count opened, closed, and reopened verified roots only;
exclude proposals. For coverage, statement and branch denominator
definitions must match. For debug_ldab, matches require exact SHA,
run, job, and fingerprint. For evidence_quality, use valid and fresh
receipts; keep UNKNOWN separate. For repair_effectiveness, count only
verified first-pass accepted repairs. For throughput, use verified root
closures and measured native worker-hours.

The initial data file contains only real terminal ci_reliability
observations. Other families remain missing, **not zero**. Native exact
head, UTC event time, metric version, run/job identity, and source URL are
mandatory. A repeated CI job is not an independent observation.

## Admission decision policy

M1 MEASUREMENT_VALID requires complete, nonduplicated, matched native
observations. M2 STABILITY_ASSESSABLE requires at least 20 independent
runs as an initial screening rule. PROCESS_STABLE remains false until a
separately justified chart and special-cause review exists. M3
CAPABILITY_ASSESSABLE remains false until specifications, suitable
distribution, and stability are verified.

BACKTEST_ELIGIBLE is only a diagnostic flag for sufficiently long,
consistent-denominator, weakly-autocorrelated series with a five-point
forward holdout, **not predictive certification**.

The current simple holdout is a last-observation baseline and reports
MAE. For incident prediction, future editions must additionally report
Brier/log-loss and calibration. For backlog and throughput, they must
report rolling-origin count errors with exposure. No same-run training
and testing, no random shuffles, and no denominator switching.

## Next collection / fanout

First collect independent, time-ordered CI measurements across
subsequent runs; do not replay the same head to synthesize independent
samples. Then add BD transition receipts, coverage artifact-byte
extraction, debugger/LDAB native session receipts, evidence freshness,
and worker-hour provenance. Compute change-point and control chart
signals only after sufficient comparable history. Explicitly keep
security A10, BLACK/ISORT, Bandit/Safety, and eligible review separate.

Deployment must preserve merge_admission=HOLD. Missing data, failed
collection, and missing native OS/REX evidence remain UNKNOWN, never
silent zero.
