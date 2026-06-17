# ABACUS Integration Matrix

Date: 2026-06-11

## Scope

This matrix checks runtime **consumption**, not merely existence. The components below are treated as consumed only when repository code, workflows, tests, or configuration invoke or reference them as part of an execution path.

## Consumption matrix

| Component | Exists | Referenced | Executed | SSOT |
| --------- | ------ | ---------- | -------- | ---- |
| KEB | Yes: `core/keb/keb.py` defines `KEB` and `schedule_task`. | Yes: `local_mcp/knowledge_integration_v2.3.py` imports `core.keb.keb.KEB`; `DMAIC_V3/core/twelve_cluster_orchestrator.py` imports `KEB`; README maps C9-C10 runtime operations to `local_mcp/knowledge_integration_v2.3.py`. | Partial: `KnowledgeIntegrationV23` constructs `KEB(max_workers=2, max_memory_mb=2048)` and exposes `schedule_agent_task`; `TwelveClusterOrchestrator` constructs KEB when `KEB_AVAILABLE`; `.github/workflows/v23-cicd.yml` executes `python local_mcp/knowledge_integration_v2.3.py`. | Implementation SSOT: `core/keb/keb.py`; consumption adapter: `local_mcp/knowledge_integration_v2.3.py`. |
| GBOGEB | Yes: `core/gbogeb/gbogeb.py` defines `GBOGEB`, `collect_metric`, and `check_compliance`. | Yes: `local_mcp/knowledge_integration_v2.3.py` imports `core.gbogeb.gbogeb.GBOGEB`; `DMAIC_V3/core/twelve_cluster_orchestrator.py` imports `GBOGEB`; `.github/workflows/gbogeb-abacus-integration-ci-cd.yml` references the GBOGEB bridge. | Partial: `KnowledgeIntegrationV23` constructs `GBOGEB`; `TwelveClusterOrchestrator` constructs GBOGEB when `GBOGEB_AVAILABLE`; bridge workflow references root-level bridge path while implementation found under `staging/`. | Implementation SSOT: `core/gbogeb/gbogeb.py`; bridge candidate: `staging/GBOGEB_ABACUS_DOW_INTEGRATION_BRIDGE.py` pending workflow path reconciliation. |
| DMAIC | Yes: `DMAIC_V3/dmaic_v3_engine.py`, `DMAIC_V3/full_pipeline_orchestrator.py`, and `DMAIC_V3/phases/`. | Yes: `.github/workflows/cd.yml` and `.github/workflows/cd-unified.yml` run `python -m DMAIC_V3.dmaic_v3_engine`; DOW workflows run `DMAIC_V3/full_pipeline_orchestrator.py`; README marks `DMAIC_V3/core/twelve_cluster_orchestrator.py` canonical. | Yes: active workflows execute DMAIC engine/full pipeline commands; tests cover `TwelveClusterOrchestrator`. | Runtime governance SSOT: `DMAIC_V3/core/twelve_cluster_orchestrator.py`; operational workflow entrypoints remain `DMAIC_V3/dmaic_v3_engine.py` and `DMAIC_V3/full_pipeline_orchestrator.py` until consolidated. |
| Agents | Yes: `local_mcp/agents/*_v2.3_OPTIMIZED.py` and `DMAIC_V3/agents/`. | Yes: `local_mcp/agent_orchestrator_v3.0.py` `_AGENT_CATALOGUE`; `orchestrator_config.yaml` DOW integration agents; `.github/workflows/v23-cicd.yml` tests the V2.3 orchestrator and smoke agent. | Partial: V2.3 workflow executes `local_mcp/agent_orchestrator_v3.0.py`, `local_mcp/knowledge_integration_v2.3.py`, and one smoke agent; DOW executor calls DOW agents by name. | Agent catalogue SSOT: `local_mcp/agent_orchestrator_v3.0.py` for V2.3 compatibility; DOW agent routing SSOT: `orchestrator_config.yaml` plus `DMAIC_V3/dow_integration_executor.py`. |

## Evidence details

### KEB consumption

- `local_mcp/knowledge_integration_v2.3.py` imports `KEB` from `core.keb.keb` and `GBOGEB` from `core.gbogeb.gbogeb`.
- `KnowledgeIntegrationV23.__init__` constructs `KEB(max_workers=2, max_memory_mb=2048)` and `GBOGEB(workspace=...)` when core modules are available.
- `KnowledgeIntegrationV23.schedule_agent_task` calls `self.keb.schedule_task(...)` through timeout protection.
- `DMAIC_V3/core/twelve_cluster_orchestrator.py` imports `KEB`, sets `KEB_AVAILABLE`, and constructs `KEB(max_workers=min(max_workers, 4), max_memory_mb=2048)` when enabled.

### GBOGEB consumption

- `KnowledgeIntegrationV23.collect_agent_metric` calls `self.gbogeb.collect_metric(...)`.
- `KnowledgeIntegrationV23.check_compliance` calls `self.gbogeb.check_compliance(...)`.
- `DMAIC_V3/core/twelve_cluster_orchestrator.py` constructs `GBOGEB(workspace="DMAIC_V3_OUTPUT/12cluster_workspace")` when enabled.
- `.github/workflows/gbogeb-abacus-integration-ci-cd.yml` references root-level `GBOGEB_ABACUS_DOW_INTEGRATION_BRIDGE.py`, while the located implementation is `staging/GBOGEB_ABACUS_DOW_INTEGRATION_BRIDGE.py`; therefore bridge execution is not closed.

### DMAIC and agent consumption

- `.github/workflows/cd.yml` and `.github/workflows/cd-unified.yml` run `python -m DMAIC_V3.dmaic_v3_engine --mode full --iterations 1`.
- `.github/workflows/dow-scheduled.yml` and `.github/workflows/dow-main-cicd.yml` run `python DMAIC_V3/full_pipeline_orchestrator.py`.
- `.github/workflows/v23-cicd.yml` runs `python local_mcp/agent_orchestrator_v3.0.py`, `python local_mcp/knowledge_integration_v2.3.py`, and a V2.3 smoke agent.
- `DMAIC_V3/tests/test_twelve_cluster_orchestrator.py` imports and verifies `TwelveClusterOrchestrator` contract, parallel execution, temporal hooks, and timeout behavior.

## Integration conclusion

KEB and GBOGEB are consumed, but the consumption is **partial** because execution paths are split across `KnowledgeIntegrationV23`, optional 12-cluster initialization, and a GBOGEB workflow that points at stale root-level bridge paths. No new integration layer should be created; the next work is import/path consolidation and bridge workflow correction.
