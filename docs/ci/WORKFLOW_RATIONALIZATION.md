# ABACUS CI workflow rationalisation

Policy: `ABACUS-CI-SSOT-001`  
Policy file SHA-256: `a03e9803550db55842c2efb2d467d2423ced71a07f05e291c9c764d6e6a3aef7`

## Outcome

The proposed state contains **87 workflow definitions** (86 existing plus this governance workflow). Every definition is assigned to one primary functional cluster, lifecycle stage and disposition. The pre-change baseline was PR #681 with 119 check runs (111 queued, 8 skipped) and ABACUS main with 122 check runs.

## Execution order

| Order | Lifecycle | Purpose |
|---:|---|---|
| 10 | `pr_fast` | Always-fast structural and unit evidence |
| 20 | `pr_domain` | Path-relevant domain, integration and security evidence |
| 30 | `post_merge` | Build, release, publication and reporting |
| 40 | `scheduled` | Comprehensive, maintenance and monitoring work |
| 50 | `manual` | Diagnostic or migration comparison only |
| 90 | `retire` | Remove after replacement evidence is accepted |

## Cluster ownership

| Cluster | Canonical workflow | Definitions | Intent |
|---|---|---:|---|
| `core_test` | `ci-abacus.yml` | 10 | Fast cross-version unit, pre-commit and smoke evidence. |
| `full_regression` | `ci-cd-tests.yml` | 1 | Broad OS/version/integration/coverage regression for code changes. |
| `statistics` | `ci-cd.yml` | 2 | Bootstrap, AHT, performance and statistical validation. |
| `bridge_federation` | `bridge-ci.yml` | 4 | CODEX/ABACUS bridge contract and federation smoke evidence. |
| `dmaic` | `dmaic-enterprise-ci.yml` | 8 | DMAIC phase, convergence and maturity execution. |
| `dow` | `dow-integration.yml` | 10 | DOW parent mechanics, integration, monitoring and warm-up. |
| `runtime_governance` | `governance.yml` | 12 | Runtime evidence, governance, review artifacts and schema validation. |
| `security` | `security-scan.yml` | 7 | Ruff security, Bandit, CodeQL, dependency and supply-chain scanning. |
| `delivery` | `cd-pipeline.yml` | 8 | Build, release, deployment and publication. |
| `documentation` | `docs-build.yml` | 6 | Documentation validation, rendering, export and Pages. |
| `automation` | `post-merge-pr-summary.yml` | 8 | Repository maintenance, reporting, branch and PR automation. |
| `specialised` | `qps-cost-roundtrip-contract.yml` | 7 | Bounded product or historical pipelines retained outside core CI. |
| `ci_governance` | `ci-governance.yml` | 1 | This policy, inventory, overlap and staleness gate. |
| `legacy` | — | 3 | Superseded workflows kept temporarily for manual comparison before deletion. |

## Immediate consolidation decisions

- `security-scan.yml` is the automatic security owner; standalone `bandit.yml` becomes manual comparison only.
- `bridge-ci.yml` is the bridge owner; legacy `ci.yml` becomes manual comparison only.
- `ci-codex.yml` is retired from automatic ABACUS execution. Cross-repo truth moves only through a versioned manifest/hash contract.
- Full regression, bootstrap/statistics, bridge and DMAIC suites use path-scoped PR triggers; `ci-abacus.yml` remains the fast general gate.
- Auto-merge, branch analysis and reporting remain separate because their permissions, events and side effects differ.

## Workflow inventory

| Order | Cluster | Workflow | Events | Jobs | Decision | Replacement |
|---:|---|---|---|---:|---|---|
| 10 | `ci_governance` | `ci-governance.yml` | pull_request, push, workflow_dispatch | 1 | `canonical` | — |
| 10 | `core_test` | `abacus-cicd.yml` | push, pull_request, workflow_dispatch | 6 | `keep` | — |
| 10 | `core_test` | `ariana-cicd.yml` | push, pull_request, workflow_dispatch | 2 | `keep` | — |
| 10 | `core_test` | `ci-abacus.yml` | push, pull_request, workflow_dispatch | 1 | `keep` | — |
| 10 | `core_test` | `ci-enhanced.yml` | push, pull_request, workflow_dispatch | 7 | `keep` | — |
| 10 | `core_test` | `ci-pipeline.yml` | push, pull_request, schedule, workflow_dispatch | 4 | `keep` | — |
| 10 | `core_test` | `format-check.yml` | push, pull_request, workflow_dispatch | 1 | `keep` | — |
| 10 | `core_test` | `main.yml` | push, pull_request, workflow_dispatch | 5 | `keep` | — |
| 10 | `core_test` | `pytest-config-validation.yml` | pull_request, push | 1 | `keep` | — |
| 10 | `core_test` | `smoke-test.yml` | pull_request, workflow_dispatch | 1 | `keep` | — |
| 10 | `core_test` | `tooling-ci.yml` | push, pull_request, workflow_dispatch | 5 | `keep` | — |
| 20 | `bridge_federation` | `bridge-ci.yml` | push, pull_request, workflow_dispatch | 6 | `keep` | — |
| 20 | `bridge_federation` | `codespace-federation.yml` | push, pull_request, workflow_dispatch, repository_dispatch | 1 | `keep` | — |
| 20 | `bridge_federation` | `federation-notebook.yml` | push, pull_request, workflow_dispatch | 1 | `keep` | — |
| 20 | `bridge_federation` | `gbogeb-abacus-integration-ci-cd.yml` | push, pull_request, workflow_dispatch | 10 | `keep` | — |
| 20 | `dmaic` | `book-build.yml` | push, pull_request, workflow_dispatch | 1 | `keep` | — |
| 20 | `dmaic` | `dmaic-commit-metrics.yml` | push, workflow_run, workflow_dispatch | 3 | `keep` | — |
| 20 | `dmaic` | `dmaic-enterprise-ci.yml` | push, pull_request, workflow_dispatch | 7 | `keep` | — |
| 20 | `dmaic` | `dmaic-phase-execution.yml` | none | 1 | `keep` | — |
| 20 | `dmaic` | `dmaic-v3-cd.yml` | push, release, workflow_dispatch | 7 | `keep` | — |
| 20 | `dmaic` | `dmaic-v3-ci.yml` | push, pull_request, schedule, workflow_dispatch | 9 | `keep` | — |
| 20 | `dmaic` | `dmaic-v3-cognitive-cicd.yml` | push, pull_request, workflow_dispatch | 9 | `keep` | — |
| 20 | `dmaic` | `recursive-build.yml` | push, workflow_dispatch | 1 | `keep` | — |
| 20 | `dow` | `background_orchestrator.yml` | schedule, workflow_dispatch | 2 | `keep` | — |
| 20 | `dow` | `dow-integration-ci-cd.yml` | push, pull_request, workflow_dispatch | 8 | `keep` | — |
| 20 | `dow` | `dow-integration.yml` | push, pull_request, workflow_dispatch, schedule | 4 | `keep` | — |
| 20 | `dow` | `dow-main-cicd.yml` | pull_request, push, schedule | 1 | `keep` | — |
| 20 | `dow` | `dow-monitoring.yml` | none | 1 | `keep` | — |
| 20 | `dow` | `dow-scheduled.yml` | schedule, workflow_dispatch | 1 | `keep` | — |
| 20 | `dow` | `dow-sprint6-cicd.yml` | push, pull_request, workflow_dispatch | 7 | `keep` | — |
| 20 | `dow` | `dow-sut-pipeline.yml` | workflow_dispatch, schedule, push | 6 | `keep` | — |
| 20 | `dow` | `qps-dow-wave01-warmup.yml` | workflow_dispatch, push | 1 | `keep` | — |
| 20 | `dow` | `sprint-trigger.yml` | schedule, workflow_dispatch | 1 | `keep` | — |
| 20 | `full_regression` | `ci-cd-tests.yml` | push, pull_request, schedule, workflow_dispatch | 10 | `canonical` | — |
| 20 | `runtime_governance` | `deployment-enforcement.yml` | workflow_dispatch | 1 | `keep` | — |
| 20 | `runtime_governance` | `governance-drift-detection.yml` | schedule, workflow_dispatch | 1 | `keep` | — |
| 20 | `runtime_governance` | `governance.yml` | push, pull_request, workflow_dispatch | 1 | `keep` | — |
| 20 | `runtime_governance` | `inventory.yml` | schedule, workflow_dispatch | 1 | `keep` | — |
| 20 | `runtime_governance` | `review-artifact-validation.yml` | push, pull_request | 1 | `keep` | — |
| 20 | `runtime_governance` | `runtime-governance.yml` | workflow_dispatch | 1 | `keep` | — |
| 20 | `runtime_governance` | `runtime-smoke.yml` | push, pull_request | 1 | `keep` | — |
| 20 | `runtime_governance` | `runtime-verification.yml` | workflow_dispatch, workflow_run | 1 | `keep` | — |
| 20 | `runtime_governance` | `validate_docs.yml` | push, pull_request | 1 | `keep` | — |
| 20 | `runtime_governance` | `validate-setup.yml` | workflow_dispatch | 1 | `keep` | — |
| 20 | `runtime_governance` | `validation.yml` | push, pull_request, workflow_dispatch | 1 | `keep` | — |
| 20 | `runtime_governance` | `yaml-validation.yml` | push, pull_request | 1 | `keep` | — |
| 20 | `security` | `codeql.yml` | push, pull_request, schedule | 1 | `keep` | — |
| 20 | `security` | `dependency-review.yml` | pull_request | 1 | `keep` | — |
| 20 | `security` | `osv-scanner.yml` | push, pull_request, merge_group, schedule | 2 | `keep` | — |
| 20 | `security` | `reusable-security.yml` | workflow_call | 1 | `keep` | — |
| 20 | `security` | `security-dashboard.yml` | workflow_run, schedule, workflow_dispatch | 1 | `keep` | — |
| 20 | `security` | `security-scan.yml` | push, pull_request, schedule | 2 | `keep` | — |
| 20 | `security` | `semgrep.yml` | push, pull_request, schedule, workflow_dispatch | 1 | `keep` | — |
| 20 | `specialised` | `delta-1-baseline.yml` | workflow_dispatch | 1 | `keep` | — |
| 20 | `specialised` | `qps_line_s.yml` | pull_request, workflow_dispatch | 1 | `keep` | — |
| 20 | `specialised` | `qps-cost-roundtrip-contract.yml` | pull_request, push | 1 | `keep` | — |
| 20 | `specialised` | `qps-v24-refresh-unresolved-selector.yml` | workflow_dispatch, push | 1 | `keep` | — |
| 20 | `specialised` | `reusable-ci.yml` | workflow_call | 1 | `keep` | — |
| 20 | `specialised` | `session_tuple_ci.yml` | push, pull_request, workflow_dispatch | 3 | `keep` | — |
| 20 | `specialised` | `v23-cicd.yml` | push, pull_request, workflow_dispatch | 2 | `keep` | — |
| 20 | `statistics` | `bootstrap-integration.yml` | push, pull_request, workflow_dispatch | 6 | `keep` | — |
| 20 | `statistics` | `ci-cd.yml` | push, pull_request, schedule | 8 | `keep` | — |
| 30 | `delivery` | `cd-pipeline.yml` | push, pull_request, workflow_dispatch | 6 | `keep` | — |
| 30 | `delivery` | `cd-unified.yml` | push, pull_request, schedule, workflow_dispatch | 7 | `keep` | — |
| 30 | `delivery` | `cd.yml` | push, pull_request, schedule, workflow_dispatch | 1 | `keep` | — |
| 30 | `delivery` | `delta-1-deploy.yml` | workflow_dispatch | 1 | `keep` | — |
| 30 | `delivery` | `delta-1-release.yml` | workflow_dispatch | 1 | `keep` | — |
| 30 | `delivery` | `history-purge-20260827.yml` | push | 1 | `keep` | — |
| 30 | `delivery` | `release.yml` | push, workflow_dispatch | 2 | `keep` | — |
| 30 | `delivery` | `remove-public-binaries.yml` | push | 1 | `keep` | — |
| 30 | `documentation` | `deploy-docs.yml` | push, workflow_dispatch | 3 | `keep` | — |
| 30 | `documentation` | `docs-build.yml` | push | 1 | `keep` | — |
| 30 | `documentation` | `export-docs.yml` | push, workflow_dispatch | 1 | `keep` | — |
| 30 | `documentation` | `pages.yml` | push, workflow_dispatch | 1 | `keep` | — |
| 30 | `documentation` | `reports.yml` | schedule, workflow_dispatch, push | 2 | `keep` | — |
| 30 | `documentation` | `update-docs.yml` | push, workflow_dispatch | 1 | `keep` | — |
| 40 | `automation` | `auto-merge-prs.yml` | pull_request, check_suite, workflow_dispatch | 3 | `keep` | — |
| 40 | `automation` | `branch-analysis.yml` | pull_request, workflow_dispatch | 2 | `keep` | — |
| 40 | `automation` | `branch-pruner.yml` | workflow_dispatch | 1 | `keep` | — |
| 40 | `automation` | `ci_monitor_and_issue_creator.yml` | workflow_run, pull_request, deployment_status | 3 | `keep` | — |
| 40 | `automation` | `ci-failure-debug-rerun.yml` | workflow_run | 1 | `keep` | — |
| 40 | `automation` | `copilot-pr-creator.yml` | workflow_dispatch, workflow_call | 1 | `keep` | — |
| 40 | `automation` | `dashboard-health.yml` | schedule, workflow_dispatch | 1 | `keep` | — |
| 40 | `automation` | `post-merge-pr-summary.yml` | pull_request | 1 | `keep` | — |
| 50 | `legacy` | `bandit.yml` | push, pull_request, schedule | 1 | `consolidate` | `security-scan.yml` |
| 50 | `legacy` | `ci.yml` | push, pull_request | 3 | `consolidate` | `bridge-ci.yml` |
| 90 | `legacy` | `ci-codex.yml` | push, pull_request, workflow_dispatch | 1 | `retire` | `CODEX/.github workflows via versioned manifest; no ABACUS-to-CODEX dispatch` |

## Control rule

A workflow change fails CI governance when a definition is unclassified, matches more than one policy rule, or a canonical owner is missing. This report is derived; `ci/governance/workflow_policy.json` is the SSOT.

