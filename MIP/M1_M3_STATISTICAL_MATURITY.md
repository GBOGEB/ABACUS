# CODE PURPLE MIP M1–M3 statistical admission

This is a **read-only diagnostic producer**, not merge or worker authority.

## Seven series families

| Family | Native metric contract | Backtest target |
| --- | --- | --- |
| ci_reliability | terminal failed workflow / terminal workflow; recovery duration requires start+end | next-wave red incidence |
| bd_burndown | native verified opened/closed/reopened root transitions; proposal excluded | next-wave net root backlog |
| coverage | covered/eligible statements and branches with same denominator definition | next-head covered opportunity delta |
| debug_ldab | validated exact SHA/run/job/fingerprint matches / accepted native sessions | held-out linkage precision |
| evidence_quality | valid/fresh receipts / required receipts; UNKNOWN separately | held-out missing/stale receipt rate |
| repair_effectiveness | verified first-pass accepted fixes / evaluated native repairs | held-out reopen/regression incidence |
| throughput | verified root closures / measured native worker-hours | held-out validated closures per hour |

The initial data file contains only real terminal `ci_reliability` observations. Other families remain missing, **not zero**. Native exact head, UTC event time, metric version, run/job identity, and source URL are mandatory. A repeated CI job is not an independent observation.

## Admission decision policy

M1 `MEASUREMENT_VALID` requires complete, nonduplicated, matched native observations. M2 `STABILITY_ASSESSABLE` requires at least 20 independent runs as an initial screening rule. `PROCESS_STABLE` remains false until a separately justified chart and special-cause review exists. M3 `CAPABILITY_ASSESSABLE` remains false until specifications, suitable distribution and stability are verified. `BACKTEST_ELIGIBLE` is only a diagnostic flag for sufficiently long, consistent-denominator, weakly-autocorrelated series with a five-point forward holdout, **not predictive certification**.

The current simple holdout is a last-observation baseline and reports MAE; for incident prediction, future editions must additionally report Brier/log-loss and calibration; for backlog and throughput, rolling origin count errors with exposure. No same-run training and testing, no random shuffles, and no denominator switching.

## Next collection / fanout

First collect independent, time-ordered CI measurements across subsequent runs; do not replay the same head to synthesize independent samples. Then add BD transition receipts, coverage artifact-byte extraction, debugger/LDAB native session receipts, evidence freshness and worker-hour provenance. Compute change-point and control chart signals only after sufficient comparable history. Explicitly keep security A10, BLACK/ISORT, Bandit/Safety and eligible review separate.

Deployment must preserve `merge_admission=HOLD`. Missing data, failed collection, and missing native OS/REX evidence remain UNKNOWN, never silent zero.
