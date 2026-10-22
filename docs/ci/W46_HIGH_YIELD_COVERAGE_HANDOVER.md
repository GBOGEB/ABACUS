# CODE PURPLE W46 — high-yield source coverage execution / DOV triage

**Evidence date: 18 October 2026 (UTC source timestamp).**
**DoD implemented; full native W46 DoV pending; MERGE_ADMISSION = HOLD.**
This is a source-owned report and restart hook, not a new authority or a protected merge.

## 1. Verified N to N+1, identical W34 artifact-verifier source

Read-only owner [W34 verifier](../../tools/recovery/w34_native_artifact_verify.py) Git blob `3c1249dc54e74ab0cb0f4ea3ebebe216ad2c650a`. [W46-A new tests](https://github.com/GBOGEB/ABACUS/blob/test/cbd-w46-zip-failclosed-100pct-20261019/tests/test_w46_zip_negative_coverage.py) on separate disjoint branch.

| Fixed-source local measurement | N | N+1 | Qualified local gain |
|---|---:|---:|---:|
| Test cases PASS / total | 18/18 | 45/45 | +27 adversarial cases |
| Statements | 104/111 | 111/111 | +7 visited |
| Branches | 16/16 | 16/16 | Equal, already saturated |
| Combined opportunities | 120/127 | 127/127 | **+5.511811 pp** |
| Independent GitHub-native W46 verification | UNKNOWN | UNKNOWN | Not claimed |
| Governed merge/root closure | 0 | 0 | HOLD |

The newly exercised code paths are JSON decoding exceptions, corrupt ZIP CRC, malformed XML and invalid/missing JUnit headers. Additional negative/reverse cases check duplicate identities, unsafe scope paths and false approval metadata. One intermediate fixture failed because the external scope and embedded receipt differed; the fixture was corrected, and 45/45 passed at final local readback. That failure is preserved as a developer test correction, not as a repo source defect.

**LOCAL SATURATION:** 127/127 on the unchanged source means there is no further statement+branch opportunity in this exact scope. Stop this lane and transfer worker attention to ranked uncovered modules. This is not DMAIC stability or Six Sigma certification.

## 2. Exact current-main native B0 proof and yellow action

GitHub main source `2687f2bcb0705027eefe04df789365d6c9970678`. [Native B0 run 39170902976](https://github.com/GBOGEB/ABACUS/actions/runs/39170902976), attempt 1, **13/13 terminal successful jobs**. Canonical job `117803544289`. Canonical test census: **5,155 PASS / 5,158**, 3 governed skips, zero failed; one source-missing optional external ZIP remains BLOCKED rather than falsely green.

B0 ZIP artifacts independently downloaded, raw SHA-256 checked against GitHub digests:
- #12152488350 canonical: `5bfe091ca1150d22664574b9d33843e445227b05255eb2ed576a27c135cc61d1`
- #12152671934 report-only: `54d79a3ff5e25b6698a02e792b3a299cf35ce7fc24bfb4a1189486fffe805301`
- #12152970363 aggregation: `3e51193b5e3e41aa946b81b0580c92ed38d399cf6857a0da59a811420b4ab7c8`

Native full measurement from `coverage-dab.json` within the report-only ZIP:
- **Statements:** 7,779 / 22,456 = 34.641076%
- **Branches:** 1,651 / 5,558 = 29.704930%
- **Combined:** 9,430 / 28,014 = 33.661741%
- **Missing:** 18,584 opportunities.
- `active_source` subset is distinct (7,720/21,248 = 36.3328%) and must not be added to the full population.

**Yellow denominator UNKNOWN -> RESOLVED for this exact source and B0 scope.** Global coverage remains inadequate; across-head uplift is UNKNOWN without path/config/instrumentor parity. The older W38 focused 707/723 result is a different population, not a direct denominator comparison.

## 3. High-yield disjoint source-owner gap scouting

Using the byte-verified report's `coverage-contexts.json`, the [W46-B read-only scorer](../../tools/recovery/w46_gap_census.py) reconciled **223 measured paths**, of which **114 had zero executed coverage** in this B0 population. Its **16/16 synthetic adversarial census tests** passed. The top six disjoint owners total **1,768 missed opportunities**, or **9.51% of 18,584 missing**. Full theoretical saturation would be +6.31 percentage points on the frozen 28,014 denominator, **not a forecast**.

See [machine-readable ranked snapshot](W46_HIGH_YIELD_COVERAGE_SCOUT.json). Priority source targets:

1. `DMAIC_V3/debug_pipeline.py` — 469 missed, sandbox-only diagnostic/fault oracles
2. `cicd_github_orchestrator.py` — 406 missed, dry-run/no-dispatch protocol negatives
3. `models/qps_line_s/closure_contract.py` — 342 missed, QPS owner-extraction and invalid-receipt tests
4. `mission_control_lite/coverage_pulse.py` — 276 missed, exact-SHA matched counts and attempt telemetry
5. `core/execution_backbone/backbone.py` — 142 missed, event/replay rollback boundaries
6. `rich_padding/markdown_reader_engine.py` — 133 missed, corrupt parser and boundary cases

These are **uncovered within this B0 measurement**, not proven untested across all CI matrices. Proposed distinct paths are staging lanes only. Do not dispatch the six automatically.

## 4. Red governance action: NOT CLOSED

[Effective ruleset 24494381](https://github.com/GBOGEB/ABACUS/rules/24494381) still has 0 mandatory approvals, 0 mandatory required-status rules and six always-bypass integration actors. Last-push and review-thread enforcement disabled; branch protection detail could not be authoritatively read, and no server-side rejected RED canary or eligible independent human approval is proved. Observed GitHub merges are not controlled-admission evidence. [Canonical issue #1860](https://github.com/GBOGEB/ABACUS/issues/1860#issuecomment-6214640143) remains owner SSOT.

P0 authorized administrator must restore effective required contexts including PR Feedback Gate, policy-and-inventory, ABACUS compatibility and security/B0 applicability; enable 1+ truly independent eligible review, review/thread/last-push rules, narrow bypasses, and demonstrate rejected RED canary. Security/A10/Safety independently remain fail-closed. **No waiver, settings mutation, merge, owner attestation or remote dispatch was performed in W46.**

## 5. DOV and DMAIC control

- **L0:** five-repo HEAD observations only, federation receipt not authenticated
- **L1:** current-main B0 workflow/job success verified; W46 new source-branch native runs pending
- **L2:** three B0 artifact ZIP digests checked, inner evidence SHA reconciled; no proof of future W46 source branch
- **L3:** QPS/CODEX/REX owner signature and independent security disposition unknown
- **L4:** governed admission HOLD
- **L5:** main-wide matched coverage gain and causal root closure unproven

Stop local ZIP-verifier expansion at 100% identical-source statement+branch saturation; do not confuse a local saturation with statistically stable process. To claim 3.4 DPMO one-sided 95% with zero defects would require >=881,097 genuinely independent defect-free opportunities and separate stationarity validation; no such claim is made.

## 6. Resume / next bounded wave

Read current main/branches, #1860 and ruleset fresh. Deduplicate any PR owners, especially W40-W44 parser/QPS/telemetry drafts. Next root-owned candidates are DMAIC diagnostics, CI dry-run orchestration and Mission Control Lite telemetry. Execute local fault tests on isolated workspaces; require fresh exact-head native proof before credit. Do not rerun unchanged deterministic failed SHA, launch high-volume matrices or auto-merge with governance P0 unresolved. Maintain the source graph:
`artifact_id -> SHA256 byte readback -> exact_main_sha -> coverage-contexts -> disjoint file owner -> test branch SHA -> exact-head run/job/attempt -> permitted reviewer -> serial governed merge -> current-main matched scope`.

If three consecutive independent terminal *comparable* waves yield no measurable root or coverage gain, stop that local lane and choose a new source family. That is STOP_LOCAL_PLATEAU, **not** global stable Six Sigma.
