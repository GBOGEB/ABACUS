# Chapter 2: 12-Cluster Architecture Deep Dive

## 2.1 Architecture Overview

The 12-Cluster Architecture is the **core functioning model** of ABACUS. It organizes all 
system components into 12 functional clusters across 4 tiers:

```
┌─────────────────────────────────────────────────────────────────┐
│                    12-CLUSTER ARCHITECTURE                       │
│                                                                  │
│  ANALYSIS TIER (C1-C4)                                          │
│    C1: Define Agent      — Problem scoping, requirements         │
│    C2: Measure Agent     — Data collection, baseline metrics     │
│    C3: Analyze Agent     — Root cause, pattern detection         │
│    C4: Improve Agent     — Solution generation, optimization     │
│                                                                  │
│  DOCUMENTATION TIER (C5-C6)                                     │
│    C5: Doc Generator     — Automated documentation creation      │
│    C6: Version Tracker   — Version lineage, changelog mgmt      │
│                                                                  │
│  ORCHESTRATION TIER (C7-C8)                                     │
│    C7: Recursive Build   — Self-improvement iteration loops      │
│    C8: Orchestrator      — Central coordination hub              │
│                                                                  │
│  KNOWLEDGE TIER (C9-C12)                                        │
│    C9:  KEB              — Task scheduling, execution bridge     │
│    C10: GBOGEB           — Governance, observability metrics     │
│    C11: Temporal Scanner — Time-based tracking and history       │
│    C12: Metrics Collector— Performance and quality metrics       │
└─────────────────────────────────────────────────────────────────┘
```

## 2.2 Design Principles

1. **Functional Organization** — Clusters are functional roles, not rigid numbered units
2. **Parallel Execution** — Up to 12 workers process phases simultaneously
3. **Phase Mapping** — Each DMAIC phase maps to primary and secondary clusters
4. **Self-Improvement** — Recursive tier enables continuous improvement loops
5. **Observability** — Knowledge tier provides full system monitoring

## 2.3 DMAIC Phase ↔ Cluster Mapping

| DMAIC Phase | Primary Clusters | Secondary | Description |
|------------|-----------------|-----------|-------------|
| Phase 0: Init | C8, C9, C10 | C11, C12 | Bootstrap, orchestrator setup |
| Phase 1: Define | C1, C3 | C10, C11, C12 | Problem definition |
| Phase 2a: Measure | C1, C3, C4 | C12 | Data collection |
| Phase 2b: Deep Measure | C4, C9 | C11, C12 | KEB-distributed analysis |
| Phase 3: Analyze | C3, C4 | C7, C12 | Root cause analysis |
| Phase 4: Improve | C4, C7 | C5, C6 | Solution generation |
| Phase 5: Control | C8, C10 | C11, C12 | Quality gates |
| Phase 6: Knowledge | C5, C6, C9 | C7 | Knowledge extraction |
| Phase 7-8: Action | C7, C8 | C11 | Action & TODO tracking |
| Phase 9: Recursive | ALL | ALL | Full iteration cycle |

## 2.4 Implementation Location

The primary implementation is in `DMAIC_V3/core/twelve_cluster_orchestrator.py`:
- `TwelveClusterOrchestrator` class with 12-worker thread pool
- `ClusterConfig` class for per-cluster configuration
- KEB integration for task scheduling
- GBOGEB integration for observability

## 2.5 Cluster Lifecycle

```
IDLE → INITIALIZING → ACTIVE → PROCESSING → COMPLETED
                                    ↓
                              FAILED (retry → PROCESSING)
```

Each cluster maintains:
- Task execution count
- Failure count  
- Priority level (1-10)
- Current status
- Phase assignment
