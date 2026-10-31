# DMAIC Sprint System - Quick Start Guide

## 🚀 Quick Start

### Running All Phases (Full DMAIC Cycle)

```bash
# Run all phases for Iteration 1
python run_all_phases.py

# Run all phases for Iteration 2
python run_all_phases.py --iteration 2
```

### Running Individual Phases

```bash
# Phase 3: Analyze
python run_phase3.py

# Phase 4: Improve
python run_phase4.py

# Phase 5: Control
python run_phase5.py
```

### Comparing Iterations

```bash
# Compare Iteration 1 vs Iteration 2
python compare_iterations.py --iter1 1 --iter2 2

# Save comparison to specific file
python compare_iterations.py --iter1 1 --iter2 2 --output comparison_report.json
```

---

## 📊 Available Tools

### 1. **run_all_phases.py** - Full Cycle Executor
Runs all 6 DMAIC phases sequentially with automatic error handling and reporting.

**Features:**
- ✅ Automatic phase handoff fixes
- ✅ Comprehensive error handling
- ✅ Real-time progress reporting
- ✅ JSON execution report generation
- ✅ Duration tracking per phase

**Usage:**
```bash
python run_all_phases.py [--iteration N]
```

**Output:**
- Console: Real-time execution status
- File: `full_cycle_report_YYYYMMDD_HHMMSS.json`

---

### 2. **compare_iterations.py** - Iteration Comparator
Compares metrics and improvements between different DMAIC iterations.

**Features:**
- ✅ Side-by-side metric comparison
- ✅ Percentage change calculations
- ✅ Improvement indicators
- ✅ JSON comparison report

**Usage:**
```bash
python compare_iterations.py --iter1 1 --iter2 2 [--output FILE]
```

**Output:**
- Console: Formatted comparison table
- File: `iteration_comparison_YYYYMMDD_HHMMSS.json`

---

### 3. **dmaic_progress_visualizer.py** - Progress Visualizer
Generates ASCII-based progress charts and visualizations.

**Usage:**
```bash
python dmaic_progress_visualizer.py
```

**Output:**
- Console: ASCII progress bars and charts
- Shows phase completion status and metrics

---

## 📁 Output Structure

```
DMAIC_V3_OUTPUT/
└── sprints/
    ├── iteration_1/
    │   ├── phase0_setup.json
    │   ├── phase1_define/
    │   │   └── phase1_define.json
    │   ├── phase2_measure/
    │   │   └── phase2_measure.json
    │   ├── phase2_metrics.json (handoff copy)
    │   ├── phase3_analysis.json
    │   ├── phase4_improvements.json
    │   ├── phase4_improve/
    │   │   └── phase4_improve.json (handoff copy)
    │   └── phase5_control/
    │       └── phase5_control.json
    ├── iteration_2/
    │   └── (same structure)
    ├── full_cycle_report_*.json
    └── iteration_comparison_*.json
```

---

## 🎯 Common Workflows

### Workflow 1: First Time Setup & Execution
```bash
# 1. Run complete DMAIC cycle (Iteration 1)
python run_all_phases.py --iteration 1

# 2. View progress
python dmaic_progress_visualizer.py

# 3. Check results
cat DMAIC_V3_OUTPUT/sprints/full_cycle_report_*.json
```

### Workflow 2: Continuous Improvement (Iteration 2)
```bash
# 1. Run Iteration 2 with improvements
python run_all_phases.py --iteration 2

# 2. Compare with Iteration 1
python compare_iterations.py --iter1 1 --iter2 2

# 3. Review improvements
cat DMAIC_V3_OUTPUT/sprints/iteration_comparison_*.json
```

### Workflow 3: Debugging Failed Phases
```bash
# 1. Run individual phase that failed
python run_phase3.py  # or run_phase4.py, run_phase5.py

# 2. Check phase output
cat DMAIC_V3_OUTPUT/sprints/iteration_1/phase3_analysis.json

# 3. Fix issues and re-run
python run_all_phases.py --iteration 1
```

---

## 🔧 Troubleshooting

### Issue: Phase handoff file not found
**Solution:** The unified runner automatically fixes handoff paths. If running individual phases, manually copy files:
```bash
# Fix Phase 2 -> Phase 3 handoff
cp DMAIC_V3_OUTPUT/sprints/iteration_1/phase2_measure/phase2_measure.json \
   DMAIC_V3_OUTPUT/sprints/iteration_1/phase2_metrics.json

# Fix Phase 4 -> Phase 5 handoff
mkdir -p DMAIC_V3_OUTPUT/sprints/iteration_1/phase4_improve
cp DMAIC_V3_OUTPUT/sprints/iteration_1/phase4_improvements.json \
   DMAIC_V3_OUTPUT/sprints/iteration_1/phase4_improve/phase4_improve.json
```

### Issue: Unicode encoding errors
**Solution:** The scripts include UTF-8 wrappers. If issues persist:
```bash
# Set environment variable (Windows)
set PYTHONIOENCODING=utf-8

# Set environment variable (Linux/Mac)
export PYTHONIOENCODING=utf-8
```

### Issue: Module not found errors
**Solution:** Ensure you're running from the workspace root:
```bash
cd /path/to/Master_Input
python run_all_phases.py
```

---

## 📈 Key Metrics Tracked

### Phase 0: Setup
- System checks passed/failed
- Environment validation status

### Phase 1: Define
- Total files scanned
- Documentation files count
- Code files count
- Scan duration

### Phase 2: Measure
- Metrics collected
- Baseline established
- Measurement duration

### Phase 3: Analyze
- Critical issues identified
- High priority issues
- Medium priority issues
- Total issues

### Phase 4: Improve
- Improvements planned
- Improvements applied
- Files modified

### Phase 5: Control
- Quality gates defined
- Validation checkpoints
- Control mechanisms established

---

## 🎓 Best Practices

1. **Always run from workspace root** - Ensures correct path resolution
2. **Use iteration numbers sequentially** - Maintains clear progression
3. **Review reports after each iteration** - Understand improvements
4. **Keep output directory clean** - Archive old iterations periodically
5. **Run comparison after each iteration** - Track continuous improvement

---

## 📚 Additional Resources

- **Full Completion Report**: `DMAIC_SPRINT_3_COMPLETION_REPORT.md`
- **Dashboard**: `DMAIC_SPRINT_DASHBOARD.md`
- **Final Summary**: `DMAIC_SPRINT_FINAL_SUMMARY.md`

---

## 🚦 Status Indicators

- ✅ **SUCCESS** - Phase completed successfully
- ❌ **FAILED** - Phase encountered errors
- ⚠️ **WARNING** - Phase completed with warnings
- 🔄 **RUNNING** - Phase currently executing
- ⏸️ **PENDING** - Phase not yet started

---

## 💡 Tips

1. **Monitor execution time** - Phases should complete within expected durations
2. **Check logs for warnings** - Even successful phases may have warnings
3. **Compare iterations regularly** - Track improvement trends
4. **Archive old iterations** - Keep workspace clean
5. **Document custom changes** - Maintain change log for modifications

---

**Last Updated**: 2025-01-13  
**DMAIC Version**: 3.3.0  
**Status**: Production Ready ✅
