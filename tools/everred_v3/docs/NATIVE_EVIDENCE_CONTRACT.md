# EVERRED V3 native evidence and control contract

## Read-only collection

Use `scripts/collect_native.py` with a GitHub Actions read token,
exact repository, run ID and full 40-character head SHA. It fetches
run metadata and the complete paginated job set. Missing or mismatched
run/job identity fails closed; no check is inferred from job naming.

Explicit artifact plans map `artifact_id`, `job_id`, ZIP member and
producer configuration to an exact source. The artifact SHA-256 is
checked against GitHub artifact metadata before parsing. Its uploading
job is still a declared binding until independently corroborated.

Input families:

- **Bandit:** native JSON results and scanner config/rule/version.
- **Coverage:** Cobertura XML with line-level numerators and totals.
- **JUnit:** failing test case identities and unclassified signatures.
- **Runtime:** typed RHEL, UBI, Docker, LDAB or LLDB receipts.

Artifacts with unknown scanner profiles, unsafe source paths, oversized
ZIP entries, missing digests or malformed XML are rejected.

## Source and trust levels

**MANUAL_UNVERIFIED:** imported JSON and operator-supplied artifacts.

**API_AUTHENTICATED_METADATA:** read from the GitHub API using a token.

**GITHUB_ARTIFACT_BOUND:** bytes match the GitHub SHA-256 listing.
Upload-job attribution still requires the workflow's producer proof.

No level automatically qualifies an independent code/security review.
Fingerprint identity is not a verified causal root identity.

## Joined evidence

`src/joined_census.py` joins native events only on repository, exact
SHA and source run. Job references are preserved within the run.
The census emits separate arrays for CI first-red, Bandit, coverage,
runtime and verification. Missing root attribution, active workers,
security disposition or fingerprint burndown remains `null`.

ABACUS's existing BD/LDAB joiner remains authoritative and read-only.
Cross-repository CODEX receipts must not implicitly become ABACUS proof.

## Coordination and replay

The dedicated lease ref stores versioned source/path ownership.
A Git `--force-with-lease` push is atomic at ref update. Failed CAS
updates are rejected and retried only after fresh inspection.
No automatic theft occurs on a stale lease or expired timestamp.

An immutable replay uses declared main-base, consumer and repair SHAs.
The three refs must exist and share the declared base. `merge-tree`
creates a preview tree; optional isolated tests never claim unchanged
consumer native CI PASS and cannot update any branch.

## KPI and recurrence

KPI pulses are hash-chained. A new pulse must include its ledger
fingerprint; repeated identical inputs do not inflate progress.
Coverage and scanner deltas require matching unit, version, scope,
configuration and comparable fingerprint sets.

Recurrence after closure produces a review-required alert with links to
the earlier closure and new observation. Alert delivery needs a separate
notification transport and successful delivery receipt.

## Effective admission boundary

The evaluator needs effective server-branch rules, strict checks,
independent approval, resolved conversations and separate native
coverage/security/workflow-policy decisions on the identical head SHA.

Its maximum output is eligibility for **external authorized merge**.
It never calls a merge API, grants security waivers, or supplies its own
approval. Imported receipts always return HOLD.

## Native workflow

`.github/workflows/everred-v3-validation.yml` runs on V3 changes.
Manual dispatch accepts exact run and SHA plus an optional artifact
plan. The workflow uploads observational dashboards and JSON artifacts,
not commits to main. It cannot run from the default branch until a
governed integration admits that workflow definition.
