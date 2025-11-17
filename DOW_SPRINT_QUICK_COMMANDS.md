# DOW & SPRINT RUNNER - QUICK COMMAND REFERENCE

**Quick reference for running DOW and Sprint automation**

---

## 🚀 QUICK START COMMANDS

### 1. DOW CI/CD Integration Runner
```bash
cd ABACUS-v031
python run_cicd_integration.py
```
**Purpose:** Full DMAIC pipeline with Git integration and quality gates

---

### 2. DOW Phase 4+ Runner (Artifact Ranking)
```bash
cd ABACUS-v031
python run_phase4_phase5.py
```
**Purpose:** Advanced artifact ranking and improvement identification

---

### 3. Sprint Planner
```bash
# List available sprints
python runners/sprint_planner.py

# View specific sprint details
python runners/sprint_planner.py 5
```
**Purpose:** Sprint planning and task management

---

### 4. Full DMAIC Pipeline
```bash
cd ABACUS-v031
python run_full_dmaic_pipeline.py
```
**Purpose:** Complete DMAIC cycle (Define → Measure → Analyze → Improve → Control)

---

### 5. Agent-Enhanced Pipeline V2
```bash
cd ABACUS-v031
python run_full_dmaic_pipeline_v2_with_agents.py
```
**Purpose:** Enhanced pipeline with agent orchestration and feedback loops

---

### 6. Sprint Execution via Orchestrator
```bash
python dmaic_v23_master_orchestrator.py --action run-sprint --sprint 5
```
**Purpose:** Execute specific sprint with DMAIC orchestration

---

## 📊 OUTPUT FILES

All runners generate outputs in `ABACUS-v031/`:

| File | Size | Description |
|------|------|-------------|
| `canonical.index.json` | ~112 KB | Canonical artifact index |
| `canonical.index.yaml` | - | YAML version of index |
| `artifact_rankings.json` | ~220 KB | Detailed artifact rankings |
| `ranking_report.txt` | ~3 KB | Human-readable ranking report |
| `improvement_plan.txt` | ~5 KB | Prioritized improvement actions |
| `compliance_report.json` | ~2 KB | Standards compliance report |

---

## 🎯 COMMON WORKFLOWS

### Workflow 1: Initial Quality Assessment
```bash
cd ABACUS-v031
python run_cicd_integration.py
# Review: improvement_plan.txt
```

### Workflow 2: Detailed Artifact Analysis
```bash
cd ABACUS-v031
python run_phase4_phase5.py
# Review: ranking_report.txt
```

### Workflow 3: Sprint-Based Development
```bash
# 1. View sprint details
python runners/sprint_planner.py 5

# 2. Execute sprint
python dmaic_v23_master_orchestrator.py --action run-sprint --sprint 5

# 3. Run full pipeline
cd ABACUS-v031
python run_full_dmaic_pipeline.py
```

### Workflow 4: Continuous Improvement Iteration
```bash
# 1. Run CI/CD integration
cd ABACUS-v031
python run_cicd_integration.py

# 2. Review quality gates
cat improvement_plan.txt

# 3. Run agent-enhanced pipeline
python run_full_dmaic_pipeline_v2_with_agents.py

# 4. Validate improvements
python run_phase4_phase5.py
```

---

## 🔍 QUALITY GATES

### Gate 1: Average Score ≥ 0.5
- **Current:** 0.299
- **Target:** 0.500
- **Status:** ❌ FAILED

### Gate 2: Top 10% Score ≥ 0.4
- **Current:** 0.592
- **Target:** 0.400
- **Status:** ✅ PASSED

### Gate 3: Rank 5 Artifacts < 30%
- **Current:** 130/136 (95.6%)
- **Target:** <30%
- **Status:** ❌ FAILED

### Gate 4: High-Priority Actions < 2x Artifacts
- **Current:** 108
- **Target:** <272
- **Status:** ✅ PASSED

---

## 📈 METRICS TRACKING

### Current State (Iteration 1)
- **Total Artifacts:** 136
- **Average Score:** 0.299
- **Top 10 Average:** 0.603
- **Bottom 10 Average:** 0.200
- **High-Priority Actions:** 108
- **Quality Gate Pass Rate:** 50% (2/4)

### Target State (Iteration 3)
- **Average Score:** 0.500+
- **Top 10 Average:** 0.700+
- **Bottom 10 Average:** 0.300+
- **High-Priority Actions:** <100
- **Quality Gate Pass Rate:** 100% (4/4)

---

## 🛠️ TROUBLESHOOTING

### Issue: Quality gates failing
**Solution:**
```bash
# Review improvement plan
cat ABACUS-v031/improvement_plan.txt

# Run with execution flag (if available)
cd ABACUS-v031
python run_full_dmaic_pipeline_v2_with_agents.py --execute
```

### Issue: Low artifact scores
**Solution:**
```bash
# Identify low-scoring artifacts
cat ABACUS-v031/ranking_report.txt | grep "0.200"

# Focus on bottom 10 artifacts for improvement
```

### Issue: Git integration not working
**Solution:**
```bash
# Ensure you're in a git repository
git status

# Check git configuration
git config --list
```

---

## 📁 DIRECTORY STRUCTURE

```
Master_Input/
├── ABACUS-v031/                    # DOW Engine directory
│   ├── run_cicd_integration.py     # CI/CD runner
│   ├── run_phase4_phase5.py        # Phase 4+ runner
│   ├── run_full_dmaic_pipeline.py  # Full pipeline
│   ├── run_full_dmaic_pipeline_v2_with_agents.py  # Agent-enhanced
│   ├── dow_engine/                 # Core engine
│   ├── canonical.index.json        # Output: Canonical index
│   ├── artifact_rankings.json      # Output: Rankings
│   ├── ranking_report.txt          # Output: Report
│   └── improvement_plan.txt        # Output: Improvements
├── DOW/
│   └── sprints.yaml                # Sprint configuration
├── runners/
│   └── sprint_planner.py           # Sprint planner
├── dmaic_v23_master_orchestrator.py  # DMAIC orchestrator
└── DOW_SPRINT_DEPLOYMENT_SUMMARY.md  # Deployment summary
```

---

## 🔄 ITERATION CYCLE

### Step 1: Assess Current State
```bash
cd ABACUS-v031
python run_cicd_integration.py
```

### Step 2: Analyze Rankings
```bash
python run_phase4_phase5.py
cat ranking_report.txt
```

### Step 3: Plan Sprint
```bash
cd ..
python runners/sprint_planner.py 5
```

### Step 4: Execute Improvements
```bash
cd ABACUS-v031
python run_full_dmaic_pipeline_v2_with_agents.py
```

### Step 5: Validate Results
```bash
python run_cicd_integration.py
# Check if quality gates improved
```

### Step 6: Commit Changes
```bash
git add .
git commit -m "[DOW] Iteration N - Score: X.XXX, Actions: XXX"
git push
```

---

## 📞 SUPPORT

### Documentation
- `CI_CD_AUTOMATION_README.md` - Full CI/CD guide
- `DOW_SPRINT_DEPLOYMENT_SUMMARY.md` - Deployment details
- `ABACUS-v031/DOW_QUICKSTART.md` - Quick start guide

### Key Configuration Files
- `ABACUS-v031/dow_engine_config.yaml` - DOW engine config
- `DOW/sprints.yaml` - Sprint definitions

---

## ✅ CHECKLIST FOR EACH ITERATION

- [ ] Run CI/CD integration runner
- [ ] Review quality gate results
- [ ] Analyze artifact rankings
- [ ] Review improvement plan
- [ ] Execute sprint tasks
- [ ] Run full DMAIC pipeline
- [ ] Validate quality improvements
- [ ] Commit changes to Git
- [ ] Update sprint documentation
- [ ] Plan next iteration

---

*Last Updated: 2025-11-16*  
*Version: 1.0*  
*Status: OPERATIONAL*
