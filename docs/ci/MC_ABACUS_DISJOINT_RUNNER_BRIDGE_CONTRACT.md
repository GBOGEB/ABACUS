# MissionControl / ABACUS disjoint-runner bridge contract (review candidate)

Status: **DESIGN ONLY — NOT ENABLED**. Source owner: GBOGEB/ABACUS. CODEX #977 is an orchestration proposal; it has no authority to mutate ABACUS. This contract adds no workflow, secrets, permissions, runner, or automatic dispatch.

## Typed dispatch envelope (future implementation)
A request MUST bind `principal`, `target_repository=GBOGEB/ABACUS`, `expected_head_sha` (40 lowercase hex), `approved_action`, `allowed_paths`, `dry_run_receipt`, `explicit_owner_approval_ref`, `idempotency_key`, `parent_request_digest`, and `expires_at`.
Default DENY. ABACUS validates the authenticated principal and approval independently, not using browser or CODEX assertions. Changed-path ownership must be locked server-side; overlapping paths serialize, independent lanes may proceed. A stale head, replay, missing approval, invalid allowlist, expired envelope, forged principal or nonzero security gate MUST fail closed. Never let stage-only CODEX transport become remote mutation by configuration switch.

## Native response / REX proof (not source-asserted execution)
Only an actual ABACUS GitHub Actions execution may promote `launched=true`, with authenticated `workflow_run_id`, `workflow_job_id`, `run_attempt`, exact `head_sha`, event, run URL, terminal conclusion, artifact ID/digest, policy digest, and input digest. A staged plan, checkbox, PR, or comment does not prove a launch.

Provide one root fingerprint per **independently confirmed** causal defect, include affected jobs and the exact first failing log line; separate manifestations from roots. Record before/after queue counts at identical scope and source query. Coverage must carry configuration digest, scope, SHA, numerator and denominator (line, branch, broad, changed-line). Main and PR must not be compared as equivalent populations. If missing or noncomparable, fields are `null` (UNKNOWN), never 0.

## N→N+3 proof boundary

| Pulse | Object | Required evidence | Credit |
| --- | --- | --- | --- |
| N | source freeze | both heads and branch/contract hashes | documentation only |
| N+1 | owner/runner qualification | authentication, approval, allowlist, stale/replay/path tests | none until native CI |
| N+2 | disjoint execution | real run/job/attempt and artifacts per independent worker | per-source verified |
| N+3 | P0 / admission / REX | exact-head CI, eligible human review, security, terminal merge on main, paired REX | only after readback |

**Acceptance**: CODEX #977 remains open until the 7 actual checklist obligations are discharged. ABACUS #1860 remains P0 HOLD until its independent admission criteria pass. No waiver or authority transfer. No merge credit for this document.

## Relations

- [CODEX #977](https://github.com/GBOGEB/CODEX/issues/977): execution promotion blocker
- [CODEX #975](https://github.com/GBOGEB/CODEX/pull/975): historical inventory repair, not dispatch authorization
- [ABACUS #1860](https://github.com/GBOGEB/ABACUS/issues/1860): admission and owner decisions
- [Existing MC Wide contract](MC_WIDE_FEDERATION_PULSE_CONTRACT.md): source receipt adapters and population guards

## SIPOC
Supplier: CODEX proposal / ABACUS owner → Input: exact SHA, approval, path set → Process: ABACUS-local authenticate/lock/execute/retest → Output: native run/job+digest+first-red → Customer: admission reviewer and CODEX typed REX consumer.

## Forbidden in this change
No remote execution, enabling mutation, workflow dispatch, approval simulation, security bypass, ruleset changes, coverage uplift claim, root closure claim or branch merge.
