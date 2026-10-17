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

A collaborator with write access records one exact-head disposition comment
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

A classification covers only the thread content it was made against. If any
comment in an unresolved thread is created or edited after, or in the same
second as, the disposition comment's last update, the deferral is invalid
until the disposition is re-issued.

The open tracking issue must be opened by a repository collaborator with
write access or higher and contain:

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
`items` entry for every unresolved S2 thread, recorded as S2 (a downgrade to
S3 or a duplicate thread entry is rejected), so the issue alone carries the
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

The gate re-evaluates on every tracking-issue lifecycle event (edited,
closed, reopened, deleted, transferred) and on deleted PR comments, so closing
the issue or removing its debt evidence withdraws the deferral immediately
rather than at the next scheduled sweep.

A material head change invalidates the old disposition. Re-census the new
head and create/update exact-head debt evidence.

## Sensitive control-plane exception

Codex **security review** can be deferred only for PRs whose every changed
path is an inert raster image: `*.png`, `*.jpg`, `*.jpeg` or `*.gif`. Any
other path is sensitive. ABACUS runs many workflows with write tokens that
execute repository code after merge (`.github/scripts/**`, `scripts/**`,
installed packages), so a list of "privileged" paths cannot be kept complete;
the classifier is an allowlist and fails closed. Formats that look like
content are sensitive because they are executed or published as active
content: Markdown pipelines under `handover/pipelines/**` run through
`scripts/markdown_exec_runner.py`; Pandoc builds (`book-build.yml`,
`export-docs.yml`) pass raw HTML in `*.md`/`*.rst` into published HTML/EPUB;
`*.svg` and `*.pdf` can carry script and are published to GitHub Pages from
`docs/**`.

A deferral marker and its tracking issue are accepted only from authors with
write, maintain or admin permission on the repository, resolved through the
collaborator-permission API. Author association alone is not enough: `MEMBER`
and `COLLABORATOR` include read- and triage-only users.

A renamed file is classified by both its new path and its previous path. If
the PR file listing is incomplete (GitHub caps it at 3,000 files, so the
record count differs from `changed_files`), the PR is treated as sensitive
and every conditional CI workflow is required.

For sensitive changes, unavailable Codex security capacity remains a pre-merge HOLD.
This prevents the mechanism that defines the gate from self-waiving its own
security review.

## GitHub repository setting

Keep GitHub's **Require conversation resolution before merging** setting
enabled on `main` (it is enabled in the `main` ruleset as of 2026-10-17).
Resolving or unresolving a thread emits only the `pull_request_review_thread`
webhook, which GitHub Actions does not support as a workflow trigger, so the
repository-native `PR Feedback Gate` cannot see a thread being reopened until
the five-minute scheduled sweep. The native setting closes that window.

Disable it only after the webhook is bridged into `repository_dispatch`
through a GitHub App and a reopened thread is observed to re-census the PR
immediately. Until then the gate's materiality-aware disposition rule
applies in addition to, not instead of, native conversation resolution.

A head change (`pull_request` synchronize or reopened) marks the gate pending
outside the per-PR census queue, the same way a tracking-issue event does. On
synchronize it also marks the departing head (the event's `before` SHA)
pending, so a PR moved from head A to B and back to A cannot re-expose A's
earlier success. The same event's census runs only after that invalidation,
so its result is never rejected as older than the pending mark.

Overlapping evaluator runs for one PR (for example a tracking-issue event and
a CI `workflow_run`) cannot interleave: the workflow first routes the event to
its PRs, then evaluates each PR in its own job inside the
`pr-feedback-gate-pr-<number>` concurrency group, so only one census of a PR
reads and writes its check at a time. A newer queued census replaces an older
queued one, and a running census is never cancelled. There is no
workflow-level concurrency group, so an unrelated no-op event (such as a
public comment on a tracking issue) cannot cancel or displace a run that has
PRs to re-census. As a second
guard, censuses are ordered by the `census_started` stamp on the check: a
census never publishes over a result from one that started later. The stamp is
taken once per job, so its pending mark, its result and its failure
publication all carry the same start time.

Because a tracking-issue close or edit re-censuses the PR in a job that
queues behind any census already running, that running census re-runs the
whole evaluation immediately before it publishes a success that rests on a
deferral, and publishes it only if the re-census reproduces it exactly. If the
evidence changed, the fresh result is published instead (up to three
re-censuses, after which the check stays pending).

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
