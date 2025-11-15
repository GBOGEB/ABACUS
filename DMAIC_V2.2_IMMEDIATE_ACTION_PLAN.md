# DMAIC V2.2 - IMMEDIATE ACTION PLAN


**Version:** 2.3.0  
**Generated:** 2025-11-08T19:22:18.821261+00:00  
**Date:** 2025-11-08 17:05 UTC  
**Status:** 🔴 READY TO EXECUTE  
**Time Estimate:** 3 days  
**Current State:** Engine has stub implementations, comprehensive logic exists separately

---

## 🎯 OBJECTIVE

Integrate ALL existing DMAIC knowledge into `recursive_dmaic_engine_v2.py` without dilution.

---

## 📋 DAY 1: PHASE 3-5 INTEGRATION

### Task 1.1: Integrate Phase 3 Analysis (3 hours)

**Source:** `run_phase3_analyze.py` (180 lines)

**Steps:**
1. Open `recursive_dmaic_engine_v2.py`
2. Locate `phase3_analyze()` method (currently ~line 1274)
3. Replace stub implementation with logic from `run_phase3_analyze.py`:
   - Copy `analyze_measurements()` function body
   - Adapt paths: `Path("RECURSIVE_DMAIC_OUTPUT/...")` → `self.output_dir / ...`
   - Adapt data access: `measure_data['measurements']` → use `self.state` or read from Phase 2 output
   - Keep all 4 complexity categories
   - Keep all 6 issue types
   - Keep all 4 improvement opportunities
4. Test Phase 3 output
5. Compare with standalone runner output
6. Verify JSON structure matches

**Expected Output:**
```json
{
  "phase": "ANALYZE",
  "timestamp": "...",
  "categories": {
    "simple": 1234,
    "moderate": 567,
    "complex": 89,
    "very_complex": 12
  },
  "issues": {
    "large_files": 568,
    "many_functions": 815,
    "many_classes": 123,
    "high_complexity": 654,
    "no_functions": 234,
    "few_imports": 456
  },
  "opportunities": [
    {
      "id": "OPP-001",
      "title": "Refactor Large Files",
      "description": "...",
      "priority": "HIGH",
      "impact": "...",
      "files": [...]
    },
    ...
  ],
  "detailed_issues": {...}
}
```

### Task 1.2: Integrate Phase 4 Improvements (2 hours)

**Source:** `run_phase4_improve.py` (220 lines)

**Steps:**
1. Locate `phase4_improve()` method (currently ~line 1458)
2. Replace stub implementation with logic from `run_phase4_improve.py`:
   - Copy `generate_improvements()` function body
   - Adapt to read Phase 3 output from `self.output_dir`
   - Keep all action plan generation logic
   - Keep all 4 opportunity types with specific actions
   - Keep effort estimation
   - Keep priority-based recommendations
3. Test Phase 4 output
4. Compare with standalone runner output
5. Verify JSON structure matches

**Expected Output:**
```json
{
  "phase": "IMPROVE",
  "timestamp": "...",
  "action_plans": [
    {
      "opportunity_id": "OPP-001",
      "title": "Refactor Large Files",
      "priority": "HIGH",
      "affected_files": 568,
      "sample_files": [...],
      "actions": [
        {
          "action": "Identify logical modules within large files",
          "method": "Analyze function groupings and dependencies",
          "tool": "Static analysis"
        },
        ...
      ],
      "estimated_effort": "2272 person-hours",
      "expected_benefit": "Improves maintainability and readability"
    },
    ...
  ],
  "recommendations": {
    "immediate": [...],
    "short_term": [...],
    "long_term": [...]
  }
}
```

### Task 1.3: Integrate Phase 5 Controls (2 hours)

**Source:** `run_phase5_control.py` (260 lines)

**Steps:**
1. Locate `phase5_control()` method (currently ~line 1501)
2. Replace stub implementation with logic from `run_phase5_control.py`:
   - Copy `establish_controls()` function body
   - Adapt to read Phase 4 output from `self.output_dir`
   - Keep all 5 control mechanisms (CTRL-001 through CTRL-005)
   - Keep monitoring plan (daily/weekly/monthly/quarterly)
   - Keep implementation roadmap (4 phases)
   - Keep success criteria
3. Test Phase 5 output
4. Compare with standalone runner output
5. Verify JSON structure matches

**Expected Output:**
```json
{
  "phase": "CONTROL",
  "timestamp": "...",
  "controls": [
    {
      "id": "CTRL-001",
      "name": "Code Quality Metrics Dashboard",
      "description": "...",
      "metrics": [...],
      "tools": [...],
      "automation": "..."
    },
    ...
  ],
  "monitoring_plan": {
    "daily": [...],
    "weekly": [...],
    "monthly": [...],
    "quarterly": [...]
  },
  "roadmap": {
    "phase_1": {...},
    "phase_2": {...},
    "phase_3": {...},
    "phase_4": {...}
  },
  "success_criteria": {
    "short_term": [...],
    "long_term": [...]
  }
}
```

### Task 1.4: Test Full Phase 3-5 Pipeline (1 hour)

**Steps:**
1. Run engine with Phases 3-5 only:
   ```bash
   python recursive_dmaic_engine_v2.py --phase3 --phase4 --phase5
   ```
2. Verify all outputs are generated
3. Compare with standalone runner outputs
4. Check for any missing data
5. Fix any discrepancies

**Success Criteria:**
- ✅ Phase 3 output includes all 4 complexity categories
- ✅ Phase 3 output includes all 6 issue types
- ✅ Phase 3 output includes all 4 improvement opportunities
- ✅ Phase 4 output includes action plans for all opportunities
- ✅ Phase 4 output includes priority-based recommendations
- ✅ Phase 5 output includes all 5 control mechanisms
- ✅ Phase 5 output includes monitoring plan with 4 frequencies
- ✅ Phase 5 output includes implementation roadmap
- ✅ Phase 5 output includes success criteria

---

## 📋 DAY 2: RUNTIME TRACKING & PATH BUG FIX

### Task 2.1: Integrate Runtime Dependency Tracker (3 hours)

**Source:** `runtime_dependency_tracker.py` (150 lines)

**Steps:**
1. Add import at top of `recursive_dmaic_engine_v2.py`:
   ```python
   from runtime_dependency_tracker import get_tracker
   ```
2. Locate Phase 2B execution loop (around line 1200)
3. Find where each file is executed
4. Wrap execution with tracker:
   ```python
   def execute_file_with_tracking(self, file_path):
       tracker = get_tracker()
       tracker.start_tracking()
       
       try:
           result = self.execute_python_file(file_path)
           result['runtime_dependencies'] = tracker.get_dependencies()
           return result
       finally:
           tracker.stop_tracking()
           tracker.clear()
   ```
5. Update Phase 2B to use `execute_file_with_tracking()`
6. Test runtime dependency capture
7. Verify dependencies are saved in Phase 2B results

**Expected Phase 2B Output Addition:**
```json
{
  "file_path": "example.py",
  "success": true,
  "runtime_dependencies": {
    "file_io": [
      {"operation": "read", "path": "data.txt", "timestamp": "..."},
      {"operation": "write", "path": "output.txt", "timestamp": "..."}
    ],
    "dynamic_imports": [
      {"module": "pandas", "timestamp": "..."}
    ],
    "env_vars": [
      {"name": "HOME", "timestamp": "..."}
    ],
    "db_connections": [],
    "api_calls": []
  }
}
```

### Task 2.2: Merge Runtime Dependencies into Phase 3 (2 hours)

**Steps:**
1. In Phase 3 analysis, read Phase 2B results
2. Extract runtime dependencies for each file
3. Add dependency graph generation:
   ```python
   def build_dependency_graph(phase2b_results):
       graph = {}
       for result in phase2b_results:
           file_path = result['file_path']
           deps = result.get('runtime_dependencies', {})
           graph[file_path] = {
               'reads': [f['path'] for f in deps.get('file_io', []) if f['operation'] == 'read'],
               'writes': [f['path'] for f in deps.get('file_io', []) if f['operation'] == 'write'],
               'imports': [m['module'] for m in deps.get('dynamic_imports', [])],
               'env_vars': [e['name'] for e in deps.get('env_vars', [])],
           }
       return graph
   ```
4. Add dependency graph to Phase 3 output
5. Test dependency graph generation

**Expected Phase 3 Output Addition:**
```json
{
  "phase": "ANALYZE",
  "dependency_graph": {
    "example.py": {
      "reads": ["data.txt", "config.json"],
      "writes": ["output.txt"],
      "imports": ["pandas", "numpy"],
      "env_vars": ["HOME", "PATH"]
    },
    ...
  }
}
```

### Task 2.3: Fix Phase 2B Path Doubling Bug (2 hours)

**Steps:**
1. Locate `execute_python_file()` method (around line 650-750)
2. Add debug logging:
   ```python
   print(f"[DEBUG] Executing file: {file_path}")
   print(f"[DEBUG] Resolved path: {resolved_path}")
   print(f"[DEBUG] Working directory: {os.getcwd()}")
   ```
3. Run Phase 2B with debug logging on a few files
4. Identify where path doubling occurs
5. Common issues to check:
   - Path joining with already-absolute paths
   - Incorrect use of `os.path.join()` with absolute paths
   - Working directory changes not being reverted
6. Fix the path construction logic
7. Remove debug logging
8. Test with sample files
9. Verify paths are correct

**Example Fix:**
```python
# BEFORE (causes doubling):
file_path = os.path.join(self.workspace_root, file_path)
file_path = os.path.join(self.workspace_root, file_path)  # Accidental double join

# AFTER (correct):
if not os.path.isabs(file_path):
    file_path = os.path.join(self.workspace_root, file_path)
file_path = os.path.abspath(file_path)
```

### Task 2.4: Re-run Phase 2B with Fixed Paths (1 hour)

**Steps:**
1. Clear old Phase 2B results:
   ```bash
   rm DMAIC_V2_OUTPUT/phase2b_execution_results.jsonl
   ```
2. Re-run Phase 2B:
   ```bash
   python recursive_dmaic_engine_v2.py --phase2b
   ```
3. Monitor execution
4. Check success rate
5. Verify path errors are reduced

**Success Criteria:**
- ✅ Path errors reduced from 99.7% to < 5%
- ✅ Successful execution rate > 10%
- ✅ Runtime dependencies captured for successful executions

---

## 📋 DAY 3: FULL INTEGRATION TEST & DOCUMENTATION

### Task 3.1: Full DMAIC Cycle Test (2 hours)

**Steps:**
1. Run complete DMAIC cycle:
   ```bash
   python recursive_dmaic_engine_v2.py --all --execute
   ```
2. Monitor all phases
3. Verify outputs for each phase
4. Check file sizes and line counts
5. Compare with previous runs
6. Identify any issues

**Expected Outputs:**
- `phase1_define.json` (~6 MB)
- `phase2_measure.jsonl` (~33 MB)
- `phase2a_clean_files.json` (~700 KB)
- `phase2b_execution_results.jsonl` (~4 MB)
- `phase3_analyze.json` (~500 KB) ← Should be much larger now
- `phase4_improve.json` (~100 KB) ← Should be much larger now
- `phase5_control.json` (~50 KB) ← Should be much larger now

### Task 3.2: Compare with Standalone Runners (1 hour)

**Steps:**
1. Run standalone Phase 3:
   ```bash
   python run_phase3_analyze.py
   ```
2. Compare `RECURSIVE_DMAIC_OUTPUT/phase3_analyze.json` with `DMAIC_V2_OUTPUT/phase3_analyze.json`
3. Verify all fields match
4. Run standalone Phase 4:
   ```bash
   python run_phase4_improve.py
   ```
5. Compare outputs
6. Run standalone Phase 5:
   ```bash
   python run_phase5_control.py
   ```
7. Compare outputs
8. Document any differences

**Success Criteria:**
- ✅ All complexity categories match
- ✅ All issue counts match
- ✅ All improvement opportunities match
- ✅ All action plans match
- ✅ All control mechanisms match
- ✅ All monitoring plans match

### Task 3.3: Generate Analysis Dashboard (1 hour)

**Steps:**
1. Run analysis dashboard:
   ```bash
   python create_analysis_dashboard.py
   ```
2. Review dashboard output
3. Verify all metrics are present
4. Check for any anomalies
5. Update dashboard if needed

### Task 3.4: Update Documentation (2 hours)

**Steps:**
1. Update `DMAIC_V2.2_EXECUTION_STATUS.md`:
   - Mark Phase 3-5 integration as complete
   - Update Phase 2B status with new success rate
   - Add runtime dependency tracking status
2. Update `DMAIC_V2.2_KNOWLEDGE_RECONCILIATION.md`:
   - Document all integrated knowledge sources
   - Verify no knowledge dilution
   - List all preserved features
3. Create `DMAIC_V2.2_INTEGRATION_COMPLETE.md`:
   - Summary of all changes
   - List of integrated files
   - Before/after comparison
   - Success metrics
4. Update `DMAIC_V2.2_COMPREHENSIVE_ANALYSIS.md`:
   - Add new Phase 3-5 outputs
   - Update metrics
   - Add runtime dependency analysis

### Task 3.5: Final Verification (2 hours)

**Steps:**
1. Review all documentation
2. Check all code changes
3. Run full DMAIC cycle one more time
4. Verify all outputs
5. Create backup of working engine:
   ```bash
   cp recursive_dmaic_engine_v2.py recursive_dmaic_engine_v2_integrated.py
   ```
6. Commit changes (if using git):
   ```bash
   git add .
   git commit -m "Integrate Phase 3-5 enhancements, runtime tracking, and fix Phase 2B path bug"
   ```

---

## ✅ FINAL SUCCESS CRITERIA

### Code Integration
- ✅ Phase 3 logic from `run_phase3_analyze.py` fully integrated
- ✅ Phase 4 logic from `run_phase4_improve.py` fully integrated
- ✅ Phase 5 logic from `run_phase5_control.py` fully integrated
- ✅ Runtime tracker from `runtime_dependency_tracker.py` integrated
- ✅ Phase 2B path bug fixed

### Output Quality
- ✅ Phase 3 output includes all 4 complexity categories
- ✅ Phase 3 output includes all 6 issue types
- ✅ Phase 3 output includes all 4 improvement opportunities
- ✅ Phase 3 output includes dependency graph
- ✅ Phase 4 output includes action plans for all opportunities
- ✅ Phase 4 output includes priority-based recommendations
- ✅ Phase 5 output includes all 5 control mechanisms
- ✅ Phase 5 output includes monitoring plan
- ✅ Phase 5 output includes implementation roadmap
- ✅ Phase 5 output includes success criteria

### Execution Quality
- ✅ Phase 2B path errors < 5%
- ✅ Phase 2B success rate > 10%
- ✅ Runtime dependencies captured for all successful executions
- ✅ Full DMAIC cycle completes without errors

### Documentation Quality
- ✅ All changes documented
- ✅ All knowledge sources referenced
- ✅ No knowledge dilution
- ✅ Integration complete document created

---

## 📊 PROGRESS TRACKING

| Task | Estimated Time | Status | Notes |
|------|---------------|--------|-------|
| **DAY 1** | **8 hours** | ⏳ Pending | |
| 1.1 Integrate Phase 3 | 3 hours | ⏳ Pending | |
| 1.2 Integrate Phase 4 | 2 hours | ⏳ Pending | |
| 1.3 Integrate Phase 5 | 2 hours | ⏳ Pending | |
| 1.4 Test Phase 3-5 | 1 hour | ⏳ Pending | |
| **DAY 2** | **8 hours** | ⏳ Pending | |
| 2.1 Integrate Runtime Tracker | 3 hours | ⏳ Pending | |
| 2.2 Merge Runtime Deps | 2 hours | ⏳ Pending | |
| 2.3 Fix Path Bug | 2 hours | ⏳ Pending | |
| 2.4 Re-run Phase 2B | 1 hour | ⏳ Pending | |
| **DAY 3** | **8 hours** | ⏳ Pending | |
| 3.1 Full Cycle Test | 2 hours | ⏳ Pending | |
| 3.2 Compare Outputs | 1 hour | ⏳ Pending | |
| 3.3 Generate Dashboard | 1 hour | ⏳ Pending | |
| 3.4 Update Documentation | 2 hours | ⏳ Pending | |
| 3.5 Final Verification | 2 hours | ⏳ Pending | |
| **TOTAL** | **24 hours** | ⏳ Pending | **3 days** |

---

## 🚀 START HERE

1. **Read this document completely**
2. **Review `DMAIC_V2.2_COMPREHENSIVE_INTEGRATION_REQUIREMENTS.md`**
3. **Backup current engine**
4. **Start with Task 1.1: Integrate Phase 3**
5. **Follow the plan step by step**
6. **Test thoroughly at each step**
7. **Document all changes**
8. **Verify no knowledge loss**

---

**Document Created:** 2025-11-08 17:05 UTC  
**Status:** READY TO EXECUTE  
**Priority:** P0 - CRITICAL  
**Estimated Effort:** 3 days (24 hours)  
**Success Metric:** 100% knowledge preservation, 0% dilution  
**Next Action:** Start Task 1.1 - Integrate Phase 3 Analysis
