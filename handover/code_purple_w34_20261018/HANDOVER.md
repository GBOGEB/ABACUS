# CODE PURPLE W34 — GitHub-first operational lossless handover

**Status: MERGE_ADMISSION = HOLD; DMAIC_STABLE = NOT_PROVEN; NATIVE_W34 = NOT_RUN.**
Observed and assembled 18 October 2026, timezone Europe/Brussels. This is a dated, non-atomic GitHub source readback and continuation packet, not a complete verbatim chat export or a sealed/replayed LOSSLESS_HANDOVER_V2 capsule. All unverified quantities remain UNKNOWN/null.

## 0. Authority, method and restart

- Canonical owner register: [ABACUS issue #1860](https://github.com/GBOGEB/ABACUS/issues/1860); historical CBD W10 [comment 6214640143](https://github.com/GBOGEB/ABACUS/issues/1860#issuecomment-6214640143).
- Existing template: [HANDOVER_MESSAGE_TEMPLATE.md](../../handover/HANDOVER_MESSAGE_TEMPLATE.md).
- Existing V2 specification: [process_spec.json](../../tools/handover_v2/process_spec.json), input schema and generator. **This packet is GITHUB_FIRST_OPERATIONAL, not V2_SCHEMA_AND_REPLAY_VERIFIED**; it lacks independently archived complete source/raw bytes.
- Existing restart protocol: [LOSSLESS_RESTART_PROTOCOL_V1.md](../mip/LOSSLESS_RESTART_PROTOCOL_V1.md).
- Existing BD/LDAB authority: ABACUS #1929, including the historic root register. No counted PR is itself a closed root.
- Required recensus on next session: actual default branches, exact main/PR heads, reviews, rules and bypass actors, latest run/job/attempt/step and artifact bytes, source/test/config hashes, coverage populations, issue states.

## 1. Five-repository snapshot crosswalk (observation, not federation acceptance)

| Repository | Resolved default | Observed source SHA | Depth |
|---|---|---|---|
| [ABACUS](https://github.com/GBOGEB/ABACUS) | main | `994ad6e73c748923841d92b12651e92d41b2d4ff` | Exact head observed |
| [CODEX](https://github.com/GBOGEB/CODEX) | main | `774d51eb4a58fa259f059764e586d12a7935b2e1` | Head observed only |
| [cryoplant-project](https://github.com/GBOGEB/cryoplant-project) | main | `fc07545c3986181a1b837c0eb7ff9a8393fd4058` | Head observed only |
| [pipeline-automation-hub](https://github.com/GBOGEB/pipeline-automation-hub) | master | `339bee59cf790498408be19e9c7deb092cc51738` | Head observed only |
| [gg_MATH](https://github.com/GBOGEB/gg_MATH) | main | `6d5310280740e50fe7fbe45712ca62e2dee0c36b` | Head observed only |

No authenticated CODEX Crew, receiver-approved QPS, or REX return was verified. Source metadata is not authorization. A private QPS blob must not be copied into a public handover.

## 2. Immutable B0/first-red time spine

| Epoch | Main HEAD | Exact native run/attempt/job | Numerator/denominator | Disposition |
|---|---|---|---|---|
| W31 | `0dd018768f46dbfecf8aad872776d4ba3f6d4fc8` | [B0 39156907500](https://github.com/GBOGEB/ABACUS/actions/runs/39156907500), a1, job `117762201715` | 11/13 jobs PASS; 4,781 pytest PASS, 2 FAIL, 2 SKIP | FAIL; NumPy/G3CS independently diagnosed |
| W32 | `405e161d0090bbe94a33e298fb031b6cdbc92cb0` | [CI/CD 39159216550](https://github.com/GBOGEB/ABACUS/actions/runs/39159216550), a1, seven listed jobs in HISTORY.json | 7 manifestations of one missing NetworkX root | Historical only; #2272 later merged |
| W34 | `994ad6e73c748923841d92b12651e92d41b2d4ff` | [B0 39159906022](https://github.com/GBOGEB/ABACUS/actions/runs/39159906022), a1; canonical [job 117771668289](https://github.com/GBOGEB/ABACUS/actions/runs/39159906022/job/117771668289); report [job 117773239113](https://github.com/GBOGEB/ABACUS/actions/runs/39159906022/job/117773239113) | 11/13 jobs PASS; 3,854 pytest PASS, 3 FAIL, 1 SKIP | Current snapshot FAIL; derivative report-only job FAIL |

**New first-red:** the optional historical W10 ZIP test in `MIP/G3CS_CONVERGENCE_V2/observatory/w10/test_w10_spine.py` has two pytest markers of type `TEST_BLOCKED_SOURCE_MISSING` and a skip reason of `TEST_BLOCKED_DEPENDENCY`. Three source-contract assertions fail. **Three failing tests → one typed source root, not three independently closed roots.** Synthetic archive integrity tests are retained and no optional ZIP is fabricated. W34-C stages a single marker and required reason; exact-head native qualification is still unknown.

**Previous W32 weakness:** `tools/recovery/w32_runner_telemetry.py` promoted caller-supplied JUnit/ZIP verification booleans to `verified_successful_evidence` without reading bytes. W34-B changes those fields to null and moves claims to `source_reported_positive_claims`. A new independent ZIP/JUnit/coverage verifier exists with 18 locally passing adversarial fixtures, but no authentic GitHub artifact has been fetched and qualified through it.

## 3. W34 three-pronged disjoint source-owner implementation

| Lane | Exact staged branch / code commit | Changed paths and DoD | DoV and next evidence |
|---|---|---|---|
| A — CI dependency | [w34-matrix-networkx-sourceowner](https://github.com/GBOGEB/ABACUS/tree/code-purple/w34-matrix-networkx-sourceowner-20261018), `f5dd75a2055b58e67e0d42de3b56a3e013a2488f` | `requirements-test.txt` adds NetworkX 3.4.2 on 3.10 and 3.6.1 on >=3.11; five contract tests in `tests/test_w34_matrix_networkx_dependency.py`; does not remove collection or exclusions | Real Windows/macOS/Ubuntu 3.10–3.12 matrix, no NetworkX first-red, bounded exact-head artifacts |
| B — evidence integrity | [w34-proof-verified-handover](https://github.com/GBOGEB/ABACUS/tree/code-purple/w34-proof-verified-handover-20261018), verifier commit `793631257ce9594c0f0e94263189e051471214e0` | W32 telemetry claim demotion, W32 test adjustments, new `w34_native_artifact_verify.py` and 18 adversarial test cases; source/test Git blob SHA matched local | 18/18 LOCAL synthetic PASS; same cases plus actual ZIP bytes, run/job/attempt and scope must be verified in native CI |
| C — G3CS contract | [w34-g3cs-single-source-missing-marker](https://github.com/GBOGEB/ABACUS/tree/code-purple/w34-g3cs-single-source-missing-marker-20261018), `fa2616cb2323f21f430095bbbb793ba9d89e1b19` | Removes the redundant decorator, retains optional wrapper and typed source-missing skip, fixes the reason; no suppressed tests | Prior three targeted failures must pass on exact head with full B0 proof; optional archive absence remains blocked, not green |

Three branches are intentionally **not PRs and are not merged**. No workflow dispatch, native re-run, waiver, review approval or settings change was made by W34. This avoids the observed earlier automated merge burst while the effective gate is unqualified. Do not auto-open PRs unless the owner verifies real protections or explicitly authorizes a bounded secure submission with independent review.

## 4. DMAIC source/metrics (DoD != DoV != admission)

**Define:** first-red signatures and source ownership above. **Measure:** 12 open ordinary PRs, 38 open ordinary issues at API readback; do not count them as 12/38 causal roots. **Analyze:** source → exact SHA → run → attempt → job → first-red root → repair branch → artifact proof → consumer, with reference/feedback arcs non-authoritative. **Improve:** A, B, C with negative controls and no culling. **Control:** exact-source fresh native JUnit, denominator-matched branch/statement coverage, full Safety/Bandit/A10/governance/review rules, RED canary and post-merge exact-main proof.

| Metric | Prior / historical basis | W34 observed | Eligible delta |
|---|---|---|---|
| Current B0 job success | W31 11/13 at a DIFFERENT main SHA | 11/13 at `994ad6e7` | NO: comparable source/test/config not established |
| Current B0 failing testcase population | W31 2 FAIL/4,785 elements, different suite | W34 3 FAIL; 3,854 PASS / 1 SKIP | NO: different denominator |
| Disjoint owned slices staged | 0 for this W34 baseline | 3 branches / 7 touched source+test paths | Engineering output, not verified root closure |
| Verified local synthetic byte-verifier tests | 0 | 18/18 | LOCAL_SYNTHETIC only |
| Current-main statement+branch matched uplift | UNKNOWN | UNKNOWN | UNKNOWN |
| Unique formal BD root closures | UNKNOWN | UNKNOWN | NO credit |
| Queue p95 / execution p95 | UNKNOWN with matched job population | UNKNOWN | Cannot calculate |
| Eligible human approvals on W34 source branches | None requested | 0 verified | No admission |

**Rolling forecasts:** see [FORECAST.json](FORECAST.json). Predictions are conditional and frozen before any W34 native source-head outcome. W34-C: target three contract assertions resolved; W34-A: target zero NetworkX collection errors on 9-cell matrix; W34-B: re-run 18 negative tests and independently verify actual ZIP bytes. No proposed target becomes an observed PASS by being written in this file.

## 5. P0 independent admission control (unchanged)

Current effective [ruleset #24494381](https://github.com/GBOGEB/ABACUS/rules/24494381) on main: **0 required approvals, 0 required status-check rules, last-push approval OFF, resolved threads OFF, stale-review dismissal ON, 6 always-bypass integrations**. Branch-protection details returned HTTP 403 (UNKNOWN), despite `protected=true` metadata. No observed server-side rejected RED canary or eligible independent review. #1860 remains OPEN with previously recognized **1/12** obligations.

An authorized administrator must restore required contexts (PR Feedback Gate, policy-and-inventory, ABACUS compatibility gate, plus source-relevant security/B0), >=1 eligible independent approval, last-push/review-thread safeguards, controlled bypasses and real blocked-RED canary. **No test code, self-attestation or archived ZIP substitutes for these settings.**

Safety/CVE new-debt and A10 remain separately fail-closed; historical scanner 6,607 findings are occurrences, not proven current-app exposure or distinct roots. Preserve nonzero Safety; a legitimate security reviewer must approve any root disposition.

## 6. Dependency DAG / owner gates

Read [EVIDENCE_GRAPH.json](EVIDENCE_GRAPH.json) and [DAG.mmd](DAG.mmd). Key critical path:

`ADMIN_RULES -> blocked_RED_CANARY -> eligible_HUMAN_REVIEW -> exact_HEAD_SECURITY+B0 -> authorization -> main_SHA_READBACK -> matched_MAIN_COVERAGE+root_disposition`.

Technical tasks A/B/C are source-disjoint and may undergo local QA in parallel; they must not merge or claim governed admission without the independent gate.

## 7. Next bounded G3P, STOP and Six Sigma limit

**Pulse N+1 (P0)**: administrator verifies protections and rejects RED canary. In parallel, independently inspect finished queued work; **do not replay unchanged deterministic failed SHA**. If controls remain ineffective or queue nonterminal, HOLD, no PR and no new runner fan-out.

**Pulse N+2 (conditional)**: stage owner review on A/C after protections are restored; at most 6 fresh qualified native cells in one budgeted flight, and preserve full 9-cell CI matrix as an independent gate, not a substitute for the budget.

**Pulse N+3 (conditional)**: prove the B verifier against API-identified ZIP bytes and member SHA-256; reconcile 18/18 focused local tests to native JUnit and exact source; compare matched statement+branch opportunities; allow serial controlled merge only with all P0 gates, review and exact HEAD. Record N+1/N+2 predicted/actual without rewriting earlier forecast.

**STOP_LOCAL_PLATEAU** only after at least three independent **comparable, fully terminal, byte-verified zero-value transitions**, equal source/scope/instrumentor and a stationary measured queue/root population; a repeated poll of one SHA is not an independent wave. High queue or unknown proof is **HOLD_CAPACITY** not a statistical plateau. **Six Sigma is NOT proven**: a simple independent zero-defect Bernoulli 95% one-sided upper bound at 3.4 DPMO requires >=881,097 independently verified defect-free opportunities and stationarity assumptions, not mere absence of recent failures. This does not certify Cp/Cpk, process variance, or deployment quality.

## 8. Operational TODO and escalation

| Priority | Blocker / owner | Current state | Next linked action |
|---|---|---|---|
| P0 | #1860 admin hard rules and RED canary | OPEN, protection detail API 403 | [ABACUS ruleset](https://github.com/GBOGEB/ABACUS/rules/24494381) / independent admin action |
| P0 | B0 G3CS root | 3 failed cases; W34-C staged, no native proof | [B0 run](https://github.com/GBOGEB/ABACUS/actions/runs/39159906022) and G3CS source branch |
| P1 | Broad CI NetworkX | Historical 7 failures, #2272 dev-pin merged; broad test-pin staged | [CI run 39159216550](https://github.com/GBOGEB/ABACUS/actions/runs/39159216550) / W34-A branch |
| P1 | W32 proof integrity | False promotion of supplied flags | W34-B verifier + native ZIP/member checks |
| P1 | Security/A10 and human reviewers | UNQUALIFIED | Get exact-head native receipts and real reviewer identity |
| P2 | CODEX/QPS federation | HEAD-observed only | Authenticated sender/consumer and owner decision |
| P2 | Broad root/coverage | UNKNOWN same-scope denominators | Compare only identical source blobs, instrumentor and coverage scopes |

## 9. Handover fidelity, manifest and replay

[STATE.json](STATE.json) and [HISTORY.json](HISTORY.json) preserve quantitative and source-lineage claims; [FORECAST.json](FORECAST.json) preserves forecasts; [DROPIN.md](DROPIN.md) provides exact receiver commands; [TEMPLATE.md](TEMPLATE.md) maps the canonical seven-section published template to this cohort. [MANIFEST.json](MANIFEST.json) is a **GitHub blob-index release receipt**, not a cryptographically authenticated V2 replay seal. Full V2 generation needs validated handover input, complete declared raw evidence bytes, SHA256 plus independent replay under the existing generator; that evidence archive is not available here. Do not describe this as full verbatim conversation recovery.

No private files, tokens or user-uploaded raw bytes were copied into these public GitHub documents. Do not copy prompt/session internals into repository history.
