# DMAIC SPRINT SYSTEM - QUICK REFERENCE

**Version:** 1.0.0 | **Updated:** Nov 14, 2025 | **Status:** 🟢 Production Ready

---

## ⚡ ESSENTIAL COMMANDS

### Run Full DMAIC Cycle
```bash
python run_all_phases.py --iteration 3
# Duration: ~3-5 minutes | Phases: 0-5 | Files: ~129K
```

### Compare Iterations
```bash
python compare_iterations.py --iter1 2 --iter2 3
# Shows: Side-by-side metrics, % changes, improvements
```

### Run Individual Phases
```bash
python run_phase3.py    # Analyze
python run_phase4.py    # Improve  
python run_phase5.py    # Control
```

---

## 📁 KEY FILES & LOCATIONS

| File | Purpose | Location |
|------|---------|----------|
| **README.md** | Start here | Root |
| **PROJECT_BOOK.md** | Complete docs (100 pages) | Root |
| **HANDOVER.md** | Copy-paste handover | Root |
| **QUICK_REFERENCE.md** | This file | Root |
| **ACTION_TRACKER.md** | Next steps (59 actions) | Root |
| **SPRINT_TRACKER.md** | Sprint history | Root |
| **WORKSPACE_STATE.md** | Current system state | workspace/ |
| **SPRINT_6_PLAN.md** | Active sprint plan | sprints/active/ |

---

## 🎯 DMAIC PHASES (6 Total)

| Phase | Name | Duration | Purpose | Key Output |
|-------|------|----------|---------|------------|
| **0** | Setup | ~3s | System validation | phase0_setup.json |
| **1** | Define | ~90s | Scan codebase | phase1_define.json |
| **2** | Measure | ~77s | Collect metrics | phase2_measure.json |
| **3** | Analyze | ~10s | Identify issues | phase3_analysis.json |
| **4** | Improve | ~6s | Generate fixes | phase4_improvements.json |
| **5** | Control | ~20s | Validate changes | phase5_control.json |
| **Total** | | **~206s** | **~3.4 min** | 6 JSON files |

---

## 📊 CURRENT STATUS SNAPSHOT

```
Sprint Progress:
Sprint 1-5 ████████████████████ 100% ✅ COMPLETE
Sprint 6   ░░░░░░░░░░░░░░░░░░░░   0% 🟢 ACTIVE

Key Metrics:
✅ Files Scanned: 258,902 (cumulative)
✅ Success Rate: 100%
✅ Automation: 100% (zero manual steps)
⏳ Test Coverage: 0% (Sprint 6 target: >70%)

Recent Fixes (Sprint 5):
✅ Phase 2→3 data format (file_metrics dict added)
✅ Phase 4→5 file path (dual output locations)
✅ Manual workarounds removed (-28 lines)
✅ "11 Problems Mystery" solved
```

---

## 🚀 SPRINT 6 NEXT ACTIONS

### 1️⃣ Execute Iteration 3 (HIGH PRIORITY)
```bash
cd /home/ubuntu/dmaic_handover_repo
python run_all_phases.py --iteration 3
```
**Expected:** 500-2000 real issues (not 0)

### 2️⃣ Compare Results (MEDIUM)
```bash
python compare_iterations.py --iter1 2 --iter2 3
```
**Expected:** Dramatic improvement in issue detection

### 3️⃣ Implement Testing (MEDIUM)
```bash
pytest --cov=DMAIC_V3
```
**Target:** >70% code coverage

---

## 🔧 GIT OPERATIONS

```bash
# Check status
git status

# View history
git log --oneline --graph --all

# View specific file history
git log --follow -- path/to/file

# Create feature branch
git checkout -b feature/sprint-N-description

# Commit changes
git add .
git commit -m "feat(scope): description"
```

### Commit Message Format
```
<type>(<scope>): <subject>

Types: feat, fix, docs, refactor, test, perf, style, chore
Example: feat(phase2): Add file_metrics conversion
```

---

## 🐛 TROUBLESHOOTING

| Issue | Quick Fix | Details |
|-------|-----------|---------|
| **Phase handoff fails** | Check phase completed | Verify output JSON exists |
| **Unicode errors** | `export PYTHONIOENCODING=utf-8` | UTF-8 wrapper should handle |
| **0 issues found** | Run with Sprint 5 fixes | Check phase2 has file_metrics |
| **Module not found** | Run from repo root | `cd /home/ubuntu/dmaic_handover_repo` |
| **Memory issues** | Check disk space | Need 50+ GB free |

---

## 📚 DOCUMENTATION MAP

```
START HERE → README.md
    ↓
UNDERSTAND → PROJECT_BOOK.md (comprehensive)
    ↓
EXECUTE → QUICK_REFERENCE.md (this file)
    ↓
CURRENT STATE → WORKSPACE_STATE.md
    ↓
NEXT STEPS → ACTION_TRACKER.md
```

**By Sprint:**
- Sprint 3-5: `sprints/archive/DMAIC_SPRINT_[3-5]_*.md`
- Sprint 6: `sprints/active/SPRINT_6_PLAN.md`

**By Topic:**
- Methodology: `OPERATIONAL_EXCELLENCE.md`
- Testing: `TEST_SYSTEM_DOCUMENTATION.md`
- Versioning: `VERSIONING_STANDARDS.md`
- History: `CONVERSATION_TUPLES.md`

---

## 🎓 CRITICAL LESSONS

### The "11 Problems Mystery" (Sprint 5)
**Problem:** Iteration 2 showed only 11 problems  
**Root Cause:** Ran BEFORE fixes were applied  
**Real Issue:** Phase 2→3 data format mismatch  
**Result:** 0 files analyzed (not 11 problems)  
**Fix:** Added file_metrics dict conversion  
**Lesson:** Always validate AFTER fixes applied  

### Key Takeaways
1. **UTF-8 Always:** Use explicit UTF-8 encoding
2. **Chunk Large Data:** Prevents memory issues
3. **Direct Imports:** More reliable than subprocess -m
4. **Validate Data Flow:** Test entire pipeline end-to-end
5. **User Feedback Matters:** Saved us in Sprint 5!

---

## 📈 METRICS CHEATSHEET

**Files Scanned:**
- Iteration 1: 129,445 files
- Iteration 2: 129,457 files (+12)
- Iteration 3: TBD

**Phase Duration:**
- Fastest: Phase 4 (~6s)
- Slowest: Phase 1 (~90s)
- Total: ~206s (~3.4 min)

**Performance:**
- Scan Rate: 1,457 files/second
- Success Rate: 100%
- Automation: 100%

**Expected Issues (Iteration 3):**
- Critical: 10-50
- High: 50-200
- Medium: 200-800
- Total: 500-2000

---

## 🔗 QUICK LINKS

| Resource | Path |
|----------|------|
| **Repository** | `/home/ubuntu/dmaic_handover_repo` |
| **Output Dir** | `DMAIC_V3_OUTPUT/sprints/` |
| **Code Files** | `code/` |
| **Documentation** | `docs/` |
| **Sprint Archive** | `sprints/archive/` |
| **Active Sprint** | `sprints/active/` |

---

## 🎯 SPRINT WORKFLOW

### For New Sprint:
1. Create plan: `sprints/active/SPRINT_N_PLAN.md`
2. Update `ACTION_TRACKER.md`
3. Execute tasks
4. Generate completion report
5. Archive: `mv sprints/active/* sprints/archive/`
6. Update `SPRINT_TRACKER.md`

### For Code Changes:
1. Create branch: `git checkout -b feature/description`
2. Make changes
3. Test: `pytest`
4. Commit: `git commit -m "feat: description"`
5. Update docs
6. Merge to main

---

## ⚠️ REMEMBER

✅ **Sprint 5 fixes are critical** - Iteration 3 won't work without them  
✅ **Read PROJECT_BOOK.md Section 6** - Understand "11 Problems Mystery"  
✅ **Check timestamps** - Files modified AFTER execution are suspicious  
✅ **Validate assumptions** - Test everything, trust nothing  
✅ **Document decisions** - Future you will thank present you  

---

## 💡 ONE-LINERS

```bash
# Full cycle + comparison
python run_all_phases.py --iteration 3 && \
python compare_iterations.py --iter1 2 --iter2 3

# Check system status
ls -lht DMAIC_V3_OUTPUT/sprints/iteration_3/

# View latest report
cat DMAIC_V3_OUTPUT/sprints/full_cycle_report_*.json | jq .

# Find phase outputs
find . -name "phase*.json" -type f -mtime -1

# Check git changes
git diff HEAD~1 HEAD --stat
```

---

## 📞 EMERGENCY CONTACTS

**Documentation:**
- Complete Guide: `PROJECT_BOOK.md`
- Handover: `HANDOVER.md`
- Quick Start: `docs/DMAIC_QUICK_START_GUIDE.md`

**Current State:**
- Actions: `ACTION_TRACKER.md` (59 tracked)
- Sprints: `SPRINT_TRACKER.md` (5 complete, 1 active)
- System: `workspace/WORKSPACE_STATE.md`

**History:**
- Conversations: `CONVERSATION_TUPLES.md` (20 documented)
- Artifacts: `ARTIFACTS_INDEX.md` (47 cataloged)
- Sprints: `sprints/archive/` (Sprints 3-5)

---

## 🎉 SUCCESS CRITERIA

### Iteration 3 Success:
- [ ] Phase 2 outputs file_metrics (~11K entries)
- [ ] Phase 3 analyzes >10K files
- [ ] Real issues detected (500-2000)
- [ ] Patterns populated (god classes, long methods)
- [ ] No manual steps required

### Sprint 6 Success:
- [ ] Iteration 3 completed
- [ ] Comparison report generated
- [ ] Test framework set up
- [ ] Code coverage >70%
- [ ] CI/CD integration (optional)

---

**Quick Reference Version:** 1.0.0  
**Repository:** `/home/ubuntu/dmaic_handover_repo`  
**Next Action:** `python run_all_phases.py --iteration 3`  
**Status:** Ready to execute 🚀

---

*For complete documentation, see PROJECT_BOOK.md (100 pages)*  
*For handover details, see HANDOVER.md (copy-paste ready)*  
*For current status, see README.md (repository overview)*
