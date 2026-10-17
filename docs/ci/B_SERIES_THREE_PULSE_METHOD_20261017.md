# B-series three-pulse temporal metric engine

**Scope:** read-only, selected ABACUS B0 workflow observations from 17 October 2026. Native source: https://github.com/GBOGEB/ABACUS/blob/main/.github/workflows/mip-coverage-evidence.yml

**P0 admission: HOLD.** This is a nonrepresentative sample of exact-head GitHub receipts, not a federation census, independent risk review or autonomous worker action.

## Reproduce

From ABACUS root:
    python scripts/b_series_temporal_metrics.py --input docs/ci/B_SERIES_NATIVE_PULSES_20261017.json --json-out /tmp/bseries-report.json --markdown-out /tmp/bseries-report.md

    python -m unittest discover -s tests -p test_b_series_temporal_metrics.py -v

## Three native pulses

| Pulse | PR | Run ID | Successful jobs | Tests passed/skipped | Runtime (s) | B1 unguarded | Read-only DAB |
| --- | --- | --- | --- | --- | --- | --- | --- |
| N-2 | #2099 | 39024853388 | 13/13 | 2262/2 | 325.53 | 139 | 8/8 |
| N-1 | #2113 | 39028590924 | 13/13 | 2238/2 | 277.54 | 139 | 8/8 |
| N | #2099 | 39029208988 | 13/13 | 2263/2 | 322.81 | 139 | 8/8 |

Source SHA and all canonical job IDs, B1 job IDs and native artifact IDs are in the immutable input ledger. All runs are from distinct exact source SHAs; passing-test differences are not a same-population velocity.

## Metric hierarchy

Federation (UNKNOWN) -> ABACUS repo (sample; not all CI) -> MIP B0 workflow -> B0 canonical / B1 false-green / DAB proposal / B0 fan-in -> jobs and artifacts.

Weighted Producer Receipt Completeness Index (PRCI), not an engineering quality or security index:
- 40% B0 successful / eligible native jobs.
- 20% B1 successful native census with artifact (regardless of outstanding findings).
- 15% successful / eligible read-only DAB proposal workers.
- 25% successful final fan-in.

PRCI = 100/100/100 in this selected three-run sample. All weights must be available; absent data gives UNKNOWN, never redistributed weights or assumed zeros. Security, governance and review are non-compensating P0 gates and cannot be outweighed.

## Model identifiability and measured movement

- Sampled B0 workflow run success = 3/3. The 39 jobs are clustered in 3 runs, not 39 independent replicates.
- B1 false-green census = 139 / 139 / 139 unguarded findings. The workflow's ceiling of 267 is a threshold, not an elimination target. Identical scanner configuration digests have NOT been established: numerical stability observed, qualified velocity and acceleration UNKNOWN.
- Native pytest passing counts = 2262 / 2238 / 2263 across different PR code/test sets. Do not infer normalized growth from these.
- Native pytest runtimes = 325.53 / 277.54 / 322.81 seconds. Descriptive median = 322.81 s; MAD = 2.72 s. Not a controlled speedup experiment.
- Same-source statement/branch/changed-line coverage deltas, BD/root closures, cost-normalized yield, prospective forecast error, fleet shares and authenticated Crew dispatch are UNKNOWN.
- B2+ was not seen as distinct jobs in this B0 workflow, which is not a global nonexistence proof.

## SIPOC and DAG

Source: exact PR commits, native run/job/attempt and artifacts.
Input: source SHA, census configuration, execution and test receipts.
Process: source pin -> verify denominators/provenance -> B0/B1/DAB census -> fan-in -> temporal projection -> optional #2106 chronology gate -> optional #2113 matched coverage gate -> governed review.
Output: portable source-bound JSON hierarchy and Markdown readout.
Controls: BD/LDAB #1929 root attribution, #1860 P0 admission, independently enforced Safety/governance/security and review.

A forecast must be registered before its outcome; no retroactive forecast error is credited here. No waiver, REX, governed main merge or engineering-root closure is implied.
