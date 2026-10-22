# CBD W+2 — Canonical queue crosswalk (17 October 2026)

Source-of-truth owner: [BD–LDAB #1929](https://github.com/GBOGEB/ABACUS/issues/1929). This checkpoint is an **observational append-only sidecar**, not a second SSOT.

| Measure | Observed | Provenance |
|---|---:|---|
| Declared failed workflow rows | 78 | 6PR + 10PR-A + 10PR-B manifests |
| Distinct failed run IDs | 66 | 12 exact aliases removed |
| Total / current sampled PR heads | 20 / 18 | native PR API; #2080 and #2033 moved |
| Authentic terminal failed latest attempts | 63 | native run IDs, pull-head SHA, PR binding, workflow and attempt |
| Full jobset readbacks | 66 / 66 | native job API with run-attempt/head SHA |
| Failed jobs / failed steps | 125 / 135 | latest-attempt native job/step census |
| First failed step observed | 64 / 66 | first failed step is not a confirmed causal root |
| Downloaded sampled first-red logs | 23 / 66 | jobs explicitly sampled, not all 66 |
| Shared Matplotlib resolver signatures | 13 across 8 PRs | 13/13 candidate install-step logs |
| Verified causal-root closures | 0 | not yet integrated/accepted |
| Comparable statement / branch coverage | UNKNOWN | do not substitute test counts |

**Priority BD root:** incompatible Matplotlib Python 3.10 resolver. Existing source owner [PR #2026](https://github.com/GBOGEB/ABACUS/pull/2026). Observed in 13 native job logs affecting PRs #2027, #2037, #2039, #2041, #2072, #2074, #2075, #2080. Separate governance/security/formatter root gates remain active.

**SIPOC/DAG:** source manifests → live run readback → run-attempt + head-verified jobset → first failed step → job-log signature → source owner → isolated integration retest → governed admission. Exactly **two disjoint writer leases** at most; read-only log scouts may fan out independently. No waiver; no acceptance without native current-head checks.

**Efficiency:** 66 run + 66 job native REST readbacks and 23 targeted job-log retrievals. Metadata and step census coverage are 66/66; targeted log coverage is 23/66; 13/23 sampled logs confirm this shared resolver signature (selection-biased, not an unbiased fleet proportion). No synthetic improvement in CI pass rate is claimed.

**Data caution:** the 533 workflow associations / 66 failures in 20 source manifests are non-atomic and are not an eligible global pass-rate denominator for the combined union.

[Full raw observation evidence](https://github.com/GBOGEB/ABACUS/pull/2092#issuecomment-6232367720) · [Stacked PR #2092](https://github.com/GBOGEB/ABACUS/pull/2092) · [Source owner #2026](https://github.com/GBOGEB/ABACUS/pull/2026).

**Admission: HOLD.** No merge, security waiver or independent review.
