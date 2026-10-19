<!-- markdownlint-disable MD013 MD060 -->

# ABACUS CI workflow rationalisation

Policy: `ABACUS-CI-SSOT-001`  
Policy SHA-256 (canonical sorted JSON bytes of `ci/governance/workflow_policy.json`): `4d781b34231a4c6884e145c1bd2a4898c0c92cbe79f0057cd306171836c70faa`

## Outcome

The repository currently contains **209 workflow definitions**. All **209** are assigned to one primary functional cluster and lifecycle stage.

The observed baseline that motivated this control was PR #681 with 119 check runs (111 queued, 8 skipped) and main with 122 check runs.

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
| `core_test` | `ci-abacus.yml` | 21 | Fast cross-version unit, pre-commit and smoke evidence. |
| `full_regression` | `ci-cd-tests.yml` | 1 | Broad OS/version/integration/coverage regression for code changes. |
| `statistics` | `ci-cd.yml` | 18 | Bootstrap, AHT, performance and statistical validation. |
| `bridge_federation` | `bridge-ci.yml` | 20 | CODEX/ABACUS bridge contract and federation smoke evidence. |
| `dmaic` | `dmaic-enterprise-ci.yml` | 9 | DMAIC phase, convergence and maturity execution. |
| `dow` | `dow-integration.yml` | 22 | DOW parent mechanics, integration, monitoring and warm-up. |
| `runtime_governance` | `governance.yml` | 29 | Runtime evidence, governance, review artifacts and schema validation. |
| `security` | `security-scan.yml` | 12 | Ruff PR security, scheduled Bandit, CodeQL, dependency and supply-chain scanning. |
| `delivery` | `cd-pipeline.yml` | 8 | Build, release, deployment and publication. |
| `documentation` | `docs-build.yml` | 7 | Documentation validation, rendering, export and Pages. |
| `automation` | `post-merge-pr-summary.yml` | 13 | Repository maintenance, reporting, branch and PR automation. |
| `specialised` | `qps-cost-roundtrip-contract.yml` | 45 | Bounded product or historical pipelines retained outside core CI. |
| `ci_governance` | `ci-governance.yml` | 2 | This policy, inventory, overlap and staleness gate. |
| `legacy` | — | 2 | Superseded workflows kept temporarily for manual comparison before deletion. |

## Immediate consolidation decisions

- `security-scan.yml` is the Ruff PR/push security owner; `bandit.yml` retains scheduled/manual Bandit SARIF evidence.
- `bridge-ci.yml` is the bridge owner; legacy `ci.yml` becomes manual comparison only.
- `ci-codex.yml` is retired from automatic ABACUS execution. Cross-repo truth travels only through a versioned manifest/hash contract.
- Full regression, bootstrap/statistics, bridge and DMAIC suites use path-scoped PR triggers; `ci-abacus.yml` remains the fast general gate.
- Auto-merge, branch analysis and reporting remain separate because they have different permissions, events and side effects.

## Permission controls

Make PR-triggered workflows with write-class GitHub token scopes explicit and reviewable.

| Control | Workflows |
|---|---|
| PR write exceptions | `bootstrap-integration.yml`, `branch-hygiene.yml`, `codeql.yml`, `dependency-review.yml`, `gloob-causal-responder.yml`, `osv-scanner.yml`, `post-merge-pr-summary.yml`, `pr-feedback-gate.yml`, `semgrep.yml`, `w67-measured-id-pulse.yml` |
| `pull_request_target` write exceptions | none |

## Workflow inventory

| Order | Lifecycle | Cluster | Workflow | Events | Jobs | Decision | Replacement |
|---:|---|---|---|---|---:|---|---|
| 10 | `pr_fast` | `ci_governance` | `ci-governance.yml` | pull_request, push, workflow_dispatch | 1 | `canonical` | — |
| 10 | `pr_fast` | `core_test` | `abacus-cicd.yml` | push, pull_request, workflow_dispatch | 6 | `keep` | — |
| 10 | `pr_fast` | `core_test` | `ariana-cicd.yml` | push, pull_request, workflow_dispatch | 2 | `keep` | — |
| 10 | `pr_fast` | `core_test` | `ci-abacus.yml` | push, pull_request, schedule, workflow_dispatch | 6 | `keep` | — |
| 10 | `pr_fast` | `core_test` | `ci-enhanced.yml` | push, pull_request, schedule, workflow_dispatch | 7 | `keep` | — |
| 10 | `pr_fast` | `core_test` | `ci-pipeline.yml` | push, pull_request, schedule, workflow_dispatch | 4 | `keep` | — |
| 10 | `pr_fast` | `core_test` | `format-check.yml` | push, pull_request, workflow_dispatch | 1 | `keep` | — |
| 10 | `pr_fast` | `core_test` | `main.yml` | push, workflow_dispatch | 5 | `keep` | — |
| 10 | `pr_fast` | `core_test` | `pytest-config-validation.yml` | pull_request, push | 1 | `keep` | — |
| 10 | `pr_fast` | `core_test` | `smoke-test.yml` | pull_request, workflow_dispatch | 1 | `keep` | — |
| 10 | `pr_fast` | `core_test` | `testpilot-preflight.yml` | pull_request, push, workflow_dispatch | 1 | `keep` | — |
| 10 | `pr_fast` | `core_test` | `tooling-ci.yml` | push, pull_request, workflow_dispatch | 5 | `keep` | — |
| 10 | `pr_fast` | `security` | `a10-guard.yml` | pull_request, push | 1 | `keep` | — |
| 20 | `pr_domain` | `automation` | `code-purple-hosted-operator.yml` | pull_request, workflow_dispatch | 2 | `keep` | — |
| 20 | `pr_domain` | `automation` | `post-merge-summary-contract.yml` | pull_request, push | 1 | `keep` | — |
| 20 | `pr_domain` | `bridge_federation` | `abacus-missioncontrol-stage-contract-qa.yml` | pull_request, workflow_dispatch | 1 | `keep` | — |
| 20 | `pr_domain` | `bridge_federation` | `bridge-ci.yml` | push, pull_request, workflow_dispatch | 6 | `keep` | — |
| 20 | `pr_domain` | `bridge_federation` | `codespace-federation.yml` | push, pull_request, workflow_dispatch, repository_dispatch | 1 | `keep` | — |
| 20 | `pr_domain` | `bridge_federation` | `creq-federation-ci.yml` | pull_request, workflow_dispatch | 1 | `keep` | — |
| 20 | `pr_domain` | `bridge_federation` | `cryoplant-federation.yml` | push, pull_request, schedule, workflow_dispatch | 2 | `keep` | — |
| 20 | `pr_domain` | `bridge_federation` | `dependency-spine-peer-census.yml` | pull_request, push, workflow_dispatch, schedule | 1 | `keep` | — |
| 20 | `pr_domain` | `bridge_federation` | `dependency-spine-stage-only.yml` | pull_request, workflow_dispatch | 1 | `keep` | — |
| 20 | `pr_domain` | `bridge_federation` | `federation-delivery-consumer.yml` | pull_request, push, workflow_dispatch | 2 | `keep` | — |
| 20 | `pr_domain` | `bridge_federation` | `federation-notebook.yml` | push, workflow_dispatch | 1 | `keep` | — |
| 20 | `pr_domain` | `bridge_federation` | `gbogeb-abacus-integration-ci-cd.yml` | push, workflow_dispatch | 10 | `keep` | — |
| 20 | `pr_domain` | `bridge_federation` | `gloob-causal-responder.yml` | pull_request, push | 1 | `keep` | — |
| 20 | `pr_domain` | `bridge_federation` | `gm-i-a-coolprop-runtime-bridge-p002.yml` | pull_request | 1 | `keep` | — |
| 20 | `pr_domain` | `bridge_federation` | `gm-i-a-coolprop-runtime-bridge.yml` | pull_request, workflow_dispatch | 1 | `keep` | — |
| 20 | `pr_domain` | `bridge_federation` | `mcl-roundtrip-hub-qa.yml` | pull_request, workflow_dispatch | 3 | `keep` | — |
| 20 | `pr_domain` | `bridge_federation` | `mcw-artifact-cold-build.yml` | workflow_dispatch, pull_request | 1 | `keep` | — |
| 20 | `pr_domain` | `bridge_federation` | `mission-control-lite-testflight.yml` | workflow_dispatch, pull_request | 1 | `keep` | — |
| 20 | `pr_domain` | `bridge_federation` | `w189f-federation-sample4-exact.yml` | pull_request, push | 1 | `keep` | — |
| 20 | `pr_domain` | `bridge_federation` | `w286-gloob-pandoc-p1.yml` | pull_request, workflow_dispatch | 1 | `keep` | — |
| 20 | `pr_domain` | `ci_governance` | `bd-workflow-frequency-telemetry.yml` | workflow_dispatch, schedule, pull_request | 1 | `keep` | — |
| 20 | `pr_domain` | `core_test` | `bd-w1-three-pulse-regression.yml` | pull_request | 1 | `keep` | — |
| 20 | `pr_domain` | `core_test` | `cbd-cohort-union-testflight.yml` | pull_request, workflow_dispatch | 1 | `keep` | — |
| 20 | `pr_domain` | `core_test` | `cbd-w6c-office-style-qa.yml` | pull_request | 1 | `keep` | — |
| 20 | `pr_domain` | `core_test` | `g3a-n14-phase4-import.yml` | pull_request, workflow_dispatch | 1 | `keep` | — |
| 20 | `pr_domain` | `core_test` | `g3a-n15-python-matrix.yml` | pull_request, workflow_dispatch | 1 | `keep` | — |
| 20 | `pr_domain` | `core_test` | `mip-w1-python-dependency-qa.yml` | pull_request | 1 | `keep` | — |
| 20 | `pr_domain` | `core_test` | `mip-wave-pulse-testflight.yml` | pull_request, workflow_dispatch | 1 | `keep` | — |
| 20 | `pr_domain` | `core_test` | `w2-ariana-isolated-xml-qa.yml` | pull_request | 1 | `keep` | — |
| 20 | `pr_domain` | `core_test` | `w28-testpilot-git-failure-coverage.yml` | pull_request, workflow_dispatch | 1 | `keep` | — |
| 20 | `pr_domain` | `dmaic` | `book-build.yml` | push, workflow_dispatch | 1 | `keep` | — |
| 20 | `pr_domain` | `dmaic` | `dmaic-commit-metrics.yml` | push, workflow_run, workflow_dispatch | 5 | `keep` | — |
| 20 | `pr_domain` | `dmaic` | `dmaic-enterprise-ci.yml` | push, pull_request, workflow_dispatch | 7 | `keep` | — |
| 20 | `pr_domain` | `dmaic` | `dmaic-phase-execution.yml` | none | 1 | `keep` | — |
| 20 | `pr_domain` | `dmaic` | `dmaic-v3-cd.yml` | push, release, workflow_dispatch | 7 | `keep` | — |
| 20 | `pr_domain` | `dmaic` | `dmaic-v3-ci.yml` | push, pull_request, schedule, workflow_dispatch | 9 | `keep` | — |
| 20 | `pr_domain` | `dmaic` | `dmaic-v3-cognitive-cicd.yml` | push, workflow_dispatch | 9 | `keep` | — |
| 20 | `pr_domain` | `dmaic` | `recursive-build.yml` | push, workflow_dispatch | 1 | `keep` | — |
| 20 | `pr_domain` | `dmaic` | `w2-dmaic-phase-cache-qa.yml` | pull_request | 1 | `keep` | — |
| 20 | `pr_domain` | `documentation` | `w4-dashboard-publication-qa.yml` | pull_request | 1 | `keep` | — |
| 20 | `pr_domain` | `dow` | `background_orchestrator.yml` | schedule, pull_request, workflow_dispatch | 2 | `keep` | — |
| 20 | `pr_domain` | `dow` | `cycle2-temporal-pca-independent-consumer.yml` | pull_request, workflow_dispatch | 1 | `keep` | — |
| 20 | `pr_domain` | `dow` | `dow-bounded-first-red-burndown.yml` | pull_request, workflow_dispatch | 1 | `keep` | — |
| 20 | `pr_domain` | `dow` | `dow-integration.yml` | push, workflow_dispatch, schedule | 4 | `keep` | — |
| 20 | `pr_domain` | `dow` | `dow-main-cicd.yml` | push, schedule, workflow_dispatch | 1 | `keep` | — |
| 20 | `pr_domain` | `dow` | `dow-monitoring.yml` | push, schedule, workflow_dispatch | 1 | `keep` | — |
| 20 | `pr_domain` | `dow` | `dow-remaining-gates-telemetry.yml` | pull_request, workflow_dispatch, schedule | 1 | `keep` | — |
| 20 | `pr_domain` | `dow` | `dow-scheduled.yml` | schedule, workflow_dispatch | 1 | `keep` | — |
| 20 | `pr_domain` | `dow` | `dow-sprint6-cicd.yml` | push, workflow_dispatch | 7 | `keep` | — |
| 20 | `pr_domain` | `dow` | `dow-w1-coverage-contract-qa.yml` | pull_request | 1 | `keep` | — |
| 20 | `pr_domain` | `dow` | `gg-math-temporal-pca-exact-live-dow.yml` | pull_request, workflow_dispatch | 1 | `keep` | — |
| 20 | `pr_domain` | `dow` | `qps-debug-dow-consumer.yml` | pull_request, workflow_dispatch, repository_dispatch | 2 | `keep` | — |
| 20 | `pr_domain` | `dow` | `qps-dow-wave01-warmup.yml` | workflow_dispatch, pull_request, push | 1 | `keep` | — |
| 20 | `pr_domain` | `dow` | `qps-math-wormhole-dow.yml` | pull_request, workflow_dispatch | 1 | `keep` | — |
| 20 | `pr_domain` | `dow` | `qps-triage-dow-contract.yml` | pull_request, push, workflow_dispatch | 1 | `keep` | — |
| 20 | `pr_domain` | `dow` | `qps-w04-dow-receipt.yml` | workflow_dispatch, pull_request, push | 3 | `keep` | — |
| 20 | `pr_domain` | `dow` | `qps-w05-bidder-eval-dow.yml` | workflow_dispatch, pull_request, push | 1 | `keep` | — |
| 20 | `pr_domain` | `dow` | `qps_m05_dow_independent_consumer.yml` | pull_request, push, workflow_dispatch | 1 | `keep` | — |
| 20 | `pr_domain` | `dow` | `sprint-trigger.yml` | schedule, workflow_dispatch | 1 | `keep` | — |
| 20 | `pr_domain` | `dow` | `w259-p4-method-cards-independent-dow.yml` | pull_request, push | 1 | `keep` | — |
| 20 | `pr_domain` | `dow` | `w285-dow-depth-recompute.yml` | pull_request, push, workflow_dispatch | 1 | `keep` | — |
| 20 | `pr_domain` | `dow` | `w306-dow-typed-findings-proof.yml` | pull_request, push, workflow_dispatch | 1 | `keep` | — |
| 20 | `pr_domain` | `full_regression` | `ci-cd-tests.yml` | push, pull_request, schedule, workflow_dispatch | 12 | `canonical` | — |
| 20 | `pr_domain` | `runtime_governance` | `cbd-w38-route-yield.yml` | none | 1 | `keep` | — |
| 20 | `pr_domain` | `runtime_governance` | `code-purple-dashboard-v31.yml` | pull_request, workflow_dispatch | 2 | `keep` | — |
| 20 | `pr_domain` | `runtime_governance` | `code-purple-sut-gui.yml` | pull_request, workflow_dispatch | 1 | `keep` | — |
| 20 | `pr_domain` | `runtime_governance` | `deployment-enforcement.yml` | workflow_dispatch | 1 | `keep` | — |
| 20 | `pr_domain` | `runtime_governance` | `everred-real-pipeline-proof.yml` | pull_request, workflow_dispatch | 1 | `keep` | — |
| 20 | `pr_domain` | `runtime_governance` | `everred-v3-validation.yml` | pull_request, schedule, workflow_dispatch | 3 | `keep` | — |
| 20 | `pr_domain` | `runtime_governance` | `g3a-bounded-continuation-proof.yml` | pull_request, workflow_dispatch | 2 | `keep` | — |
| 20 | `pr_domain` | `runtime_governance` | `governance-drift-detection.yml` | schedule, workflow_dispatch | 1 | `keep` | — |
| 20 | `pr_domain` | `runtime_governance` | `governance.yml` | push, pull_request, workflow_dispatch | 1 | `keep` | — |
| 20 | `pr_domain` | `runtime_governance` | `inventory.yml` | schedule, workflow_dispatch | 1 | `keep` | — |
| 20 | `pr_domain` | `runtime_governance` | `leg5-federation-dashboard-proof.yml` | pull_request, workflow_dispatch | 1 | `keep` | — |
| 20 | `pr_domain` | `runtime_governance` | `mesh-status-runtime.yml` | push, workflow_dispatch | 1 | `keep` | — |
| 20 | `pr_domain` | `runtime_governance` | `mip-bminus1-worker-contract.yml` | pull_request, workflow_dispatch | 1 | `keep` | — |
| 20 | `pr_domain` | `runtime_governance` | `pr-feedback-gate.yml` | issue_comment, issues, pull_request_review, pull_request_review_comment, pull_request, workflow_run, schedule, workflow_dispatch | 3 | `keep` | — |
| 20 | `pr_domain` | `runtime_governance` | `recovery-action-value-evidence.yml` | pull_request, workflow_dispatch | 1 | `keep` | — |
| 20 | `pr_domain` | `runtime_governance` | `review-artifact-validation.yml` | push, pull_request | 1 | `keep` | — |
| 20 | `pr_domain` | `runtime_governance` | `runtime-governance.yml` | workflow_dispatch | 1 | `keep` | — |
| 20 | `pr_domain` | `runtime_governance` | `runtime-smoke.yml` | push, workflow_dispatch | 1 | `keep` | — |
| 20 | `pr_domain` | `runtime_governance` | `runtime-verification.yml` | workflow_dispatch, workflow_run | 1 | `keep` | — |
| 20 | `pr_domain` | `runtime_governance` | `triage-repo-census.yml` | pull_request, push | 1 | `keep` | — |
| 20 | `pr_domain` | `runtime_governance` | `v5-w62-self-smoke.yml` | pull_request, workflow_dispatch | 1 | `keep` | — |
| 20 | `pr_domain` | `runtime_governance` | `v5-w62-twelve-cluster-requalification.yml` | pull_request, workflow_dispatch | 1 | `keep` | — |
| 20 | `pr_domain` | `runtime_governance` | `validate-setup.yml` | workflow_dispatch | 1 | `keep` | — |
| 20 | `pr_domain` | `runtime_governance` | `validate_docs.yml` | push, pull_request, workflow_dispatch | 1 | `keep` | — |
| 20 | `pr_domain` | `runtime_governance` | `validation.yml` | push, pull_request, workflow_dispatch | 1 | `keep` | — |
| 20 | `pr_domain` | `runtime_governance` | `w007-runtime-validator-qa.yml` | pull_request, workflow_dispatch | 1 | `keep` | — |
| 20 | `pr_domain` | `runtime_governance` | `w33-backbone-pool.yml` | pull_request, workflow_dispatch | 1 | `keep` | — |
| 20 | `pr_domain` | `runtime_governance` | `w64-census-p3.yml` | pull_request, workflow_dispatch | 1 | `keep` | — |
| 20 | `pr_domain` | `runtime_governance` | `yaml-validation.yml` | push, pull_request | 1 | `keep` | — |
| 20 | `pr_domain` | `security` | `bandit-disjoint-census.yml` | workflow_dispatch, pull_request | 1 | `keep` | — |
| 20 | `pr_domain` | `security` | `code-maroon.yml` | pull_request, workflow_dispatch | 1 | `keep` | — |
| 20 | `pr_domain` | `security` | `codeql.yml` | push, pull_request, schedule | 1 | `keep` | — |
| 20 | `pr_domain` | `security` | `dependency-review.yml` | pull_request | 1 | `keep` | — |
| 20 | `pr_domain` | `security` | `osv-scanner.yml` | pull_request, merge_group | 1 | `keep` | — |
| 20 | `pr_domain` | `security` | `osv-scheduled.yml` | schedule, workflow_dispatch | 1 | `keep` | — |
| 20 | `pr_domain` | `security` | `reusable-security.yml` | workflow_call | 1 | `keep` | — |
| 20 | `pr_domain` | `security` | `security-dashboard.yml` | schedule, workflow_dispatch | 1 | `keep` | — |
| 20 | `pr_domain` | `security` | `security-scan.yml` | push, pull_request, schedule | 1 | `keep` | — |
| 20 | `pr_domain` | `security` | `semgrep.yml` | push, pull_request, schedule, workflow_dispatch | 1 | `keep` | — |
| 20 | `pr_domain` | `specialised` | `code-purple-w40-binary-penetration.yml` | pull_request, workflow_dispatch | 1 | `keep` | — |
| 20 | `pr_domain` | `specialised` | `code-purple-w42-remaining-arcs.yml` | pull_request, workflow_dispatch | 1 | `keep` | — |
| 20 | `pr_domain` | `specialised` | `dab-flake8-census.yml` | workflow_call, pull_request, push, schedule, workflow_dispatch | 1 | `keep` | — |
| 20 | `pr_domain` | `specialised` | `delta-1-baseline.yml` | workflow_dispatch | 1 | `keep` | — |
| 20 | `pr_domain` | `specialised` | `mip-coverage-evidence.yml` | workflow_dispatch, push, pull_request | 6 | `keep` | — |
| 20 | `pr_domain` | `specialised` | `mip-n2-self-index.yml` | pull_request, workflow_dispatch | 2 | `keep` | — |
| 20 | `pr_domain` | `specialised` | `mip-qps-external-probe.yml` | pull_request, workflow_dispatch | 1 | `keep` | — |
| 20 | `pr_domain` | `specialised` | `mip-v2-federated-control.yml` | pull_request, workflow_dispatch, push | 1 | `keep` | — |
| 20 | `pr_domain` | `specialised` | `qps-canonicalization.yml` | [pull_request, push] | 1 | `keep` | — |
| 20 | `pr_domain` | `specialised` | `qps-cost-roundtrip-contract.yml` | pull_request, push | 1 | `keep` | — |
| 20 | `pr_domain` | `specialised` | `qps-dow-w43-triage.yml` | workflow_dispatch, pull_request, push | 1 | `keep` | — |
| 20 | `pr_domain` | `specialised` | `qps-p05f-measured-sensitivity.yml` | pull_request, workflow_dispatch | 1 | `keep` | — |
| 20 | `pr_domain` | `specialised` | `qps-p05j-quantitative.yml` | workflow_dispatch, pull_request | 1 | `keep` | — |
| 20 | `pr_domain` | `specialised` | `qps-v24-refresh-unresolved-selector.yml` | workflow_dispatch, push | 1 | `keep` | — |
| 20 | `pr_domain` | `specialised` | `qps-w111-power-utility-dow.yml` | pull_request, workflow_dispatch | 1 | `keep` | — |
| 20 | `pr_domain` | `specialised` | `qps_line_s.yml` | pull_request, workflow_dispatch | 1 | `keep` | — |
| 20 | `pr_domain` | `specialised` | `reusable-ci.yml` | workflow_call | 1 | `keep` | — |
| 20 | `pr_domain` | `specialised` | `session_tuple_ci.yml` | push, workflow_dispatch | 3 | `keep` | — |
| 20 | `pr_domain` | `specialised` | `v23-cicd.yml` | push, workflow_dispatch | 2 | `keep` | — |
| 20 | `pr_domain` | `specialised` | `w102-qps-mip-reconciliation-receiver.yml` | pull_request, workflow_dispatch | 1 | `keep` | — |
| 20 | `pr_domain` | `specialised` | `w105-qps-b1b2-mip-probe.yml` | pull_request, workflow_dispatch | 1 | `keep` | — |
| 20 | `pr_domain` | `specialised` | `w169-qplant-k8s-runtime.yml` | pull_request, workflow_dispatch | 1 | `keep` | — |
| 20 | `pr_domain` | `specialised` | `w52-p2m-helium-proof.yml` | pull_request, workflow_dispatch | 1 | `keep` | — |
| 20 | `pr_domain` | `specialised` | `w52-p2r-supplier-a-ts-strict-residual.yml` | pull_request, workflow_dispatch | 1 | `keep` | — |
| 20 | `pr_domain` | `specialised` | `w52-p2t-hp-power-residual.yml` | pull_request | 1 | `keep` | — |
| 20 | `pr_domain` | `specialised` | `w52-p2t-ts-runtime-receipt.yml` | pull_request, workflow_dispatch | 1 | `keep` | — |
| 20 | `pr_domain` | `specialised` | `w53-p05t-qcell-jt-runtime.yml` | pull_request, workflow_dispatch | 1 | `keep` | — |
| 20 | `pr_domain` | `specialised` | `w66-abacus-id-burndown-split.yml` | pull_request, workflow_dispatch, schedule | 2 | `keep` | — |
| 20 | `pr_domain` | `specialised` | `w67-measured-id-pulse.yml` | pull_request, workflow_dispatch | 1 | `keep` | — |
| 20 | `pr_domain` | `specialised` | `w67-pulse3-pca-promotion.yml` | pull_request, workflow_dispatch | 1 | `keep` | — |
| 20 | `pr_domain` | `specialised` | `w70-measured-id-pulse-exact-sha.yml` | pull_request, workflow_dispatch | 1 | `keep` | — |
| 20 | `pr_domain` | `specialised` | `w70-retain-measured-pulse.yml` | workflow_run, workflow_dispatch | 1 | `keep` | — |
| 20 | `pr_domain` | `specialised` | `w71-residual-lineage-census.yml` | pull_request, workflow_dispatch | 1 | `keep` | — |
| 20 | `pr_domain` | `specialised` | `w72-clean-clone-proof.yml` | pull_request, workflow_dispatch | 1 | `keep` | — |
| 20 | `pr_domain` | `specialised` | `w72-versioned-semantic-backfill.yml` | pull_request, workflow_dispatch | 3 | `keep` | — |
| 20 | `pr_domain` | `specialised` | `w72-zero-delta-wheel.yml` | pull_request, workflow_dispatch | 1 | `keep` | — |
| 20 | `pr_domain` | `specialised` | `w74-qplant-k8s-contract.yml` | pull_request, workflow_dispatch | 1 | `keep` | — |
| 20 | `pr_domain` | `specialised` | `w77-phase-runtime-instrumentation.yml` | pull_request, workflow_dispatch | 3 | `keep` | — |
| 20 | `pr_domain` | `specialised` | `w78-deterministic-work-census.yml` | pull_request, workflow_dispatch | 3 | `keep` | — |
| 20 | `pr_domain` | `specialised` | `w79-deterministic-multivariate.yml` | pull_request, workflow_dispatch | 1 | `keep` | — |
| 20 | `pr_domain` | `specialised` | `w81-repair-outcome-block.yml` | pull_request, workflow_dispatch | 5 | `keep` | — |
| 20 | `pr_domain` | `specialised` | `w85-census-proof.yml` | pull_request, workflow_dispatch | 1 | `keep` | — |
| 20 | `pr_domain` | `specialised` | `w93-docker-deployment-proof.yml` | pull_request, workflow_dispatch | 2 | `keep` | — |
| 20 | `pr_domain` | `specialised` | `w95-accelerator-receiver.yml` | pull_request, workflow_dispatch | 1 | `keep` | — |
| 20 | `pr_domain` | `specialised` | `w99-r1-reconciliation-return.yml` | pull_request, workflow_dispatch | 1 | `keep` | — |
| 20 | `pr_domain` | `statistics` | `bootstrap-integration.yml` | push, pull_request, workflow_dispatch | 6 | `keep` | — |
| 20 | `pr_domain` | `statistics` | `cbd-matched-coverage.yml` | pull_request, workflow_dispatch | 1 | `keep` | — |
| 20 | `pr_domain` | `statistics` | `cbd-w38-source-branch.yml` | none | 1 | `keep` | — |
| 20 | `pr_domain` | `statistics` | `ci-cd.yml` | push, pull_request, schedule, workflow_dispatch | 8 | `keep` | — |
| 20 | `pr_domain` | `statistics` | `code-purple-w43-matched-proof.yml` | pull_request, workflow_dispatch | 1 | `keep` | — |
| 20 | `pr_domain` | `statistics` | `code-purple-w44-matched-proof.yml` | pull_request, workflow_dispatch | 1 | `keep` | — |
| 20 | `pr_domain` | `statistics` | `g3a-n14-matched-arc-flight.yml` | pull_request, workflow_dispatch | 1 | `keep` | — |
| 20 | `pr_domain` | `statistics` | `mip-py310-combined-head-probe.yml` | pull_request, workflow_dispatch | 1 | `keep` | — |
| 20 | `pr_domain` | `statistics` | `mip2-method-qualification.yml` | pull_request, workflow_dispatch, push | 1 | `keep` | — |
| 20 | `pr_domain` | `statistics` | `w13-neural-spine.yml` | pull_request, workflow_dispatch | 1 | `keep` | — |
| 20 | `pr_domain` | `statistics` | `w26-testpilot-matched-coverage.yml` | pull_request, workflow_dispatch | 1 | `keep` | — |
| 20 | `pr_domain` | `statistics` | `w29-cbd-temporal-matched-coverage.yml` | pull_request, workflow_dispatch | 1 | `keep` | — |
| 20 | `pr_domain` | `statistics` | `w29-disjoint-frontier-coverage.yml` | push, pull_request, workflow_dispatch | 1 | `keep` | — |
| 20 | `pr_domain` | `statistics` | `w36-g3cs-skip-contract.yml` | pull_request, workflow_dispatch | 1 | `keep` | — |
| 20 | `pr_domain` | `statistics` | `w38-local-pool-mip.yml` | pull_request, workflow_dispatch | 1 | `keep` | — |
| 20 | `pr_domain` | `statistics` | `w64-3p-r01-retained-baseline.yml` | pull_request, workflow_dispatch | 1 | `keep` | — |
| 20 | `pr_domain` | `statistics` | `w64-3p-r02-id-discovery-graph.yml` | pull_request, workflow_dispatch | 1 | `keep` | — |
| 20 | `pr_domain` | `statistics` | `w65-parallel-discovery-pulses.yml` | pull_request, workflow_dispatch, schedule | 5 | `keep` | — |
| 30 | `post_merge` | `delivery` | `cd-pipeline.yml` | push, workflow_dispatch | 7 | `keep` | — |
| 30 | `post_merge` | `delivery` | `cd-unified.yml` | push, schedule, workflow_dispatch | 7 | `keep` | — |
| 30 | `post_merge` | `delivery` | `cd.yml` | schedule, workflow_dispatch | 1 | `keep` | — |
| 30 | `post_merge` | `delivery` | `delta-1-deploy.yml` | workflow_dispatch | 1 | `keep` | — |
| 30 | `post_merge` | `delivery` | `delta-1-release.yml` | workflow_dispatch | 1 | `keep` | — |
| 30 | `post_merge` | `delivery` | `history-purge-20260827.yml` | push | 1 | `keep` | — |
| 30 | `post_merge` | `delivery` | `release.yml` | push, workflow_dispatch | 2 | `keep` | — |
| 30 | `post_merge` | `delivery` | `remove-public-binaries.yml` | push | 1 | `keep` | — |
| 30 | `post_merge` | `documentation` | `deploy-docs.yml` | push, workflow_dispatch | 3 | `keep` | — |
| 30 | `post_merge` | `documentation` | `docs-build.yml` | push | 1 | `keep` | — |
| 30 | `post_merge` | `documentation` | `export-docs.yml` | push, workflow_dispatch | 1 | `keep` | — |
| 30 | `post_merge` | `documentation` | `pages.yml` | workflow_dispatch | 1 | `keep` | — |
| 30 | `post_merge` | `documentation` | `reports.yml` | schedule, workflow_dispatch, push | 2 | `keep` | — |
| 30 | `post_merge` | `documentation` | `update-docs.yml` | push, workflow_dispatch | 1 | `keep` | — |
| 40 | `scheduled` | `automation` | `auto-merge-prs.yml` | workflow_dispatch | 1 | `keep` | — |
| 40 | `scheduled` | `automation` | `branch-analysis.yml` | workflow_dispatch | 2 | `keep` | — |
| 40 | `scheduled` | `automation` | `branch-pruner.yml` | workflow_dispatch | 1 | `keep` | — |
| 40 | `scheduled` | `automation` | `ci-failure-debug-rerun.yml` | workflow_run | 1 | `keep` | — |
| 40 | `scheduled` | `automation` | `ci_monitor_and_issue_creator.yml` | workflow_run, workflow_dispatch | 1 | `keep` | — |
| 40 | `scheduled` | `automation` | `code-purple-evidence-observatory.yml` | workflow_dispatch, schedule | 1 | `keep` | — |
| 40 | `scheduled` | `automation` | `copilot-pr-creator.yml` | workflow_dispatch, workflow_call | 1 | `keep` | — |
| 40 | `scheduled` | `automation` | `dashboard-health.yml` | schedule, workflow_dispatch | 1 | `keep` | — |
| 40 | `scheduled` | `automation` | `missioncontrol-issue-burndown.yml` | workflow_dispatch, schedule, pull_request | 1 | `keep` | — |
| 40 | `scheduled` | `automation` | `post-merge-pr-summary.yml` | pull_request | 1 | `keep` | — |
| 40 | `scheduled` | `security` | `bandit.yml` | schedule, workflow_dispatch | 1 | `keep` | — |
| 50 | `manual` | `automation` | `branch-hygiene.yml` | workflow_dispatch, pull_request | 3 | `keep` | — |
| 50 | `manual` | `bridge_federation` | `abacus-missioncontrol-stage-only.yml` | workflow_dispatch | 1 | `keep` | — |
| 50 | `manual` | `bridge_federation` | `qps-metric-census-receiver.yml` | workflow_dispatch, repository_dispatch | 2 | `keep` | — |
| 50 | `manual` | `core_test` | `code-purple-quality-ratchet-proof.yml` | push, workflow_dispatch | 1 | `keep` | — |
| 50 | `manual` | `legacy` | `ci.yml` | workflow_dispatch | 3 | `consolidate` | `bridge-ci.yml` |
| 90 | `retire` | `legacy` | `ci-codex.yml` | workflow_dispatch | 1 | `retire` | `CODEX/.github workflows via versioned manifest; no ABACUS-to-CODEX dispatch` |

## Repeated quality/test commands

- `python -m pytest -q \` — `ariana-cicd.yml`, `ci-abacus.yml`, `code-purple-w40-binary-penetration.yml`, `code-purple-w42-remaining-arcs.yml`, `code-purple-w43-matched-proof.yml`, `code-purple-w44-matched-proof.yml`, `leg5-federation-dashboard-proof.yml`, `w29-disjoint-frontier-coverage.yml`
- `python -m pip install pytest numpy` — `abacus-missioncontrol-stage-contract-qa.yml`, `bd-w1-three-pulse-regression.yml`, `book-build.yml`, `dow-w1-coverage-contract-qa.yml`, `leg5-federation-dashboard-proof.yml`
- `python -m pytest \` — `bridge-ci.yml`, `codespace-federation.yml`, `governance.yml`, `mip-coverage-evidence.yml`, `validation.yml`
- `python -m pip install pytest` — `branch-hygiene.yml`, `cryoplant-federation.yml`, `v5-w62-twelve-cluster-requalification.yml`, `w306-dow-typed-findings-proof.yml`
- `pip install pytest` — `cd-unified.yml`, `federation-notebook.yml`, `tooling-ci.yml`
- `pip install pytest pyyaml` — `ci-abacus.yml`, `codespace-federation.yml`, `dow-sprint6-cicd.yml`
- `python -m pip install --quiet pytest numpy` — `w77-phase-runtime-instrumentation.yml`, `w78-deterministic-work-census.yml`, `w81-repair-outcome-block.yml`
- `bandit -r . -f json -o bandit-report.json` — `ci-cd-tests.yml`, `ci-cd.yml`
- `black --check --diff .` — `ci-cd.yml`, `ci-pipeline.yml`
- `flake8 DMAIC_V3/core/test_system_bridge.py run_deployment_test_system.py --max-line-length=120` — `ci.yml`, `reusable-ci.yml`
- `pip install flake8 black isort mypy pylint` — `ci-cd-tests.yml`, `ci-cd.yml`
- `pip install flake8 mypy pylint black ruff` — `bridge-ci.yml`, `ci.yml`
- `pip install pytest pytest-cov pytest-benchmark pytest-mock` — `bridge-ci.yml`, `main.yml`
- `pip install pytest pytest-mock flake8 mypy pylint` — `bridge-ci.yml`, `ci.yml`
- `pre-commit run --all-files` — `cd-unified.yml`, `ci-codex.yml`
- `pylint **/*.py --exit-zero` — `ci-cd-tests.yml`, `ci-pipeline.yml`
- `pytest --benchmark-disable -v --cov=. --cov-report=term-missing` — `cd-unified.yml`, `ci-codex.yml`
- `python -m pip install 'pytest>=7.4,<10' 'numpy>=1.24,<3'` — `cbd-w6c-office-style-qa.yml`, `w4-dashboard-publication-qa.yml`
- `python -m pip install 'pytest>=7.4,<10' 'pytest-cov>=4.1,<8' 'numpy>=1.24,<3'` — `w007-runtime-validator-qa.yml`, `w29-disjoint-frontier-coverage.yml`
- `python -m pip install pytest pyyaml` — `cryoplant-federation.yml`, `mip-qps-external-probe.yml`

## Control rule

A workflow change fails CI governance when a definition is unclassified, a canonical owner is missing, or the generated report no longer matches the policy. This report is derived; `ci/governance/workflow_policy.json` is the SSOT.
