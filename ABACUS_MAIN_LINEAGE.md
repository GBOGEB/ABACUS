# ABACUS Main Architectural Lineage

Date: 2026-06-11

## Purpose

This lineage record maps the main ABACUS runtime architecture before new implementation work begins. Its central conclusion is that the requested V2.3/V3.0 capabilities are not absent; they are distributed across historical, current, and staging paths.

## Mainline lineage graph

```text
V2.1 / V2.2 recursive DMAIC artifacts
  ├─ recursive_dmaic_engine lineage documented in V2.2 status/handover files
  ├─ KEB/GBOGEB templates and timeout notes documented in session quick references
  └─ recursive behavior expectations captured in recursive hook parity documents
        ↓
V2.3 agent and knowledge integration layer
  ├─ local_mcp/agent_orchestrator_v3.0.py
  ├─ local_mcp/knowledge_integration_v2.3.py
  ├─ local_mcp/agents/*_v2.3_OPTIMIZED.py
  └─ orchestrator_config.yaml
        ↓
DMAIC_V3 production pipeline and 12-cluster runtime
  ├─ DMAIC_V3/full_pipeline_orchestrator.py
  ├─ DMAIC_V3/core/twelve_cluster_orchestrator.py
  ├─ DMAIC_V3/phases/phase0_init.py ... phase9_documentation.py
  ├─ core/keb/keb.py
  └─ core/gbogeb/gbogeb.py
        ↓
ABACUS-v032 / v4.4 lineage and runtime manifests
  ├─ ABACUS-v032/execute_full_dmaic_phases_0_to_9_v033.py
  ├─ runtime/**/*.yaml
  ├─ reports/runtime_registry_report.json
  └─ metrics/federation/runtime_registry.json
        ↓
Deployment / CI/CD layer
  ├─ .github/workflows/*.yml
  ├─ .github/workflows/legacy/*.old
  ├─ .github/workflows-pending/*.yml
  └─ DMAIC_V3/.github/workflows/*.yml
```

## Canonical runtime candidates

| Runtime candidate | File path | Exact symbol / entrypoint | Role | Status | Confidence | Recommendation |
|---|---|---|---|---:|---:|---|
| V2.3 Agent Orchestrator V3.0 | `local_mcp/agent_orchestrator_v3.0.py` | `AgentOrchestratorV3`, `initialize_agents`, `execute_dmaic_cycle`, `main` | Loads six V2.3 agents and knowledge integration | RENAMED | HIGH | retain; document as agent orchestration layer |
| DMAIC V3 full pipeline | `DMAIC_V3/full_pipeline_orchestrator.py` | `FullPipelineOrchestrator`, `execute_full_pipeline`, `main` | Current phase pipeline runner | COMPLETE | HIGH | retain as DMAIC pipeline entrypoint |
| 12-cluster orchestration | `DMAIC_V3/core/twelve_cluster_orchestrator.py` | `TwelveClusterOrchestrator`, `CLUSTER_CONTRACT`, `run_phases_with_hooks` | Parallel cluster/temporal hook runtime | COMPLETE | HIGH | retain; mark as cluster execution layer |
| DOW/GBOGEB bridge | `staging/GBOGEB_ABACUS_DOW_INTEGRATION_BRIDGE.py` | `GBOGEBAbacusDOWBridge`, `execute_integrated_pipeline` | Cross-system bridge between DOW, DMAIC, and GBOGEB namespace | PARTIAL | HIGH | retain; promote or update workflow paths |
| Runtime manifest plane | `runtime/` | YAML manifests such as `runtime/manifests/runtime-topology.yaml` | Declarative runtime topology and governance plane | PARTIAL | MEDIUM | retain; validate against code entrypoints |

## Evidence basis

The lineage evidence is organized below by concern and uses exact repository paths, symbols, workflows, and configuration references.

## Mainline evidence by concern

### Orchestration

- The V3.0 agent orchestrator exists as `AgentOrchestratorV3` and explicitly coordinates V2.3 optimized agents.
- The DMAIC V3 runtime exists as `FullPipelineOrchestrator`, which executes phase modules and writes execution artifacts.
- The 12-cluster runtime exists as `TwelveClusterOrchestrator`, with a static cluster contract, optional KEB/GBOGEB integration, and phase hooks.
- The DOW/GBOGEB bridge imports `FullPipelineOrchestrator` and invokes it during integrated execution.

### Knowledge and KEB

- `KnowledgeIntegrationV23` is the current knowledge integration adapter. It initializes canonical knowledge entries and bridges KEB/GBOGEB calls.
- `core/keb/keb.py` is the execution backbone implementation.
- Knowledge packages and ABACUS-UNIFIED knowledge books preserve the non-code lineage.

### Governance and GBOGEB

- `core/gbogeb/gbogeb.py` is the local governance/observability implementation.
- The GBOGEB namespace appears in repository metadata, workflows, RTM automation config, and tracking JSON.
- `staging/GBOGEB_ABACUS_DOW_INTEGRATION_BRIDGE.py` is the active bridge implementation found in the tree, but its workflow path filters still reference root-level paths.

### Recursion

- V2.2 recursive expectations survived as artifact injection, temporal events, phase-level registration, and stop/convergence utilities.
- A direct `get_recursive_hooks()` runtime retrieval function was not found and is therefore the only validated missing recursive API surface.

### Deployment

- `.github/workflows/` is populated with active workflows.
- `.github/workflows/legacy/` and `.github/workflows-pending/` show archived/pending workflow lineages rather than missing deployment work.
- `DMAIC_V3/.github/workflows/` adds nested project workflows.

## Duplicate architecture elimination decision

No new orchestrator, KEB adapter, GBOGEB connector, recursive hook engine, or deployment pipeline should be created until the following refactor-only tasks are complete:

1. Declare canonical entrypoints for agent orchestration, DMAIC pipeline execution, and 12-cluster execution.
2. Normalize KEB/GBOGEB imports so `core/keb/keb.py` and `core/gbogeb/gbogeb.py` can be imported consistently.
3. Update `gbogeb-abacus-integration-ci-cd.yml` path filters or promote the staging bridge to the expected path.
4. Add or document a recursive hook retrieval/read API only if current consumers require V2.2 parity.
5. Archive or label duplicate workflow families to reduce CI ambiguity.
