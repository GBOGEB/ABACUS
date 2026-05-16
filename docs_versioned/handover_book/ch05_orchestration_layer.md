# Chapter 5: Clusters 7-8 — Orchestration Layer

## 5.1 Overview
The Orchestration Layer provides recursive self-improvement and central coordination.

## 5.2 Cluster 7 (C7): Recursive Build — Validation

**Purpose:** Self-improvement iteration, convergence detection

**Implementations:**
- `local_mcp/agents/recursive_framework_v2.3_OPTIMIZED.py` — Recursive agent
- `DMAIC_V3/convergence/change_detector.py` — Change detection (FIXED)
- `scripts/check_convergence.py` — Convergence checking

**Convergence Detection:**
```python
from DMAIC_V3.convergence.change_detector import ChangeDetector
detector = ChangeDetector(repo_path='.')
changes = detector.detect_changes()
if not detector.has_changes():
    print("Converged!")  # No more changes needed
```

**Capabilities:**
- File change tracking via hashing
- Convergence analysis
- Iteration management
- Feedback loop: Phase 7 → Phase 1

## 5.3 Cluster 8 (C8): TwelveClusterOrchestrator — Central Hub

**Purpose:** Coordination of all 12 clusters, pipeline execution

**Implementation:** `DMAIC_V3/core/twelve_cluster_orchestrator.py`

**Key Classes:**
- `TwelveClusterOrchestrator` — Main orchestrator with ThreadPoolExecutor
- `ClusterConfig` — Per-cluster configuration
- `OrchestratorV3` — V3 orchestrator variant

**Orchestrator Hierarchy (4 levels):**
1. `TwelveClusterOrchestrator` — Top-level parallel coordinator
2. `full_pipeline_orchestrator.py` — Sequential pipeline runner
3. `agent_orchestrator_v3.0.py` — Agent-level coordination
4. Phase-specific orchestration within each phase module

**Pipeline Orchestrator Variants:**
| Variant | Path | Status |
|---------|------|--------|
| Primary | `DMAIC_V3/full_pipeline_orchestrator.py` | 🟢 Canonical |
| Fixed | `DMAIC_V3/full_pipeline_orchestrator_fixed.py` | 🟢 Clean |
| Corrupted | `DMAIC_V3/full_pipeline_orchestrator_corrupted.py` | 🔴 Merge conflict |
| v032 | `ABACUS-v032/execute_full_dmaic_phases_0_to_9_v033.py` | 🟢 v032 variant |

## 5.4 Execution Modes
- **Parallel** — All 12 clusters via ThreadPoolExecutor (default)
- **Sequential** — Phase-by-phase execution
- **Hybrid** — Parallel within phases, sequential across phases
