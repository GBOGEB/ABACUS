# GoGREEN root leverage — Wave N0/N1/N2

Owner: [ABACUS #2079](https://github.com/GBOGEB/ABACUS/issues/2079).

## Waves

- N0: collect exact-head PR/run/job/attempt records; preserve origin.
- N1: compare first-red logs with source-bound main baseline evidence.
- N2: repair an independently confirmed root in its source-owner lane.
- N3: measure genuinely unblocked or merged PRs and recurrence.

## Core metrics

- Observed and failed PR denominators, not a guessed global census.
- Unique failed job identities by PR, head, run, attempt and job.
- Candidate step-signature overlap, distinguished from accepted roots.
- Qualified root attribution per failed PR, excluding unknown roots.
- Source-owned root evidence, disposition, and PR association.
- Potential PRs released: upper bound only, not merge eligibility.
- Main/PR/diff coverage using matched tools and exact source identity.
- Actual eligible merges: GitHub main-readback evidence, not this script.

## N0 and N1 evidence

Owner example: [ABACUS #2070](https://github.com/GBOGEB/ABACUS/pull/2070)
and the N0 [EVERRED census](https://github.com/GBOGEB/ABACUS/pull/2077)
show repeated
Code Quality, Security, governance, and Full Red Summary job labels.

These labels are not proof of common causal roots. Do not equate the
aggregate summary with an independent defect.

The [N1 first-red module](https://github.com/GBOGEB/ABACUS/pull/2080)
validates exact native
run/job/attempt identities. Its bounded source sample has twelve failed
job observations, six candidate signatures and zero admitted root closures.

## Version-two input contract

A JSON object contains an `observations` list of up to 512 records.
Each record must provide:

- `pr`, full 40-character `head_sha`, `run_id`, `run_attempt`, `job_id`.
- `job` and terminal `status` of `failure`, `success` or `skipped`.
- A first-red signature when an owner-accepted root is proposed.

For a non-authoritative owner claim, supply `root_id`, `root_owner`,
`owner_disposition=ACCEPTED`, and an actual GitHub issue/PR/run URL in
`root_evidence`. An unsupported or conflicting owner claim fails closed.

The output's `owner_claim_attribution_fraction` is null when no failed
PRs were observed. The claimed fraction is not a verified root count.
`root_attribution_pr_fraction` stays null without authenticated root
receipts; `proven_root_leverage` is empty and `root_claims_authenticated`
is false. `candidate_pr_impact_upper_bound` is descriptive only.
`actually_unblocked_prs` stays null pending independent verification.

### Commands

```bash
python scripts/gogreen_root_leverage.py input.json --output metrics.json
python -m unittest discover -s tests -p 'test_gogreen_root_leverage.py'
```

## Admission and REX

The module is read-only. It is neither a merge controller nor a security
approval. Every root closure requires source-owner disposition, exact-head
repair proof, eligible review and an independently verified main replay.

No administrative waiver, fake worker launch, source-binary publication,
or inferred REX acceptance is permitted.
