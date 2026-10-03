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

A previous-head review may remain useful history, but it cannot satisfy the
current-head review requirement.

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
Codex code review complete for current head
+
Codex security review complete for current head
+
GitHub comment and review-thread census refreshed
+
all material findings explicitly disposed
+
no unresolved material review thread
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
