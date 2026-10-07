# MissionControl PR Feedback Control

## Purpose

Every active pull request must consume review and comment evidence before
merge. CI is necessary, but it is not the only source of actionable
evidence.

This control exists to prevent a green or apparently admissible PR from
passing identified gaps, improvement opportunities, future reds, security
concerns, or unintended consequences that were already visible in GitHub.

## Default exact-head intake

For the current PR head, refresh all of these surfaces:

1. CI, MIP, DAB, governance, test, coverage, and security checks.
2. Codex code review.
3. Codex security review.
4. Copilot and other automated review findings.
5. GitHub inline review threads.
6. GitHub issue-style PR comments.
7. Dependency-review and security-review comments or warnings.
8. Human reviewer comments and requested changes.

A material head change invalidates any claim that an earlier review covers
the new head. Refresh review and comment evidence after each material push.

## Default Codex request

For every active head, request both reviews as separate PR comments:

```text
comment 1:
@codex review

comment 2:
@codex security review
```

Do not combine the two commands into one comment. The observed GitHub
integration may start only one review from a combined request.

A previous-head review may remain useful history, but it cannot substitute
for current-head evidence. For ABACUS, exact-head Codex review is satisfied
either by completed review or by the controlled S2/S3 deferral contract in
`governance/ABACUS_DEFERRED_REVIEW_POLICY.md`. Lack of review capacity,
quota, credits, or service availability is never PASS: it is
`DEFERRED_BUDGET` and must be bound to durable exact-head debt. S0/S1 remains
blocking. Codex security review remains mandatory before merge for sensitive
control-plane paths defined by that policy.

## Finding disposition contract

Every substantive item receives one explicit disposition:

```text
FIXED_IN_CURRENT_HEAD
ACCEPTED_NO_CHANGE_WITH_RATIONALE
DEFERRED_WITH_TRACKED_ISSUE
NON_ACTIONABLE_INFORMATION
SUPERSEDED_BY_NEWER_EXACT_HEAD
```

Do not silently ignore a finding because CI is green.

A possible future red, unintended consequence, coverage gap, security risk,
or missed improvement opportunity must either be repaired now or retained
as a durable tracked item with source evidence.

## Merge gate

Before merge, require:

```text
exact-head CI / MIP / DAB census
+
exact-head Codex review complete OR valid exact-head S2/S3 deferral
+
Codex security review complete for sensitive control-plane changes
+
current-head GitHub Actions terminal and green
+
GitHub comment and review-thread census refreshed
+
all unresolved threads explicitly classified
+
S0 = 0 and S1 = 0
+
every S2/Codex deferral bound to durable open debt
=
PR feedback gate eligible
```

If a material review finding is found, treat it as attributable evidence.
Repair only the first admissible material item, rerun exact-head proof,
then refresh the review and comment census before consuming another
residual.

## Review evidence and first-red ordering

Review evidence participates in the same controlled sequence as execution
evidence. It does not create permission to consume multiple residuals at
once.

```text
refresh exact head
-> consume completed CI / review / security / comment evidence
-> identify first attributable material item
-> repair or disposition
-> exact-head reproof
-> review/comment recensus
-> only then consume next material residual
```

## Invariants

```text
repository authority > chat memory
review evidence is exact-head evidence
Codex review completion or valid exact-head S2/S3 deferral is an admission predicate
no cross-SHA review substitution
CI green does not erase review findings
security green does not erase code-review findings
comments are evidence inputs, not automatic authority
material future-red risks must remain durable
unresolved material review blocks merge
authority_transfer=false
formal_credit_delta=0
engineering_credit_delta=0
```

## Hard-gate implementation

The repository now stages a single merge-gate check named:

```text
PR Feedback Gate
```

It is produced only by trusted default-branch code:

```text
ci/governance/pr_feedback_gate.py
ci/governance/tests/test_pr_feedback_gate.py
.github/workflows/pr-feedback-gate.yml
```

The evaluator is fail-closed for repository-native admission and review
evidence. It requires:

```text
exact-head Codex review complete or valid exact-head S2/S3 deferral
Codex security review complete for sensitive control-plane changes
zero unresolved S0/S1 review items
all unresolved S2/S3 threads explicitly classified
current-head GitHub Actions terminal
current-head GitHub Actions green
all deferred review obligations linked to durable open issues
```

If Codex review capacity or credits are unavailable, the gate remains PENDING
until a trusted collaborator records the exact-head deferred-review marker and
durable tracking issue required by the ABACUS deferred-review policy. This is
DEFERRED_WITH_DURABLE_DEBT, not PASS. No older-SHA review may be substituted.

The evaluator must not check out or execute PR-supplied code with write
credentials. Review/comment and workflow-run events execute the workflow
definition from the trusted default branch.

### Required GitHub owner bind

Repository settings are a separate owner/admin control. The live readback
on 2026-10-03 showed:

```text
main.protected = false
active rulesets = none
PR Feedback Gate mergeGateEnabled = false
```

After this workflow is merged and has produced the check at least once,
configure GitHub Settings so `main` requires the exact status check:

```text
PR Feedback Gate
```

Also require strict/up-to-date branches, no ordinary bypass/admin exemption,
and block force-push/deletion. For ABACUS, do **not** require GitHub's global
conversation-resolution gate; material review disposition is enforced by the
repository-native PR Feedback Gate instead.

Until that settings bind is proven by live readback, the hard gate is
implemented but not non-bypassable.

### Merge interpretation

```text
PR Feedback Gate GREEN
+ branch protection/ruleset requires PR Feedback Gate
= HARD merge block active

PR Feedback Gate GREEN
+ main.protected=false
= evidence only; merge remains bypassable
```
