# B-series N+2: native fingerprint stability and scope diagnosis

Date: 17 October 2026. Repository: GBOGEB/ABACUS.
Control boundary: read-only GitHub-native observations.
**P0 admission: HOLD.** No source-owner or review authority changes.

## Five native pulses

| Pulse | Run | Jobs | Tests passed | B1 findings | Scanned files |
| --- | ---: | ---: | ---: | ---: | ---: |
| N-2 | 39024853388 | 13/13 | 2262 | 139 | 160 |
| N-1 | 39028590924 | 13/13 | 2238 | 139 | 161 |
| N | 39029208988 | 13/13 | 2263 | 139 | 160 |
| N+1 | 39046191707 | 13/13 | 2229 | 139 | 160 |
| N+2 | 39047236023 | 13/13 | 2262 | 139 | 160 |

All five runs have distinct source SHAs. The ledger preserves these.
Run/job/artifact receipts are frozen in the N+2 JSON data file.
These are five selected B0 runs, not five independent CI populations.

## New observable: exact B1 fingerprint persistence

Native B1 jobs report 186 total findings: 47 allowed, 139 unguarded.
All five scans have the same 139 unguarded finding fingerprints.
One historical scan covered 161 files; the other four covered 160.

Fingerprint key: workflow path, source line, pattern names, text.
Exact baseline intersection: 139/139 on each of the five runs.
New fingerprints: zero observed. Missing fingerprints: zero observed.
The complete reference atoms and source job links are preserved in
docs/ci/B_SERIES_B1_FINGERPRINT_CENSUS_20261017.json.

## Statistical meaning

Raw B1 event-count velocity per hour is zero across four intervals.
Observed fingerprint Jaccard overlap equals one across all five.
Those are descriptive estimates of detector output persistence.

Finding intensity is an observable count per scanned workflow file.
It is not test coverage, a defect probability, or a success fraction:

- N-1 intensity = 139 / 161, about 0.86335 findings/file.
- Other intensities = 139 / 160, or 0.86875 findings/file.

The single extra scanned workflow affects the measurement population.
An unchanged count and identity set cannot establish full scope
equivalence, a Six Sigma defect rate, or causal code-health stability.

Native canonical test runtime is also descriptive across PR heads:
325.53, 277.54, 322.81, 305.18, 226.46 seconds.
Median = 305.18 seconds; median absolute deviation = 20.35 seconds.
Test selection and source are not identical across these heads.

Source-qualified B0 sample jobs pass 65/65 across 5 selected runs.
This does not overrule full CI, Safety, Python compatibility or A10.
The existing weighted producer receipt index remains distinct from
any code-health, root-closure, or main admission score.

## DAG and SIPOC

Source: exact PR heads, B0/B1 native jobs, versioned artifacts.
Inputs: test reports, scanner/workflow blobs, finding fingerprints.
Process: PIN -> CENSUS -> MATCH -> INTERSECT -> TREND -> REVIEW.
Outputs: five-pulse KPI JSON and null-safe forecast hypothesis.
Controls: #1929 BD roots, #2106 chronology, #2113 matched coverage,
#1860 independent P0 admission and required human/security gates.

Only qualified source/config comparisons enter temporal differences.
Missing denominators, unproven launches and roots remain UNKNOWN.
Do not turn a successful GitHub Action into a MissionControl launch.

## Forecast and next admissible scale

Conditional persistence hypothesis for N+3: 139 B1 findings.
The proposed model has no calibrated uncertainty distribution.
Forecast error remains UNKNOWN until an independently subsequent
native result is observed against a preserved pre-outcome forecast.

Next expand to six and then eight terminal source-bound flights.
Require stable scope and test cohort identities for comparisons.
Preserve the N-2 to N+1 data untouched; append versioned leaves.
Do not declare stabilized engineering risk or formal root closure.
