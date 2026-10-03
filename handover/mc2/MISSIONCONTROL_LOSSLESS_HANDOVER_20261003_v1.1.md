# MissionControl Lossless Handover v1.1 — 2026-10-03

## Authority refresh

This handover extends the merged #1734 lossless cut without rewriting its
historical receipt.

Current authority at this refresh:

```text
ABACUS main
055bb5c1d787e1fe0d7e52f1e04fc5cea08a06d4

CODEX main
c8bdedd2912ceb456f4582988ab9aa72eea844de
```

Historical W80 remains immutable.

## Why v1.1 exists

PR #1734 proved that CI-only admission is insufficient.

After the PR was opened:

- Codex code review was still running.
- no bound Codex security-review result was recorded before merge;
- Copilot identified a chronological inconsistency in the receipt;
- dependency review reported no vulnerabilities but warned that no
  dependency snapshot existed for the exact PR head.

The PR nevertheless merged.

Those observations are preserved as evidence, not erased.

## New governing PR control

Read:

```text
handover/mc2/PR_FEEDBACK_CONTROL.md
handover/mc2/MISSIONCONTROL_REVIEW_AMENDMENT_20261003.json
```

Every active PR must now refresh and consume:

```text
CI / MIP / DAB / governance
+ Codex review
+ Codex security review
+ Copilot / automated reviews
+ GitHub review threads
+ GitHub PR comments
+ dependency/security warnings
+ human review feedback
```

A substantive finding must be fixed or explicitly dispositioned before
merge.

## Current live PR heads

At this refresh:

```text
#1730
d7539ba6bda902fb2444295873285381526a5bab

#1731
29988c4f8c62ff131a1d106c77f8ea72c43b7f90

#1732
f61d2aaebb4d652acc8175097f53cfb016432a56
```

Refresh these again before acting.

## Default continuation

```text
refresh ABACUS + CODEX
-> refresh active PR heads
-> request Codex review on current head
-> request Codex security review on current head
-> read CI / MIP / DAB / governance evidence
-> read all GitHub reviews, threads, and comments
-> classify first attributable material item
-> repair or disposition it
-> exact-head reproof
-> review/comment recensus
-> merge only when feedback gate is eligible
-> exact-main readback
```

## Invariants

```text
authority_transfer=false
formal_credit_delta=0
engineering_credit_delta=0
repository authority > chat memory
no cross-SHA evidence substitution
no cross-SHA review substitution
first completed attributable red only
no second residual before recensus
unresolved material review blocks merge
historical W80 handover immutable
```
