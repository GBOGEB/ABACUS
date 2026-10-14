# MIP root taxonomy extension v1

Status: PROPOSED / OBSERVATIONAL. No security waiver or merge authority.
Canonical authority remains `docs/ci/BD_LDAB_JOIN_CONTRACT_20261014.md`,
`tools/everred_v3/src/four_planes.py`, and the existing LDAB adapter.
This extension does not replace their root IDs, schema, or evidence rules.

## Purpose

Separate causal identity from affected jobs, evidence, symptoms and proposed
remedies. A failed job is not automatically a distinct causal root.

## Root classes (secondary labels, never replacement identities)

| Code | Decision |
| --- | --- |
| CONTRACT | Producer and test contract disagree |
| GOVERNANCE | Policy and inventory diverge |
| CONTENT | Restricted-content guard blocks a change |
| FORMAT | Linter identifies a source-format defect |
| SECURITY | Scanner reports a scoped finding |
| COVERAGE | Tested source numerator or denominator fails |
| RUNTIME | Authenticated execution or debugger failure |
| PRODUCER | Missing or invalid output artifact |
| INFRA | Runner or toolchain failure |
| UNKNOWN | Evidence insufficient |

## Observation contract

Each observation SHALL retain repository, exact source SHA, run ID, job ID,
workflow, step, evidence URL, observed failure signature, source path where
available, root candidate ID, class, evidence level and disposition.
A root-to-consumer edge SHALL be supported by a specific observation.
Only an authenticated producer can promote an observation to VERIFIED.
Never infer a root from a filename or a successful proposal worker.

Use evidence levels SOURCE_DISCOVERY_ONLY, CONTRACT_EXECUTED,
NATIVE_JOB_VERIFIED and OUTPUT_BYTES_VERIFIED, with distinct
SECURITY_REVIEW_PENDING and ADMISSION_HOLD flags.

## Fingerprint and comparisons

Use existing canonical fingerprints when present. For CI-only candidates,
hash canonical JSON of repository, failure code, normalized assertion or
diagnostic, and source contract identifier. Exclude job ID, timestamps,
retry count and Python version from causal identity; preserve these as
separate observations. Normalize paths cautiously: a moved source line is
not by itself a repaired finding.

Only compare opened/resolved/persistent counts when repository, scanner
version, configuration digest, exclusions and comparable scope are
established. Otherwise delta is UNKNOWN, not zero. Separate CI roots,
Bandit findings, OSV advisories, Ruff violations, coverage lines/branches
and debugger receipts into their own units.

## Current bounded case study — PR #1979

Baseline SHA: 85dad8fbdab530d40e6ccf2f664c455f89454aad.
Candidate SHA: f89bf0f24ed670db12dde1118f8b11d94d5509db.

- CONTRACT SUT-H1: historical two Python-version job failures share one
  literal-heading assertion; native candidate SUT jobs 3.10 and 3.12 PASS.
- GOVERNANCE GOV-01: governance and Bandit census fail on stale derived
  WORKFLOW_RATIONALIZATION.md; two consumers, one observed root.
- CONTENT A10-01: restricted term in workflow_policy.json; exact match
  remains withheld/UNKNOWN. Do not weaken guard.
- FORMAT YAML-01: ten YAML line-length failures in
  .github/workflows/code-purple-sut-gui.yml, not Markdown errors.

No broad security, coverage, producer determinism or governed merge
improvement is claimed by this case study.

## MIP feedback cycle

1. MEASURE: capture exact SHA/run/job and native first-red.
2. IDENTIFY: fingerprint root; map consumer edges; mark unknowns.
3. PRIORITIZE: rank by severity, consumer fan-out, recurrence and repair
   confidence; never treat rank as permission to bypass security.
4. IMPROVE: repair once in source with disjoint file ownership.
5. PROVE: targeted positive/negative tests, native exact-head CI,
   artifact hashes and separate security/admission verification.
6. PERPETUATE: store comparable before/after evidence and recurrence
   checks; promote root to CLOSED only with a closure receipt.

## Invariants

- A root is not closed merely because a job was retried or a PR merged.
- No unverified zero, inferred runtime, fabricated denominator or
  self-approval. A bot comment is not an eligible GitHub approval.
- Existing canonical schemas and admission controls remain authoritative.
- Draft changes and telemetry are not merge authority.
