# CANONICAL REPOSITORY STRUCTURE & PIPELINE INTEGRATION

**Date:** 2025-01-15
**Version:** 1.0
**Purpose:** Define canonical repository structure, show local workspace organization, and map pipeline integration points

---

## 📋 TABLE OF CONTENTS

1. [Executive Summary](#executive-summary)
2. [Local Workspace vs Repository](#local-workspace-vs-repository)
3. [Canonical Repository Structure](#canonical-repository-structure)
4. [Pipeline Integration Map](#pipeline-integration-map)
5. [File Usage in Pipeline](#file-usage-in-pipeline)
6. [DOW Integration Points](#dow-integration-points)
7. [Action Plan Implementation](#action-plan-implementation)

---

## 🎯 EXECUTIVE SUMMARY

### Current State
- **Local Workspace:** Messy, with duplicates, test folders, and archived outputs
- **Repository (Canonical):** Clean, production-ready structure
- **Gap:** 148 MB of duplicates, missing DOW integration, no recursive hooks

### Target State
- **Repository:** Single source of truth with canonical structure
- **Local Workspace:** Development/testing area that syncs to repository
- **Pipeline:** Uses repository files exclusively for production runs

---

## 🗂️ LOCAL WORKSPACE VS REPOSITORY

### ASCII Diagram: Current State

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         LOCAL WORKSPACE (MESSY)                         │
│                    c:\Users\gbonthuy\OneDrive\Master_Input              │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    │                               │
        ┌───────────▼──────────┐      ┌────────────▼─────────────┐
        │   PRODUCTION FILES   │      │    DEVELOPMENT/TEST      │
        │   (CANONICAL)        │      │    (TO BE CLEANED)       │
        └───────────┬──────────┘      └────────────┬─────────────┘
                    │                               │
    ┌───────────────┼───────────────┐              │
    │               │               │              │
┌───▼────┐   ┌─────▼──────┐  ┌────▼─────┐  ┌─────▼──────────┐
│DMAIC_V3│   │DMAIC_      │  │DMAIC_    │  │DMAIC_TEST_     │
│        │   │CANONICAL_  │  │PRODUCTION│  │OUTPUT          │
│        │   │OUTPUT      │  │_FULL     │  │                │
└────────┘   └────────────┘  └──────────┘  └────────────────┘
   │              │               │              │
   │              │               │              │
   │         ┌────▼────┐     ┌────▼────┐    ┌────▼────┐
   │         │phase1   │     │phase1   │    │phase1   │
   │         │phase2   │     │phase2   │    │phase2   │
   │         │phase3   │     │phase3   │    │phase3   │
   │         │...      │     │...      │    │...      │
   │         └─────────┘     └─────────┘    └─────────┘
   │              │               │              │
   │              │               │              │
   │         CANONICAL       DUPLICATE       DUPLICATE
   │         (KEEP)          (DELETE)        (DELETE)
   │
   │
┌──▼──────────────────────────────────────────────────────────────────┐
│                    DMAIC_V3 CORE STRUCTURE                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │
│  │   phases/    │  │   core/      │  │   local_mcp/ │             │
│  │              │  │              │  │              │             │
│  │ phase1_      │  │ state.py     │  │ agents/      │             │
│  │ define.py    │  │ planning.py  │  │ recursive_   │             │
│  │              │  │              │  │ self_ranking │             │
│  │ phase2_      │  │ idempotency  │  │ _v2.3.py     │             │
│  │ measure.py   │  │ _wrapper.py  │  │              │             │
│  │              │  │              │  │              │             │
│  │ ...          │  │ ...          │  │ ...          │             │
│  └──────────────┘  └──────────────┘  └──────────────┘             │
│                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │
│  │convergence/  │  │ generators/  │  │ utils/       │             │
│  │              │  │              │  │              │             │
│  │background_   │  │phase1_       │  │file_utils.py │             │
│  │change_       │  │generator.py  │  │json_utils.py │             │
│  │detector.py   │  │              │  │              │             │
│  │              │  │phase2_       │  │              │             │
│  │              │  │generator.py  │  │              │             │
│  │              │  │              │  │              │             │
│  │              │  │...           │  │...           │             │
│  └──────────────┘  └──────────────┘  └──────────────┘             │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────┐      │
│  │  full_pipeline_orchestrator.py (MAIN ENTRY POINT)        │      │
│  │  config.py (CONFIGURATION)                               │      │
│  │  planning_history.json (TRACKING)                        │      │
│  │  bug_tracking_log.json (TRACKING)                        │      │
│  │  background_snapshot.json (TRACKING)                     │      │
│  └──────────────────────────────────────────────────────────┘      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 📦 CANONICAL REPOSITORY STRUCTURE

### ASCII Diagram: Target Repository Structure

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    CANONICAL REPOSITORY STRUCTURE                       │
│                         (SINGLE SOURCE OF TRUTH)                        │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    │                               │
        ┌───────────▼──────────┐      ┌────────────▼─────────────┐
        │   REPOSITORY ROOT    │      │    GITHUB WORKFLOWS      │
        │   (Master_Input)     │      │    (.github/workflows)   │
        └───────────┬──────────┘      └────────────┬─────────────┘
                    │                               │
    ┌───────────────┼───────────────┐              │
    │               │               │              │
┌───▼────────┐ ┌───▼────────┐ ┌───▼────────┐ ┌───▼────────────┐
│ DMAIC_V3/  │ │ DMAIC_     │ │ docs/      │ │ dmaic-v3-      │
│            │ │ CANONICAL_ │ │            │ │ integrated.yml │
│ (SOURCE)   │ │ OUTPUT/    │ │ (DOCS)     │ │                │
│            │ │ (OUTPUTS)  │ │            │ │ (CI/CD)        │
└────┬───────┘ └────┬───────┘ └────┬───────┘ └────────────────┘
     │              │              │
     │              │              │
┌────▼──────────────▼──────────────▼────────────────────────────────────┐
│                         DMAIC_V3/ STRUCTURE                            │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │  ROOT FILES (Configuration & Orchestration)                     │  │
│  │  ─────────────────────────────────────────────────────────────  │  │
│  │  • full_pipeline_orchestrator.py  ← MAIN ENTRY POINT           │  │
│  │  • config.py                      ← CONFIGURATION               │  │
│  │  • planning_history.json          ← PLANNING TRACKING           │  │
│  │  • bug_tracking_log.json          ← BUG TRACKING                │  │
│  │  • background_snapshot.json       ← CONVERGENCE STATE           │  │
│  │  • README.md                      ← DOCUMENTATION               │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │  phases/ (DMAIC Phase Implementations)                          │  │
│  │  ─────────────────────────────────────────────────────────────  │  │
│  │  • phase0_init.py           ← Phase 0: Initialization           │  │
│  │  • phase1_define.py         ← Phase 1: Define                   │  │
│  │  • phase2_measure.py        ← Phase 2: Measure                  │  │
│  │  • phase3_analyze.py        ← Phase 3: Analyze                  │  │
│  │  • phase4_improve.py        ← Phase 4: Improve                  │  │
│  │  • phase5_control.py        ← Phase 5: Control                  │  │
│  │  • phase6_knowledge.py      ← Phase 6: Knowledge (DOW)          │  │
│  │  • phase7_action_tracking.py ← Phase 7: Action Tracking         │  │
│  │  • phase8_todo_management.py ← Phase 8: TODO Management         │  │
│  │  • phase9_documentation_generation.py ← Phase 9: Docs           │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │  core/ (Core Infrastructure)                                    │  │
│  │  ─────────────────────────────────────────────────────────────  │  │
│  │  • state.py                 ← State Management                  │  │
│  │  • planning_matrix_tracker.py ← Planning Matrix                 │  │
│  │  • idempotency_wrapper.py   ← Idempotency                       │  │
│  │  • phase_base.py            ← Base Phase Class                  │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │  convergence/ (Convergence & Change Detection)                  │  │
│  │  ─────────────────────────────────────────────────────────────  │  │
│  │  • background_change_detector.py ← Change Detection             │  │
│  │  • convergence_tracker.py   ← Convergence Tracking              │  │
│  │  • metrics_calculator.py    ← Metrics Calculation               │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │  generators/ (Phase Output Generators)                          │  │
│  │  ─────────────────────────────────────────────────────────────  │  │
│  │  • phase1_generator.py      ← Phase 1 Output Generator          │  │
│  │  • phase2_generator.py      ← Phase 2 Output Generator          │  │
│  │  • phase3_generator.py      ← Phase 3 Output Generator          │  │
│  │  • phase4_generator.py      ← Phase 4 Output Generator          │  │
│  │  • phase5_generator.py      ← Phase 5 Output Generator          │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │  local_mcp/ (MCP Agents & Tools)                                │  │
│  │  ─────────────────────────────────────────────────────────────  │  │
│  │  • agents/                                                       │  │
│  │    ├── recursive_self_ranking_v2.3_OPTIMIZED.py ← RANKING       │  │
│  │    ├── knowledge_extractor.py ← KNOWLEDGE EXTRACTION            │  │
│  │    └── convergence_analyzer.py ← CONVERGENCE ANALYSIS           │  │
│  │  • tools/                                                        │  │
│  │    ├── file_analyzer.py     ← FILE ANALYSIS                     │  │
│  │    └── metadata_injector.py ← METADATA INJECTION                │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │  utils/ (Utility Functions)                                     │  │
│  │  ─────────────────────────────────────────────────────────────  │  │
│  │  • file_utils.py            ← File Operations                   │  │
│  │  • json_utils.py            ← JSON Operations                   │  │
│  │  • logging_utils.py         ← Logging                           │  │
│  │  • validation_utils.py      ← Validation                        │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │  tests/ (Unit & Integration Tests)                              │  │
│  │  ─────────────────────────────────────────────────────────────  │  │
│  │  • test_phases.py           ← Phase Tests                       │  │
│  │  • test_core.py             ← Core Tests                        │  │
│  │  • test_convergence.py      ← Convergence Tests                 │  │
│  │  • test_integration.py      ← Integration Tests                 │  │
│  └─────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                    DMAIC_CANONICAL_OUTPUT/ STRUCTURE                    │
│                         (PRODUCTION OUTPUTS)                            │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │  PHASE OUTPUTS (Canonical Production Outputs)                   │  │
│  │  ─────────────────────────────────────────────────────────────  │  │
│  │  • phase1_define.json       ← Phase 1 Output (11.5 MB)          │  │
│  │  • phase2_measure.json      ← Phase 2 Output (2.2 MB)           │  │
│  │  • phase2_metrics.json      ← Phase 2 Metrics (2.2 MB)          │  │
│  │  • phase3_analyze.json      ← Phase 3 Output (1.8 MB)           │  │
│  │  • phase4_improve.json      ← Phase 4 Output                    │  │
│  │  • phase5_control.json      ← Phase 5 Output                    │  │
│  │  • phase6_knowledge.json    ← Phase 6 Output (DOW)              │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │  ITERATION OUTPUTS (Iteration-Specific Outputs)                 │  │
│  │  ─────────────────────────────────────────────────────────────  │  │
│  │  • iteration_1/                                                  │  │
│  │    ├── phase1_define.json                                        │  │
│  │    ├── phase2_measure.json                                       │  │
│  │    └── ...                                                       │  │
│  │  • iteration_2/                                                  │  │
│  │    ├── phase1_define.json                                        │  │
│  │    ├── phase2_measure.json                                       │  │
│  │    └── ...                                                       │  │
│  │  • iteration_N/                                                  │  │
│  │    └── ...                                                       │  │
│  └─────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                         .github/workflows/                              │
│                         (CI/CD WORKFLOWS)                               │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │  dmaic-v3-integrated.yml (Main CI/CD Pipeline)                  │  │
│  │  ─────────────────────────────────────────────────────────────  │  │
│  │  Triggers:                                                       │  │
│  │    • push to main/develop                                        │  │
│  │    • pull_request                                                │  │
│  │    • manual workflow_dispatch                                    │  │
│  │                                                                   │  │
│  │  Jobs:                                                           │  │
│  │    1. Setup & Validation                                         │  │
│  │    2. Run DMAIC Pipeline                                         │  │
│  │    3. Generate Reports                                           │  │
│  │    4. Archive Artifacts                                          │  │
│  │    5. Deploy to Production                                       │  │
│  └─────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 🔄 PIPELINE INTEGRATION MAP

### ASCII Diagram: Pipeline Execution Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    DMAIC V3 PIPELINE EXECUTION FLOW                     │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────▼───────────────┐
                    │  ENTRY POINT                  │
                    │  full_pipeline_orchestrator.py│
                    └───────────────┬───────────────┘
                                    │
                    ┌───────────────▼───────────────┐
                    │  CONFIGURATION                │
                    │  config.py                    │
                    │  • Paths                      │
                    │  • Settings                   │
                    │  • Feature Flags              │
                    └───────────────┬───────────────┘
                                    │
                    ┌───────────────▼───────────────┐
                    │  STATE MANAGEMENT             │
                    │  core/state.py                │
                    │  • Load State                 │
                    │  • Track Progress             │
                    │  • Save State                 │
                    └───────────────┬───────────────┘
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        │                           │                           │
┌───────▼────────┐      ┌──────────▼──────────┐      ┌────────▼────────┐
│ PHASE 0        │      │ PLANNING MATRIX     │      │ BACKGROUND      │
│ Initialization │      │ planning_matrix_    │      │ CHANGE DETECTOR │
│ phase0_init.py │      │ tracker.py          │      │ background_     │
│                │      │                     │      │ change_         │
│ • 12 Agents    │      │ • Track Plans       │      │ detector.py     │
│ • Setup        │      │ • Monitor Progress  │      │                 │
│ • Validation   │      │ • Generate Reports  │      │ • Detect Changes│
└───────┬────────┘      └──────────┬──────────┘      └────────┬────────┘
        │                          │                           │
        └──────────────────────────┼───────────────────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │  DMAIC PHASES (1-5)         │
                    └──────────────┬──────────────┘
                                   │
        ┌──────────────────────────┼──────────────────────────┐
        │                          │                          │
┌───────▼────────┐      ┌──────────▼──────────┐      ┌──────▼──────────┐
│ PHASE 1        │      │ PHASE 2             │      │ PHASE 3         │
│ Define         │      │ Measure             │      │ Analyze         │
│ phase1_        │      │ phase2_             │      │ phase3_         │
│ define.py      │      │ measure.py          │      │ analyze.py      │
│                │      │                     │      │                 │
│ • Problem Def  │      │ • Metrics           │      │ • Root Cause    │
│ • Scope        │      │ • Baselines         │      │ • Analysis      │
│ • Goals        │      │ • Data Collection   │      │ • Insights      │
└───────┬────────┘      └──────────┬──────────┘      └────────┬────────┘
        │                          │                          │
        │                          │                          │
        │              ┌───────────▼───────────┐              │
        │              │ PHASE 2 GENERATOR     │              │
        │              │ generators/           │              │
        │              │ phase2_generator.py   │              │
        │              │                       │              │
        │              │ • Generate Metrics    │              │
        │              │ • Create Reports      │              │
        │              │ • Save Outputs        │              │
        │              └───────────┬───────────┘              │
        │                          │                          │
        └──────────────────────────┼──────────────────────────┘
                                   │
        ┌──────────────────────────┼──────────────────────────┐
        │                          │                          │
┌───────▼────────┐      ┌──────────▼──────────┐      ┌──────▼──────────┐
│ PHASE 4        │      │ PHASE 5             │      │ PHASE 6         │
│ Improve        │      │ Control             │      │ Knowledge       │
│ phase4_        │      │ phase5_             │      │ phase6_         │
│ improve.py     │      │ control.py          │      │ knowledge.py    │
│                │      │                     │      │                 │
│ • Solutions    │      │ • Monitoring        │      │ • DOW Learning  │
│ • Implement    │      │ • Sustain           │      │ • Knowledge     │
│ • Validate     │      │ • Iterate           │      │ • Extraction    │
└───────┬────────┘      └──────────┬──────────┘      └────────┬────────┘
        │                          │                          │
        └──────────────────────────┼──────────────────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │  RECURSIVE SELF-RANKING     │
                    │  local_mcp/agents/          │
                    │  recursive_self_ranking_    │
                    │  v2.3_OPTIMIZED.py          │
                    │                             │
                    │  • Rank Outputs             │
                    │  • Quality Assessment       │
                    │  • Improvement Suggestions  │
                    └──────────────┬──────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │  OUTPUT GENERATION          │
                    │  DMAIC_CANONICAL_OUTPUT/    │
                    │                             │
                    │  • phase1_define.json       │
                    │  • phase2_measure.json      │
                    │  • phase3_analyze.json      │
                    │  • phase4_improve.json      │
                    │  • phase5_control.json      │
                    │  • phase6_knowledge.json    │
                    └──────────────┬──────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │  TRACKING & LOGGING         │
                    │                             │
                    │  • planning_history.json    │
                    │  • bug_tracking_log.json    │
                    │  • background_snapshot.json │
                    └──────────────┬──────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │  GIT COMMIT                 │
                    │  (if enabled)               │
                    │                             │
                    │  • Commit Phase Outputs     │
                    │  • Tag Iteration            │
                    │  • Push to Remote           │
                    └─────────────────────────────┘
```

---

## 📂 FILE USAGE IN PIPELINE

### Table: File-to-Pipeline Mapping

| File Path | Used By | Purpose | Phase | Critical |
|-----------|---------|---------|-------|----------|
| **DMAIC_V3/full_pipeline_orchestrator.py** | Main Entry | Orchestrates entire pipeline | All | ✅ YES |
| **DMAIC_V3/config.py** | All Phases | Configuration management | All | ✅ YES |
| **DMAIC_V3/core/state.py** | All Phases | State management | All | ✅ YES |
| **DMAIC_V3/core/planning_matrix_tracker.py** | Orchestrator | Planning tracking | All | ✅ YES |
| **DMAIC_V3/core/idempotency_wrapper.py** | All Phases | Idempotency | All | ✅ YES |
| **DMAIC_V3/phases/phase0_init.py** | Orchestrator | Initialization | 0 | ✅ YES |
| **DMAIC_V3/phases/phase1_define.py** | Orchestrator | Define phase | 1 | ✅ YES |
| **DMAIC_V3/phases/phase2_measure.py** | Orchestrator | Measure phase | 2 | ✅ YES |
| **DMAIC_V3/phases/phase3_analyze.py** | Orchestrator | Analyze phase | 3 | ✅ YES |
| **DMAIC_V3/phases/phase4_improve.py** | Orchestrator | Improve phase | 4 | ✅ YES |
| **DMAIC_V3/phases/phase5_control.py** | Orchestrator | Control phase | 5 | ✅ YES |
| **DMAIC_V3/phases/phase6_knowledge.py** | Orchestrator | Knowledge phase | 6 | ✅ YES |
| **DMAIC_V3/convergence/background_change_detector.py** | Orchestrator | Change detection | All | ✅ YES |
| **DMAIC_V3/generators/phase1_generator.py** | Phase 1 | Generate Phase 1 output | 1 | ✅ YES |
| **DMAIC_V3/generators/phase2_generator.py** | Phase 2 | Generate Phase 2 output | 2 | ✅ YES |
| **DMAIC_V3/generators/phase3_generator.py** | Phase 3 | Generate Phase 3 output | 3 | ✅ YES |
| **DMAIC_V3/generators/phase4_generator.py** | Phase 4 | Generate Phase 4 output | 4 | ✅ YES |
| **DMAIC_V3/generators/phase5_generator.py** | Phase 5 | Generate Phase 5 output | 5 | ✅ YES |
| **DMAIC_V3/local_mcp/agents/recursive_self_ranking_v2.3_OPTIMIZED.py** | Phase 6 | Self-ranking & quality | 6 | ✅ YES |
| **DMAIC_V3/utils/file_utils.py** | All Phases | File operations | All | ✅ YES |
| **DMAIC_V3/utils/json_utils.py** | All Phases | JSON operations | All | ✅ YES |
| **DMAIC_V3/planning_history.json** | Planning Tracker | Planning history | All | ✅ YES |
| **DMAIC_V3/bug_tracking_log.json** | Bug Tracker | Bug tracking | All | ✅ YES |
| **DMAIC_V3/background_snapshot.json** | Change Detector | Convergence state | All | ✅ YES |
| **DMAIC_CANONICAL_OUTPUT/phase1_define.json** | Phase 1 | Phase 1 output | 1 | ✅ YES |
| **DMAIC_CANONICAL_OUTPUT/phase2_measure.json** | Phase 2 | Phase 2 output | 2 | ✅ YES |
| **DMAIC_CANONICAL_OUTPUT/phase2_metrics.json** | Phase 2 | Phase 2 metrics | 2 | ✅ YES |
| **DMAIC_CANONICAL_OUTPUT/phase3_analyze.json** | Phase 3 | Phase 3 output | 3 | ✅ YES |
| **DMAIC_CANONICAL_OUTPUT/phase4_improve.json** | Phase 4 | Phase 4 output | 4 | ✅ YES |
| **DMAIC_CANONICAL_OUTPUT/phase5_control.json** | Phase 5 | Phase 5 output | 5 | ✅ YES |
| **DMAIC_CANONICAL_OUTPUT/phase6_knowledge.json** | Phase 6 | Phase 6 output | 6 | ✅ YES |

---

## 🔗 DOW INTEGRATION POINTS

### ASCII Diagram: DOW Integration Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    DOW (DATA-ORCHESTRATION-WORKFLOW)                    │
│                         INTEGRATION ARCHITECTURE                        │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────▼───────────────┐
                    │  DOW LEVEL 5                  │
                    │  Self-Learning & Optimization │
                    └───────────────┬───────────────┘
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        │                           │                           │
┌───────▼────────┐      ┌──────────▼──────────┐      ┌────────▼────────┐
│ RECURSIVE      │      │ KNOWLEDGE GAIN      │      │ CONVERGENCE     │
│ HOOKS          │      │ TRACKING            │      │ METRICS         │
│                │      │                     │      │                 │
│ • consumed_from│      │ • Patterns          │      │ • Iteration     │
│ • feeds_into   │      │ • Insights          │      │   Comparison    │
│ • iteration    │      │ • Learnings         │      │ • Quality Gates │
│ • version      │      │ • Improvements      │      │ • Convergence   │
└───────┬────────┘      └──────────┬──────────┘      └────────┬────────┘
        │                          │                          │
        └──────────────────────────┼──────────────────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │  INTEGRATION POINTS         │
                    └──────────────┬──────────────┘
                                   │
        ┌──────────────────────────┼──────────────────────────┐
        │                          │                          │
┌───────▼────────┐      ┌──────────▼──────────┐      ┌──────▼──────────┐
│ POINT 1        │      │ POINT 2             │      │ POINT 3         │
│ Phase Outputs  │      │ Iteration Tracking  │      │ Knowledge Base  │
│                │      │                     │      │                 │
│ • Add metadata │      │ • Link iterations   │      │ • Extract       │
│ • Add hooks    │      │ • Track convergence │      │   knowledge     │
│ • Add metrics  │      │ • Compare quality   │      │ • Store insights│
└───────┬────────┘      └──────────┬──────────┘      └────────┬────────┘
        │                          │                          │
        └──────────────────────────┼──────────────────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │  IMPLEMENTATION             │
                    └──────────────┬──────────────┘
                                   │
        ┌──────────────────────────┼──────────────────────────┐
        │                          │                          │
┌───────▼────────┐      ┌──────────▼──────────┐      ┌──────▼──────────┐
│ JSON STRUCTURE │      │ GENERATOR UPDATES   │      │ AGENT UPDATES   │
│                │      │                     │      │                 │
│ {              │      │ • Add metadata      │      │ • Ranking       │
│   "metadata": {│      │ • Add hooks         │      │ • Quality       │
│     "version"  │      │ • Add metrics       │      │ • Convergence   │
│     "timestamp"│      │ • Add knowledge     │      │ • Knowledge     │
│   },           │      │                     │      │                 │
│   "recursive": │      │                     │      │                 │
│   "knowledge": │      │                     │      │                 │
│   "convergence"│      │                     │      │                 │
│ }              │      │                     │      │                 │
└────────────────┘      └─────────────────────┘      └─────────────────┘
```

### DOW Integration Points Detail

#### Point 1: Phase Outputs
- **Location:** `DMAIC_CANONICAL_OUTPUT/*.json`
- **Action:** Add DOW structure to all phase outputs
- **Structure:**
  ```json
  {
    "metadata": {
      "version": "3.3.0",
      "timestamp": "2025-01-15T10:00:00Z",
      "iteration": 1,
      "phase": "phase1_define"
    },
    "recursive_hooks": {
      "consumed_from": ["background_snapshot.json", "planning_history.json"],
      "feeds_into": ["phase2_measure.json"],
      "iteration_lineage": [0, 1],
      "version_history": ["3.2.0", "3.3.0"]
    },
    "knowledge_gain": {
      "patterns_discovered": [],
      "insights_generated": [],
      "learnings_captured": [],
      "improvements_suggested": []
    },
    "convergence_metrics": {
      "quality_score": 0.85,
      "completeness": 0.90,
      "improvement_from_previous": 0.05,
      "convergence_status": "improving"
    }
  }
  ```

#### Point 2: Iteration Tracking
- **Location:** `DMAIC_V3/planning_history.json`, `DMAIC_V3/background_snapshot.json`
- **Action:** Add iteration linkage and convergence tracking
- **Structure:**
  ```json
  {
    "iterations": [
      {
        "iteration": 1,
        "timestamp": "2025-01-15T10:00:00Z",
        "phases_completed": ["phase1", "phase2"],
        "convergence_metrics": {
          "overall_quality": 0.85,
          "improvement_rate": 0.05
        },
        "links_to_previous": 0,
        "links_to_next": 2
      }
    ]
  }
  ```

#### Point 3: Knowledge Base
- **Location:** `DMAIC_CANONICAL_OUTPUT/phase6_knowledge.json`
- **Action:** Extract and store knowledge from all phases
- **Structure:**
  ```json
  {
    "knowledge_base": {
      "patterns": [],
      "insights": [],
      "learnings": [],
      "best_practices": []
    },
    "dow_level": 5,
    "self_learning_enabled": true
  }
  ```

---

## 🚀 ACTION PLAN IMPLEMENTATION

### Phase 1: Cleanup (IMMEDIATE - 2 hours)

#### Step 1.1: Identify Duplicates
```bash
# Run duplicate detection
python DMAIC_V3/analyze_recent_files.py --mode=duplicates

# Output: List of duplicate files to delete
```

#### Step 1.2: Create Backup
```bash
# Create backup before deletion
mkdir DMAIC_V3_BACKUP_20250115
cp -r DMAIC_CANONICAL_OUTPUT DMAIC_V3_BACKUP_20250115/
cp -r DMAIC_CANONICAL_DEEP_OUTPUT DMAIC_V3_BACKUP_20250115/
cp -r DMAIC_CANONICAL_TEST DMAIC_V3_BACKUP_20250115/
cp -r DMAIC_PRODUCTION_FULL DMAIC_V3_BACKUP_20250115/
```

#### Step 1.3: Delete Duplicates
```bash
# Delete duplicate folders (keep only DMAIC_CANONICAL_OUTPUT)
rm -rf DMAIC_CANONICAL_DEEP_OUTPUT
rm -rf DMAIC_CANONICAL_TEST
rm -rf DMAIC_PRODUCTION_FULL
rm -rf DMAIC_TEST_OUTPUT

# Verify deletion
du -sh DMAIC_*
```

**Expected Result:** 148 MB freed

---

### Phase 2: Add Metadata (CRITICAL - 4 hours)

#### Step 2.1: Create Metadata Schema
```python
# File: DMAIC_V3/utils/metadata_schema.py

METADATA_SCHEMA = {
    "metadata": {
        "version": str,
        "timestamp": str,
        "iteration": int,
        "phase": str,
        "generator": str
    }
}
```

#### Step 2.2: Create Metadata Injector
```python
# File: DMAIC_V3/local_mcp/tools/metadata_injector.py

def inject_metadata(file_path, iteration, phase):
    """Inject metadata into JSON file"""
    with open(file_path, 'r') as f:
        data = json.load(f)

    data['metadata'] = {
        'version': '3.3.0',
        'timestamp': datetime.now().isoformat(),
        'iteration': iteration,
        'phase': phase,
        'generator': f'phase{phase}_generator.py'
    }

    with open(file_path, 'w') as f:
        json.dump(data, f, indent=2)
```

#### Step 2.3: Run Metadata Injection
```bash
# Run metadata injection on all JSON files
python DMAIC_V3/local_mcp/tools/metadata_injector.py --target=DMAIC_CANONICAL_OUTPUT

# Verify metadata
python DMAIC_V3/utils/validate_metadata.py
```

**Expected Result:** All 52 JSON files have metadata

---

### Phase 3: Add Recursive Hooks (CRITICAL - 8 hours)

#### Step 3.1: Create Recursive Hooks Schema
```python
# File: DMAIC_V3/utils/recursive_hooks_schema.py

RECURSIVE_HOOKS_SCHEMA = {
    "recursive_hooks": {
        "consumed_from": list,
        "feeds_into": list,
        "iteration_lineage": list,
        "version_history": list
    }
}
```

#### Step 3.2: Create Recursive Hooks Injector
```python
# File: DMAIC_V3/local_mcp/tools/recursive_hooks_injector.py

def inject_recursive_hooks(file_path, consumed_from, feeds_into):
    """Inject recursive hooks into JSON file"""
    with open(file_path, 'r') as f:
        data = json.load(f)

    data['recursive_hooks'] = {
        'consumed_from': consumed_from,
        'feeds_into': feeds_into,
        'iteration_lineage': get_iteration_lineage(file_path),
        'version_history': get_version_history(file_path)
    }

    with open(file_path, 'w') as f:
        json.dump(data, f, indent=2)
```

#### Step 3.3: Run Recursive Hooks Injection
```bash
# Run recursive hooks injection on all JSON files
python DMAIC_V3/local_mcp/tools/recursive_hooks_injector.py --target=DMAIC_CANONICAL_OUTPUT

# Verify hooks
python DMAIC_V3/utils/validate_recursive_hooks.py
```

**Expected Result:** All 76 JSON files have recursive hooks

---

### Phase 4: Add Convergence Metrics (HIGH - 6 hours)

#### Step 4.1: Create Convergence Metrics Schema
```python
# File: DMAIC_V3/utils/convergence_metrics_schema.py

CONVERGENCE_METRICS_SCHEMA = {
    "convergence_metrics": {
        "quality_score": float,
        "completeness": float,
        "improvement_from_previous": float,
        "convergence_status": str
    }
}
```

#### Step 4.2: Create Convergence Metrics Calculator
```python
# File: DMAIC_V3/convergence/metrics_calculator.py

def calculate_convergence_metrics(current_file, previous_file):
    """Calculate convergence metrics"""
    current_data = load_json(current_file)
    previous_data = load_json(previous_file) if previous_file else None

    quality_score = calculate_quality_score(current_data)
    completeness = calculate_completeness(current_data)
    improvement = calculate_improvement(current_data, previous_data)
    status = determine_convergence_status(improvement)

    return {
        'quality_score': quality_score,
        'completeness': completeness,
        'improvement_from_previous': improvement,
        'convergence_status': status
    }
```

#### Step 4.3: Run Convergence Metrics Calculation
```bash
# Run convergence metrics calculation on all iteration files
python DMAIC_V3/convergence/metrics_calculator.py --target=DMAIC_CANONICAL_OUTPUT

# Verify metrics
python DMAIC_V3/utils/validate_convergence_metrics.py
```

**Expected Result:** All 67 iteration files have convergence metrics

---

### Phase 5: Add Knowledge Gain (CRITICAL - 10 hours)

#### Step 5.1: Create Knowledge Gain Schema
```python
# File: DMAIC_V3/utils/knowledge_gain_schema.py

KNOWLEDGE_GAIN_SCHEMA = {
    "knowledge_gain": {
        "patterns_discovered": list,
        "insights_generated": list,
        "learnings_captured": list,
        "improvements_suggested": list
    }
}
```

#### Step 5.2: Create Knowledge Extractor
```python
# File: DMAIC_V3/local_mcp/agents/knowledge_extractor.py

def extract_knowledge(file_path):
    """Extract knowledge from JSON file"""
    data = load_json(file_path)

    patterns = discover_patterns(data)
    insights = generate_insights(data)
    learnings = capture_learnings(data)
    improvements = suggest_improvements(data)

    return {
        'patterns_discovered': patterns,
        'insights_generated': insights,
        'learnings_captured': learnings,
        'improvements_suggested': improvements
    }
```

#### Step 5.3: Run Knowledge Extraction
```bash
# Run knowledge extraction on all JSON files
python DMAIC_V3/local_mcp/agents/knowledge_extractor.py --target=DMAIC_CANONICAL_OUTPUT

# Verify knowledge gain
python DMAIC_V3/utils/validate_knowledge_gain.py
```

**Expected Result:** All 76 JSON files have knowledge gain tracking

---

### Phase 6: Update Generators (HIGH - 8 hours)

#### Step 6.1: Update Phase Generators
```python
# File: DMAIC_V3/generators/phase1_generator.py

def generate_phase1_output(data, iteration):
    """Generate Phase 1 output with DOW structure"""
    output = {
        'metadata': create_metadata(iteration, 'phase1'),
        'recursive_hooks': create_recursive_hooks(iteration, 'phase1'),
        'knowledge_gain': extract_knowledge(data),
        'convergence_metrics': calculate_convergence_metrics(data, iteration),
        'phase1_data': data
    }

    save_json(output, f'DMAIC_CANONICAL_OUTPUT/phase1_define.json')
```

#### Step 6.2: Update All Generators
```bash
# Update all phase generators
python DMAIC_V3/generators/update_all_generators.py

# Verify generators
python DMAIC_V3/utils/validate_generators.py
```

**Expected Result:** All generators updated with DOW structure

---

### Phase 7: Testing (HIGH - 6 hours)

#### Step 7.1: Unit Tests
```bash
# Run unit tests
pytest DMAIC_V3/tests/test_phases.py
pytest DMAIC_V3/tests/test_core.py
pytest DMAIC_V3/tests/test_convergence.py
```

#### Step 7.2: Integration Tests
```bash
# Run integration tests
pytest DMAIC_V3/tests/test_integration.py
```

#### Step 7.3: End-to-End Test
```bash
# Run full pipeline
python DMAIC_V3/full_pipeline_orchestrator.py --iteration=1 --test-mode

# Verify outputs
python DMAIC_V3/utils/validate_pipeline_outputs.py
```

**Expected Result:** All tests pass, pipeline runs successfully

---

## 📊 SUCCESS CRITERIA

### Completion Checklist

- [ ] **Phase 1: Cleanup**
  - [ ] 31 duplicate files deleted
  - [ ] 148 MB disk space freed
  - [ ] Backup created

- [ ] **Phase 2: Metadata**
  - [ ] 52 JSON files have metadata
  - [ ] Metadata schema validated
  - [ ] Metadata injector tested

- [ ] **Phase 3: Recursive Hooks**
  - [ ] 76 JSON files have recursive hooks
  - [ ] Hooks schema validated
  - [ ] Hooks injector tested

- [ ] **Phase 4: Convergence Metrics**
  - [ ] 67 iteration files have convergence metrics
  - [ ] Metrics schema validated
  - [ ] Metrics calculator tested

- [ ] **Phase 5: Knowledge Gain**
  - [ ] 76 JSON files have knowledge gain tracking
  - [ ] Knowledge schema validated
  - [ ] Knowledge extractor tested

- [ ] **Phase 6: Update Generators**
  - [ ] All generators updated
  - [ ] Generators validated
  - [ ] Generators tested

- [ ] **Phase 7: Testing**
  - [ ] Unit tests pass
  - [ ] Integration tests pass
  - [ ] End-to-end test passes

### Final Validation

```bash
# Run final validation
python DMAIC_V3/utils/final_validation.py

# Expected output:
# ✅ All metadata present
# ✅ All recursive hooks present
# ✅ All convergence metrics present
# ✅ All knowledge gain tracking present
# ✅ All generators updated
# ✅ All tests passing
# ✅ DOW Level 5 operational
```

---

## 📝 NOTES

### Repository vs Local Workspace

**Repository (Canonical):**
- Single source of truth
- Production-ready code
- Clean structure
- No duplicates
- Full DOW integration

**Local Workspace:**
- Development/testing area
- May have temporary files
- May have test outputs
- Syncs to repository after validation

### Pipeline Execution

**Production Run:**
```bash
# Uses repository files exclusively
python DMAIC_V3/full_pipeline_orchestrator.py --mode=production
```

**Development Run:**
```bash
# Uses local workspace files
python DMAIC_V3/full_pipeline_orchestrator.py --mode=development
```

### Maintenance

**Weekly:**
- Run duplicate detection
- Validate DOW structure
- Check convergence metrics

**Monthly:**
- Review knowledge base
- Update generators
- Optimize pipeline

---

**Status:** 📋 READY FOR IMPLEMENTATION

**Prepared By:** DOW Integration Team
**Date:** 2025-01-15
**Version:** 1.0
**Next Review:** After Phase 1 completion
