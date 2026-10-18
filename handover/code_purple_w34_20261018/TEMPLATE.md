# W34 field map to canonical published GitHub-first handover template

This is a cohort-specific overlay, **not** another schema, standalone source of truth, waiver, evidence generator or admission authority.

Canonical parents: [HANDOVER_MESSAGE_TEMPLATE.md](../HANDOVER_MESSAGE_TEMPLATE.md), [LOSSLESS_HANDOVER_V2 process spec](../../tools/handover_v2/process_spec.json), [LOSSLESS_RESTART_PROTOCOL_V1](../mip/LOSSLESS_RESTART_PROTOCOL_V1.md).

| Canonical template section | W34 source | Required restart QA |
|---|---|---|
| 1. Snapshot identity/fidelity | STATE.json: five-repo crosswalk, SHA, data classes | Resolve live branches and tag stale SHAs HISTORICAL |
| 2. Source-owned G3P N to N+3 | HISTORY.json + three staged branches | Unique exact SHA, run/job/attempt, authentic ZIP and no queued=green |
| 3. DMAIC/MIP metrics/forecasts | HANDOVER.md section 4 + FORECAST.json | Numerator/denominator, identical statement/branch scope or null |
| 4. DAG and SIPOC | EVIDENCE_GRAPH.json + DAG.mmd | Dependency vs reference arcs; no implicit dispatch authority |
| 5. P0 governance | STATE.json.governance and issue #1860 | Check mandatory contexts, review, bypass, A10/Safety and server RED canary |
| 6. TODO/BD/DoD/DoV | HANDOVER.md section 8 | Typed first-red, source owner, next direct linked action |
| 7. Receiver/QA | DROPIN.md, QA_REPORT.json, MANIFEST.json | Replay only when full verified V2 evidence/raw bytes exist |

## Mandatory successor fields

SOURCE_SHA, PR_HEAD_SHA, PR_BASE_SHA, CURRENT_MAIN_SHA, RULESET_SHA_OR_UPDATED_AT,
RUN_ID, RUN_ATTEMPT, JOB_ID, STEP_FIRST_RED, STATUS, CONCLUSION, ARTIFACT_ID,
ZIP_SHA256, INNER_SHA256, JUNIT_ACTUAL_CASES, JUNIT_PASS/FAIL/SKIP,
STATEMENTS_COVERED/ELIGIBLE, BRANCHES_COVERED/ELIGIBLE,
INSTRUMENTOR_CONFIG_HASH, ROOT_FINGERPRINT, ROOT_MANIFESTATIONS,
ROOT_OWNER_DISPOSITION_OR_NULL, QUEUE_P95, EXECUTION_P95, PROOF_YIELD,
EXPECTED_N_PLUS_1, OBSERVED_N_PLUS_1, FORECAST_ERROR,
P0_ADMIN_RULES, ELIGIBLE_APPROVAL, REJECTED_RED_CANARY,
MERGE_ADMISSION=HOLD, SECURITY_WAIVER=false, AUTHORITY_TRANSFER=false.

Null is not zero. Same PR across two GitHub heads is two snapshots, not the same verified case.

## Acceptance state ladder

SOURCE_PREPARED -> LOCAL_SYNTHETIC_QA -> NATIVE_EXACT_HEAD -> BYTE_VERIFIED_CONSUMER -> GOVERNANCE_ELIGIBLE -> GOVERNED_MAIN_MERGE -> POST_MAIN_MATCHED_METRICS.

W34-A: SOURCE_PREPARED. W34-B: LOCAL_SYNTHETIC_QA (18/18, local synthetic only). W34-C: SOURCE_PREPARED. All subsequent stages: HOLD or UNKNOWN.

## Negative controls for every N+1

1. Reject foreign SHAs, wrong run attempts or job IDs and missing/falsified artifact bytes.
2. Reject JUnit header inflation, skips/failed/errors and duplicate case identities.
3. Reject branch coverage omissions, changed scope, mismatched counters and fake denominators.
4. Do not count GitHub merge as protected admission or issue close as causal root closure.
5. Retain scanner nonzero and A10; do not allow review-comment bots to satisfy human approval.
6. Compare identical source/instrumentor/denominator before reporting a percentage-point gain.
7. Three independent byte-verified zero-gain comparable transitions can stop a local branch, not imply Six Sigma process capability.
8. Verify full V2 input schema plus raw file archive replay before calling a package V2 sealed.
9. Preserve old native failures as immutable observations, including source SHA and time.
10. Do not create new PRs or native fan-out while admission controls or queue capacity remain unproven.
