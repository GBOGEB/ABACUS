# Bandit / LDAB error census crosswalk (evidence contract)

This is a non-authoritative linkage contract for ABACUS #1860, PR #1915, and the
MIP `repo_self_assess_debug_ldab` lane. It does **not** claim a debug session,
worker dispatch, security clearance, or debt closure.

## Join keys

Each observable error/finding shall record `repository`, full `source_sha`,
`producer_run_id`, `producer_job_id`, `source_path`, `rule_or_error_code`,
`line`, `normalized_fingerprint`, `owner_lane`, `first_red_signature`,
`disposition`, and `evidence_url`. LDAB-specific linkage shall record
`debug_session_id`, `debug_step_id`, `runner_id`, `port_lease_id`, and
`rex_receipt_url` **only if authenticated native receipts exist**. Missing
fields remain null/UNKNOWN, not zero or fabricated IDs.

## Source evidence and taxonomy

- Bandit full scan: `bandit-evidence/full.json`, disjoint file ownership:
  `bandit-evidence/disjoint.json`, configured scan:
  `bandit-evidence/configured.json`. Full and configured use separate
  denominators and scanner configuration identities.
- CI test evidence: `bandit-evidence/junit.xml` and
  `bandit-evidence/coverage.xml`; no line or branch metric without
  source-SHA-matched numerator and denominator.
- Governance: `bandit-evidence/workflow-audit.json` and
  `docs/ci/WORKFLOW_RATIONALIZATION.md`; second-pass equality is required.
- LDAB observability: `MIP/receipts/repo_self_index.json` assessment lane
  `repo_self_assess_debug_ldab`. An assessment is **not** proof of an executed
  debugger session.
- Root cause is keyed by (normalized error signature, owning file,
  producer/config identity); repeated CI symptoms may share one primary first
  red. Do not double-count downstream failures.
- Debt transitions: OPEN, RESOLVED, REOPENED, INHERITED, UNVERIFIED. A
  proposal/run success does not imply RESOLVED.
- BD queue statistics: report open/closed counts **only from a scope-defined
  exact-head census**, with historical and current fingerprints compared under
  identical configuration. If missing, mark UNKNOWN.

## Minimal acceptance

1. Verify all report source SHAs and scanner settings, reject missing or
   ambiguous ownership.
2. Reconcile every finding to one B2/B3/B4/B5 owner (exclusive per file) and a
   root-cause key.
3. Attach authentic LDAB runner/debug/port evidence where available; otherwise
   leave linkage UNKNOWN.
4. Record opened/resolved/net fingerprint deltas separately for full and
   configured scans.
5. Publish receipts as observations only: `authority_transfer=false`,
   `security_waiver=false`. Human independent review and protected-main
   admission remain separate gates.
