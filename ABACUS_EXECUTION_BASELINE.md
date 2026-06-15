# ABACUS Execution Baseline

Date: 2026-06-11

## Purpose

This baseline converts the validated lineage findings into runtime ownership and execution governance. It does not create new architecture, new orchestrators, duplicate registries, or duplicate integration layers.

## Runtime SSOT

**Selected orchestrator:** `DMAIC_V3/core/twelve_cluster_orchestrator.py` / `TwelveClusterOrchestrator`.

**Status:** Active SSOT for runtime governance and canonical 12-cluster execution.

**Justification:**

- `README.md` explicitly declares `DMAIC_V3/core/twelve_cluster_orchestrator.py` as the canonical orchestrator path and `local_mcp/agent_orchestrator_v3.0.py` as compatibility wrapper.
- `TwelveClusterOrchestrator` is named "Canonical 12-Cluster Orchestrator V3.0 for DMAIC" in the module docstring.
- `TwelveClusterOrchestrator` owns the cluster contract, phase sequence, KEB/GBOGEB optional initialization, temporal event capture, phase parallel execution, phase hook execution, and report generation.
- `DMAIC_V3/tests/test_twelve_cluster_orchestrator.py` directly tests the canonical 12-cluster contract, parallel execution, temporal hooks, run scoping, failed phase behavior, and timeout enforcement.

**Evidence:**

- `README.md`: canonical orchestrator section maps canonical path to `DMAIC_V3/core/twelve_cluster_orchestrator.py` and compatibility wrapper to `local_mcp/agent_orchestrator_v3.0.py`.
- `DMAIC_V3/core/twelve_cluster_orchestrator.py`: module docstring, `TwelveClusterOrchestrator`, `CLUSTER_CONTRACT`, `PHASE_SEQUENCE`, KEB/GBOGEB initialization, `run_phases_with_hooks`, and `generate_report`.
- `DMAIC_V3/tests/test_twelve_cluster_orchestrator.py`: coverage for contract, temporal hooks, and timeout behavior.

### Runtime authority table

| Runtime | Status | References | Recommendation |
| -------------------- | ------ | ---------- | -------------- |
| Active SSOT: `DMAIC_V3/core/twelve_cluster_orchestrator.py` / `TwelveClusterOrchestrator` | Active SSOT | `README.md` canonical path; `docs_versioned/v2.3/migration/to_v33.md` names it central; direct tests in `DMAIC_V3/tests/test_twelve_cluster_orchestrator.py`; optional KEB/GBOGEB runtime initialization. | Retain as governance SSOT; do not create a new orchestrator. |
| Secondary Runtime: `DMAIC_V3/full_pipeline_orchestrator.py` / `FullPipelineOrchestrator` | Secondary operational runtime | Active DOW workflows run it; deployment docs use it; it imports and executes phase modules 0-9. | Retain as operational phase-runner until a later consolidation task aligns workflow entrypoints with the 12-cluster SSOT. |
| Legacy Runtime: `local_mcp/agent_orchestrator_v3.0.py` / `AgentOrchestratorV3` | Compatibility / V2.3 lineage runtime | README labels it compatibility wrapper; V2.3 CI workflow executes it; it loads six V2.3 optimized agents and `KnowledgeIntegrationV23`. | Retain for compatibility and agent tests; do not promote it above 12-cluster SSOT. |
| Experimental Runtime | None selected from the three requested candidates | The three analyzed candidates map to active SSOT, secondary operational runtime, and compatibility runtime. Separate corrupted/fixed copies of `full_pipeline_orchestrator` are deprecated lineage artifacts, not requested candidates. | Do not create or nominate an experimental orchestrator. |

## Runtime candidate analysis

### `local_mcp/agent_orchestrator_v3.0.py`

- **Purpose:** V2.3 agent orchestration and compatibility runtime; coordinates six optimized agents and initializes `KnowledgeIntegrationV23`.
- **Invocation path:** direct script execution in `.github/workflows/v23-cicd.yml`; README “Get Started” also lists `python local_mcp/agent_orchestrator_v3.0.py`.
- **Dependencies:** dynamically loads `local_mcp/knowledge_integration_v2.3.py`; dynamically loads six files from `local_mcp/agents/` through `_AGENT_CATALOGUE`.
- **Active references:** README compatibility wrapper, V2.3 workflow, tooling workflow help check, API docs and handover index.
- **Downstream consumers:** V2.3 agent CI, generated V2.3 artifacts, handover-to-execution bridge documentation.
- **Baseline decision:** legacy/compatibility runtime, not SSOT.

### `DMAIC_V3/core/twelve_cluster_orchestrator.py`

- **Purpose:** canonical 12-cluster orchestration, temporal phase hooks, cluster contract, optional KEB/GBOGEB runtime integration.
- **Invocation path:** `python DMAIC_V3/core/twelve_cluster_orchestrator.py --test`; imported by tests; named in README as canonical path.
- **Dependencies:** optional `KEB` and `GBOGEB`; standard library concurrency; phase task factories supplied by callers.
- **Active references:** README canonical orchestrator section, migration docs, tests, lineage docs.
- **Downstream consumers:** tests, runtime reports, consumers requiring the canonical cluster contract and temporal hook events.
- **Baseline decision:** Active Runtime SSOT.

### `DMAIC_V3/full_pipeline_orchestrator.py`

- **Purpose:** operational DMAIC V3.3 phase pipeline runner for phase 0 initialization through phase 9 documentation generation.
- **Invocation path:** direct script execution; active DOW workflows run `python DMAIC_V3/full_pipeline_orchestrator.py`; docs show `python DMAIC_V3/full_pipeline_orchestrator.py --iteration ...`.
- **Dependencies:** `DMAICConfig`, `StateManager`, idempotency wrapper, planning matrix tracker, background change detector, phase modules 0-9.
- **Active references:** DOW scheduled/main CI workflows, enhanced CI workflow, deployment/handover docs.
- **Downstream consumers:** workflow runs, reports, `staging/GBOGEB_ABACUS_DOW_INTEGRATION_BRIDGE.py`, deployment artifacts.
- **Baseline decision:** Secondary runtime. Retain; do not duplicate.

## Registry SSOT

**Selected registry:** `runtime/manifests/runtime-topology.yaml` for runtime/deployment topology governance.

**Justification:**

- The topology manifest declares the runtime repository, governance repository, protected environments, and runtime capabilities.
- `metrics/federation/runtime_registry.json` and `reports/runtime_registry_report.json` are evidence/report outputs, not the topology authority.
- `knowledge_packages/dmaic_core_knowledge.yaml` is the seed knowledge package SSOT for DMAIC knowledge, not a runtime topology registry.

**Evidence:**

- `runtime/manifests/runtime-topology.yaml` defines `runtime.repository: GBOGEB/ABACUS`, governance metadata, capabilities, and protected environments.
- `metrics/federation/runtime_registry.json` stores repository runtime evidence/truth matrix/renderability status.
- `reports/runtime_registry_report.json` stores runtime coverage report output.
- `knowledge_packages/dmaic_core_knowledge.yaml` defines the DMAIC process knowledge package.

## Integration SSOT

### KEB status

- **Status:** PARTIAL but consumed.
- **Implementation SSOT:** `core/keb/keb.py`.
- **Consumption adapter:** `local_mcp/knowledge_integration_v2.3.py`.
- **Evidence:** `KnowledgeIntegrationV23` imports and constructs `KEB`; `TwelveClusterOrchestrator` optionally constructs `KEB`; `.github/workflows/v23-cicd.yml` runs `local_mcp/knowledge_integration_v2.3.py`.
- **Decision:** retain `core/keb/keb.py`; normalize imports and start/stop expectations before adding features.

### GBOGEB status

- **Status:** PARTIAL but consumed.
- **Implementation SSOT:** `core/gbogeb/gbogeb.py`.
- **Bridge candidate:** `staging/GBOGEB_ABACUS_DOW_INTEGRATION_BRIDGE.py`.
- **Evidence:** `KnowledgeIntegrationV23` imports and constructs `GBOGEB`; `TwelveClusterOrchestrator` optionally constructs `GBOGEB`; `.github/workflows/gbogeb-abacus-integration-ci-cd.yml` references GBOGEB bridge execution but points at root-level paths.
- **Decision:** retain `core/gbogeb/gbogeb.py`; fix stale bridge workflow paths before claiming bridge closure.

### DMAIC status

- **Status:** COMPLETE as an operational runtime, with SSOT governance split requiring consolidation.
- **Execution entrypoints:** `DMAIC_V3/dmaic_v3_engine.py` and `DMAIC_V3/full_pipeline_orchestrator.py`.
- **Governance SSOT:** `DMAIC_V3/core/twelve_cluster_orchestrator.py`.
- **Evidence:** CD workflows execute `DMAIC_V3.dmaic_v3_engine`; DOW workflows execute `DMAIC_V3/full_pipeline_orchestrator.py`; README declares 12-cluster orchestrator canonical.
- **Decision:** retain current operational entrypoints; backlog a workflow alignment task rather than creating new orchestration.

## Validated Gaps

Evidence-backed only:

1. **GBOGEB bridge path drift:** active workflow references root-level `GBOGEB_ABACUS_DOW_INTEGRATION_BRIDGE.py`, `test_integration_bridge.py`, and `UNIFIED_GLOB_CONFIG.yaml`, while the bridge implementation found in this repo is `staging/GBOGEB_ABACUS_DOW_INTEGRATION_BRIDGE.py`.
2. **Recursive hook retrieval parity:** historical `get_recursive_hooks(enabled_only=True)` is documented, but active runtime modules do not expose a dedicated retrieval API. Current equivalents are artifact-level `recursive_hooks` injection and phase-level temporal registration.
3. **Runtime entrypoint split:** README declares `TwelveClusterOrchestrator` canonical, while active deployment/DOW workflows still execute `DMAIC_V3.dmaic_v3_engine` and `DMAIC_V3/full_pipeline_orchestrator.py`.
4. **Integration import inconsistency:** `KnowledgeIntegrationV23` imports `core.keb.keb` and `core.gbogeb.gbogeb`; `TwelveClusterOrchestrator` uses top-level `from keb import KEB` / `from gbogeb import GBOGEB` after path insertion. This is import consolidation work, not a missing component.

## Deferred Work

The following work is explicitly not required for this baseline:

- Building a new orchestrator.
- Building a new KEB adapter.
- Building a new GBOGEB connector.
- Replacing `DOWRecursiveHooksInjector`.
- Replacing the DMAIC phase runner.
- Implementing `get_recursive_hooks()` in this task.
- Moving or deleting workflows in this task.

## Deprecated Targets

Items that should **not** be developed as new architecture:

- A second “Orchestrator V3.0” implementation.
- A parallel KEB registry separate from `core/keb/keb.py` and `KnowledgeIntegrationV23`.
- A parallel GBOGEB metrics engine separate from `core/gbogeb/gbogeb.py`.
- A new recursive hook engine separate from `DMAIC_V3/local_mcp/agents/dow_recursive_hooks_injector.py`.
- Root-level duplicate GBOGEB bridge files unless the chosen remediation is to promote the existing `staging/` implementation with matching tests/config.
- Corrupted/fixed duplicate full-pipeline copies as canonical runtime targets.
