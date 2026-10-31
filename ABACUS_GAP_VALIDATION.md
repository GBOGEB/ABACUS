# ABACUS Gap Validation — Architectural Lineage Verification

Date: 2026-06-11

## Validation rule

This document validates the requested V2.3/V3.0 gaps before implementation. It treats a gap as missing only when no active code, workflow, runtime manifest, or documented lineage exists. The intent is to avoid duplicate architecture.

## Executive status table

| Gap / capability | Status | Confidence | Primary evidence | Recommendation |
|---|---:|---:|---|---|
| Orchestrator V3.0 | RENAMED | HIGH | `local_mcp/agent_orchestrator_v3.0.py` (`AgentOrchestratorV3`), `DMAIC_V3/core/twelve_cluster_orchestrator.py` (`TwelveClusterOrchestrator`), `DMAIC_V3/full_pipeline_orchestrator.py` (`FullPipelineOrchestrator`) | retain + refactor entrypoint naming |
| KEB integration | PARTIAL | HIGH | `core/keb/keb.py` (`KEB`), `local_mcp/knowledge_integration_v2.3.py` (`KnowledgeIntegrationV23`), `DMAIC_V3/core/twelve_cluster_orchestrator.py` (`KEB_AVAILABLE`, `self.keb`) | retain + refactor imports/packaging |
| GBOGEB integration | PARTIAL | HIGH | `core/gbogeb/gbogeb.py` (`GBOGEB`), `staging/GBOGEB_ABACUS_DOW_INTEGRATION_BRIDGE.py` (`GBOGEBAbacusDOWBridge`), `.github/workflows/gbogeb-abacus-integration-ci-cd.yml` | retain + replace stale workflow paths |
| Recursive hooks parity | PARTIAL | HIGH | `DMAIC_V3/local_mcp/agents/dow_recursive_hooks_injector.py`, `DMAIC_V3/phases/phase6_knowledge.py`, `src/dmaic/recursion.py`, `PHASE_B_RECURSIVE_HOOKS_PARITY_AUDIT_V4.4.0.md` | retain + add retrieval/query API if needed |
| Deployment automation | COMPLETE | HIGH | `.github/workflows/*.yml`, `.github/workflows-pending/*.yml`, `.github/workflows/legacy/*.old`, `run_streamlined_deployment.py`, `run_comprehensive_deployment.py` | retain + archive disabled/duplicate workflows |

## Detailed gap records

### 1. Orchestrator V3.0

**Status:** RENAMED  
**Confidence:** HIGH  
**Recommendation:** retain the existing orchestrators; refactor documentation and entrypoint naming instead of creating a new orchestrator.

**Determination:** An orchestrator already exists under more than one lineage. The strongest direct match is `local_mcp/agent_orchestrator_v3.0.py`, which defines `AgentOrchestratorV3` and explicitly describes itself as an Agent Orchestrator V3.0 for V2.3 agents. The production DMAIC runtime also has `FullPipelineOrchestrator`, and the parallel/cluster runtime has `TwelveClusterOrchestrator`.

**Evidence:**

- `local_mcp/agent_orchestrator_v3.0.py`: `AgentOrchestratorV3`, `_AGENT_CATALOGUE`, `initialize_agents`, `execute_agent`, `execute_dmaic_cycle`, and `main`.
- `local_mcp/agent_orchestrator_v3.0.py`: loads `KnowledgeIntegrationV23` before the six V2.3 agents, making it a coordination runtime rather than a placeholder.
- `orchestrator_config.yaml`: configures agent paths, pipelines, DOW integration stages, `dmaic_phases`, `dow_integration`, and recursive hook/convergence agents.
- `DMAIC_V3/full_pipeline_orchestrator.py`: `FullPipelineOrchestrator`, `execute_full_pipeline`, and `main` for the DMAIC phase pipeline.
- `DMAIC_V3/core/twelve_cluster_orchestrator.py`: `TwelveClusterOrchestrator`, `CLUSTER_CONTRACT`, `execute_phase_parallel`, and `run_phases_with_hooks`.
- `staging/GBOGEB_ABACUS_DOW_INTEGRATION_BRIDGE.py`: imports and instantiates `FullPipelineOrchestrator` for cross-system execution.
- `deployment_matrix.md`: lists DMAIC V3 Engine, 12-Cluster Orchestrator, CI/CD Orchestrator, and DOW Bridge as working deployment units.

**Duplicate architecture risk:** HIGH if a new “Orchestrator V3.0” is created without first choosing which current runtime is canonical. The correct next action is to define canonical ownership among agent orchestration, DMAIC phase orchestration, and 12-cluster execution.

### 2. KEB integration

**Status:** PARTIAL  
**Confidence:** HIGH  
**Recommendation:** retain the current KEB implementation; refactor imports and package boundaries before adding features.

**Determination:** KEB is implemented as a core execution backbone and is referenced by orchestration and knowledge layers. The integration is partial because some code uses top-level imports (`from keb import KEB`) that depend on path manipulation or execution context, while canonical code lives under `core/keb/keb.py`.

**Evidence:**

- `core/keb/keb.py`: `KEB` class provides queued task execution, worker lifecycle, task scheduling, and results tracking.
- `local_mcp/knowledge_integration_v2.3.py`: `KnowledgeIntegrationV23` initializes `KEB(max_workers=2, max_memory_mb=2048)` and exposes `schedule_agent_task` with timeout protection.
- `DMAIC_V3/core/twelve_cluster_orchestrator.py`: attempts to import `KEB`, gates it through `KEB_AVAILABLE`, and initializes `self.keb` when enabled.
- `orchestrator_config.yaml`: defines pipeline stages and DOW/recursive integration agents, while KEB runtime parameters are constructed in code (`KEB(max_workers=...)`).
- `knowledge_packages/dmaic_core_knowledge.yaml` and `knowledge_packages/dmaic_core_knowledge.json`: provide seed knowledge content used by the knowledge lineage.
- `ABACUS-UNIFIED/KNOWLEDGE_PACK_INDEX.md` and `ABACUS-UNIFIED/books/KNOWLEDGE_MANAGEMENT_BOOK_v032.1.md`: document the knowledge-pack lineage.
- `DMAIC_V3/phases/phase6_knowledge.py`: implements the Phase 6 knowledge layer and report generation, with recursive hook registration support.

**Hidden integration points:** `KnowledgeIntegrationV23` is invoked by `AgentOrchestratorV3.initialize_agents`, while `TwelveClusterOrchestrator` invokes KEB as an optional execution backbone. This means KEB is not missing; it is split across core, local MCP, and DMAIC runtimes.

**Partiality / risk:** Import resolution is inconsistent (`core/keb/keb.py` versus `from keb import KEB`), so a new adapter should not be created until imports are normalized and package exports are audited.

### 3. GBOGEB integration

**Status:** PARTIAL  
**Confidence:** HIGH  
**Recommendation:** retain the current GBOGEB implementation and bridge; replace stale workflow paths and archive superseded references.

**Determination:** GBOGEB exists as a core observability/governance component, bridge implementation, workflow integration, and repository namespace. It is partial because the active workflow points to root-level bridge/test/config paths while the current bridge implementation is under `staging/`.

**Evidence:**

- `core/gbogeb/gbogeb.py`: `GBOGEB` class implements metric collection, compliance checks, report generation, and workspace persistence.
- `local_mcp/knowledge_integration_v2.3.py`: initializes `GBOGEB` and uses it for metrics and compliance checks through timeout-protected calls.
- `DMAIC_V3/core/twelve_cluster_orchestrator.py`: imports `GBOGEB`, gates it through `GBOGEB_AVAILABLE`, and initializes `self.gbogeb` for observability.
- `staging/GBOGEB_ABACUS_DOW_INTEGRATION_BRIDGE.py`: `GBOGEBAbacusDOWBridge` coordinates DOW processing and DMAIC processing, imports `FullPipelineOrchestrator`, and provides `create_unified_glob_config`.
- `.github/workflows/gbogeb-abacus-integration-ci-cd.yml`: active workflow for “GBOGEB/ABACUS ↔ DOW Integration CI/CD”.
- `rtm_integration/automation/config/project.yml`: names `GBOGEB/ABACUS` and `GBOGEB/DOCX_RTM_Automation` cross-repository integration targets.
- `tracking_v2.3/tasks/tasks.json`: stores GitHub links to `GBOGEB/ABACUS` PRs, workflow runs, and pages deployments.
- `src/dmaic/contract.py`: references `GBOGEB/codespace_jyperter` as tuple-source repository metadata.

**Partiality / risk:** The workflow path filter includes `GBOGEB_ABACUS_DOW_INTEGRATION_BRIDGE.py`, `test_integration_bridge.py`, and `UNIFIED_GLOB_CONFIG.yaml` at repository root; the bridge file actually found is `staging/GBOGEB_ABACUS_DOW_INTEGRATION_BRIDGE.py`. This should be fixed before implementing new GBOGEB connectors.

### 4. Recursive hooks

**Status:** PARTIAL  
**Confidence:** HIGH  
**Recommendation:** retain current artifact-level recursive hooks and stop-rule utilities; add/refactor a retrieval API only if consumers require V2.2 API parity.

**Determination:** V2.2-style recursive behavior migrated into multiple current forms: artifact hook injection, phase-level registration, convergence/stop-rule utilities, and 12-cluster temporal hooks. The lost or incomplete portion is a dedicated active `get_recursive_hooks()` retrieval API, already documented as a gap in the parity audit.

**V2.2 → V2.3/current map:**

| V2.2 feature | V2.3 / current equivalent | Current status | Confidence | Recommendation |
|---|---|---:|---:|---|
| Recursive DMAIC engine execution | `ABACUS-v032/execute_full_dmaic_phases_0_to_9_v033.py` phase 0-9 runner and `DMAIC_V3/full_pipeline_orchestrator.py` phase runner | SUPERSEDED | HIGH | retain v032 as lineage; use DMAIC_V3 for current runtime |
| Recursive hooks embedded in artifacts | `DMAIC_V3/local_mcp/agents/dow_recursive_hooks_injector.py` writes `recursive_hooks` payloads | COMPLETE | HIGH | retain |
| Phase-level hook registration | `DMAIC_V3/phases/phase6_knowledge.py` calls `register_recursive_hook` when temporal tracker is available | PARTIAL | HIGH | retain; normalize tracker import |
| Iteration stop/convergence rules | `src/dmaic/recursion.py` (`should_stop`, `analyze_convergence`, `generate_stop_rules`) | COMPLETE | HIGH | retain |
| Temporal start/end hooks per phase | `DMAIC_V3/core/twelve_cluster_orchestrator.py` (`run_phases_with_hooks`, `_record_temporal_event`) | RENAMED | HIGH | retain |
| Dedicated `get_recursive_hooks()` API | Not found in active runtime; documented by parity audit as missing | MISSING | HIGH | refactor/add lightweight read utility if needed |

**Evidence:**

- `PHASE_B_RECURSIVE_HOOKS_PARITY_AUDIT_V4.4.0.md`: concludes recursive hooks are actively injected and validated, but a historical `get_recursive_hooks` API is not present in active runtime modules.
- `DMAIC_V3/local_mcp/agents/dow_recursive_hooks_injector.py`: `DOWRecursiveHooksInjector.inject_recursive_hooks` writes `recursive_hooks` fields with hook metadata, dependency chain, validation rules, and idempotency fields.
- `DMAIC_V3/phases/phase6_knowledge.py`: `Phase6Knowledge.execute` attempts temporal tracker hook registration and records `recursive_hooks_registered` in outputs.
- `src/dmaic/recursion.py`: provides reusable stop and convergence analysis functions.
- `DMAIC_V3/core/twelve_cluster_orchestrator.py`: `run_phases_with_hooks` records standardized phase start/end events.
- `.github/workflows/dow-integration.yml`: invokes DOW integration activities; `.github/workflows/recursive-build.yml` provides recursive build automation.

### 5. Deployment

**Status:** COMPLETE  
**Confidence:** HIGH  
**Recommendation:** retain active workflows, reconcile duplicate CI/CD names, and archive disabled or pending scaffolds.

**Determination:** CI and deployment workflows are present and active. There are also pending and legacy workflow locations that should not be treated as missing implementation.

**Evidence:**

- Active workflow directory: `.github/workflows/` contains CI, CD, release, docs deployment, pages, runtime governance, runtime verification, DOW, GBOGEB, recursive build, and validation workflows.
- Disabled/archived workflow directory: `.github/workflows/legacy/` contains `.old` workflow files.
- Pending/scaffold workflow directory: `.github/workflows-pending/` contains workflow files plus a catalog that describes 37 active workflows and separates pending documentation.
- Nested DMAIC workflows: `DMAIC_V3/.github/workflows/` contains `DMAIC_V3/.github/workflows/ci-main.yml`, `DMAIC_V3/.github/workflows/cd-main.yml`, phase CI workflows, and `DMAIC_V3/.github/workflows/release.yml`.
- Deployment scripts: `run_streamlined_deployment.py`, `run_comprehensive_deployment.py`, `abacus_v21_deployment_execution.py`, `ci_cd_automation.ps1`, and `setup_github.sh`.
- Release pipelines: `.github/workflows/release.yml`, `.github/workflows/delta-1-release.yml`, `.github/workflows/cd-unified.yml`, and `DMAIC_V3/.github/workflows/release.yml`.

**Active versus disabled:** Active GitHub Actions are files directly under `.github/workflows/` with `on:` triggers. Legacy disabled files are retained under `.github/workflows/legacy/*.old`. Pending/scaffold workflows exist under `.github/workflows-pending/` and should not be counted as active GitHub Actions until moved into `.github/workflows/`.

## Final recommendation

Do not implement new architecture for any of the above categories yet. The repository already contains orchestrators, KEB, GBOGEB, recursive hooks, and deployment automation. The next safe work is consolidation: pick canonical entrypoints, normalize package imports, repair stale workflow paths, and document supported runtime paths.
