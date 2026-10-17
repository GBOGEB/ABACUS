# B-series three-pulse temporal metric engine

Scope: read-only ABACUS B0 workflow, 17 October 2026.
Source: .github/workflows/mip-coverage-evidence.yml.
Mode: selected historical GitHub receipts, not a fleet-wide census.
**P0 admission: HOLD.** No Crew launch or root closure is implied.

## Reproduce

From the repository root, run the following commands:

```sh
python scripts/b_series_temporal_metrics.py \
  --input docs/ci/B_SERIES_NATIVE_PULSES_20261017.json \
  --json-out /tmp/bseries-report.json \
  --markdown-out /tmp/bseries-report.md
python -m unittest discover -s tests \
  -p test_b_series_temporal_metrics.py -v
```

## Three pinned native pulses

- N-2, PR #2099, run 39024853388:
  13/13 jobs PASS; 2262 tests PASS; 2 skipped;
  runtime 325.53 s; B1 raw findings 139; DAB proposals 8/8 PASS.
- N-1, PR #2113, run 39028590924:
  13/13 jobs PASS; 2238 tests PASS; 2 skipped;
  runtime 277.54 s; B1 raw findings 139; DAB proposals 8/8 PASS.
- N, PR #2099, run 39029208988:
  13/13 jobs PASS; 2263 tests PASS; 2 skipped;
  runtime 322.81 s; B1 raw findings 139; DAB proposals 8/8 PASS.

The input ledger holds source SHAs, native job IDs and artifact IDs.
Each pulse has a distinct PR source SHA; test cohorts are unmatched.

## Hierarchy and weighted composite

Federation (UNKNOWN) -> ABACUS (sample only) -> B0 workflow.
Leaves: B0 canonical, B1 false-green, DAB proposal, B0 fan-in.

Producer Receipt Completeness Index (PRCI) weights:

- B0 successful native jobs / eligible jobs: 0.40.
- B1 successful census job and available artifact: 0.20.
- DAB read-only proposal jobs successful / eligible: 0.15.
- B0 final evidence fan-in completed successfully: 0.25.

Observed PRCI = 100 / 100 / 100 across three selected flights.
This does NOT indicate zero security risk, accepted code quality,
engineering closure or permission to merge to main.
Missing components make the composite UNKNOWN: no reweighting.

## Temporal interpretation

- Run success: 3/3 selected flights; jobs are clustered in runs.
- B1 findings: 139 -> 139 -> 139; same config digest unverified.
- Pytest passing: 2262 -> 2238 -> 2263; cohorts are unmatched.
- Runtime: 325.53 -> 277.54 -> 322.81 seconds.
- Median runtime: 322.81 s; descriptive MAD: 2.72 s.
- Coverage uplift, per-test velocity and acceleration: UNKNOWN.
- Root leverage, accepted yield, queue p95 and fleet share: UNKNOWN.
- No prospective forecast was issued before these observations.
- B2+ absent as named jobs in this B0 workflow, not globally disproven.

## SIPOC and non-compensating governance

Source: native repository commits, runs, jobs and artifacts.
Input: exact SHA, configuration, test outcomes and receipts.
Process: PIN -> VALIDATE -> B0/B1/DAB -> FAN-IN -> TEMPORAL.
Next: #2106 temporal qualification, then #2113 matched coverage.
Output: machine JSON hierarchy and readable Markdown report.
Control: #1929 BD/LDAB, #1860 P0, security and independent review.

All unknown engineering counts remain null, never numeric zero.
No waiver, REX, Crew dispatch or main admission is claimed.
