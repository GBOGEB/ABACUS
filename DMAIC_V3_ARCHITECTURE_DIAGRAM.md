# DMAIC V3.0 - Comprehensive ASCII Architecture Diagram

```
╔═══════════════════════════════════════════════════════════════════════════════════════════════════════╗
║                                    DMAIC V3.0 SYSTEM ARCHITECTURE                                      ║
║                                  Modular • Idempotent • Observable                                     ║
╚═══════════════════════════════════════════════════════════════════════════════════════════════════════╝

┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                         ENTRY POINT                                                  │
│                                    dmaic_v3_engine.py                                                │
│                                  ┌──────────────────────┐                                            │
│                                  │  CLI Argument Parser │                                            │
│                                  │  • --iterations N    │                                            │
│                                  │  • --resume          │                                            │
│                                  │  • --config PATH     │                                            │
│                                  │  • --validate-only   │                                            │
│                                  └──────────┬───────────┘                                            │
│                                             │                                                         │
│                                             ▼                                                         │
│                                  ┌──────────────────────┐                                            │
│                                  │  Main Orchestrator   │                                            │
│                                  │  • Load Config       │                                            │
│                                  │  • Initialize State  │                                            │
│                                  │  • Run Iterations    │                                            │
│                                  └──────────┬───────────┘                                            │
└─────────────────────────────────────────────┼───────────────────────────────────────────────────────┘
                                              │
                    ┌─────────────────────────┼─────────────────────────┐
                    │                         │                         │
                    ▼                         ▼                         ▼
        ┌───────────────────┐   ┌───────────────────┐   ┌───────────────────┐
        │   CONFIG LAYER    │   │   CORE ENGINE     │   │   STATE LAYER     │
        │   config.py       │   │   Central Hub     │   │   core/state.py   │
        └───────────────────┘   └───────────────────┘   └───────────────────┘
                │                         │                         │
                │                         │                         │
                ▼                         ▼                         ▼
    ┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────────────┐
    │ DMAICConfig          │  │ Iteration Manager    │  │ StateManager         │
    │ • PathConfig         │  │ • Start Iteration    │  │ • start_iteration()  │
    │ • Phase0-6Config     │  │ • Phase Orchestration│  │ • start_phase()      │
    │ • IdempotencyConfig  │  │ • Pause/Resume       │  │ • save_checkpoint()  │
    │ • MetricsConfig      │  │ • Error Handling     │  │ • end_phase()        │
    │ • KnowledgeConfig    │  │ • Convergence Check  │  │ • can_skip_phase()   │
    │ • LoggingConfig      │  └──────────┬───────────┘  │ • get_summary()      │
    └──────────────────────┘             │              └──────────────────────┘
                                         │
                    ┌────────────────────┼────────────────────┐
                    │                    │                    │
                    ▼                    ▼                    ▼
        ┌───────────────────┐ ┌───────────────────┐ ┌───────────────────┐
        │   CORE MODULES    │ │   CORE MODULES    │ │   CORE MODULES    │
        │   core/models.py  │ │  core/metrics.py  │ │ core/knowledge.py │
        └───────────────────┘ └───────────────────┘ └───────────────────┘
                │                       │                       │
                ▼                       ▼                       ▼
    ┌──────────────────────┐ ┌──────────────────────┐ ┌──────────────────────┐
    │ Data Structures      │ │ MetricsTracker       │ │ KnowledgeManager     │
    │ • Metric             │ │ • track()            │ │ • extract()          │
    │ • PhaseMetrics       │ │ • aggregate()        │ │ • aggregate()        │
    │ • IterationResult    │ │ • export()           │ │ • persist()          │
    │ • KnowledgePack      │ │ MetricsAggregator    │ │ KnowledgeExtractor   │
    │ • ExecutionState     │ │ MetricsExporter      │ │ KnowledgeAggregator  │
    └──────────────────────┘ └──────────────────────┘ └──────────────────────┘
                                         │
                    ┌────────────────────┼────────────────────┐
                    │                    │                    │
                    ▼                    ▼                    ▼
        ┌───────────────────┐ ┌───────────────────┐ ┌───────────────────┐
        │   CORE UTILITIES  │ │   CORE UTILITIES  │ │   CORE UTILITIES  │
        │   core/utils.py   │ │   core/utils.py   │ │   core/utils.py   │
        └───────────────────┘ └───────────────────┘ └───────────────────┘
                │                       │                       │
                ▼                       ▼                       ▼
    ┌──────────────────────┐ ┌──────────────────────┐ ┌──────────────────────┐
    │ File Operations      │ │ Hash Functions       │ │ Validation Helpers   │
    │ • safe_write_json()  │ │ • compute_hash()     │ │ • validate_path()    │
    │ • safe_read_json()   │ │ • compute_file_hash()│ │ • validate_file()    │
    │ • ensure_directory() │ │ Logging Utilities    │ │ • validate_dir()     │
    │ • archive_directory()│ │ • setup_logger()     │ │ Format Utilities     │
    │ • copy_with_backup() │ │ • format_duration()  │ │ • truncate_string()  │
    └──────────────────────┘ └──────────────────────┘ └──────────────────────┘

═══════════════════════════════════════════════════════════════════════════════════════════════════════

                                    PHASE EXECUTION PIPELINE
                                    
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    ITERATION LOOP (1..N)                                             │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘
                                             │
                    ┌────────────────────────┼────────────────────────┐
                    │                        │                        │
                    ▼                        ▼                        ▼
        ┌───────────────────┐   ┌───────────────────┐   ┌───────────────────┐
        │   PHASE 0: SETUP  │   │  PHASE 1: DEFINE  │   │ PHASE 2: MEASURE  │
        │ phase0_setup.py   │   │ phase1_define.py  │   │ phase2_measure.py │
        └───────────────────┘   └───────────────────┘   └───────────────────┘
                │                        │                        │
                ▼                        ▼                        ▼
    ┌──────────────────────┐ ┌──────────────────────┐ ┌──────────────────────┐
    │ Pre-flight Checks    │ │ Scope Definition     │ │ Data Collection      │
    │ • Python version     │ │ • Objectives         │ │ • Metrics tracking   │
    │ • System reqs        │ │ • Stakeholders       │ │ • Baseline measure   │
    │ • Disk space         │ │ • Constraints        │ │ • Word frequency     │
    │ • Git availability   │ │ • Success criteria   │ │ • Document stats     │
    │ • Virtual env        │ │ • Artifacts          │ │ • Word cloud gen     │
    │ • Dependencies       │ │ • Documentation      │ │ • Validation         │
    │ • Configuration      │ │ • Validation         │ │ • Analysis           │
    │ • Workspace          │ │ • Reporting          │ │ • Reporting          │
    │ • Previous state     │ │ • Knowledge capture  │ │ • Visualization      │
    └──────────────────────┘ └──────────────────────┘ └──────────────────────┘
                                             │
                    ┌────────────────────────┼────────────────────────┐
                    │                        │                        │
                    ▼                        ▼                        ▼
        ┌───────────────────┐   ┌───────────────────┐   ┌───────────────────┐
        │ PHASE 3: ANALYZE  │   │ PHASE 4: IMPROVE  │   │ PHASE 5: CONTROL  │
        │ phase3_analyze.py │   │ phase4_improve.py │   │ phase5_control.py │
        └───────────────────┘   └───────────────────┘   └───────────────────┘
                │                        │                        │
                ▼                        ▼                        ▼
    ┌──────────────────────┐ ┌──────────────────────┐ ┌──────────────────────┐
    │ Root Cause Analysis  │ │ Solution Design      │ │ Monitoring Setup     │
    │ • Pattern detection  │ │ • Implementation     │ │ • Control mechanisms │
    │ • Correlation        │ │ • Testing            │ │ • Validation         │
    │ • Statistical tests  │ │ • Validation         │ │ • Documentation      │
    │ • Hypothesis testing │ │ • Documentation      │ │ • Handoff            │
    │ • Reporting          │ │ • Rollout            │ │ • Sustainability     │
    │ • Knowledge capture  │ │ • Knowledge capture  │ │ • Knowledge capture  │
    └──────────────────────┘ └──────────────────────┘ └──────────────────────┘
                                             │
                                             ▼
                              ┌───────────────────────────┐
                              │ PHASE 6: KNOWLEDGE DEVOUR │
                              │  phase6_knowledge.py      │
                              └───────────────────────────┘
                                             │
                                             ▼
                              ┌───────────────────────────┐
                              │ Knowledge Aggregation     │
                              │ • Cross-iteration learn   │
                              │ • Pattern synthesis       │
                              │ • Best practices extract  │
                              │ • Documentation update    │
                              │ • Archive creation        │
                              │ • Report generation       │
                              └───────────────────────────┘

═══════════════════════════════════════════════════════════════════════════════════════════════════════

                                    DATA FLOW & PERSISTENCE

┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    OUTPUT DIRECTORY STRUCTURE                                        │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

DMAIC_V3_OUTPUT/
├── state/
│   ├── execution_state.json          ← Global execution state
│   ├── iteration_1/
│   │   ├── phase0_checkpoint.json    ← Phase checkpoints (idempotency)
│   │   ├── phase1_checkpoint.json
│   │   ├── phase2_checkpoint.json
│   │   ├── phase3_checkpoint.json
│   │   ├── phase4_checkpoint.json
│   │   ├── phase5_checkpoint.json
│   │   └── phase6_checkpoint.json
│   ├── iteration_2/
│   │   └── ...
│   └── iteration_N/
│       └── ...
├── metrics/
│   ├── global_metrics.json           ← Cross-iteration metrics
│   ├── iteration_1_metrics.json      ← Per-iteration metrics
│   ├── iteration_2_metrics.json
│   └── iteration_N_metrics.json
├── knowledge/
│   ├── iteration_1/
│   │   ├── phase1_knowledge.json     ← Phase knowledge packs
│   │   ├── phase2_knowledge.json
│   │   └── ...
│   ├── iteration_2/
│   │   └── ...
│   └── aggregated_knowledge.json     ← Cross-iteration synthesis
├── artifacts/
│   ├── iteration_1/
│   │   ├── phase1/                   ← Phase-specific artifacts
│   │   ├── phase2/
│   │   └── ...
│   └── iteration_N/
│       └── ...
├── reports/
│   ├── iteration_1_report.md         ← Iteration reports
│   ├── iteration_2_report.md
│   ├── iteration_N_report.md
│   └── final_report.md               ← Comprehensive final report
└── logs/
    ├── dmaic_v3.log                  ← Main execution log
    ├── phase0.log                    ← Phase-specific logs
    ├── phase1.log
    └── ...

═══════════════════════════════════════════════════════════════════════════════════════════════════════

                                    RECURSIVE HOOKS & VERSIONING

┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    VERSION LINEAGE                                                   │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

    V1.0 (Initial)                V2.0 (Enhanced)              V3.0 (Modular)
         │                              │                            │
         ├─ Monolithic                  ├─ Improved                  ├─ Fully Modular
         ├─ Basic DMAIC                 ├─ Better Logging            ├─ Idempotent
         └─ Limited Docs                ├─ More Metrics              ├─ State Management
                                        └─ Enhanced Docs             ├─ Phase 0 Pre-checks
                                                                     ├─ Comprehensive Docs
                                                                     └─ Production-Ready

    Each version maintains:
    • Backward compatibility hooks
    • Migration scripts (v1→v2, v2→v3)
    • Cumulative documentation
    • State conversion utilities
    • Artifact preservation

═══════════════════════════════════════════════════════════════════════════════════════════════════════

                                    BOOK STRUCTURE (Pandoc)

┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    DMAIC V3.0 BOOK CHAPTERS                                          │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

book.yaml (Pandoc metadata)
│
├── Chapter 1: Introduction
│   └── DMAIC_V3_MASTER_SUMMARY.md
│
├── Chapter 2: Quick Start
│   └── DMAIC_V3_QUICK_REFERENCE.md
│
├── Chapter 3: Architecture
│   ├── DMAIC_V3_REFACTORING_PLAN.md
│   └── DMAIC_V3_ARCHITECTURE_DIAGRAM.md
│
├── Chapter 4: Implementation
│   └── DMAIC_V3_IMPLEMENTATION_SUMMARY.md
│
├── Chapter 5: Final Report
│   └── DMAIC_V3_FINAL_REPORT.md
│
├── Chapter 6: Git Integration
│   ├── DMAIC_V3_GIT_SETUP_GUIDE.md
│   ├── DMAIC_V3_GIT_GITHUB_STRATEGY.md
│   └── DMAIC_V3_GIT_INTEGRATION_SUMMARY.md
│
├── Chapter 7: Documentation Index
│   └── DMAIC_V3_DOCUMENTATION_INDEX.md
│
├── Appendix A: Version History
│   ├── V1_SUMMARY.md (recursive hook)
│   └── V2_SUMMARY.md (recursive hook)
│
└── Appendix B: API Reference
    ├── core/models.py
    ├── core/state.py
    ├── core/metrics.py
    ├── core/knowledge.py
    └── core/utils.py

═══════════════════════════════════════════════════════════════════════════════════════════════════════

                                    EXECUTION FLOW (ASCII)

Entry → CLI Parse → Load Config → Initialize State → Phase 0 (Setup)
                                                            │
                                                            ▼
                                                    ┌───────────────┐
                                                    │ Iteration 1   │
                                                    └───────┬───────┘
                                                            │
        ┌───────────────────────────────────────────────────┼───────────────────────────────────────┐
        │                                                   │                                       │
        ▼                                                   ▼                                       ▼
    Phase 1                                            Phase 2                                 Phase 3
    (Define)                                          (Measure)                               (Analyze)
        │                                                   │                                       │
        ├─ Check idempotency                                ├─ Check idempotency                   ├─ Check idempotency
        ├─ Load checkpoint (if exists)                      ├─ Load checkpoint (if exists)         ├─ Load checkpoint (if exists)
        ├─ Execute phase logic                              ├─ Execute phase logic                 ├─ Execute phase logic
        ├─ Save checkpoint                                  ├─ Save checkpoint                     ├─ Save checkpoint
        ├─ Track metrics                                    ├─ Track metrics                       ├─ Track metrics
        ├─ Capture knowledge                                ├─ Capture knowledge                   ├─ Capture knowledge
        └─ Generate artifacts                               └─ Generate artifacts                  └─ Generate artifacts
                                                            │
        ┌───────────────────────────────────────────────────┼───────────────────────────────────────┐
        │                                                   │                                       │
        ▼                                                   ▼                                       ▼
    Phase 4                                            Phase 5                                 Phase 6
    (Improve)                                         (Control)                          (Knowledge Devour)
        │                                                   │                                       │
        ├─ Check idempotency                                ├─ Check idempotency                   ├─ Aggregate knowledge
        ├─ Load checkpoint (if exists)                      ├─ Load checkpoint (if exists)         ├─ Synthesize patterns
        ├─ Execute phase logic                              ├─ Execute phase logic                 ├─ Generate reports
        ├─ Save checkpoint                                  ├─ Save checkpoint                     ├─ Archive artifacts
        ├─ Track metrics                                    ├─ Track metrics                       └─ Update docs
        ├─ Capture knowledge                                ├─ Capture knowledge
        └─ Generate artifacts                               └─ Generate artifacts
                                                            │
                                                            ▼
                                                    ┌───────────────┐
                                                    │ Iteration 2   │
                                                    └───────┬───────┘
                                                            │
                                                           ...
                                                            │
                                                            ▼
                                                    ┌───────────────┐
                                                    │ Iteration N   │
                                                    └───────┬───────┘
                                                            │
                                                            ▼
                                                    Convergence Check
                                                            │
                                                            ▼
                                                    Final Report → Exit

═══════════════════════════════════════════════════════════════════════════════════════════════════════
```

## Key Architecture Principles

### 1. **Central Engine (dmaic_v3_engine.py)**
- Orchestrates all phases
- Manages iteration loops
- Handles pause/resume
- Coordinates state and config

### 2. **Core Nodes (Radial Branches)**
- **config.py** → Configuration management
- **core/state.py** → State persistence & idempotency
- **core/models.py** → Data structures
- **core/metrics.py** → Metrics tracking
- **core/knowledge.py** → Knowledge management
- **core/utils.py** → Utility functions

### 3. **Phase Modules (Execution Branches)**
- **phase0_setup.py** → Pre-flight checks
- **phase1_define.py** → Scope definition
- **phase2_measure.py** → Data collection & analysis
- **phase3_analyze.py** → Root cause analysis
- **phase4_improve.py** → Solution implementation
- **phase5_control.py** → Monitoring & sustainability
- **phase6_knowledge.py** → Knowledge aggregation

### 4. **Idempotency Mechanism**
- State checkpoints at each phase
- Hash-based verification
- Resume from any point
- Deterministic execution

### 5. **Recursive Hooks**
- Version lineage (V1→V2→V3)
- Cumulative documentation
- Migration scripts
- Backward compatibility

### 6. **Book Structure (Pandoc)**
- Markdown chapters
- Hierarchical organization
- Cross-references
- Version history appendices
