# QPS Metric Census — ABACUS

**Status:** Adoption PR; receiver is not yet on the default branch.

- Repository: `GBOGEB/ABACUS`
- Lane: `ABACUS`
- Scope: Python compatibility, first-red taxonomy, unit-test and
  control-flow branch-coverage evidence
- Toolkit: immutable Mission Control commit
  `dd606d8897c70fa797a3a585fa12850bacd1d9e1`
- Entry points: approved `workflow_dispatch` or opt-in
  `repository_dispatch` event `qps-metric-census-v1`
- DAG routes: `native_checks` and `coverage_catalog`; both read-only
- Request identity: wave, lane, repository, expected SHA, selector and ID
- Fail-closed rule: stale or mismatched source heads are rejected
- Receipts: execution SHA, target SHA, run ID, attempt, job ID and metadata
- Native tests and coverage: UNKNOWN until independent log/artifact proof
- First-red: matching job names are not causal-root evidence
- Test-file counts do not count as executed tests
- Token permissions: `contents: read`, `actions: read`, `checks: read`
- No authority to merge, waive security, relax rules or accept engineering

Mission Control [Metric Atlas owner][atlas] and ABACUS
[root census owner][root-census] retain their separate responsibilities.

[atlas]: https://github.com/GBOGEB/pipeline-automation-hub/pull/622
[root-census]: https://github.com/GBOGEB/ABACUS/issues/2079

## Definition of Done / Verification

**DoD:** Repository owner review and all existing required checks.
Negative tests must pass and a real run must emit source-bound metadata.

**DoV:** Observe each requested route at the intended source SHA.
Inspect native run/job/attempt and actual ZIP/member bytes independently.
Produce an identity-validated federation roll-up.

A passing census receiver is not domain acceptance, security approval,
coverage improvement, or merge authorization.
