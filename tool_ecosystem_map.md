# Tool Ecosystem Map — DOW, KEB, GBOGEB & Interconnections

**Generated:** 2026-05-16 | **References:** DOW: 1327 | KEB: 298 | GBOGEB: 781 | CRYO: 30

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        DOW — GOVERNANCE LAYER                           │
│                    (Design of Work — OMNIPOTENT)                         │
│                                                                          │
│  Oversight: Design | Code | HUMAN | MCP | GITHUB | CRYO Knowledge      │
│                                                                          │
│  Components:                                                             │
│  ├── TaskRunner      → Agent lifecycle management                       │
│  ├── StateStore      → Persistent state across phases                   │
│  ├── VersionControl  → Git integration, lineage tracking                │
│  ├── MarkdownTangler → Documentation generation from code               │
│  ├── ADRValidator    → Architecture Decision Record validation          │
│  ├── RTMValidator    → Requirements Traceability validation             │
│  ├── Knowledge Devour Engine → Phase 6 knowledge extraction             │
│  └── Recall System   → 4 mechanisms (Keyword/Semantic/Temporal/Hier)    │
│                                                                          │
│  DOW Agents (in DMAIC_V3/local_mcp/agents/):                            │
│  ├── dow_knowledge_extractor.py    → Extract patterns, insights         │
│  ├── dow_recursive_hooks_injector.py → Inject dependency lineage        │
│  ├── dow_metadata_injector.py      → Enrich outputs with metadata       │
│  └── dow_convergence_calculator.py → Calculate improvement convergence  │
└────────────┬──────────────────────────────┬──────────────────────────────┘
             │                              │
             ▼                              ▼
┌────────────────────────┐    ┌──────────────────────────────┐
│   KEB — EXECUTION      │    │   GBOGEB — OBSERVABILITY     │
│  (Knowledge Execution  │    │  (Goal-Based Orchestration   │
│   Bridge)              │    │   Graph Execution Bridge)     │
│                        │    │                               │
│  Features:             │    │  Features:                    │
│  ├── Priority Queue    │    │  ├── Metric Collection        │
│  ├── Multi-threaded    │    │  ├── Compliance Checking      │
│  │   (4-12 workers)    │    │  ├── Quality Gates            │
│  ├── Resource Monitor  │    │  │   (70/100 threshold)       │
│  │   (14GB system)     │    │  ├── Victory Criteria         │
│  ├── Task Success/Fail │    │  ├── Audit Trail              │
│  └── Memory Limits     │    │  └── Workspace Management     │
│                        │    │                               │
│  Key Class: KEB        │    │  Key Class: GBOGEB            │
│  Files:                │    │  Files:                        │
│  ├── knowledge_        │    │  ├── GBOGEB_Repository/       │
│  │   packages/keb.py   │    │  │   gbogeb.py                │
│  └── knowledge_        │    │  └── staging/GBOGEB_ABACUS_   │
│      integration_      │    │      DOW_INTEGRATION_BRIDGE.py│
│      v2.3.py           │    │                               │
└────────────┬───────────┘    └──────────────┬────────────────┘
             │                               │
             └───────────┬───────────────────┘
                         ▼
┌──────────────────────────────────────────────────────────────┐
│              12-CLUSTER ORCHESTRATOR                          │
│         (TwelveClusterOrchestrator + OrchestratorV3)         │
│                                                               │
│  C1-C4: DMAIC Analysis  │  C5-C6: Documentation              │
│  C7-C8: Recursive/Orch  │  C9-C12: Knowledge/Monitoring      │
└──────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│              CRYO_LINAC FRAMEWORK                             │
│         (Cryogenic Analysis Domain Logic)                     │
│                                                               │
│  ├── Phase 1A-1E execution with recursive improvement        │
│  ├── Self-ranking (0.0-1.0) and group-ranking system         │
│  ├── 10 Phase 1B subtasks (P1B-001 is CRITICAL blocker)      │
│  ├── QPLANT cryoplant requirements (16 requirements)         │
│  └── SBS: QSYS → QPLANT/QINFRA/QCELL/QDIST                 │
└──────────────────────────────────────────────────────────────┘
```

---

## DOW as GOVERNANCE Layer (NOT Legacy)

### What DOW Controls
DOW is the **omnipotent governance layer** with oversight across:

| Domain | DOW Role | Implementation |
|--------|----------|----------------|
| **Design** | Architecture decisions, ADR validation | `ADRValidator` in Phase 6 |
| **Code** | Quality gates, complexity limits | `min_coverage=0.80, max_complexity=10` |
| **HUMAN** | User-facing documentation, handover | `MarkdownTangler`, handover generators |
| **MCP** | IDE integration (VS Code, Cursor) | `MCP_INTEGRATION_BOOK.md`, `local_mcp/` |
| **GITHUB** | Git integration, CI/CD workflows | `integrations/git_manager.py`, 32 workflows |
| **CRYO Knowledge** | Domain expertise via KEB | `KnowledgeIntegrationV23`, QPLANT RTM |

### DOW Agent-Interaction Matrix
From `ABACUS-UNIFIED/AGENT_DOW_INTERACTIONS.md`:

| Agent | DOW Interactions | Primary DOW Components |
|-------|-----------------|----------------------|
| AnalyzerAgent | 50+ | TaskRunner, StateStore |
| BuilderAgent | 40+ | VersionControl, TaskRunner |
| ValidatorAgent | 30+ | ADRValidator, RTMValidator |
| KnowledgeAgent | 25+ | Knowledge Devour, Recall |
| IntegrationAgent | 15+ | Git Manager, StateStore |
| ReportingAgent | 10+ | MarkdownTangler |
| **Total** | **170+** | All components |

### Key DOW Files
| File | Purpose |
|------|---------|
| `ENGINE_DOW_handover_min.md` | Lean bootstrap specification |
| `ABACUS-v031/dow_engine_config.yaml` | Pipeline configuration |
| `DMAIC_V3/DOW_DMAIC_12CLUSTER_INTEGRATION_MASTER.md` | Integration master plan |
| `DMAIC_V3/dow_integration_executor.py` | Phase 6 executor |
| `DMAIC_V3/local_mcp/agents/dow_*.py` | 4 DOW agents |
| `staging/GBOGEB_ABACUS_DOW_INTEGRATION_BRIDGE.py` | Integration bridge |

---

## KEB — Knowledge Execution Bridge

### Architecture
```python
class KEB:
    """Kernel Execution Backbone — core execution engine for all agents"""
    def __init__(self, max_workers=4, max_memory_mb=4096):
        self.task_queue = PriorityQueue()  # Priority-based scheduling
        self.workers = ThreadPool(max_workers)  # Multi-threaded execution
        self.resource_monitor = ResourceMonitor()  # Memory/CPU tracking
```

### KEB Capabilities
- **Task Scheduling:** Priority queue with configurable workers (4-12)
- **Resource Monitoring:** Memory limits (14GB system detected), CPU tracking
- **Error Handling:** Task success/failure tracking with retry mechanisms
- **Integration:** Distributes work across 12 clusters via OrchestratorV3

### Known Issues
- ⚠️ Timeout issues at scale (10+ JSON files per phase)
- ⚠️ Full versions exist in workspace but need merging into `core/` directory
- ⚠️ Integration with Phase 2 (Measure) still pending

---

## GBOGEB — Goal-Based Orchestration Graph Execution Bridge

### Architecture
```python
class GBOGEB:
    """Governance, Business, Observability, Governance, Execution, Backbone"""
    def __init__(self, workspace: str):
        self.metrics = MetricsCollector()
        self.compliance = ComplianceChecker()
        self.audit_trail = AuditTrailGenerator()
        self.victory_criteria = VictoryCriteriaTracker()
```

### GBOGEB Capabilities
- **Metric Collection:** Gathers performance data from all phases
- **Compliance Checking:** Validates against quality gates (70/100 threshold)
- **Victory Criteria:** Tracks goal completion across DMAIC phases
- **Audit Trail:** Full execution history for reproducibility

### Integration Bridge
`staging/GBOGEB_ABACUS_DOW_INTEGRATION_BRIDGE.py` provides:
```python
class GBOGEBAbacusDOWBridge:
    """Integration modes: DOW_ONLY, DMAIC_ONLY, UNIFIED, PARALLEL, SEQUENTIAL"""
```

---

## CRYO_LINAC Framework

### Purpose
Domain-specific framework for cryogenic engineering analysis at SCK CEN.

### Key Components
| Component | Description |
|-----------|-------------|
| Phase 1A-1E | Recursive execution with quality improvement loops |
| Self-Ranking | 0.0-1.0 scale for agent self-assessment |
| Group-Ranking | Cluster-based aggregation of rankings |
| QPLANT RTM | 16 cryoplant requirements with SBS hierarchy |
| Target | 0.95 quality threshold |

### Current Status
- Phase 1B: 75% complete (P1B-001 Recursive Build Quality is CRITICAL blocker)
- Self-ranking system: Defined, partially implemented
- QPLANT requirements: 16/16 captured in RTM

---

## Tool Interconnection Summary

```
DOW (Governance) ──controls──→ All Components
    │
    ├──feeds──→ KEB (Execution) ──distributes──→ 12 Clusters
    │                                              │
    ├──feeds──→ GBOGEB (Observability) ←──reports──┘
    │               │
    │               └──enforces──→ Quality Gates
    │
    ├──generates──→ Documentation (Phase 6 Devour)
    │
    └──integrates──→ MCP (IDE Connectivity, optional)
                        │
                        └──→ VS Code, Cursor
```

### Idempotency Pattern (Critical)
Every tool output includes:
```json
{
  "input_hash": "computed_before_enrichment",
  "output_hash": "computed_after_enrichment",
  "consumed_from": ["phase_N_output.json"],
  "feeds_into": ["phase_N+1_input.json"],
  "iteration_lineage": [1, 2, 3],
  "version_history": ["v0.31", "v0.32", "v3.3"]
}
```

### Post-Execution Documentation Principle
> Books and documentation are generated AFTER code execution when the system is bug-free and CD-ready — NOT during development. This is a core DOW governance principle.
