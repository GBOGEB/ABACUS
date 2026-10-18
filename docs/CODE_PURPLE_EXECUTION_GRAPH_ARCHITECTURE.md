# CODE PURPLE — ABACUS graph, LDAB and merge runway

Status: read-only architecture and pinned observation prototype.
ABACUS owns execution evidence. CODEX owns cross-repository orchestration.
QPS retains engineering acceptance. No security waiver or authority transfer.

## Views and evidence contract

- The viewer is at `docs/code_purple_execution_graph.html`.
  It offers dark/light mode, job lanes, focus and an evidence inspector.
  Its original diagram jobs are historical examples, not live metrics.
- The merge runway reads a static JSON observation from
  `docs/data/code_purple_abacus_merge_census_20261012.json`.
  It never accesses private GitHub credentials or mutates repository state.
  The observed date, main SHA and every PR head SHA remain visible.
- ABACUS Matrix (`ci-abacus.yml`) has a planner, three jobs,
  proof-completeness and a compatibility gate.
  MIP B0 uses an independent coverage census and proposal-worker matrix.
  A successful Actions job is **not** an authenticated CODEX crew run.
- Admission requires an exact-head first-red decision, trustworthy
  review/security evidence, resolved threads, all required checks
  terminal and green, and a controlled merge/main readback.
- Existing authorities: ABACUS issue #1860; CODEX issue #977 and PR #975;
  ABACUS `MIP/README.md`. Do not create a parallel SSOT.

## Merge runway: observed and derived measures

The 12 October readback observed 20 open PRs on ABACUS,
main `53688f26d5b9c4cd074ef905e426849e85324383`.

- 18 Ready for review; two Draft (#1876 and #1834).
- Five PR heads have zero **completed red** check records.
  They are #1858, #1869, #1854, #1843 and #1842.
  A zero-red head still can have a pending feedback gate or missing review.
- Fifteen heads show at least one completed red check.
- Zero heads had a successful terminal `PR Feedback Gate` in this census.
- Two feedback-gate checks were terminal red because unresolved
  review threads were present (#1847 and #1855).
- Three PRs (#1839, #1841 and #1842) were based on an older main SHA.
  Retargeting requires dependency assessment and exact-head revalidation.
- Each recorded check failure name is one **check entry**, not a distinct
  vulnerability, test case or root cause. Root attribution is UNKNOWN
  without a same-policy main comparison and job-level evidence.

These are observation facts, not engineering DoV or an admission waiver.
The snapshot is static: every change to a PR head invalidates the
prior check state. Regenerate evidence; never silently label it live.

## Metrics added to the CODE PURPLE measurement contract

All denominators, periods and provenance are compulsory.
An UNKNOWN value shall not be treated as zero.

1. **Open WIP**: open PR count at a pinned observation, target 0.
   Breakdown by Draft, Ready and admission state.
2. **Gate throughput**: terminal green feedback gates divided by
   PR heads evaluated in that cohort. Missing reviews are withheld.
3. **Red-head fraction**: PR heads with at least one completed material
   red divided by all open PRs with a head-bound check census.
4. **First-red convergence**: unique independently attributable roots
   resolved per bounded iteration. Deduplicate propagated failures.
5. **Gate wait time**: elapsed time from latest head push until
   exact-head terminal gate; use native timestamps, not guesswork.
6. **Review re-entry pressure**: changed-head review cycles and
   repeated review requests per PR. Limit redundant same-head retries.
7. **Review budget backlog**: PR heads blocked only by code or security
   review, with quota state and human-owner decisions kept separate.
8. **CI replay cost**: workflow-run attempts, total job-minutes and
   cancelled/superseded execution minutes per admitted head.
9. **Net queue burn**: admitted merges plus owner-dispositioned closures
   minus new PRs over a declared interval. Count classifications
   separately; closure is not equivalent to a passing merge.
10. **Debt regression delta**: new and removed *unique* finding
    identities against the same scanner, config, baseline and rules.
11. **Coverage improvement**: changed covered/coverable lines,
    test-case evidence and main/PR/diff measurements separately.
12. **Proof freshness**: current-head and baseline SHA match, with
    stale or missing receipts explicitly withheld.
13. **Merge conflict/dependency age**: stale-base branches,
    required retargeting and transitive blockers; no blind rebase.
14. **SIPOC / pay-it-forward yield**: independently accepted reusable
    repair receipts per attempted consumer reuse. No acceptance by
    publication alone.
15. **LDAB diagnostic burden**: unique diagnostic signatures,
    recurrence, mean time to resolve and the number of PRs blocked.
16. **OVERTIME value**: measured spare-runner minutes actually reused,
    preemptions and saved critical-path time. An advisory task plan
    is not a dispatched or completed worker.

## Additional metrics to drive zero open PRs

### Cohort-level progress

Report a beginning snapshot, end snapshot, and all transition events.
A PR that closes without merging must carry its owner-approved
supersession or disposition link. Show **productive merges** separately
from administrative PR closures.

### Blocker reduction

Prioritize independently provable first-red families.
When ten PRs show the same historical full-red check, measure one
root-cause repair and the affected dependents, not ten repaired defects.
Never compare different check populations as one test suite.

### Queue scheduling

Keep the gate-recovery lane (#1858 and #1847) separate from:
the first merge candidate (#1857), ratchet bootstrap (#1859),
federation (#1855 and #1873), documentation and easy low-risk work.
Idle OVERTIME work is possible only after actual free capacity,
completed dependencies, exact source pins and disjoint write scope
are shown. No permission or security authority is inherited.

## Typed evidence and first-red production contract

A future governed producer shall emit:

- Observation identity, schema, timestamp and source repository.
- PR number, full head/main SHA and policy/config fingerprint.
- Workflow, run attempt, job, step, result and source URL.
- First independent material red with root classification,
  as distinct from downstream, inherited and unknown results.
- Code/security review state, reviewer identity where authorized,
  unresolved threads and required-status evidence.
- Coverage numerator and denominator, base SHA and report source.
- Crew principal, dispatch and receipt IDs only when real
  authenticated work was performed.
- One semantic delta receipt to follow the previous accepted state.

Suggested edge types: NEEDS, BLOCKS, PRODUCES, VERIFIED_BY,
TRACKED_AS, REPLACES, DISPATCHES and ACCEPTED_BY.
Never infer causality from visual proximity or raw check counts.

## LDAB, coverage and temporal windows

LDAB lives at
`MIP/receipts/repo_self_index.json#/assessments/repo_self_assess_debug_ldab`.
The diagnostic view needs unique errors, severity, recurrence,
source URLs and resolved/unresolved root IDs.

Coverage main, PR broad and PR diff are separate populations.
Historical reference only: main 36.85% (11 October),
PR broad 36.92% and PR diff 51% (12 October).
These are **not** this observation's current measurements.

Top 7/14/21 windows shall publish absolute window timestamps,
separate totals by PR, root cause and BD item, and contain
an UNKNOWN flag whenever evidence is missing.

## Definition of done

- Exact source/head validation, missing/invalid JSON fail-closed.
- Regression fixtures for skips, cancellations, stale heads,
  first-red propagation and changed policy fingerprints.
- Static and live-looking data never share the same status label.
- Playwright dark/light, responsive, focus and evidence-link QA.
- One publisher, exact deployment SHA and external content readback.
- No workers or merged PRs are inferred from an HTML rendering.
- After a governed merge, rebaseline against actual ABACUS main.

This PR is an architecture and evidence viewer, not an autonomous
production telemetry or merge service.


## Supplemental weighted N+i graph and USER SPINE proposal (18 October 2026)

The proposed [weighted-user-spine read-only projection](ci/NPLUS_WEIGHTED_USER_SPINE_V1.md) reuses this canonical architecture; it does **not** supersede the existing graph viewer, repo authority, LDAB, merge runway, or CODEX/QPS source ownership. Its [typed source/run category snapshot](data/NPLUS_WEIGHTED_RUN_CATEGORY_20261018.json) distinguishes executed workflow runs, successful runs, failed runs, workflow IDs and JUnit test cases. Network edge widths use one absolute square-root count scale across three adjacent views. N23's 12 QPS repetitions are not 12 independent test suites.

[USER SPINE Mermaid source](ci/NPLUS_WEIGHTED_USER_SPINE_V1.mmd) adds user choice/override/veto, competing diagnostic lanes and an explicitly separate next-iteration feedback return. User preference is advisory: source owners, native evidence, required checks, eligible review and QPS child authority remain independent prerequisites. No dispatch, policy waiver, accepted root closure, or correctly governed merge is inferred from the projection. The visualization source/render assets require separate owner acceptance before publication. `MERGE_ADMISSION=HOLD`.
