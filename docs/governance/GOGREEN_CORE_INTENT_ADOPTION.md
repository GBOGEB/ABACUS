# GoGREEN core-intent adoption (candidate)

Upstream contract: https://github.com/GBOGEB/pipeline-automation-hub/pull/589
Status: REPO-LOCAL PROPOSAL; upstream is not merged; no protection changes.

## Local GO policy
- GO_EXECUTE: isolated core-intent development and source-bound proof.
- GO_PROVE: relevant exact-head checks demonstrate intended functionality.
- GO_MERGE: all existing required CI, approval, thread, security and domain-owner gates satisfied at current head.
- DEFER_NONCRITICAL: optional findings only, tracked by owner, issue and re-entry deadline; never defer required approval.
- SPLIT_CORE: extract a smaller independently proven change if unrelated required failures block the original PR.
- HOLD_REQUIRED: missing or failing required evidence, unknown ruleset, security blocker or nonmergeable head.
- CONTROL_POSTMERGE: tracked optional debt, regression checks and adoption metrics.

## Glossary
Core intent = minimum useful PR functionality; exact head = immutable source SHA; first-red = first observed failing step, not necessarily causal root; root = deduplicated evidence-backed cause; manifestation = failed job/test/step; fan-out = independent repository-owned adoption; cohort = declared comparable denominator; GO is per-PR, not federation-wide green.

## Adoption acceptance
1. Preserve repository-specific source authority and existing branch protection.
2. Test stale-head, red required check, missing required review, security finding, unknown ruleset as negative HOLD cases.
3. Record exact-head CI, changed-line coverage where available, owner and optional debt links.
4. Merge only after upstream contract review or an explicit local owner-approved equivalent; do not auto-merge this proposal.
