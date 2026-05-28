# Migration Guide: v2.3 → v3.3
> *Reconstructed from code — 2026-05-16 22:34*

## Overview
v3.3 represents the DMAIC V3 engine with full 12-cluster orchestration.

## What Changes
1. **12-Cluster Orchestrator** — Parallel execution across 12 functional clusters
2. **DMAIC V3 Engine** — Complete rewrite with 10 phases
3. **Agent Framework V3** — Self-ranking, health checking, style extraction
4. **Convergence Detection** — Automated change detection and convergence analysis

## Key New Components
- `DMAIC_V3/core/twelve_cluster_orchestrator.py` — Central orchestrator
- `DMAIC_V3/phases/` — All 10 phase implementations
- `DMAIC_V3/agents/` — V3 agent framework
- `DMAIC_V3/convergence/change_detector.py` — Change detection

## Migration Steps
1. DMAIC V3 is largely standalone — imports from `DMAIC_V3/`
2. Configure via `DMAIC_V3/config.py`
3. v2.3 agents can coexist with V3 agents
4. Run `TwelveClusterOrchestrator` for parallel execution

## Breaking Changes
- Phase implementations restructured under `DMAIC_V3/phases/`
- Agent base class changed to `DMAIC_V3/agents/framework.py`
