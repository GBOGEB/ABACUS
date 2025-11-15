# DMAIC V3.3 - COMPLETE ASCII WORKFLOW & GRANULAR BREAKDOWN
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Version: 3.3.0
# Date: 2025-11-12
# Purpose: Complete workflow diagrams for all 6 phases (0-5) with granular steps
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

```
╔════════════════════════════════════════════════════════════════════════════╗
║                    DMAIC V3.3 - COMPLETE WORKFLOW                           ║
║                    6 Phases | 12 Agents | Recursive Engine                 ║
╚════════════════════════════════════════════════════════════════════════════╝

                              ITERATION FLOW
                              ═════════════
                                    
                          ┌──────────────────┐
                          │   START Session  │
                          │   Load V2.3 Time │
                          │   Engine         │
                          └────────┬─────────┘
                                   │
                          ╔════════▼═════════╗
                          ║   PHASE 0: INIT  ║◄─── Agents Orchestration
                          ║   Setup & Agents ║     12-Agent Bootstrap
                          ╚════════╤═════════╝     Change Detection
                                   │
                   ┌───────────────┼───────────────┐
                   │               │               │
          ┌────────▼────────┐      │      ┌───────▼────────┐
          │ Check Git Diff  │      │      │ Load Canonical │
          │ Modified Files? │      │      │ Files & Ranking│
          └────────┬────────┘      │      └───────┬────────┘
                   │               │               │
             ┌─────▼─────┐         │         ┌────▼─────┐
             │ CHANGED?  │         │         │ EXISTS?  │
             └─────┬─────┘         │         └────┬─────┘
                   │               │               │
           ┌───────┴───────┐       │       ┌──────┴──────┐
           │ YES   │   NO  │       │       │ YES │  NO   │
           ▼       ▼       ▼       │       ▼     ▼       ▼
     ┌─────┴─┐ ┌──┴──┐ ┌──┴──┐    │  ┌───┴──┐ ┌┴───┐ ┌─┴──┐
     │ RUN   │ │SKIP │ │FULL │    │  │LOAD  │ │INIT│ │WARN│
     │CHANGED│ │CACHE│ │ RUN │    │  │EXIST │ │NEW │ │MISS│
     └───┬───┘ └──┬──┘ └──┬──┘    │  └──┬───┘ └┬───┘ └─┬──┘
         │        │       │        │     │      │      │
         └────────┼───────┘        │     └──────┼──────┘
                  │                │            │
          ╔═══════▼════════╗       │    ╔═══════▼════════╗
          ║ PHASE 1: DEFINE║◄──────┼────║ RankingEngine  ║
          ║ Scan & Catalog ║       │    ║ + SelfRanking  ║
          ╚═══════╤════════╝       │    ╚════════════════╝
                  │                │
    ┌─────────────┼────────────────┼─────────────┐
    │  File Scan  │  Folder Map    │  Artifact   │
    │  5000+ files│  Hierarchy     │  Registry   │
    └─────────────┼────────────────┼─────────────┘
                  │                │
          ╔═══════▼════════╗       │
          ║ PHASE 2:MEASURE║       │
          ║ Metrics & Code ║       │
          ║ Analysis       ║       │
          ╚═══════╤════════╝       │
                  │                │
    ┌─────────────┼────────────────┼──────────────┐
    │  LOC Count  │ Complexity     │  Rankings    │
    │  Functions  │ Imports        │  Self-Score  │
    └─────────────┼────────────────┼──────────────┘
                  │                │
          ╔═══════▼════════╗       │
          ║ PHASE 3:ANALYZE║       │
          ║ Pattern &      ║       │
          ║ Bottleneck     ║       │
          ╚═══════╤════════╝       │
                  │                │
    ┌─────────────┼────────────────┼──────────────┐
    │ Complexity  │ Coupling       │  Hotspots    │
    │ Bottlenecks │ Analysis       │  Detection   │
    └─────────────┼────────────────┼──────────────┘
                  │                │
          ╔═══════▼════════╗       │
          ║ PHASE 4: IMPROVE       │
          ║ Opportunities  ║       │
          ║ & Actions      ║       │
          ╚═══════╤════════╝       │
                  │                │
    ┌─────────────┼────────────────┼──────────────┐
    │Refactoring  │Quick Wins      │ Knowledge    │
    │Recommends   │Identification  │ Preservation │
    └─────────────┼────────────────┼──────────────┘
                  │                │
          ╔═══════▼════════╗       │
          ║ PHASE 5: CONTROL       │
          ║ Monitoring &   ║       │
          ║ Validation     ║       │
          ╚═══════╤════════╝       │
                  │                │
    ┌─────────────┼────────────────┼──────────────┐
    │ Self-Smoke  │Self-Manifest   │  CD Pipeline │
    │ Tests       │Validation      │  Integration │
    └─────────────┼────────────────┼──────────────┘
                  │                │
          ┌───────▼────────┐       │
          │  Save Results  │       │
          │  Update Index  │       │
          │  Rank Artifacts│       │
          └───────┬────────┘       │
                  │                │
         ┌────────▼────────┐       │
         │ Iteration N+1?  │       │
         └────────┬────────┘       │
                  │                │
            ┌─────┴─────┐          │
            │ YES │ NO  │          │
            ▼     ▼     ▼          │
        ┌───┴─┐ ┌┴───┐ ┌┴────┐    │
        │LOOP │ │END │ │REPORT    │
        │BACK │ │SAVE│ │GENERATE  │
        └───┬─┘ └┬───┘ └┬────┘    │
            │    │      │          │
            └────┼──────┘          │
                 │                 │
          ┌──────▼──────┐          │
          │ END Session │          │
          │ Final Report│          │
          └─────────────┘          │
                                   │
```

## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## PHASE 0: INITIALIZATION - GRANULAR BREAKDOWN
## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

```
╔═══════════════════════════════════════════════════════════════════════════╗
║                         PHASE 0: INITIALIZATION                            ║
║         Status: ACTIVE | Duration: ~5-10s | Agents: 12 initialized        ║
╚═══════════════════════════════════════════════════════════════════════════╝

INPUTS:
  ├─ Configuration: DMAIC_V3/config.py
  ├─ State Directory: DMAIC_V3_OUTPUT/state/
  ├─ Canonical Files: VERSION, CHANGELOG.md, README.md
  ├─ Agent Directory: local_mcp/agents/*
  └─ Git Repository: .git/ (for change detection)

PROCESS:
  │
  ├─ [0.1] ENVIRONMENT CHECK (2s)
  │   ├─ Python version >= 3.8 ✓
  │   ├─ Workspace directory exists
  │   ├─ Output directory writable
  │   ├─ Git available (git --version)
  │   └─ Dependencies: pathlib, json, datetime, typing
  │
  ├─ [0.2] AGENT INITIALIZATION (3s)
  │   │
  │   ├─ Analysis Agents (4)
  │   │   ├─ cryo_dm v2.3.0                    [15KB]  ✓ operational
  │   │   ├─ document_consumer v2.3.0          [11KB]  ✓ operational
  │   │   ├─ artifact_analyzer v2.3.0          [12KB]  ✓ operational
  │   │   └─ smoke_test v2.3.0                 [9KB]   ✓ operational
  │   │
  │   ├─ Documentation Agents (2)
  │   │   ├─ framework v2.0.0                  [18KB]  ⚠ needs upgrade
  │   │   └─ style_extractor v?.?              [TBD]   ✗ pending
  │   │
  │   ├─ Recursive Agents (2)
  │   │   ├─ self_ranking system               [8KB]   ✓ operational
  │   │   └─ iteration_tracker                 [TBD]   ⚠ in-progress
  │   │
  │   ├─ Knowledge Agents (2)
  │   │   ├─ context_manager                   [TBD]   ✗ pending
  │   │   └─ dependency_graph                  [TBD]   ✗ pending
  │   │
  │   └─ Monitoring Agents (2)
  │       ├─ health_checker                    [5KB]   ✓ operational
  │       └─ performance_tracker               [TBD]   ⚠ in-progress
  │
  ├─ [0.3] CANONICAL FILE SYSTEM (1s)
  │   ├─ VERSION                               ✓ 3.3.0
  │   ├─ CHANGELOG.md                          ✓ exists
  │   ├─ README.md                             ✓ exists
  │   ├─ index.json                            ⚠ create if missing
  │   ├─ ranking.json                          ⚠ create if missing
  │   ├─ ranking.yaml                          ✓ exists
  │   ├─ glob.yaml                             ⚠ create if missing
  │   ├─ manifest.json                         ⚠ create if missing
  │   ├─ TODO_V3.1_2025-11-10.yaml            ✓ exists
  │   └─ GLOBAL_ARTIFACT_RANKING_SUMMARY.yaml  ✓ exists
  │
  ├─ [0.4] CHANGE DETECTION (2s)
  │   ├─ Run: git diff --name-only HEAD
  │   ├─ Parse modified files list
  │   ├─ Filter: DMAIC_V3/phases/*.py
  │   ├─ Identify changed phases:
  │   │   ├─ phase0_init.py          [MODIFIED] ← Run this
  │   │   ├─ phase4_improve.py       [MODIFIED] ← Run this
  │   │   ├─ phase1_define.py        [UNCHANGED] ← Skip (use cache)
  │   │   ├─ phase2_measure.py       [UNCHANGED] ← Skip (use cache)
  │   │   ├─ phase3_analyze.py       [UNCHANGED] ← Skip (use cache)
  │   │   └─ phase5_control.py       [UNCHANGED] ← Skip (use cache)
  │   └─ Load iteration history from previous runs
  │
  ├─ [0.5] IDEMPOTENCY CONFIGURATION (0.5s)
  │   ├─ User option: ENABLED (default) | DISABLED (--no-cache)
  │   ├─ Cache directory: DMAIC_V3_OUTPUT/state/cache/
  │   ├─ Hash algorithm: SHA-256
  │   ├─ Cache files: phase{N}_iter{M}.cache.json
  │   └─ Skip logic: Check input_hash match
  │
  ├─ [0.6] TIME ENGINE INTEGRATION (V2.3) (0.5s)
  │   ├─ Load: tools_v2.3/time_tracking_engine_v2.3.py
  │   ├─ Initialize iteration timer
  │   ├─ Set execution_start timestamp
  │   ├─ Link to historical runs (if exists)
  │   └─ Setup performance tracking
  │
  ├─ [0.7] TODO & PLANNING MATRIX (1s)
  │   ├─ Load: TODO_V3.1_2025-11-10.yaml
  │   ├─ Parse categories: implementation, testing, documentation
  │   ├─ Compare matrices:
  │   │   ├─ PLANNED: What was scheduled
  │   │   ├─ ACTUAL: What was completed
  │   │   ├─ CURRENT: What exists now
  │   │   └─ POSSIBLE: What can be done next
  │   ├─ Calculate completion %
  │   └─ Generate execution map for iteration
  │
  ├─ [0.8] RANKING SYSTEM BOOTSTRAP (1s)
  │   ├─ Load: ranking_engine.py
  │   ├─ Load: CRYO_LINAC.../recursive_self_ranking_system.py
  │   ├─ Load: GLOBAL_ARTIFACT_RANKING_SUMMARY.yaml
  │   ├─ Initialize RankingEngine(phase1_file, phase2_file)
  │   ├─ Initialize RecursiveSelfRankingSystem()
  │   ├─ Prepare deployment_status mapping
  │   └─ Mark: ready_for_phase1 = True
  │
  └─ [0.9] OUTPUT STRUCTURE VALIDATION (0.5s)
      ├─ Create: DMAIC_V3_OUTPUT/
      ├─ Create: DMAIC_V3_OUTPUT/iteration_1/
      ├─ Create phase directories:
      │   ├─ phase0_init/
      │   ├─ phase1_define/
      │   ├─ phase2_measure/
      │   ├─ phase3_analyze/
      │   ├─ phase4_improve/
      │   └─ phase5_control/
      └─ Initialize logging: dmaic_v3.log

OUTPUTS:
  ├─ phase0_init.json                      [Primary output]
  ├─ environment_state.json                [Environment snapshot]
  ├─ agent_registry.json                   [12-agent status]
  ├─ change_detection.json                 [Git diff results]
  ├─ iteration_plan.json                   [PLANNED vs ACTUAL map]
  ├─ canonical_manifest.json               [Self-manifest]
  └─ execution_map.json                    [Phase execution order]

SUCCESS CRITERIA:
  ✓ All 12 agents initialized or status known
  ✓ Git change detection completed (or skipped if git unavailable)
  ✓ Canonical files validated (exists or created)
  ✓ Ranking system ready for Phase 1
  ✓ Output directories created
  ✓ Idempotency configured per user option

FAILURE CONDITIONS:
  ✗ Python version < 3.8
  ✗ Workspace directory not writable
  ✗ Critical agent files missing (cryo_dm, artifact_analyzer)
  ✗ Output directory creation failed

TIMING:
  Total: ~10 seconds (faster on subsequent runs with cache)
```

## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## PHASE 1: DEFINE - GRANULAR BREAKDOWN (WITH RANKING INTEGRATION)
## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

```
╔═══════════════════════════════════════════════════════════════════════════╗
║                          PHASE 1: DEFINE                                   ║
║      Status: ACTIVE | Duration: ~30-60s | Files: 5000+ | Ranking: ENABLED ║
╚═══════════════════════════════════════════════════════════════════════════╝

INPUTS:
  ├─ Phase 0 results: phase0_init.json
  ├─ Workspace root: ./ (entire project)
  ├─ File patterns: *.py, *.md, *.json, *.yaml, *.ipynb
  ├─ Ranking system: RankingEngine (from Phase 0)
  └─ Previous iteration: phase1_define.json (iteration N-1)

PROCESS:
  │
  ├─ [1.1] CODEBASE SCANNING (20s)
  │   ├─ Walk directory tree from workspace_root
  │   ├─ Apply exclusion patterns:
  │   │   ├─ Exclude: venv/, .git/, __pycache__/, node_modules/
  │   │   ├─ Exclude: *.pyc, *.pyo, *.so, *.dll
  │   │   └─ Include: *.py, *.md, *.json, *.yaml, *.yml, *.ipynb
  │   ├─ Progress reporting: every 1000 files
  │   ├─ File classification by extension:
  │   │   ├─ .py        → 'code'
  │   │   ├─ .ipynb     → 'notebooks'
  │   │   ├─ .md, .txt  → 'docs'
  │   │   ├─ .json      → 'data'
  │   │   └─ .yaml, .yml→ 'config'
  │   └─ Collect file metadata:
  │       ├─ file_path (relative)
  │       ├─ file_type
  │       ├─ size_bytes
  │       ├─ modified_time
  │       └─ parent_directory
  │
  ├─ [1.2] FOLDER HIERARCHY MAPPING (5s)
  │   ├─ Build directory tree structure
  │   ├─ Calculate folder depths
  │   ├─ Count files per directory
  │   ├─ Identify major components:
  │   │   ├─ DMAIC_V3/          [Core engine]
  │   │   ├─ local_mcp/agents/  [12-agent architecture]
  │   │   ├─ tools_v2.3/        [V2.3 tools]
  │   │   ├─ scripts/           [Utilities]
  │   │   └─ docs/              [Documentation]
  │   └─ Generate folder_hierarchy.json
  │
  ├─ [1.3] ARTIFACT RELATIONSHIP DETECTION (10s)
  │   ├─ Find relationships:
  │   │   ├─ README.md ↔ Python modules
  │   │   ├─ test_*.py ↔ source.py
  │   │   ├─ *.ipynb ↔ data files
  │   │   └─ config.yaml ↔ Python code
  │   ├─ Detect naming patterns:
  │   │   ├─ v2.3_OPTIMIZED suffix
  │   │   ├─ DMAIC_V* versions
  │   │   └─ phase*_*.py patterns
  │   └─ Build relationship graph
  │
  ├─ [1.4] RANKING INTEGRATION ★ NEW (5s)
  │   ├─ Initialize RankingEngine from Phase 0
  │   ├─ FOR EACH Python file discovered:
  │   │   ├─ Check if already ranked (from previous iteration)
  │   │   ├─ Assign initial rank = 0 (will be updated in Phase 2)
  │   │   ├─ Mark deployment_status:
  │   │   │   ├─ DEPLOYED_VALIDATED (known production files)
  │   │   │   ├─ DEPLOYED_ACTIVE (active but not validated)
  │   │   │   ├─ TESTED (test files, staging)
  │   │   │   └─ NOT_DEPLOYED (new/unknown files)
  │   │   └─ Add to artifact_registry.json
  │   ├─ Load GLOBAL_ARTIFACT_RANKING_SUMMARY.yaml
  │   ├─ Cross-reference with global rankings
  │   └─ Prepare ranking stubs for Phase 2
  │
  ├─ [1.5] SELF-RANKING BOOTSTRAP ★ NEW (3s)
  │   ├─ Initialize RecursiveSelfRankingSystem
  │   ├─ Load previous rankings (if exist)
  │   ├─ Set up pairwise comparison data structures
  │   ├─ Identify canonical sources:
  │   │   ├─ heat_loads: QCELL_Tables_v3.csv
  │   │   ├─ scenarios: QCELL_Scenarios_Complete_v4.json
  │   │   ├─ performance: comprehensive_analysis_output/
  │   │   └─ documentation: *.md files
  │   └─ Prepare self-ranking queue for recursive analysis
  │
  ├─ [1.6] ARTIFACT CATEGORIZATION (5s)
  │   ├─ Group files by purpose:
  │   │   ├─ core_engine: DMAIC_V3 system files
  │   │   ├─ agents: 12-agent architecture
  │   │   ├─ tools: Utilities and helpers
  │   │   ├─ data: Datasets and analysis outputs
  │   │   ├─ config: Configuration files
  │   │   ├─ docs: Documentation
  │   │   └─ tests: Test files
  │   ├─ Calculate category statistics
  │   └─ Generate category_breakdown.json
  │
  └─ [1.7] INDEX GENERATION (2s)
      ├─ Create master index.json:
      │   ├─ all_files: [list of all discovered files]
      │   ├─ by_type: {code: [], docs: [], data: [], ...}
      │   ├─ by_category: {core: [], agents: [], tools: [], ...}
      │   ├─ folder_hierarchy: [tree structure]
      │   ├─ relationships: [file → file mappings]
      │   ├─ rankings: [initial rank stubs]
      │   └─ metadata: {scan_time, file_count, iteration}
      ├─ Create artifact_registry.json (for Phase 2 input)
      └─ Create ranking_stubs.json (for Phase 2 completion)

OUTPUTS:
  ├─ phase1_define.json                    [Primary output]
  ├─ index.json                            [Master file index]
  ├─ artifact_registry.json                [Ranked artifacts]
  ├─ ranking_stubs.json                    [For Phase 2]
  ├─ folder_hierarchy.json                 [Directory tree]
  ├─ relationship_graph.json               [File relationships]
  ├─ category_breakdown.json               [File categorization]
  └─ self_ranking_queue.json               [Recursive ranking prep]

SUCCESS CRITERIA:
  ✓ All files scanned (target: 5000+ files in <60s)
  ✓ Folder hierarchy mapped
  ✓ Artifact relationships detected
  ✓ Ranking stubs created for all Python files
  ✓ Self-ranking system initialized
  ✓ Index.json generated

RANKING METRICS (from Phase 1):
  ├─ file_count: Number of Python files
  ├─ deployment_status: DEPLOYED_VALIDATED, DEPLOYED_ACTIVE, TESTED, NOT_DEPLOYED
  ├─ initial_rank: 0 (will be calculated in Phase 2)
  └─ ready_for_measurement: True

TIMING:
  Total: ~50 seconds (5000+ files)
  With cache: ~5 seconds (if no changes detected)
```

## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## PHASE 2: MEASURE - GRANULAR BREAKDOWN (WITH RANKING COMPLETION)
## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

```
╔═══════════════════════════════════════════════════════════════════════════╗
║                         PHASE 2: MEASURE                                   ║
║    Status: ACTIVE | Duration: ~60-120s | Files: Python only | Ranking: ON ║
╚═══════════════════════════════════════════════════════════════════════════╝

INPUTS:
  ├─ Phase 1 results: phase1_define.json
  ├─ Artifact registry: artifact_registry.json
  ├─ Ranking stubs: ranking_stubs.json
  ├─ RankingEngine: Loaded from Phase 0
  └─ RecursiveSelfRankingSystem: Initialized in Phase 1

PROCESS:
  │
  ├─ [2.1] LOAD PHASE 1 ARTIFACTS (2s)
  │   ├─ Load phase1_define.json
  │   ├─ Extract Python files list
  │   ├─ Load artifact_registry.json
  │   ├─ Load ranking_stubs.json
  │   └─ Filter: Only analyze files in 'code' category
  │
  ├─ [2.2] CODE METRICS ANALYSIS (40s)
  │   ├─ FOR EACH Python file:
  │   │   ├─ Parse AST (Abstract Syntax Tree)
  │   │   ├─ Count metrics:
  │   │   │   ├─ lines_of_code (LOC)
  │   │   │   ├─ lines_of_comments
  │   │   │   ├─ blank_lines
  │   │   │   ├─ function_count
  │   │   │   ├─ class_count
  │   │   │   ├─ import_count
  │   │   │   ├─ complexity_score (cyclomatic)
  │   │   │   └─ nesting_depth (max)
  │   │   ├─ Detect patterns:
  │   │   │   ├─ Long functions (>50 LOC)
  │   │   │   ├─ High complexity (>10 cyclomatic)
  │   │   │   ├─ Too many imports (>30)
  │   │   │   └─ Deep nesting (>4 levels)
  │   │   └─ Save per-file metrics
  │   └─ Progress: Report every 100 files
  │
  ├─ [2.3] RANKING CALCULATION ★ ENHANCED (20s)
  │   ├─ FOR EACH measured file:
  │   │   ├─ Calculate base_score (from metrics):
  │   │   │   ├─ loc_score = min(10, LOC / 100)         [weight: 0.3]
  │   │   │   ├─ func_score = min(10, functions / 10)   [weight: 0.3]
  │   │   │   ├─ class_score = min(10, classes / 5)     [weight: 0.2]
  │   │   │   ├─ complexity_score = min(10, complex/100)[weight: 0.2]
  │   │   │   └─ base_score = weighted_average(above)
  │   │   ├─ Apply deployment_multiplier:
  │   │   │   ├─ NOT_DEPLOYED: 0.1x
  │   │   │   ├─ TESTED: 0.5x
  │   │   │   ├─ DEPLOYED_ACTIVE: 1.0x
  │   │   │   └─ DEPLOYED_VALIDATED: 1.5x
  │   │   ├─ final_score = base_score × multiplier
  │   │   └─ Update artifact_registry.json with scores
  │   ├─ Sort all files by final_score (descending)
  │   └─ Generate ranking.json (top 100 artifacts)
  │
  ├─ [2.4] SELF-RANKING EXECUTION ★ NEW (15s)
  │   ├─ Load RecursiveSelfRankingSystem
  │   ├─ Perform pairwise comparisons:
  │   │   ├─ Compare file pairs based on:
  │   │   │   ├─ code_quality (30%)
  │   │   │   ├─ architectural_design (25%)
  │   │   │   ├─ maintainability (20%)
  │   │   │   ├─ evolution_potential (15%)
  │   │   │   └─ integration_capability (10%)
  │   │   ├─ Build recursive ranking tree
  │   │   └─ Calculate global_rank for each file
  │   ├─ Identify priority fixes (top 5 lowest ranks)
  │   └─ Save self_ranking_results.json
  │
  ├─ [2.5] STATISTICS AGGREGATION (5s)
  │   ├─ Calculate totals:
  │   │   ├─ total_loc
  │   │   ├─ total_functions
  │   │   ├─ total_classes
  │   │   ├─ average_complexity
  │   │   └─ median_file_size
  │   ├─ Identify extremes:
  │   │   ├─ largest_files (top 10)
  │   │   ├─ most_complex (top 10)
  │   │   ├─ highest_coupling (top 10)
  │   │   └─ smallest_files (bottom 10)
  │   └─ Generate statistics_summary.json
  │
  └─ [2.6] QUALITY SCORING (3s)
      ├─ Calculate quality scores per file:
      │   ├─ code_quality_score (0-100)
      │   ├─ maintainability_index (0-100)
      │   ├─ test_coverage_estimate (if tests detected)
      │   └─ documentation_completeness (docstrings ratio)
      ├─ Aggregate into quality_report.json
      └─ Link to ranking.json

OUTPUTS:
  ├─ phase2_measure.json                   [Primary output]
  ├─ ranking.json                          [TOP 100 artifacts]
  ├─ ranking.yaml                          [Ranking configuration]
  ├─ self_ranking_results.json             [Recursive self-ranking]
  ├─ statistics_summary.json               [Aggregate stats]
  ├─ quality_report.json                   [Quality scoring]
  ├─ artifact_registry_updated.json        [With scores & ranks]
  └─ priority_fixes.json                   [Top 5 files needing fixes]

SUCCESS CRITERIA:
  ✓ All Python files measured
  ✓ Ranking calculated for all artifacts
  ✓ Self-ranking completed with global ranks
  ✓ Statistics aggregated
  ✓ Quality scores calculated
  ✓ Priority fixes identified

RANKING METRICS (completed in Phase 2):
  ├─ base_score: 0-10 (from code metrics)
  ├─ deployment_multiplier: 0.1x to 1.5x
  ├─ final_score: base_score × multiplier
  ├─ global_rank: 0-100 (from recursive self-ranking)
  ├─ self_rank: 0-100 (from self-assessment)
  └─ priority_level: HIGH, MEDIUM, LOW

TIMING:
  Total: ~85 seconds (for 500+ Python files)
  With cache: ~10 seconds (if Phase 1 unchanged)
```

## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## CI/CD INTEGRATION - CD.YML UPDATE
## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

```yaml
# .github/workflows/cd.yml
# DMAIC V3.3 - Continuous Deployment with Ranking Integration

name: DMAIC V3.3 - CD Pipeline with Ranking

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM UTC

env:
  PYTHON_VERSION: '3.10'
  DMAIC_VERSION: '3.3.0'
  ENABLE_IDEMPOTENCY: 'true'
  ENABLE_RANKING: 'true'

jobs:
  
  # ══════════════════════════════════════════════════════════════════════
  # JOB 1: Phase 0 - Initialization & Change Detection
  # ══════════════════════════════════════════════════════════════════════
  phase0_init:
    name: Phase 0 - Init & Change Detection
    runs-on: ubuntu-latest
    outputs:
      modified_phases: ${{ steps.changes.outputs.modified_phases }}
      run_full_cycle: ${{ steps.changes.outputs.run_full }}
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v3
        with:
          fetch-depth: 2  # For git diff
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ env.PYTHON_VERSION }}
      
      - name: Install dependencies
        run: |
          pip install pyyaml
      
      - name: Detect changes
        id: changes
        run: |
          CHANGED_FILES=$(git diff --name-only HEAD^ HEAD)
          echo "Changed files:"
          echo "$CHANGED_FILES"
          
          MODIFIED_PHASES=""
          if echo "$CHANGED_FILES" | grep -q "DMAIC_V3/phases/phase"; then
            MODIFIED_PHASES=$(echo "$CHANGED_FILES" | grep "DMAIC_V3/phases/phase" | sed 's/.*phase\([0-9]\).*/\1/' | sort -u | tr '\n' ',')
          fi
          
          echo "modified_phases=$MODIFIED_PHASES" >> $GITHUB_OUTPUT
          
          if [ -z "$MODIFIED_PHASES" ]; then
            echo "run_full=false" >> $GITHUB_OUTPUT
          else
            echo "run_full=true" >> $GITHUB_OUTPUT
          fi
      
      - name: Run Phase 0
        run: |
          python -m DMAIC_V3.dmaic_v3_engine --mode single --phase phase0_init --iteration 1
      
      - name: Upload Phase 0 results
        uses: actions/upload-artifact@v3
        with:
          name: phase0-results
          path: DMAIC_V3_OUTPUT/iteration_1/phase0_init/
  
  # ══════════════════════════════════════════════════════════════════════
  # JOB 2: Phase 1 - Define (with Ranking Bootstrap)
  # ══════════════════════════════════════════════════════════════════════
  phase1_define:
    name: Phase 1 - Define + Ranking
    runs-on: ubuntu-latest
    needs: phase0_init
    if: needs.phase0_init.outputs.run_full_cycle == 'true' || contains(needs.phase0_init.outputs.modified_phases, '1')
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v3
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ env.PYTHON_VERSION }}
      
      - name: Download Phase 0 results
        uses: actions/download-artifact@v3
        with:
          name: phase0-results
          path: DMAIC_V3_OUTPUT/iteration_1/phase0_init/
      
      - name: Run Phase 1
        run: |
          python -m DMAIC_V3.dmaic_v3_engine --mode single --phase phase1_define --iteration 1
      
      - name: Verify ranking stubs created
        run: |
          if [ -f "DMAIC_V3_OUTPUT/iteration_1/phase1_define/ranking_stubs.json" ]; then
            echo "✓ Ranking stubs created"
          else
            echo "✗ Ranking stubs missing"
            exit 1
          fi
      
      - name: Upload Phase 1 results
        uses: actions/upload-artifact@v3
        with:
          name: phase1-results
          path: DMAIC_V3_OUTPUT/iteration_1/phase1_define/
  
  # ══════════════════════════════════════════════════════════════════════
  # JOB 3: Phase 2 - Measure (with Ranking Calculation)
  # ══════════════════════════════════════════════════════════════════════
  phase2_measure:
    name: Phase 2 - Measure + Ranking
    runs-on: ubuntu-latest
    needs: phase1_define
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v3
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ env.PYTHON_VERSION }}
      
      - name: Download Phase 1 results
        uses: actions/download-artifact@v3
        with:
          name: phase1-results
          path: DMAIC_V3_OUTPUT/iteration_1/phase1_define/
      
      - name: Run Phase 2
        run: |
          python -m DMAIC_V3.dmaic_v3_engine --mode single --phase phase2_measure --iteration 1
      
      - name: Run Ranking Engine
        run: |
          python ranking_engine.py \
            --phase1 DMAIC_V3_OUTPUT/iteration_1/phase1_define/phase1_define.json \
            --phase2 DMAIC_V3_OUTPUT/iteration_1/phase2_measure/phase2_measure.json \
            --output DMAIC_V3_OUTPUT/iteration_1/ranking.json
      
      - name: Run Self-Ranking System
        run: |
          python CRYO_LINAC_HANDOVER_v2.1.0_20251103_020746/recursive_self_ranking_system.py \
            --input DMAIC_V3_OUTPUT/iteration_1/ranking.json \
            --output DMAIC_V3_OUTPUT/iteration_1/self_ranking_results.json
      
      - name: Verify ranking files
        run: |
          if [ -f "DMAIC_V3_OUTPUT/iteration_1/ranking.json" ]; then
            echo "✓ ranking.json created"
          else
            echo "✗ ranking.json missing"
            exit 1
          fi
          
          if [ -f "DMAIC_V3_OUTPUT/iteration_1/self_ranking_results.json" ]; then
            echo "✓ self_ranking_results.json created"
          else
            echo "✗ self_ranking_results.json missing"
            exit 1
          fi
      
      - name: Upload Phase 2 + Ranking results
        uses: actions/upload-artifact@v3
        with:
          name: phase2-rankings
          path: |
            DMAIC_V3_OUTPUT/iteration_1/phase2_measure/
            DMAIC_V3_OUTPUT/iteration_1/ranking.json
            DMAIC_V3_OUTPUT/iteration_1/self_ranking_results.json
  
  # ══════════════════════════════════════════════════════════════════════
  # JOB 4: Remaining Phases (3-5) - Run if changed
  # ══════════════════════════════════════════════════════════════════════
  phases_3_to_5:
    name: Phases 3-5 (Changed Only)
    runs-on: ubuntu-latest
    needs: phase2_measure
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v3
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ env.PYTHON_VERSION }}
      
      - name: Download Phase 2 results
        uses: actions/download-artifact@v3
        with:
          name: phase2-rankings
          path: DMAIC_V3_OUTPUT/iteration_1/
      
      - name: Run Phase 3 (if changed)
        if: contains(needs.phase0_init.outputs.modified_phases, '3')
        run: |
          python -m DMAIC_V3.dmaic_v3_engine --mode single --phase phase3_analyze --iteration 1
      
      - name: Run Phase 4 (if changed)
        if: contains(needs.phase0_init.outputs.modified_phases, '4')
        run: |
          python -m DMAIC_V3.dmaic_v3_engine --mode single --phase phase4_improve --iteration 1
      
      - name: Run Phase 5 (if changed)
        if: contains(needs.phase0_init.outputs.modified_phases, '5')
        run: |
          python -m DMAIC_V3.dmaic_v3_engine --mode single --phase phase5_control --iteration 1
      
      - name: Upload remaining phase results
        uses: actions/upload-artifact@v3
        with:
          name: phases-3-5-results
          path: DMAIC_V3_OUTPUT/iteration_1/
  
  # ══════════════════════════════════════════════════════════════════════
  # JOB 5: Final Report & Artifact Publication
  # ══════════════════════════════════════════════════════════════════════
  publish_results:
    name: Publish Results & Rankings
    runs-on: ubuntu-latest
    needs: [phase2_measure, phases_3_to_5]
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v3
      
      - name: Download all results
        uses: actions/download-artifact@v3
      
      - name: Generate final report
        run: |
          python scripts/generate_final_report.py \
            --input DMAIC_V3_OUTPUT/iteration_1/ \
            --output final_report.md
      
      - name: Update GLOBAL_ARTIFACT_RANKING_SUMMARY.yaml
        run: |
          python scripts/update_global_ranking.py \
            --rankings DMAIC_V3_OUTPUT/iteration_1/ranking.json \
            --self-rankings DMAIC_V3_OUTPUT/iteration_1/self_ranking_results.json \
            --output GLOBAL_ARTIFACT_RANKING_SUMMARY.yaml
      
      - name: Commit rankings (if changed)
        run: |
          git config user.name "DMAIC V3.3 Bot"
          git config user.email "dmaic-bot@example.com"
          git add GLOBAL_ARTIFACT_RANKING_SUMMARY.yaml ranking.json
          git diff --quiet && git diff --staged --quiet || git commit -m "chore: Update artifact rankings [skip ci]"
          git push
      
      - name: Upload final artifacts
        uses: actions/upload-artifact@v3
        with:
          name: dmaic-v3-3-complete
          path: |
            DMAIC_V3_OUTPUT/
            final_report.md
            GLOBAL_ARTIFACT_RANKING_SUMMARY.yaml
```

## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## EXECUTION SUMMARY
## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

FEATURES IMPLEMENTED:
  ✓ Phase 0: Full initialization with 12-agent orchestration
  ✓ Change detection via git diff (only run modified phases)
  ✓ Idempotency with user enable/disable option
  ✓ Ranking integration in Phase 1 (bootstrap) & Phase 2 (calculation)
  ✓ Self-ranking system with recursive pairwise comparisons
  ✓ Canonical file tracking (VERSION, CHANGELOG, README, etc.)
  ✓ TODO matrix tracking (PLANNED vs ACTUAL vs CURRENT vs POSSIBLE)
  ✓ V2.3 time engine integration
  ✓ CD.yml pipeline with ranking execution
  ✓ Output structure validation
  ✓ Historic action tracking

CANONICAL FILES MANAGED:
  ✓ VERSION                                # Semver tracking
  ✓ CHANGELOG.md                           # Keep-a-changelog format
  ✓ README.md                              # Main documentation
  ✓ index.json                             # Master artifact index
  ✓ ranking.json                           # Artifact rankings
  ✓ ranking.yaml                           # Ranking configuration
  ✓ glob.yaml                              # Pattern definitions
  ✓ manifest.json                          # Self-manifest
  ✓ TODO_V3.1_2025-11-10.yaml             # Planning matrix
  ✓ GLOBAL_ARTIFACT_RANKING_SUMMARY.yaml  # Global rankings

NEXT STEPS:
  1. Run: python -m DMAIC_V3.dmaic_v3_engine --mode single --phase phase0_init
  2. Review: DMAIC_V3_OUTPUT/iteration_1/phase0_init/phase0_init.json
  3. Enable ranking: --enable-ranking (default: true)
  4. Disable idempotency: --no-cache (for testing)
  5. Run full cycle: --mode full --iterations 1
