# LOSSLESS_RESTART_PROTOCOL_V1 — reusable governed continuation

Status: **process guide, not project-specific authorization**. Adopted for ABACUS MIP / MissionControl handover on 2026-10-15. No merge, waiver, inferred approval or Crew launch is conferred by this document.

## 0. Precedence and canonical inputs

Order of authority: (1) live repository default branch + protected-ruleset response; (2) live PR base/head SHA, review threads and required check contexts; (3) native completed run/job metadata **and validated downloaded evidence bytes**; (4) immutable issue/PR comment receipts; (5) branch-pinned handover state; (6) historical snapshots; (7) conversation notes. Lower layers never overwrite contradictory live evidence. Snapshot timestamps and source SHAs must remain visible.

Reusable parent guides: `handover/mc2/MISSIONCONTROL_CURRENT.json`, `handover/mc2/MISSIONCONTROL_DROPIN_v1.1.md`, `handover/mc2/SESSION_CLOSE_CURRENT.json`, `deepagent-handover-package/handover/04_handover_manifest.yaml`; CODEX `docs/handover/RECURSIVE_IDEMPOTENT_METHOD_HANDOVER_v1.md`. Treat 2025 bundle claims and 2026-09 historic SHA/status fields as **historical examples**, not current truth.

## 1. Minimal handover contract

Publish, without ZIP or binary substitution:
- `SC_<date>_MIP_MC_STATE_V1.json`: parsed, strict snapshot with repository/PR identity, run/job links, numerical denominators, evidence class, status, gate and deficits.
- `SC_<date>_MIP_MC_HANDOVER_V1.md`: lossless narrative, six-workstream WBS, roots and bounded execution plan, cross-repo source lineage, historical versus live contradictions.
- `SC_<date>_MIP_MC_DROPIN_V1.md`: ready-to-paste receiver prompt with expected first actions.
- `LOSSLESS_RESTART_PROTOCOL_V1.md`: reusable method, not a replacement for project-specific evidence.
- PR comments and issue cross-links: durable pointers. Comments are not approval, formal closure or native worker receipts.

Every quantitative record shall contain: metric name, cohort/scope, numerator, denominator, tool/config identity, before SHA, after SHA, UTC run/job/artifact ID, test source, interpretation and comparability decision. A missing number is `UNKNOWN`/`null`, **never** silently 0.

## 2. Cold-start and N+1 recensus

1. Discover the actual accessible repositories and branches; do not trust a cached `main` or `master`.
2. Fetch the current PR head SHA/base SHA and commit event; check if any handover commit has invalidated prior native CI.
3. Read protection rules **including actual status-check and approval requirements**; `protected=true` alone is inadequate.
4. Enumerate actual issue states separately from unique BD/LDAB roots, scanner occurrences and PR counts.
5. Enumerate terminal workflow runs, jobs and artifacts on the exact SHA. Verify downloaded bytes and internal source/hash provenance before promoting evidence.
6. Read discussion threads, reviewer statuses and outstanding bot suggestions. `COMMENTED` is not an eligible approval.
7. Categorize each item as `IMPLEMENTED`, `VERIFIED`, `ROOT_RESOLVED`, `INTEGRATION_ELIGIBLE`, `MERGE_ADMITTED`, or `UNKNOWN/HOLD`. These states are not interchangeable.
8. Identify **one earliest attributable first-red per disjoint owner slice**, retain overflow in the BD queue and recensus after each mutation.

## 3. Claim and evidence classification

- `NATIVE_EXACT_HEAD`: run ID, job ID, attempt, exact PR SHA; may prove tests executed, not artifact content.
- `BYTE_VERIFIED_CONSUMER`: independent ZIP/member hashes, manifest, source/run/job/attempt, strict consumer verdict.
- `API_METADATA_ONLY`: independently fetched run/job timing/status; not Crew dispatch or worker-hours proof.
- `LOCAL_HASH_ONLY`: locally matched receipt bytes; not remote runtime admission.
- `SYNTHETIC_CONTROL`: negative/control fixtures, never operational burndown or formal closure.
- `HISTORICAL`: once verified but not transferable to another SHA/branch/denominator.
- `UNKNOWN`: unobserved or unverified. `NOT_APPLICABLE`: scope does not admit the metric.
- `AUTHENTICATED_CROSS_REPO`: allowed only after separately verified sender, transported bytes, receiver and authority.
- `QPS_ACCEPTED`: requires QPS recipient decision, not inferred from a GitHub merge.

## 4. Pulse/scale control

For each wave/pulse: freeze before SHA and target; record changes and changed files; run negative controls; measure true after SHA with exact denominators; output `delta_pp`, uncovered-line reduction, errors opened/resolved/reopened and first-red stability. Compute runner metrics from full job enumeration: success/total, summed work seconds, first-start→last-finish elapsed, no-active-job gaps, peak overlap and queue latency where available. Report lack of causal evidence explicitly.

For federation: inventory (repository × domain × evidence-level) as a matrix. `HEAD_OBSERVED`, `SOURCE_DISCOVERED`, `PRODUCER_NATIVE`, `CONSUMER_BYTE_VERIFIED`, `REX_ACCEPTED`, `QPS_ACCEPTED` are **different depths**. A 24-slot configuration does not equal 24 filled receipts.

Do not use statistical PCA, Bradley–Terry or 3P* capability labels to compensate for missing comparable independent trials, raw coverage proofs or gate failure. Keep inferential stability M2/M3 `HOLD` until assumptions and observations are established.

## 5. Mutation, PR and closure controls

For an open PR: use an isolated branch; classify changed-file ownership and method; commit bounded source/tests/evidence. Post exact evidence and previous→new metrics. For a merged PR: **do not rewrite history**; post a follow-up/link and verify the merged SHA separately on target main. For a draft PR: keep draft unless source verification + review justify change. For an issue: link evidence, map checklist status; only close with attributable native root-closure proof, ownership decision and acceptance, never because a proposal worker passed.

No generic waiver, branch-rule relaxation or third-party review impersonation. Single-seat emergency governance, if elected by repository owner, needs its own documented limited exception; this protocol does not grant it. Never auto-close A10 restricted findings.

## 6. Publication and validation

Produce all four text artifacts from one source snapshot; compare SHA/ID representations across JSON, Markdown, drop-in and comments. Publish on a named PR branch, record each resulting commit SHA, then **refresh the final PR head**. A documentation commit itself changes the head; previously green checks at the pre-handover SHA become historical. Avoid publishing derived binaries or ZIPs to Git.

Closure receipt must state `done`, `verified`, `blocked`, `deferred`, `not_applicable`, `unknown` for each task, owner/action, first-red and criterion for reopening. Never mark a todo complete solely because it was mentioned in the handover.

## 7. Receiver acceptance

The receiving worker shall: (i) cite current main and PR SHAs; (ii) confirm this file and JSON were read; (iii) identify stale snapshot discrepancies; (iv) name the first current attributable red and associated native job; (v) propose/execute the next **disjoint** bounded repair, or explicitly HOLD when authority is absent; (vi) publish new SHA-bound pulse and next handover only on genuine material change.

The attached user's separate N+2 GOGREEN same-repo consumer replay is valid historical scope; its cross-repo/QPS claims remain independently governed. Preserve all prior handover cuts as immutable history.

`authority_transfer=false`; `merge_admission=HOLD_until_live_proven`; `security_waiver=false`.
