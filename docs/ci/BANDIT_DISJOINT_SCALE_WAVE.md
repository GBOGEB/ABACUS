# Bandit at-scale disjoint worker wave (proposal-only)

Status: execution plan, not an authenticated launch or security disposition.
Authority: ABACUS #1860, #1877. Source producer: canonical full/configured
  Bandit JSON and disjoint census from #1915.

## Provenance and non-negotiable constraints

Freeze `repository`, `main_sha`, `pr_head_sha`, `scan_tool_version`,
  `scan_command_hash`, `config_hash`, `source_tree_hash`, `report_sha256`, and
  `collection_timestamp` per scan. Never compare full and configured scans. A
  finding in a touched file is not necessarily introduced. Missing scanner
  evidence is UNKNOWN, not zero. No scanner skip, nosec, waiver, or automatic
  security approval is authorized.

## Exclusive partition contract

An intake producer validates each Bandit result as a structured object with a
  safe repository-relative normalized path, rule, positive line number and
  immutable fingerprint. Full and configured reports have separate namespaces.

Ownership is **by canonical file**, not finding: every file belongs to exactly
  one lane. Priority: B5 test files; B3 subprocess rule family; B4
  files/secrets; B2 remainder. When a file has multiple rule families, all of
  its findings remain with its single owner. Reject ambiguous, unsafe or
  duplicate ownership.

### Owner responsibilities

- **B2-source:** Remaining source files. Repair unsafe assertions or
  cryptographic patterns while preserving intended semantics.
- **B3-subprocess:** Files owning subprocess findings. Validate arguments,
  shell boundaries, return codes, and negative regression tests.
- **B4-files-secrets:** Files owning filesystem or secret findings. Check
  permissions, paths, sensitive-data handling, and redaction.
- **B5-tests:** Test paths. Improve fixtures without hiding production
  findings or reducing regression coverage.
- **LDAB historian (read-only):** No source writes. Link exact native runs,
  fingerprints, BD roots, and authenticated debug receipts.
- **CI proof (read-only):** No source writes. Validate JUnit, scanner JSON,
  exact-head CI, and source-matched coverage.

No two workers may edit the same file or publish a shared census artifact. The
  controller owns baseline snapshots and final reconciliation.

## Small batch dispatch

1. Require frozen exact-head full and configured scan artifacts with valid
  SHA256 and scanner/settings identities; preserve raw input immutable.
1. Run deterministic disjoint census; publish path-owner manifest,
  finding-count reconciliation, per-lane root signatures and counts. Reject
  sum-of-lanes mismatch.
1. Rank within each lane by severity, confidence, blast radius and
  repeated first-red evidence. Group 1-5 files per candidate repair PR; avoid
  large shotgun edits.
1. Dispatch a worker **only** through an authorized authenticated runner.
  Record `worker_id`, `launch_id`, `runner_id`, `start/end`,
  `input_artifact_sha`, `owned_paths`, `branch`, `commit_sha`, `job_url`,
  `exit_code`, `junit_url`, `coverage_url`, `bandit_url`, `ldab_session_id`
  and `rex_receipt_url` (null if unavailable).
1. First pass: focused tests and re-scan exact owned paths. Second pass:
  one integrated exact-head full/configured canonical scan and mandatory
  quality/security CI. Calculate unique opened and resolved fingerprints
  against comparable frozen base; report raw finding counts and eligible-file
  denominators separately.
1. Require independent non-author security review, effective main branch
  protection and terminal required checks before any admission or merge. Merge
  serially, rebase descendants and remeasure main after each batch.

## Checkpoints / fail-closed assertions

- Every reported file maps to exactly one owner, with `sum(lane_findings)
  == global_unique_findings`.
- Every worker's changed paths are a subset of owned paths. Violation
  invalidates the proposal.
- `new = |after - before|`, `resolved = |before - after|`, `net = resolved
  - new`; identity/config mismatch makes each delta UNKNOWN.
- If Bandit fails with exit 1 and valid JSON, treat as findings-present,
  not scanner crash. Other exit codes require classified diagnostics.
- Safety exit 64 is a separate dependency/scanner root until stderr/JSON
  establishes a diagnosis.
- Coverage requires source-matched XML, JUnit and exact eligible-line
  numerators. Changed-line instrumentation gaps remain UNKNOWN.
- Full Red Proof Summary is propagated until its security and coverage
  dependencies pass.
- LDAB count means authenticated sessions with steps/port/trace receipt; an
  assessment or declared capability is not a launch.
- Required CI producers may share artifact/parsing utilities, but shall not
  be consolidated away until check-name continuity, runtime savings and
  equivalent enforcement are demonstrated.
- Work is complete only when current protected main has source-bound
  accepted CI/security coverage, independent approval, and a recorded BD
  root-cause delta.

## Initial historical observation (not contemporary census)

At PR #1923 run 38470950344, Bandit full scan reported 6,333 findings;
  touched-file 1 and untouched 6,332 are **not** introduced/resolved counts.
  Safety returned exit 64; coverage and downstream summary were red. Exact
  current-head Bandit fingerprint counts, native LDAB launches and worker
  capacity remain UNKNOWN until the producer artifacts are collected and
  validated.

`authority_transfer=false`; `security_waiver=false`;
  `authenticated_launches=UNKNOWN`; `formal_credit_delta=0`.
