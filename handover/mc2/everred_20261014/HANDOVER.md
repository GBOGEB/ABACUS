# CODE PURPLE / EVERRED — LOSSLESS OPERATIONAL CONTINUATION

**Historical cut:** 14 Oct 2026. **ABACUS main:** `85dad8fbdab530d40e6ccf2f664c455f89454aad`; protected=true at readback. This document is a **GitHub-first restart pointer**, NOT an authorization, an immutable complete chat transcript, or proof that every prior attachment is archived.

## What the conversation was actually trying to achieve
1. Global EVERRED canonical first-red elimination rather than repair every red PR independently; disjoint root owner/worker lease, producer proof, downstream replay, governed merge.
2. BD issue queue vs scanner/CI findings vs canonical roots vs GitHub workflow runs/jobs vs real runner/CREW allocation, each with separate denominator and exact run/attempt/SHA receipt.
3. Reduce repeated PR Feedback Gate evaluator fan-out with asymmetric producer completions, source/policy SHA epoch, append-only receipts, genuine cancellation-to-successor links and fail-closed all-mandatory-evidence barrier.
4. Improve current CODE PURPLE/EVERRED **V3** viewer with richer rows: colored STATUS and TRIGGER badges, subtle zebra and left status rail, keyboard hover/focus/inspector, grouped/collapsed repeats, local/UTC created time, safe actions, mobile/readability QA; NEVER create a competing UI SSOT.
5. Preserve practical handover plus HTML/PDF/code regeneration sources after closing this ChatGPT conversation, with GitHub pointers preferred to zip blobs.

## Source hierarchy / active owners
- [#1877 queue, delayed proof and asynchronous fan-in](https://github.com/GBOGEB/ABACUS/issues/1877#issuecomment-6172115901); [#1860 governed admission](https://github.com/GBOGEB/ABACUS/issues/1860); [#1929 joined BD/LDAB census](https://github.com/GBOGEB/ABACUS/issues/1929).
- [#1934 feedback terminal-only fanin](https://github.com/GBOGEB/ABACUS/pull/1934) merged; upstream workflow_run now triggers on COMPLETED only, but still starts one evaluator per terminal event. Cancellation coalescing is not demonstrably lossless without successor receipts.
- [#1938 DMAIC nested coverage repair](https://github.com/GBOGEB/ABACUS/pull/1938) merged; native exact-main coverage and security still separately need verification.
- [Existing EVERRED V3 dashboard](https://github.com/GBOGEB/ABACUS/blob/main/tools/everred_v3/sut_gui/index.html), `tools/everred_v3/dashboard/index.html`, `tools/everred_v3/dashboard/bd_queue.html`, [V3 BD data](https://github.com/GBOGEB/ABACUS/blob/main/tools/everred_v3/data/bd_queue_20261014.json), [BD joiner](https://github.com/GBOGEB/ABACUS/blob/main/scripts/bd_ldab_join_census.py), [Feedback gate](https://github.com/GBOGEB/ABACUS/blob/main/.github/workflows/pr-feedback-gate.yml), [deferred review policy](https://github.com/GBOGEB/ABACUS/blob/main/governance/ABACUS_DEFERRED_REVIEW_POLICY.md).
- Source repo should be rechecked for `handover/mc2/MISSIONCONTROL_CURRENT.json` and `docs/CODE_PURPLE_EXECUTION_GRAPH_ARCHITECTURE.md`.

## Latest control state at historical cut
- GitHub readback main SHA `85dad8fbdab530d40e6ccf2f664c455f89454aad`, `protected=true`, active ruleset #24494381 had 3 rules: deletion, non_fast_forward, pull_request; approving reviews=1, stale dismissals+most-recent-push+review conversation resolution required. **No status_checks rule in that ruleset**. Direct legacy protection endpoint returned 403; do not assume more.
- #1934 and #1938 merged; open PR count sampled 11. Previous `protected=false` and empty ruleset reflected an earlier moment, not current truth.
- The user is a single-person repository owner: eligible independent security/admission review is a real capacity/governance blocker; bot comments are not automatically qualified approval.
- Do not equate merged GitHub PRs with independent security acceptance. No waivers, main mutations, or engineering acceptance are created by this handover.

## Measurements — NEVER merge denominators
| UTC window | All runs | Feedback runs | Feedback cancelled | Interpretation |
| --- | ---: | ---: | ---: | --- |
| 10:00-10:19 | 267 | 187 | 160 | 143 upstream-trigger cancellations, not 143 cancelled producer tests |
| 10:20-~10:44 partial | 371 | 254 | 221 | still heavy feedback churn |
| 10:30-10:49 (pre #1934) | 464 | 319 | 285 | old trigger scope |
| 10:55-11:14 (post #1934) | 639 | 204 | 178 | more all-workflow traffic; NOT matched causal experiment |
| 11:15-11:34 | 185 | 150 | 128 | later feedback churn remained |

A targeted ten-cancelled-run sample executed all ten routing jobs (74 job seconds), then cancelled queued evaluation before runner assignment. Historic six queued records (ABACUS 1, CODEX 4, cryoplant 1) had zero jobs and were not six blocked workers. Nine/eleven assigned hosted-runner observations are not host capacity or CREW count.

BD = governed bug/debt issue disposition/burndown; September 26 YAML counted 12 (8 local/external, 4 parents). Native October V3 BD JSON is eight groups / sixteen observations from #1954/#1955 with analytical root candidates. Bandit #1915 had 6,393 full findings and three configured findings: not accepted vulnerabilities, nor 6,393 GitHub issues. All changed data must be recensed against current main.

## Pending implementation and acceptance
- **P0-GOV [P0; OPEN]** Owner/admin to verify required-status-check enforcement; ruleset 24494381 protects main with one approval but no required-check rule. **DoV:** Verify rule ID, actual source/check names, negative red and positive guarded merge, independent review.
- **P0-COALESCE [P0; DESIGNED_NOT_CODED]** Implement one commit-epoch completion collector/append-only cancellation-successor reconciliation under #1877; do not fork feedback gate. **DoV:** A->B->A, duplicate events, out-of-order slow/fast, retry, no-receipt tests and no false green.
- **P1-UI-ROWS [P1; NOT_CODED]** Improve EXISTING EVERRED V3 live workflow table status/trigger badges, zebra rows, focus/hover, grouped/collapsible rows and timestamps. **DoV:** Native code patch + Playwright 1440/1280/390 widths + a11y contrast; tests exact new head.
- **P1-ATLAS [P1; REVIEW_ONLY]** Reconcile standalone EVERRED V4 HTML from this chat into existing V3 SUT UI, not parallel SSOT; preserve original PDF and editable generator sources elsewhere. **DoV:** Source->generated parity, browser QA, secure local dispatch contract, GitHub PR exact head.
- **P1-BD [P1; PARTIAL]** Reconcile 2026-09-26 historical 12-item BD issue queue, 2026-10-14 V3 8 root-group snapshot, present issue backlog, disjoint Bandit/Flake8 signatures, LDAB debugger receipts. **DoV:** Comparable source SHA/run/job/config, accepted root ID vs analytical candidate, durable owner/disposition.
- **P1-CREW [P1; UNKNOWN]** Enumerate live CODEX Mission Control, RHEL8/9, Docker/Podman, user-side worker/port capacity and accepted authenticated returns. **DoV:** Real heartbeat + lease/host/runner ID, job time and REX; NEVER sum crew registry and hosted runners.
- **P1-SECURITY [P1; VERIFY]** Recensus post-merge exact-main #1938 coverage, Safety exit64, A10, DOW/AHT, Bandit, Black/isort, broad 75% and changed-line separately. **DoV:** Terminal exact-main JUnit/coverage/security receipts and eligible reviewer decisions; no waiver.
- **P2-EXPERIMENT [P2; OPEN]** Matched before/after event/queue throughput and runner consumption; avoid mixed workloads. **DoV:** Two comparable windows, arrival/terminal denominators, cancellation-successor %, wait P95.
- **P2-LOCAL-ACTIONS [P2; PROTOTYPE]** Only allowlisted explicit gh workflow dispatch with correct auth and SHA; keep browser credential free. **DoV:** CSRF/origin/lease/policy negative tests; no merge/cancel/waiver endpoint.
- **P2-FEDERATE [P2; OPEN]** Only after ABACUS native acceptance roll out CODEX/QPS/priority repos under their separate authority. **DoV:** Repo-specific reviewed source/check config and worker/return receipts.

## Chat-retirement caveat — NOT FULLY LOSSLESS YET
- This draft PR preserves the text receiver and a **review-only HTML Atlas copy**. Do not substitute it for existing EVERRED V3 code or claim original standalone HTML bytes/QA hash match.
- The previous chat's fillable/layered **PDF binary**, editable HTML/CSS/JS/companion/generation scripts in `EVERRED_4_Control_Atlas_Package.zip`, and the user's four attached source .txt files are not thereby GitHub-archived. They require separate durable private/local backup with SHA256 verification before deleting this chat.
- Prior chat's screenshots, implicit decisions and transient UI states cannot be reproduced losslessly from GitHub unless explicitly recorded.
- Do not upload private credentials/diagnostic logs or classified paths into a public repo for convenience.

## Restart / DMAIC loop
1. Read `state.json`, `DROPIN.md`, manifest and current repo Mission Control pointer.
2. Read GitHub LIVE main, ruleset, active PR heads, #1877, #1860, #1929, current native workflow run/job/artifact receipts and V3 code before proposing new work. Mark moved SHA as stale, never inherited PASS.
3. Consume **one independently attributable first-red root** and existing owner/lease, not each downstream red. Repair source + tests, verify exact-head native, replay consumers, only then consider reviewed protected admission.
4. Implement lossless cancellation proof before extending fan-in: `epoch=(repo,PR,source_SHA,policy_digest)`, immutable producer receipt `(workflow_id,run,attempt,job,SHA,conclusion,time)`; cancelled older queued events must link to successor or remain UNRECONCILED.
5. Retain S0/S1 blocks and S2/S3 durable review deferrals as distinct from CI cancellation. No PENDING->PASS for timeouts or missing evidence.
6. After every material outcome, write updated proof and handover cut to GitHub; never silently rewrite this historical cut.
