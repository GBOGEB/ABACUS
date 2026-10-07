# ABACUS deferred review disposition

## Scope

This control applies to **GBOGEB/ABACUS only**. It replaces the former
all-or-nothing rule that every open review conversation and every Codex
review must complete before merge.

The intent is unchanged: material security risk may not be hidden by green
CI or by unavailable review capacity. The timing of non-material review may
be deferred when the obligation is captured losslessly.

## Classification

### S0

Known exploitable vulnerability, secret exposure, auth/permission bypass,
unsafe workflow execution, supply-chain compromise, or genuinely RED security
evidence. **Merge disposition: BLOCK.**

### S1

Credible material security defect attributable to the changed code.
**Merge disposition: BLOCK.**

### S2

Security hardening, question, or review obligation not shown to invalidate
the PR. **Merge disposition: ALLOW only after exact-head durable deferral.**

### S3

Style, advisory, stale, broader-repository debt, or unrelated review.
**Merge disposition: NON-BLOCKING; retain when useful.**

## Exact-head deferral contract

Unavailable Codex quota, credits, token budget, or service capacity is never
recorded as PASS. Mark each deferred review explicitly:

```text
CODEX_CODE_REVIEW=DEFERRED_BUDGET
CODEX_SECURITY_REVIEW=DEFERRED_BUDGET
```

A trusted repository collaborator records one exact-head disposition comment
on the PR. The machine-readable marker is:

```html
<!-- abacus-review-disposition:v2
{
  "headSha": "<40-char SHA>",
  "trackingIssue": <issue>,
  "codexCodeReviewRequired": true,
  "codexSecurityReviewRequired": true,
  "items": [
    {"threadId": "<GraphQL thread id>", "classification": "S2"}
  ]
}
-->
```

Every unresolved thread must appear in `items` as S0, S1, S2, or S3.
S0/S1 remains blocking. If S2 is present, or either Codex review is deferred,
`trackingIssue` is mandatory.

The open tracking issue must be opened by a trusted repository collaborator
(OWNER, MEMBER or COLLABORATOR) and contain:

```html
<!-- abacus-deferred-security:v1
{
  "pr": <PR>,
  "headSha": "<40-char SHA>",
  "status": "OPEN",
  "reason": "<why the review is deferred, e.g. DEFERRED_BUDGET>",
  "codexCodeReviewRequired": true,
  "codexSecurityReviewRequired": true,
  "items": [
    {
      "threadId": "<GraphQL thread id>",
      "classification": "S2",
      "source": "<reviewer or comment URL>",
      "finding": "<finding text or faithful summary>",
      "rationale": "<why S2/S3 and why deferral is safe>"
    }
  ]
}
-->
```

The gate rejects a marker-only issue. It requires a non-empty `reason`,
`codex*ReviewRequired=true` for every deferred Codex review, and a complete
`items` entry for every unresolved S2 thread, so the issue alone carries the
obligation at burn-down time.

and preserve, in human-readable form:

- source PR and exact head SHA;
- source thread/comment URLs or IDs;
- finding text or faithful summary;
- source/reviewer;
- S2/S3 classification and rationale;
- reason deferred;
- `CODEX_SECURITY_REVIEW_REQUIRED=true` where applicable;
- closure evidence when later consumed.

A material head change invalidates the old disposition. Re-census the new
head and create/update exact-head debt evidence.

## Sensitive control-plane exception

Changes touching these paths remain strict for **Codex security review**.
A renamed file is classified by both its new path and its previous path, so
moving a file out of a protected directory is still a sensitive change:

```text
.github/workflows/**
.github/codeql/**
ci/governance/**
runtime/federation/**
.githooks/**
```

For these paths, unavailable Codex security capacity remains a pre-merge HOLD.
This prevents the mechanism that defines the gate from self-waiving its own
security review.

## GitHub repository setting

For ABACUS, the owner may disable GitHub's global **Require conversation
resolution before merging** setting. The repository-native `PR Feedback Gate`
then carries the materiality-aware disposition rule.

Do not remove the required `PR Feedback Gate` status check merely to bypass
review debt.

## Burn-down

When Codex capacity becomes available:

1. enumerate open deferred-review issues/records;
2. process S2 security review before S3/advisory debt, oldest/highest-risk
   first;
3. run Codex review against the recorded source SHA or its current successor
   with lineage preserved;
4. repair only material, attributable, repo-local findings;
5. post the outcome to the tracking issue and source PR;
6. close the deferred item only when the obligation is actually consumed.

## Invariants

```text
unresolved conversation != merge failure
unresolved S0/S1 = merge failure
unresolved S2 = merge allowed only with durable exact-head debt
unresolved S3 = non-blocking
DEFERRED_BUDGET != PASS
no silent security debt
authority_transfer=false
formal_credit_delta=0
engineering_credit_delta=0
```
