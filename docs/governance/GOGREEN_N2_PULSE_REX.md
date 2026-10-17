# GoGREEN N+2 — source repair, reverse-depth and recurrence handoff

Status: candidate testflight. Security and merge admission remain HOLD.

## Executed wave and test evidence

- N+1: exact-run readback of 10 terminal workflow runs and 12 failed jobs.
- N+2: local root-leverage v2 contract hardening and test-depth extension.
- N+3: exact-head native retest and independent owner review (not assumed).

### Attribution contract

V2 rejects incomplete run/attempt identity, short or stale source SHA,
forged owner root evidence, a conflicting duplicate job, mixed owner
claims for the same root, and unsupported workflow outcomes.

It distinguishes *claimed* root associations from authenticated closures.
No user-provided evidence URL or owner label can self-attest promotion.
A PR with an unknown failed job is not counted as fully attributed.
The fraction is null for an empty failed-PR population.

The companion first-red module tests a repeated downstream summary
and the executable CLI guard. Neither can manufacture root closure.

### Local proof

The two directly affected source modules have independent statement
and branch denominators. N+1 local first-red baseline was 138/139
statements plus 36/38 branches. N+2 has new tests for previously
unvisited branches and for the stricter source-owning root component.

A local source-scoped coverage increase is not ABACUS main coverage.
Full merged-main, changed-line and estate coverage remain UNKNOWN.

## Owner DAG and SIPOC

```text
Supplier: GitHub native run/job/step producers
Input:    run, attempt, exact head, source, failed step and evidence
Process:  validate -> deduplicate -> attribute candidate -> owner decision
Output:   reproducible root-to-PR projection, unknowns and coverage receipt
Customer: EVERRED #2077, ABACUS #1929, GoGREEN #2080, Mission Control
```

Upstream root branches remain independent:

- Python 3.10 requirements: ABACUS PR #2026.
- Workflow inventory: ABACUS PR #2041.
- Bandit/Safety and A10: independently owned admission roots.
- Formatting debt: run native formatter, not a governance bypass.

For each owner fix, attach old/new head, original root fingerprint,
actual failing job count, repaired code, tests, all required CI,
matched coverage, merged-main SHA and recurrence evidence.

## Non-compensating conditions

`merge_authorized=false`, `security_waiver=false`, and
`authority_transfer=false`. New issue/PR work must not assert that
an authenticated Crew/REX launch occurred merely because CI ran.
