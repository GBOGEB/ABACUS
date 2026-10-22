# Ariana CI/CD — N-1, N, N+1 forecast vs actual and REX

**Date:** 2026-10-17. **Authority:** read-only ABACUS/DOW measurement and REX, not an SSOT.
**Admission:** HOLD; neither CODEX/KEB nor QPS child engineering acceptance transfers.

Sources: [Ariana PR #2138](https://github.com/GBOGEB/ABACUS/pull/2138),
[BD-LDAB issue #1929](https://github.com/GBOGEB/ABACUS/issues/1929), and
native GitHub Actions runs, job logs and artifact SHA-256 digests. Run clocks
are native GitHub timestamps, not a recreated timeline.

## N-series — original predictions and observed events

The original [run #215 / 39045383015](https://github.com/GBOGEB/ABACUS/actions/runs/39045383015),
SHA 54da377cf82a358ac97903ecde0270c975b8fcc1, failed before tests at a
nonexistent legacy work directory. It is a **pre-window anchor**, not a
comparable test-population point.

| Pulse | Exact-run SHA prefix and run | Original forecast frozen before the run | Observed native result | Local first-red family |
|---|---|---|---|---|
| N-1 | [1911ffbe / 39046522554](https://github.com/GBOGEB/ABACUS/actions/runs/39046522554) | [15:42:40 UTC](https://github.com/GBOGEB/ABACUS/issues/1929#issuecomment-6235955719): bypass missing workdir, no full-run PASS promised | Preflight passed; shared pytest fixture imports missing NumPy; both lanes fail precollection; tests/coverage N/A | NumPy missing — 1 distinct root, 2 job manifestations |
| N | [da5e6e03 / 39046770415](https://github.com/GBOGEB/ABACUS/actions/runs/39046770415) | [15:49:23 UTC](https://github.com/GBOGEB/ABACUS/pull/2138#issuecomment-6236070446): collect beyond NumPy, evidence not assumed | 28/28 tests per Python lane passed, but hidden-output uploader delivered zero durable files; join failed | Hidden artifact directory — 1 root, 3 job manifestations |
| N+1 | [ba3423f3 / 39046986905](https://github.com/GBOGEB/ABACUS/actions/runs/39046986905) | [15:51:53 UTC](https://github.com/GBOGEB/ABACUS/pull/2138#issuecomment-6236107400): visible artifacts and read-only join | 29/29 tests in each Python lane; 2 native archives + 1 join archive; native join PASS | None in Ariana CI; global gates still red |

Causal chain (distinct roots are not the same as failed-job manifestations):

- Pre-window PATH_MISSING -> N-1 NUMPY_FIXTURE -> N HIDDEN_ARTIFACT -> N+1 NO_NEW_ARIANA_ROOT.
- Two separate local first-red roots and five job manifestations across the three selected checkpoints.
- A run outcome is not global security, governance, reviewer or QPS acceptance.

## Matched numerator/denominator and forecast accuracy

| Measurement | N-1 | N | N+1 |
|---|---:|---:|---:|
| Tests passed per lane | N/A | 28/28 | **29/29** |
| Focused statement coverage | N/A | N/A | **208/209 (99.52%)** |
| Focused branch coverage | N/A | N/A | **39/42 (92.86%)** |
| Focused combined coverage | N/A | N/A | **247/251 (98.41%)** |
| Durable native lane artifacts | 0 | 0 | 2 |
| Local evidence-only federation join | Skipped | Failed | Passed |
| Whole-run wall time including queue | 104 s | 62 s | 269 s |

These test cohorts differ: a twelfth new test entered at N+1. The changed-line
denominator and cross-run matched coverage velocity are **UNKNOWN**, not zero.
The source DOW/Ariana module itself was not modified by PR #2138. Do not
credit raw 28-to-29 counts as comparable quality uplift, and do not treat
run-wall timing as equal-cost worker duration.

Source-bound artifacts from N+1:

- [Python 3.11 #12105478809](https://github.com/GBOGEB/ABACUS/actions/runs/39046986905/artifacts/12105478809), ZIP SHA256 a77a084de0b54654d5aaedc5143ea65c4c1e2ec8b61f7cba7f54f412437d9d67.
- [Python 3.12 #12106247295](https://github.com/GBOGEB/ABACUS/actions/runs/39046986905/artifacts/12106247295), ZIP SHA256 594e8de7a913f0ec2f98e8dcdee6855a389149ae4d3b79a5485237b31b0f6c70.
- [Joined federation #12106595934](https://github.com/GBOGEB/ABACUS/actions/runs/39046986905/artifacts/12106595934), ZIP SHA256 b541c6b7e1e14ea2aaf75b637b2ea7cb92f71a52aa6886b74d21c8596b600c7b.

The joined receipt has remote_keb_or_qps_receipts=null,
qps_engineering_acceptance=null and merge_admission=HOLD.

**REX predictive accuracy:** 3/3 *pre-run, source-repair milestone directions*
matched their target observations. This is not 3/3 whole-run successes.
The descriptive 95% Wilson interval is approximately 43.85% to 100%.
With only three selected, correlated interventions, no Six Sigma,
stabilization, PCA refit or Bradley-Terry pairwise ranking is justified.
None of the historical forecasts predeclared probabilities: Brier score
and log loss are **N/A**, not invented retrospectively.

## Feedback actions and pre-flight control

1. Validate actual checkout directories, entrypoints and referenced files
   before pip/test; the old path was a root, not a Python logic defect.
2. Collect fixture imports and dependencies, including imports in shared
   tests/conftest.py, before declaring the focused suite ready.
3. Check upload paths and published artifact IDs/digests, not merely whether
   test jobs created temporary local files; fail closed on missing artifacts.
4. Separate executable native DOW receipts from CODEX/KEB semantic receipts,
   QPS engineering acceptance, security scanning, review and policy.
5. On the next first-red, refreeze a scoped prediction before source mutation.
   Compare only matching source SHA, test cohort, coverage unit and denominator.

## Prospective N+2, pre-registered but NOT EXECUTED

[Forecast frozen 16:13:37 UTC in #1929](https://github.com/GBOGEB/ABACUS/issues/1929#issuecomment-6236426822):

- **Conditional local prediction:** if the source blob, 29-test cohort, Python
  3.11/3.12 dependencies and runners remain eligible and unchanged, expect
  29/29 passing per lane, with focused statements 208/209 and branches 39/42.
  Changing the population invalidates this estimate; refreeze first.
- **Independent mandatory gates:** predict HOLD until verified security fixes
  (safe XML parsing and immutable action references), CI workflow governance,
  required check success and independent human approval.
- **Federation:** QPS child and CODEX/KEB remote acceptance remain UNKNOWN
  without independently signed exact-source external receipts.

No N+2 observation, native run ID or numerical probability exists yet.
At least ten independently comparable *pre-registered* binary forecasts,
with explicit population and correlation checks, are required before
attempting calibration. Keep Brier/PCA/BT withheld here.

## Machine evaluation and repeatability

- Source pointers: [ARIANA_CI_N_SERIES_20261017.json](./ARIANA_CI_N_SERIES_20261017.json).
- Deterministic, standard-library and read-only evaluator:
  [scripts/ci/ariana_rex_prediction.py](../../scripts/ci/ariana_rex_prediction.py).
- Negative/positive tests:
  [tests/test_ariana_rex_prediction.py](../../tests/test_ariana_rex_prediction.py).

From the ABACUS root:

    python -m unittest discover -s tests -p test_ariana_rex_prediction.py -v
    python scripts/ci/ariana_rex_prediction.py --input triage/rex/ARIANA_CI_N_SERIES_20261017.json --format markdown

For independent ZIP replay after downloading the three GitHub archives:

    python scripts/ci/ariana_rex_prediction.py --input triage/rex/ARIANA_CI_N_SERIES_20261017.json --archives /path/to/native-zips --format json

The evaluator has no network, dispatch, merge or implicit write side effects.
An optional output file requires an explicit command-line argument. No
downloaded ZIP is asserted re-verified on a particular invocation unless
--archives is passed and the full SHA-256, exact head, run, attempt, lane,
JUnit count, coverage numerators and remote non-promotion checks pass.

**Owner actions:** ABACUS CI/security owners resolve new findings on
[PR #2138](https://github.com/GBOGEB/ABACUS/pull/2138) before admission.
CODEX/KEB remains semantic owner, and QPS remains engineering owner.
Do not merge this analysis PR or source PR without independent approvals
and exact-head security/governance proof.
