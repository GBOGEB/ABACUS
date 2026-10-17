# CODE PURPLE MACH-III — owner activation runbook

Status: **PROPOSED / NOT ACTIVE**. Related: #1738, #1860, #2079, #2080.

## Scope
An owner-controlled, time-bounded admission mode for a **single PR**. No blanket 8-hour protection suspension. Retain required CI, critical security, exact-head identity, signed/source-bound evidence, and audit receipts.

## Implementation phases
1. **Observe** current effective org/repository rulesets and branch protection with owner/admin credentials. Record exact required check contexts, review approvals, thread-resolution rules, bypass actors, baseline SHA, and active status.
2. **Classify** security findings: P0/P1 block; P2/P3 eligible for documented deferral only where policy and existing mandatory controls permit; UNKNOWN holds. Do not convert scanner exit status to severity.
3. **Prove** with `python -m unittest discover -s tests -p test_mach_iii_admission.py` and `python scripts/mach_iii_admission.py evidence.json`. Proposal evaluator returns HOLD until `active` is deliberately changed in an approved policy. Even GO_CANDIDATE requires fresh GitHub mergeability and ruleset recheck.
4. **Authorize** owner-approved single-PR exception only when platform permits. Independent approval is not implicitly waived. Record reason, authorized actor, duration <=60 min, expiry, current source SHA, and deferred finding issue links.
5. **Apply** minimal GitHub ruleset change via owner/admin UI or separately authorized automation, with before/after snapshots. Do not change required security or CI gates.
6. **Expire and restore** exception; verify effective ruleset and merge SHA; publish immutable audit receipt and follow up deferred debt.

## Acceptance and wave telemetry
N0: effective ruleset snapshot. N1: security classification denominator P0/P1/P2/P3/UNKNOWN. N2: exact-head negative tests. N3: authorized single-PR admission proof. N4: expiry/restore evidence and post-merge tests.

Metrics: number of PRs blocked per proven root; security findings per severity; deferred items with owner+due date; approval exceptions opened/expired; required-check violations (target 0); merged functional PRs; elapsed time to eligible merge; regression count.

## Safety boundary
This is a source-controlled **proposal**, not a GitHub ruleset update. The connector does not expose effective ruleset inspection/editing; source policy does not supersede GitHub enforcement. Required check failure, unapproved review bypass, or unknown security is HOLD.
