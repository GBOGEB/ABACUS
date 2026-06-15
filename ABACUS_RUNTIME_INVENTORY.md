# ABACUS Runtime Inventory

Date: 2026-06-11

## Inventory scope

This file inventories runtime code, configuration, workflows, and manifests relevant to Orchestrator V3.0, KEB, GBOGEB, recursive hooks, and deployment automation.

## Evidence basis

Inventory evidence includes exact runtime file paths, symbols, configuration files, workflow paths, and deployment scripts.

## Runtime code inventory

| Runtime area | Path | Exact symbol / reference | Role | Status | Confidence | Recommendation |
|---|---|---|---|---:|---:|---|
| Agent orchestrator | `local_mcp/agent_orchestrator_v3.0.py` | `AgentOrchestratorV3` | Coordinates six V2.3 agents and knowledge integration | RENAMED | HIGH | retain |
| Agent catalog | `local_mcp/agent_orchestrator_v3.0.py` | `_AGENT_CATALOGUE` | Maps logical agent names to optimized V2.3 files/classes | COMPLETE | HIGH | retain |
| Knowledge integration | `local_mcp/knowledge_integration_v2.3.py` | `KnowledgeIntegrationV23`, `KnowledgeEntry` | Unified KEB/GBOGEB knowledge layer | PARTIAL | HIGH | refactor imports |
| KEB core | `core/keb/keb.py` | `KEB`, `_PriorityTask` | Priority execution backbone | PARTIAL | HIGH | retain |
| GBOGEB core | `core/gbogeb/gbogeb.py` | `GBOGEB` | Metrics, compliance, and governance reports | PARTIAL | HIGH | retain |
| DMAIC full pipeline | `DMAIC_V3/full_pipeline_orchestrator.py` | `FullPipelineOrchestrator` | DMAIC V3 phase orchestration | COMPLETE | HIGH | retain |
| 12-cluster orchestrator | `DMAIC_V3/core/twelve_cluster_orchestrator.py` | `TwelveClusterOrchestrator` | Parallel cluster runtime and temporal phase hooks | COMPLETE | HIGH | retain |
| DOW recursive hook injector | `DMAIC_V3/local_mcp/agents/dow_recursive_hooks_injector.py` | `DOWRecursiveHooksInjector` | Injects recursive metadata into artifacts | COMPLETE | HIGH | retain |
| Phase 6 knowledge | `DMAIC_V3/phases/phase6_knowledge.py` | `Phase6Knowledge`, `KnowledgeReference` | Knowledge devour/reporting and hook registration | PARTIAL | HIGH | retain |
| Recursion utilities | `src/dmaic/recursion.py` | `should_stop`, `analyze_convergence`, `generate_stop_rules` | Stop/convergence analysis | COMPLETE | HIGH | retain |
| Federation utilities | `src/dmaic/federation.py` | `assimilate` | Federation assimilation stub for runtime plane | PARTIAL | MEDIUM | retain |
| GBOGEB/DOW bridge | `staging/GBOGEB_ABACUS_DOW_INTEGRATION_BRIDGE.py` | `GBOGEBAbacusDOWBridge` | Cross-system bridge | PARTIAL | HIGH | replace stale workflow paths |
| CI/CD orchestrator | `cicd_github_orchestrator.py` | script entrypoint | GitHub CI/CD automation | PARTIAL | MEDIUM | retain if still used |
| DOW deployment orchestrator | `DOW_DEPLOYMENT_ORCHESTRATOR.py` | script entrypoint | DOW deployment orchestration | PARTIAL | MEDIUM | retain/validate |

## Configuration and registry inventory

| Path | Reference | Role | Status | Recommendation |
|---|---|---|---:|---|
| `orchestrator_config.yaml` | `agents`, `pipelines`, `dow_integration`, `dmaic_phases` | Main pipeline/orchestrator configuration | COMPLETE | retain |
| `knowledge_packages/dmaic_core_knowledge.yaml` | knowledge package content | Seed knowledge registry | COMPLETE | retain |
| `knowledge_packages/dmaic_core_knowledge.json` | knowledge package content | JSON mirror of seed registry | COMPLETE | retain |
| `metrics/federation/runtime_registry.json` | runtime registry data | Federation runtime registry | PARTIAL | validate |
| `reports/runtime_registry_report.json` | runtime registry report | Runtime publication/reporting evidence | PARTIAL | validate |
| `runtime/manifests/runtime-topology.yaml` | runtime topology | Declarative runtime plane | PARTIAL | validate against code |
| `runtime/manifests/recursive-orchestration-dag.yaml` | recursive orchestration DAG | Recursive runtime declaration | PARTIAL | validate against code |
| `runtime/memory/governance-memory-registry.yaml` | memory registry | Semantic/operational memory registry | PARTIAL | validate connector ownership |
| `ssot/semantic_traceability.yaml` | traceability registry | Semantic traceability | PARTIAL | retain |
| `rtm_integration/automation/config/project.yml` | `GBOGEB/ABACUS`, `GBOGEB/DOCX_RTM_Automation` | RTM project/repository registry | COMPLETE | retain |
| `tracking_v2.3/tasks/tasks.json` | GitHub PR/action/artifact/page URLs | V2.3 runtime tracking evidence | COMPLETE | retain |

## Active workflow inventory

Files directly under `.github/workflows/` are active GitHub Actions definitions when they contain `on:` triggers. Key categories found:

| Category | Workflow paths | Status | Recommendation |
|---|---|---:|---|
| Core CI | `.github/workflows/ci.yml`, `.github/workflows/ci-abacus.yml`, `.github/workflows/ci-codex.yml`, `.github/workflows/ci-enhanced.yml`, `.github/workflows/main.yml`, `.github/workflows/abacus-cicd.yml` | COMPLETE | retain; reduce overlap later |
| CD/deployment | `.github/workflows/cd.yml`, `.github/workflows/cd-unified.yml`, `.github/workflows/deployment-enforcement.yml`, `.github/workflows/delta-1-deploy.yml` | COMPLETE | retain |
| Release | `.github/workflows/release.yml`, `.github/workflows/delta-1-release.yml` | COMPLETE | retain |
| Docs/pages deployment | `.github/workflows/deploy-docs.yml`, `.github/workflows/pages.yml`, `.github/workflows/update-docs.yml`, `.github/workflows/export-docs.yml`, `.github/workflows/book-build.yml` | COMPLETE | retain |
| Runtime governance | `.github/workflows/runtime-governance.yml`, `.github/workflows/runtime-verification.yml`, `.github/workflows/runtime-smoke.yml`, `.github/workflows/governance.yml`, `.github/workflows/governance-drift-detection.yml` | COMPLETE | retain |
| DOW/GBOGEB | `.github/workflows/dow-integration.yml`, `.github/workflows/dow-main-cicd.yml`, `.github/workflows/dow-monitoring.yml`, `.github/workflows/dow-scheduled.yml`, `.github/workflows/gbogeb-abacus-integration-ci-cd.yml` | PARTIAL | update GBOGEB bridge paths |
| Recursive | `.github/workflows/recursive-build.yml` | COMPLETE | retain |
| Security | `.github/workflows/codeql.yml`, `.github/workflows/dependency-review.yml`, `.github/workflows/reusable-security.yml` | COMPLETE | retain |
| Validation/quality | `.github/workflows/format-check.yml`, `.github/workflows/validate_docs.yml`, `.github/workflows/validation.yml`, `.github/workflows/yaml-validation.yml`, `.github/workflows/smoke-test.yml`, `.github/workflows/tooling-ci.yml`, `.github/workflows/validate-setup.yml` | COMPLETE | retain |
| Monitoring/reporting | `.github/workflows/dashboard-health.yml`, `.github/workflows/ci_monitor_and_issue_creator.yml`, `.github/workflows/reports.yml`, `.github/workflows/inventory.yml`, `.github/workflows/dmaic-commit-metrics.yml` | COMPLETE | retain |

## Disabled, pending, and nested workflow inventory

| Location | Contents | Active? | Status | Recommendation |
|---|---|---:|---:|---|
| `.github/workflows/legacy/` | `.github/workflows/legacy/cd.yml.old`, `.github/workflows/legacy/dow-integration-ci-cd.yml.old` | No | SUPERSEDED | archive |
| `.github/workflows-pending/` | `.github/workflows-pending/deploy-docs.yml`, `.github/workflows-pending/release.yml`, `.github/workflows-pending/update-docs.yml`, dashboard and metrics scaffolds | No | PARTIAL | move only after validation |
| `DMAIC_V3/.github/workflows/` | `DMAIC_V3/.github/workflows/ci-main.yml`, `DMAIC_V3/.github/workflows/cd-main.yml`, phase CI workflows, `DMAIC_V3/.github/workflows/release.yml` | Nested project workflows | PARTIAL | validate if intended to run at repo root |

## Deployment script inventory

| Path | Role | Status | Recommendation |
|---|---|---:|---|
| `run_streamlined_deployment.py` | streamlined deployment runner | PARTIAL | validate |
| `run_comprehensive_deployment.py` | comprehensive deployment runner | PARTIAL | validate |
| `abacus_v21_deployment_execution.py` | V2.1 deployment execution and health checks | SUPERSEDED | archive or retain as lineage |
| `abacus_v21_postdeployment_validation.py` | post-deployment validation | SUPERSEDED | archive or retain as lineage |
| `ci_cd_automation.ps1` | PowerShell CI/CD automation | PARTIAL | validate current use |
| `setup_github.sh` | GitHub setup helper | PARTIAL | validate current use |

## Runtime inventory conclusion

The repo already contains the requested runtime capabilities. The remaining gaps are consolidation gaps, not greenfield implementation gaps: normalize imports, fix stale workflow path filters, document canonical entrypoints, and add a recursive hook read utility only if consumers need V2.2 parity.
