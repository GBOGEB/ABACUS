# QPS Metric Census — ABACUS

**Status:** draft adoption; not enabled on the default branch until separately admitted and merged.

- Repository: `GBOGEB/ABACUS`
- Lane: `ABACUS`
- Engineering/test scope: Python compatibility, CI first-red taxonomy, unit and branch coverage evidence
- Toolkit reference: `GBOGEB/pipeline-automation-hub@52233b5b3209d2b0878c530adcb0d51d86cd4d87` (immutable pilot pin; renew after canonical promotion)
- Receives manually approved `workflow_dispatch` or opt-in `repository_dispatch` event `qps-metric-census-v1`.
- Routes: `native_checks`, `coverage_catalog`. Both are bounded read-only DAG jobs; never execute arbitrary dispatch payload commands.
- Each request binds `wave + lane + repository + expected source SHA + selector` to an ID; stale or mismatched heads fail closed.
- Machine-readable receipts contain execution SHA, target SHA, run ID, attempt, job ID and observed metadata; **tests/coverage remain UNKNOWN** until independently attested by native test/coverage jobs.
- Check names are not accepted causal-root IDs, and test-file counts are **not tests executed**.
- Permissions: `contents:read`, `actions:read`. No merge, security waiver, branch protection change, code mutation or owner acceptance.
- Consumer: Mission Control Metric Atlas `tools/metric-atlas/metric_atlas/census.py`. See [federation owner](https://github.com/GBOGEB/pipeline-automation-hub/pull/622) and ABACUS root census [#2079](https://github.com/GBOGEB/ABACUS/issues/2079).

## DoD / DoV

DoD: owner-source PR review + unchanged repository-required gates; validator first passes negative tests and can create source-bound metadata receipt from a real run. DoV: one observed receiver workflow per requested route at the intended source SHA, independently inspected artifact ZIP/member bytes, and a correct federation rollup. A receiver passing does **not** establish domain-specific acceptance, security approval, coverage improvement or merge eligibility.
