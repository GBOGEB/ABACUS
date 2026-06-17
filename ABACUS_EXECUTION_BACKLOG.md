# ABACUS Execution Backlog

Date: 2026-06-11

## Backlog rules

- No new orchestrators.
- No duplicate registries.
- No duplicate integration layers.
- Each item must close or validate an evidence-backed gap from lineage, runtime inventory, integration matrix, or deployment status.

## P0 — Runtime SSOT selection and integration completion

### P0-1 — Publish Runtime SSOT decision

- **Description:** Treat `DMAIC_V3/core/twelve_cluster_orchestrator.py` / `TwelveClusterOrchestrator` as the runtime governance SSOT and document `DMAIC_V3/full_pipeline_orchestrator.py` as secondary operational phase runner plus `local_mcp/agent_orchestrator_v3.0.py` as V2.3 compatibility runtime.
- **Evidence:** README canonical orchestrator section names `DMAIC_V3/core/twelve_cluster_orchestrator.py` canonical and `local_mcp/agent_orchestrator_v3.0.py` compatibility; tests import and validate `TwelveClusterOrchestrator`; active DOW workflows still invoke `full_pipeline_orchestrator.py`.
- **Owner:** Runtime governance / DMAIC_V3 maintainers.
- **Dependency:** `ABACUS_EXECUTION_BASELINE.md` accepted.
- **Acceptance Criteria:** SSOT decision appears in README or governance docs; no new orchestrator files are added; workflow owners acknowledge secondary entrypoints.

### P0-2 — Reconcile GBOGEB bridge workflow paths

- **Description:** Align `.github/workflows/gbogeb-abacus-integration-ci-cd.yml` with the located bridge implementation under `staging/` or deliberately promote the staging implementation and matching tests/config to the root paths expected by the workflow.
- **Evidence:** Workflow references `GBOGEB_ABACUS_DOW_INTEGRATION_BRIDGE.py`, `test_integration_bridge.py`, and `UNIFIED_GLOB_CONFIG.yaml`; repository evidence locates `staging/GBOGEB_ABACUS_DOW_INTEGRATION_BRIDGE.py`.
- **Owner:** GBOGEB integration owner / CI owner.
- **Dependency:** P0-1 SSOT decision; no duplicate bridge creation.
- **Acceptance Criteria:** Workflow file existence checks pass against actual repository paths; bridge import commands use the selected path; `ABACUS_DEPLOYMENT_STATUS.md` no longer marks the workflow path-stale.

### P0-3 — Normalize KEB/GBOGEB imports across runtime consumers

- **Description:** Establish a single import pattern for `KEB` and `GBOGEB` so `KnowledgeIntegrationV23` and `TwelveClusterOrchestrator` consume the same implementation paths.
- **Evidence:** `KnowledgeIntegrationV23` imports `core.keb.keb.KEB` and `core.gbogeb.gbogeb.GBOGEB`; `TwelveClusterOrchestrator` currently imports top-level `keb` and `gbogeb` after path insertion.
- **Owner:** Runtime integration owner.
- **Dependency:** P0-1 SSOT decision.
- **Acceptance Criteria:** Both runtime consumers import the same implementation modules; tests cover `TwelveClusterOrchestrator(use_keb=True, use_gbogeb=True)` or a documented fallback; no new KEB/GBOGEB implementation files are introduced.

## P1 — Recursive parity closure and registry alignment

### P1-1 — Close recursive hook retrieval parity

- **Description:** Resolve the missing V2.2 `get_recursive_hooks(enabled_only=True)` parity through a lightweight read utility or documented query path over existing artifact-level `recursive_hooks` metadata.
- **Evidence:** `PHASE_B_RECURSIVE_HOOKS_PARITY_AUDIT_V4.4.0.md` marks dedicated retrieval API as missing; `V2.2_RECURSIVE_HOOKS_VERSION_ALIGNMENT.md` documents the historical retrieval function; `DOWRecursiveHooksInjector` already writes artifact-level `recursive_hooks`.
- **Owner:** Runtime governance / DMAIC_V3 maintainers.
- **Dependency:** `tracking_v2.3/tasks/TASK_recursive_hook_parity.yaml`.
- **Acceptance Criteria:** Retrieval path is implemented or documented; it reads existing `recursive_hooks` artifacts; validation covers at least one artifact; `DOWRecursiveHooksInjector` remains the source of recursive metadata.

### P1-2 — Align runtime registry terminology

- **Description:** Document `runtime/manifests/runtime-topology.yaml` as runtime/deployment topology SSOT and distinguish it from generated/evidence registries such as `metrics/federation/runtime_registry.json` and `reports/runtime_registry_report.json`.
- **Evidence:** Runtime topology manifest declares runtime repository, governance repository, capabilities, and protected environments; metrics/report JSON files contain evidence/coverage outputs.
- **Owner:** Runtime governance owner.
- **Dependency:** P0-1 SSOT decision.
- **Acceptance Criteria:** Registry docs define topology SSOT versus evidence outputs; no duplicate runtime registry is created; references in execution docs use the same terminology.

### P1-3 — Validate phase execution workflow argument compatibility

- **Description:** Review `.github/workflows/dmaic-phase-execution.yml` because it passes `--phase` to `DMAIC_V3/full_pipeline_orchestrator.py`, while the full pipeline parser evidence lists `--iteration`, `--no-idempotency`, `--no-git`, `--quiet`, and `--debug-port` but not `--phase`.
- **Evidence:** `.github/workflows/dmaic-phase-execution.yml` executes `python DMAIC_V3/full_pipeline_orchestrator.py --phase ...`; `DMAIC_V3/full_pipeline_orchestrator.py` parser does not define `--phase`; `DMAIC_V3/dmaic_v3_engine.py` parser does define `--phase`.
- **Owner:** CI owner / DMAIC runtime owner.
- **Dependency:** P0-1 SSOT decision.
- **Acceptance Criteria:** Workflow command targets an entrypoint that supports `--phase` or command arguments are corrected; validation command is documented; no new phase runner is created.

## P2 — Dashboard generation and metrics collection

### P2-1 — Preserve deployment and runtime dashboards from existing workflows

- **Description:** Keep dashboard/report generation on existing workflows (`dashboard-health`, `reports`, `dmaic-commit-metrics`, Pages workflows) and avoid adding a new dashboard pipeline until current outputs are inventoried.
- **Evidence:** `.github/workflows/dashboard-health.yml`, `.github/workflows/reports.yml`, `.github/workflows/dmaic-commit-metrics.yml`, `.github/workflows/pages.yml`, and `.github/workflows/deploy-docs.yml` are active root workflows.
- **Owner:** Documentation/dashboard owner.
- **Dependency:** P1-2 registry terminology.
- **Acceptance Criteria:** Existing dashboard/report outputs are listed; no duplicate dashboard workflow is introduced; missing dashboard outputs are tracked as tasks rather than implemented ad hoc.

### P2-2 — Consolidate metric emission ownership

- **Description:** Define whether GBOGEB metrics, DMAIC metrics, or workflow artifacts are the authoritative metrics source for each dashboard/report use case.
- **Evidence:** `GBOGEB.collect_metric` records agent metrics; `KnowledgeIntegrationV23.collect_agent_metric` routes metrics to GBOGEB; `.github/workflows/dmaic-commit-metrics.yml` generates per-commit metrics; reports workflows upload generated reports.
- **Owner:** Metrics owner / GBOGEB owner.
- **Dependency:** P0-3 import/consumption normalization.
- **Acceptance Criteria:** Metrics sources are mapped by use case; duplicate metrics stores are not introduced; GBOGEB remains the governance metrics implementation where agent metrics are needed.

## P3 — Optional enhancements

### P3-1 — Add developer-facing runtime invocation guide

- **Description:** Add a concise guide explaining when to invoke `TwelveClusterOrchestrator`, `FullPipelineOrchestrator`, `DMAIC_V3.dmaic_v3_engine`, and `AgentOrchestratorV3`.
- **Evidence:** Current evidence shows multiple valid invocation paths across README, workflows, and handover docs; confusion risks duplicate orchestration work.
- **Owner:** Documentation owner.
- **Dependency:** P0-1 through P1-3 completed or accepted.
- **Acceptance Criteria:** Guide lists each entrypoint, status, command, owner, and non-goals; no new runtime code is added.

### P3-2 — Archive or label duplicate full-pipeline variants

- **Description:** Decide archival labels for `full_pipeline_orchestrator_clean.py`, `full_pipeline_orchestrator_corrupted.py`, and `full_pipeline_orchestrator_fixed.py` without changing the active `DMAIC_V3/full_pipeline_orchestrator.py` runtime.
- **Evidence:** Existing implementation logs and deprecation notices identify duplicate/corrupted/fixed full-pipeline copies; active workflows reference `DMAIC_V3/full_pipeline_orchestrator.py`.
- **Owner:** Repository maintenance owner.
- **Dependency:** P0-1 SSOT decision.
- **Acceptance Criteria:** Duplicate files are documented as archived/deprecated or moved through an approved cleanup PR; active workflows remain pointed at the selected operational runtime.

### P3-3 — Expand integration smoke tests after path/import consolidation

- **Description:** Add smoke tests only after P0 path/import consolidation to cover KEB/GBOGEB enabled initialization and GBOGEB bridge workflow path assumptions.
- **Evidence:** Current tests cover `TwelveClusterOrchestrator(use_keb=False, use_gbogeb=False)`; runtime code includes enabled paths for KEB/GBOGEB; GBOGEB workflow path drift is known.
- **Owner:** Test owner / runtime integration owner.
- **Dependency:** P0-2 and P0-3.
- **Acceptance Criteria:** Tests cover enabled integration paths; no duplicate test harness creates alternate runtime semantics; failures produce actionable path/import fixes.
