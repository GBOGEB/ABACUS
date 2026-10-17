# W72 GoGREEN / EVERRED / CODE PURPLE three-wave control

Status: candidate. No change to required branch checks, no waiver, merge hold.

## Wave 1: source identity / first-red origin

The previous W72 workflow used PR-head checkout but wrote `GITHUB_SHA` to its
receipt. A pull request's `GITHUB_SHA` can identify a synthetic merge commit.
Three prior successful receipt observations were therefore source-mismatched.
The revised receipt attests `git rev-parse HEAD`, validates the PR event head,
and stores the synthetic event context separately. Missing, foreign or stale
SHA fails receipt emission. Producer never grants release, review or REX.

## Wave 2: case-depth coverage and negative behavior

The native W72 job runs standard-library source tests before installation and
pytest package regression with JUnit XML. The parser records every testcase's
name, terminal outcome, skip classification-needed flag, duration and a
stable case census fingerprint, plus explicit JUnit byte digest.

The parser rejects DTD/XXE, malformed XML, case duplicates, conflicting
outcomes, false counts and invalid durations. On non-green pytest, case data
remains a diagnostic artifact, not an invalid positive clean-clone proof.

`tools/w72_testcase_telemetry.py:compare()` computes recovered/regressed cases,
new and disappeared tests. New/deleted cases make populations non-comparable;
case recovery is *not* an accepted root closure. Two prior persistent skips
require owner classification: one environment/venv configuration, one Docker
configuration. Never relabel them mandatory/optional without disposition.

## Wave 3: temporal root family and queue watch

`tools/w72_root_watch.py` projects supplied actual six-wave W72 history into
one deterministic, read-only control: states, first-red manifestations, per-run
queue wait, source-mismatched receipts and owner carry-forward. Queue wait
>600 seconds is only an operator alert, not a Shewhart control limit or SLA.
No stability claim without independent observations and matched conditions.

Root action lanes:

| Signature | Source owner | Status |
| --- | --- | --- |
| W72 receipt SHA | ABACUS #1860 | Candidate; retest |
| Windows snapshot path | ABACUS #2046 | Main recurrence pending |
| Backup old content | ABACUS #2046 | Main recurrence pending |
| Workflow inventory | ABACUS #2041/#1995 | Independent gate |
| A10 confidentiality | ABACUS #1996 | Owner review pending |
| Bandit/Safety | ABACUS #1738/#2027 | Independent gate |
| Queue wait | ABACUS #1877/#2033 | Source-bound watch |
| Unclassified skips | ABACUS #1877 | Owner classification |
| M2/M3 inference | gg_MATH #27 | Matched cycles pending |

Native case recovery does not close the Windows/backup roots. Source-owner
checks must prove current head and eventual merged-main recurrence. Queue
watch events must be separated from tests actually running on the worker.

## Before / after measurement basis

- Baseline W72 sample: six native run/job rows, three GREEN and three RED.
- Three GREEN receipts were reported with wrong checkout SHA.
- Six W72 samples produced 3,335 passed, 4 failed and 12 skipped test
  occurrences, NOT unique case identities or independently reproduced roots.
- Observed queue median 511.5 s, nearest-rank p95 4,049 s; three of six
  queue waits exceed the operator's 600 s watch threshold.
- New code adds 56 local positive/negative unit methods measured before
  terminal CI. Local module coverage must be stated with matching run receipt;
  it is not an ABACUS main or PR diff coverage uplift.

## DAG, output and authority

`real GitHub W72 job -> [JUnit, exact checkout] -> W72 producer receipt ->
MIP/LDAB observation -> EVERRED root owner -> GoGREEN recurrence ->
CODE PURPLE required gates -> main (only if separately admitted)`.

This source slice does not auto-launch Crew workers, accept REX, close BD roots,
perform A10 review, bypass CODEX #977 or alter main protection. Existing
GoGREEN, DOW/KEB, MIP and CODEX contracts remain owners of their lanes.

### Acceptance TODO

- [x] Add source-bound producer and adversarial checkout tests.
- [x] Add native-case JUnit parser and reverse/negative tests.
- [x] Add root and queue watch with explicit unqualified statistical limit.
- [ ] Native exact-head W72 regression, receipt and JUnit artifact bytes.
- [ ] Source-matched case / duration and coverage comparison.
- [ ] Source owner disposition on persistent skips and 600 s queue watch.
- [ ] Separate governance (#2041), A10 (#1996), Safety/Bandit (#2027).
- [ ] Review / protected-main admission and exact-main recurrence proof.

`authority_transfer=false; security_waiver=false; merge_authorized=false`.
