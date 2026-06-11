# ABACUS Feature Lineage

Date: 2026-06-11

## Feature lineage matrix

| Feature | V2.2 lineage | V2.3/current location | Status | Confidence | Evidence | Recommendation |
|---|---|---|---:|---:|---|---|
| Agent orchestration | Historical orchestrator references and DMAIC agent coordination notes | `local_mcp/agent_orchestrator_v3.0.py` / `AgentOrchestratorV3` | RENAMED | HIGH | `_AGENT_CATALOGUE`, `initialize_agents`, `execute_dmaic_cycle` | retain |
| DMAIC phase pipeline | Recursive DMAIC engine lineage | `DMAIC_V3/full_pipeline_orchestrator.py` / `FullPipelineOrchestrator` | COMPLETE | HIGH | phase imports and `execute_full_pipeline` | retain |
| 12-cluster runtime | 12-cluster architecture documents | `DMAIC_V3/core/twelve_cluster_orchestrator.py` / `TwelveClusterOrchestrator` | COMPLETE | HIGH | `CLUSTER_CONTRACT`, `PHASE_SEQUENCE`, `run_phases_with_hooks` | retain |
| KEB execution backbone | V2.2 KEB template / timeout notes | `core/keb/keb.py` / `KEB`; `KnowledgeIntegrationV23.schedule_agent_task` | PARTIAL | HIGH | core class and knowledge adapter | refactor imports |
| Knowledge registry | V2.2 knowledge reconciliation and V2.3 preservation docs | `local_mcp/knowledge_integration_v2.3.py`, `knowledge_packages/*`, `ABACUS-UNIFIED/KNOWLEDGE_PACK_INDEX.md` | PARTIAL | HIGH | `KnowledgeEntry`, `_init_knowledge_base`, knowledge package files | retain |
| Semantic memory / runtime memory | Runtime convergence docs and semantic manifests | `runtime/memory/*.yaml`, `runtime/compiler/semantic-orchestration-compiler.yaml`, `ssot/semantic_traceability.yaml` | PARTIAL | MEDIUM | declarative YAML manifests, no single Python memory connector found | refactor/validate |
| GBOGEB governance | V2.2 GBOGEB template and timeout notes | `core/gbogeb/gbogeb.py` / `GBOGEB` | PARTIAL | HIGH | metrics/compliance/report APIs | retain |
| GBOGEB cross-repo bridge | GBOGEB/ABACUS repository lineage | `staging/GBOGEB_ABACUS_DOW_INTEGRATION_BRIDGE.py`, `.github/workflows/gbogeb-abacus-integration-ci-cd.yml`, RTM project config | PARTIAL | HIGH | bridge class and workflow | replace stale paths |
| Recursive hook injection | V2.2 recursive hooks | `DMAIC_V3/local_mcp/agents/dow_recursive_hooks_injector.py` | COMPLETE | HIGH | `DOWRecursiveHooksInjector.inject_recursive_hooks` | retain |
| Recursive hook retrieval | V2.2 API expectation | Not found in active runtime; parity audit records gap | MISSING | HIGH | `PHASE_B_RECURSIVE_HOOKS_PARITY_AUDIT_V4.4.0.md` | add/refactor only if required |
| Stop/convergence rules | Recursive iteration behavior | `src/dmaic/recursion.py` | COMPLETE | HIGH | `should_stop`, `analyze_convergence`, `generate_stop_rules` | retain |
| Deployment CI/CD | Earlier CI/CD plans and status reports | `.github/workflows/*.yml`, `DMAIC_V3/.github/workflows/*.yml` | COMPLETE | HIGH | active `on:` triggers | retain |

## Orchestrator feature lineage

### Current symbols

- `local_mcp/agent_orchestrator_v3.0.py`
  - `AgentOrchestratorV3`
  - `_AGENT_CATALOGUE`
  - `initialize_agents`
  - `execute_agent`
  - `execute_dmaic_cycle`
  - `get_agent_status`
  - `save_results`
- `DMAIC_V3/full_pipeline_orchestrator.py`
  - `FullPipelineOrchestrator`
  - `execute_full_pipeline`
  - `_generate_phase6_report`
  - `main`
- `DMAIC_V3/core/twelve_cluster_orchestrator.py`
  - `ClusterConfig`
  - `TwelveClusterOrchestrator`
  - `execute_phase_parallel`
  - `run_phases_with_hooks`
  - `generate_report`

### Lineage determination

Orchestrator V3.0 is not missing. It is split into three named runtime roles: agent orchestration, phase orchestration, and cluster orchestration. Treating these as separate missing systems would create duplicates.

## KEB feature lineage

### Existing adapters and registries

- `core/keb/keb.py` is the execution backbone.
- `local_mcp/knowledge_integration_v2.3.py` is the adapter that exposes KEB-backed task scheduling to agents.
- `DMAIC_V3/core/twelve_cluster_orchestrator.py` optionally constructs KEB for cluster execution.
- `orchestrator_config.yaml` configures agent paths and pipeline stages, including DOW recursive hook and convergence agents; KEB worker/memory parameters are constructed in code.
- `knowledge_packages/dmaic_core_knowledge.*` contains seed knowledge packages.
- `ABACUS-v032/STATS/DMAIC_FULL/knowledge/**/knowledge_index.json` and `knowledge_packs.json` are generated knowledge registries from previous runs.

### Current status

KEB is PARTIAL because implementation exists but packaging/import boundaries are inconsistent. Do not implement a second KEB adapter; normalize the existing adapter.

## GBOGEB feature lineage

### Existing connectors and references

- `core/gbogeb/gbogeb.py` implements governance metrics and compliance checks.
- `local_mcp/knowledge_integration_v2.3.py` calls GBOGEB for metric collection and compliance.
- `DMAIC_V3/core/twelve_cluster_orchestrator.py` optionally constructs GBOGEB observability.
- `staging/GBOGEB_ABACUS_DOW_INTEGRATION_BRIDGE.py` is the cross-system DOW bridge.
- `.github/workflows/gbogeb-abacus-integration-ci-cd.yml` is the CI/CD integration workflow.
- `rtm_integration/automation/config/project.yml` contains repository cross-links for `GBOGEB/ABACUS` and `GBOGEB/DOCX_RTM_Automation`.
- `tracking_v2.3/tasks/tasks.json` contains runtime tracking references to `GBOGEB/ABACUS` PRs, action runs, artifacts, and Pages URL.

### Current status

GBOGEB is PARTIAL, not missing. The highest-value next action is to reconcile staging paths with workflow path filters.

## Recursive feature lineage

### V2.2 Feature → V2.3 Equivalent → Current Status

| V2.2 feature | V2.3/current equivalent | Current status | Recommendation |
|---|---|---:|---|
| Recursive DMAIC execution | `ABACUS-v032/execute_full_dmaic_phases_0_to_9_v033.py`; `DMAIC_V3/full_pipeline_orchestrator.py` | SUPERSEDED | keep lineage, use current pipeline |
| Artifact recursive metadata | `DOWRecursiveHooksInjector.inject_recursive_hooks` | COMPLETE | retain |
| Temporal recursive registration | `Phase6Knowledge.execute` with `register_recursive_hook` | PARTIAL | normalize tracker availability |
| Stop-rule recursion | `src/dmaic/recursion.py.should_stop` | COMPLETE | retain |
| Convergence analysis | `src/dmaic/recursion.py.analyze_convergence` and ABACUS-v032 phase 9 reports | COMPLETE | retain |
| Hook retrieval API | no active `get_recursive_hooks()` found | MISSING | add/read utility if required |

## Deployment feature lineage

Deployment is COMPLETE at the repository level. Active workflows live under `.github/workflows/`. Disabled legacy workflows live under `.github/workflows/legacy/*.old`. Pending/scaffold workflows live under `.github/workflows-pending/`. Additional DMAIC-specific workflows live under `DMAIC_V3/.github/workflows/`.
