<!-- markdownlint-disable MD013 MD060 -->

# G3A W16 — Bounded DMAIC/MIP KPI charter and source-epoch qualification

**Evidence class:** SOURCE_BOUND_CANDIDATE · **Admission:** HOLD.
This is one deliberately bounded implementation wave, not a global capability
certificate, main-branch merge, or proof of formal root closure.

## 1. Measurement identity and historical split

The verified historical N13→N14 same-source series is **115/446 → 200/446**
(+85 distinct reached arcs, zero lost). Concurrent Phase 4 source repair
changed the eligible population for the later branch epoch from 134 to 132.
The first W16 epoch (`G3A_W16_V2_PHASE4_REPAIRED`) therefore used **444
four-module eligible branches** (116/132/118/78) and 164 workflows, with no
arithmetic N14→W16 slope or coverage uplift unless the same current source is
measured twice. Historical source-bound gg_MATH input remains historical and
must not silently consume new W16 measurements.

### 1a. Canonical epoch manifest and re-pin (current: V3)

The pinned epoch now lives in one file,
[`MIP/statistics/g3a_w16_epoch.json`](statistics/g3a_w16_epoch.json), read by
the preflight, the KPI contract and both native workflows. When main moves a
pinned file or the workflow population, `scripts/g3a_w16_repin.py --repin`
records the new blobs and the workflow census mapped to policy
cluster/lifecycle sub-categories, clears the affected denominators, and the
native workflows print `W16_MEASURED` records while the epoch is pending;
`--measured` pins denominators **only** from those native records.

Main moved Phase 8 (`e9e4edd4`→`d5ab3ea1`, dd0946fa) and the CI/CD
orchestrator (`2e0f80b8`→`82a9a707`, c856600b/f8c48f18) and grew the
workflow population 164→214, so V2 can no longer be reproduced. Epoch
**`G3A_W16_V3_MAIN_44CACCF7`** (pinned from main `44caccf7`) was re-measured
in full natively — N15 run `39798543241`, coverage.py 7.16.2, Python 3.10
and 3.12 identical:

| File | Sub-category | Eligible | Covered | Floor |
|---|---|---:|---:|---:|
| `DMAIC_V3/debug_pipeline.py` | carried (blob unchanged) | 116 | 94 | 94 |
| `DMAIC_V3/phases/phase4_improve.py` | carried (blob unchanged) | 132 | 51 | 42 |
| `DMAIC_V3/phases/phase8_todo_management.py` | main drift, re-pinned | 118 | 63 | 63 |
| `cicd_github_orchestrator.py` | main drift, re-pinned | 98 | 23 | 23 |
| **Four KPI modules** | | **464** | **231** | |
| `scripts/g3a_bounded_mission.py` | control (separate) | 116 | 105 | 105 |

231/464 is a **new-epoch baseline**, not an uplift over 444 or over the
historical 200/446: the orchestrator's population changed (78→98), so no
cross-epoch delta is computed. Workflow census at the pin: 214 workflows, 212
classified, 2 `UNCLASSIFIED` (`code-quality-pilot.yml`, `nextjs.yml`, main
drift fixed by #2375; re-pin the census after it merges).

Source preflight checks exact-head identity, the pinned source digests, policy
classification and sub-category mapping of all workflows, and the deterministic
generated inventory **before** installing the Python test environment.

## 2. Five authoritative KPI families — all other values are diagnostics

| KPI | Unit / estimator | W16 interpretation | Acceptance guard |
|---|---|---|---|
| K1. Matched branch coverage | `k / d`, uncovered `d-k` | Four pinned W16 modules; V3 `d=464`, native `k=231` (§1a); V2 `d=444` historical | Same source/tool/denominator |
| K2. Native proof yield | Verified focused receipts / attempted exact-head testflights | A complete native testflight can contribute one proof; project-wide yield remains N/A | Run/attempt/head and 121+ passing cohort |
| K3. Causal-root burndown | Verified closed unique causal roots / identified unique roots | **Zero credited** until owner proof and exact-head CI; symptom disappearance ≠ root closure | Independent owner disposition |
| K4. Time to evidence | Test execution seconds; job queue/run p50/p95 when timestamps exist | N15 red run wall ~1,055 s, but it never measured coverage; queue wait is UNKNOWN | Distinguish queue/run/step clocks |
| K5. Statistical CONTROL readiness | Equivalence of recent same-scope slopes; independent repeats | NOT ESTIMABLE from N13/N14 or one W16 epoch | Targeted interventions, independent receipts, confidence interval and blocker-free window |

**Not core KPIs:** raw workflow count, line count, click count, job totals,
test-count growth, PCA PC1 percentage, BT ranking scores, synthetic DPMO,
and cross-epoch percentage change. Record them only as scoped diagnostic
inputs or when a validated decision makes them relevant.

MIP/3P* mapping: **Modernize** = repair verified first-red/source
contracts and cost of avoidable CI; **Innovate** = source-bound telemetry and
fail-closed preflight; **Perpetuate** = only after repeated valid execution,
governance, independent review, and controlled re-entry. DMAIC:
Define/Measure the population; Analyze root vs failure manifestation; Improve
with bounded owner changes; CONTROL only after comparable temporal proof.
gg_MATH remains provider of PCA/BT/equivalence mathematics; CODEX/KEB own
semantic acceptance independently. PCA on N13/N14 `n=2,p=4` is
unqualified; BT has no recorded real independent pairs; Six Sigma is NOT
ASSESSABLE from passing tests or branch coverage.

## 3. Speed and scalability safeguards

Native W15 G3A N15 run `39048395974` was created at 16:12:28Z and reached
failure at 16:30:03Z (**1,055 s end-to-end**, not isolated queue time).
Its first material failure was stale Phase 4 hash before test execution.
W16 brings this check ahead of Python provisioning; speed improvement is
**forecast only** until W16 exact-head native receipts are terminal.
Do not extrapolate any p95 from one run.

Native evidence is generated using existing workflow jobs; **no new
workflow** is introduced. Keep at most four source modules and one bounded
source-frozen test cohort while requalifying. Increase to a fifth module only
if all first-red/root/stability and time-budget checks are satisfied and
the runner/job capacity can support another disjoint cohort. New tests are not
proof of better coverage until exact branch arcs are obtained.

## 4. Fail-closed operations and gates

Local PowerShell / shell pre-push:
`python scripts/g3a_w16_preflight.py --root . --expected-head <40-character-HEAD> --out test_reports/n16/preflight.json`

Native W16 uses `.github/workflows/g3a-n14-matched-arc-flight.yml` and
the already-present Python 3.10/3.12 cross-version workflow, both requalified
for Phase 4 blob `18bec7...`. W16 emits:
`test_reports/n16/preflight.json`,
`test_reports/n16/n16_receipt.json` and
`test_reports/n16/w16_kpis.json`. All source-related statistics must be
replaced by actual current-head receipts once terminal, not by a planned
test count or a visual dashboard estimate.

Unresolved independent blockers remain until authenticated:
Python 3.10 matplotlib incompatibility and any new security/A10 failures.
No reruns, waivers, main merge, break-glass exception, QPS acceptance,
source-root closure, or gg_MATH provider promotion are inferred by this charter.

**Control gate:** `MERGE_ADMISSION=HOLD`; `NEXT_SCALE=HOLD` unless the
exact-head testflight is terminal and its current-epoch coverage population
has been recensused and reviewed.

## 5. Acceptance / stop rules

1. Static local source/governance preflight returns PASS on current head.
2. Existing native tests reach >=121 actual tests, all PASS, and match the
   pinned epoch manifest exactly (V3: 464 eligible source branches, 116
   separate control branches, coverage.py 7.16.2, floors held).
3. New source-epoch phase4 fixes preserve the externally specified reason
   `No unused imports` without weakening AST import-preservation rules.
4. Native governance, security, full compatibility and reviews must succeed
   independently before any admission discussion.
5. A second W16 source-frozen independent observation is needed before a
   W16→W16 change can be claimed. Stability requires still more evidence.
