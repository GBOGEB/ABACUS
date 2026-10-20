# N+i exact-SHA telemetry extension (W24)

This is an additive read-only consumer of live native GitHub Actions **push-run**
snapshots. It does not replace the canonical #1990 MIP pulse, #1929 root census,
Mission Control wave history, #1860 admission register, or CODEX #975.

## Why this slice exists

A run count is not a closure count. Separate the **workflow-observation
denominator** (all push runs for one pinned main SHA) from the **terminal
denominator** (completed runs), and from tests, accepted engineering roots,
issues, and independently authorized merges. A pending result must never count
as a failure or success; missing coverage must never be a zero numerator.

N21, N22, N23 are **different exact source-head populations**. This
observatory displays terminal queue pressure and reports unique, terminal
workflow-family pairs only when the same workflow ID occurs exactly once in
each population. A changed family status is observational, not causal proof.

## Reproduce the committed snapshot

From the repository root:

    python tools/mip2/mip_nplus_observatory.py \
      --input triage/rex/NPLUS_W21_W23_GITHUB_PUSH_SNAPSHOT.json \
      --output /tmp/nplus-w24.json
    python -m unittest discover -s tests -p test_mip_nplus_observatory.py -v

The producer emits deterministic JSON and Markdown in /tmp. Input GitHub API
links, source SHA, run ID, workflow ID, attempt, event, status and conclusion
are preserved in the immutable input. Read-only acquisition is not native
signed ZIP-member verification; no worker launch or independently reviewed
merge authority is inferred.

## Scaling decision

Use **N23 backlog of nonterminal workflows** to size a *proposal* of
read-only diagnostic lanes: ceil(nonterminal / 4), capped at 8. This number is
NOT active workers or mutation approval. Keep disjoint source-owner tracks:
(1) effective branch rules and negative canary; (2) dashboard 53-href census;
(3) docs changed-file lint; (4) Windows coverage-mode collision;
(5) #1929 deduplicated roots; (6) matched coverage and native receipts.
No new Actions workflow is installed.

Only raise mutation concurrency after head-specific CI, security, independent
approval, effective merge rules and source/path leases all qualify.
For a stability screen, require at least 20 genuinely independent comparable
head observations **and** separate process-control tests. This tool never
claims Six Sigma control, PCA or Bradley–Terry from three source heads.

## Admission receipt and follow-up

- Canonical issue open/closed is housekeeping unless source-owner closure proof exists.
- Coverage uplift requires matched numerator, denominator, scope, configuration,
  exact source SHA and native evidence; not inferred from passed tests.
- A full run cohort at SHA A cannot be compared numerically to SHA B without
  identifying workflow family and terminal status first.
- On N24: acquire all complete run pages and job/attempt metadata, freeze
  current-main counters, compare N23->N24 and attach live native links.
- P0 remains HOLD; an observed merged PR is not a correctly admitted PR.

No rights, approvals, waivers, synthetic launches or root closures are created.
