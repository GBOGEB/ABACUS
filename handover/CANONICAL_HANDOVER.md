# Canonical Handover Index (DMAIC V3.3)

Essentials
- Engine full run: python -m DMAIC_V3.dmaic_v3_engine --mode full --iterations 1
- Phase 6 (optional): python -m DMAIC_V3.dmaic_v3_engine --mode single --phase phase6_knowledge
- Convergence: python scripts/check_convergence.py

Human-friendly
- Book (PDF): handover/DMAIC_V3_3_HANDOVER_BOOK.pdf
- Chat-ready brief: handover/HANDOVER_CHAT_READY.md
- Complete handover: DMAIC_V3_3_HANDOVER_COMPLETE.md

Automation bundles
- Manifest ZIP (+checksums): handover/DMAIC_V3_3_HANDOVER_GLOOB_MANIFEST.zip
- Universal ZIP/TAR: handover/DMAIC_V3_3_HANDOVER_ALL.zip, handover/DMAIC_V3_3_HANDOVER_ALL.tar.gz
- Manifest spec: handover/GLOOB.yaml
- Handover manifest

Quick use
- Windows (PowerShell): .\scripts\windows_run_all.ps1
- POSIX (bash): bash scripts/run_all_local.sh

Windows PDF build (direct)
```powershell
# Ensure you're in the repo root:
# PS> Set-Location "C:\Users\gbonthuy\OneDrive - Studiecentrum voor Kernenergie\Master_Input"
# Build the PDF (requires Pandoc + MiKTeX):
.\scripts\build_handover_book.ps1
# Or build HTML fallback if TeX not installed:
.\scripts\build_handover_book.ps1 -HtmlFallback
```

---

## CI/CD Implementation (V3.3.1)

### Overview
DMAIC V3.3 includes a comprehensive CI/CD system with:
- ✅ Phase 7: Action Tracking System
- ✅ Phase 8: TODO Management System
- ✅ Self-Test Framework (100% Pass Rate)
- ✅ GitHub Actions Workflows
- ✅ Full Pipeline Orchestrator (Phases 0-8)

### Quick Start

**Run Full Pipeline:**
```bash
python DMAIC_V3/full_pipeline_orchestrator.py --iteration 3
```

**Run Self-Test:**
```bash
python self_optimization/self_test.py
```

**Expected Output:**
```
Self-Test Results:
  python_version: ✅ PASS
  dependencies_installed: ✅ PASS
  output_dirs_writable: ✅ PASS
  dmaic_phases_executable: ✅ PASS
```

### Phase 7: Action Tracking

**Purpose:** Track all actions performed by agents across phases with local and global registries.

**Key Features:**
- Local action tracking per phase
- Global action registry (`DMAIC_V3_OUTPUT/global_action_registry.json`)
- Action statistics by phase, agent, status, and type
- Action-to-agent-artifact linkage
- Markdown report generation

**Outputs:**
- `DMAIC_V3_OUTPUT/iteration_*/phase7_action_tracking/phase7_action_tracking.json`
- `DMAIC_V3_OUTPUT/iteration_*/phase7_action_tracking/action_report.md`
- `DMAIC_V3_OUTPUT/global_action_registry.json`

**Usage:**
```python
from DMAIC_V3.phases.phase7_action_tracking import Phase7ActionTracking

phase7 = Phase7ActionTracking(iteration=3, workspace=".")
result = phase7.execute()
```

### Phase 8: TODO Management

**Purpose:** Manage TODOs across phases with priority ranking and completion tracking.

**Key Features:**
- Local TODO tracking per phase
- Global TODO registry (`DMAIC_V3_OUTPUT/global_todo_registry.json`)
- TODO parsing from YAML and Markdown files
- Priority-based ranking algorithm
- Completion rate tracking
- TODO-to-agent-artifact-action linkage
- Markdown report and YAML export

**Outputs:**
- `DMAIC_V3_OUTPUT/iteration_*/phase8_todo_management/phase8_todo_management.json`
- `DMAIC_V3_OUTPUT/iteration_*/phase8_todo_management/todo_report.md`
- `DMAIC_V3_OUTPUT/iteration_*/phase8_todo_management/prioritized_todos.yaml`
- `DMAIC_V3_OUTPUT/global_todo_registry.json`

**Usage:**
```python
from DMAIC_V3.phases.phase8_todo_management import Phase8TODOManagement

phase8 = Phase8TODOManagement(iteration=3, workspace=".")
result = phase8.execute()
```

### GitHub Actions Workflows

**Location:** `.github/workflows/`

**Main Workflows:**
1. **ci.yml** - Main CI pipeline
   - Bridge integration tests
   - Smoke tests
   - Lint and static analysis
   - Full deployment tests
   - Multi-version Python testing (3.11, 3.12)

2. **smoke-test.yml** - Quick validation
3. **recursive-build.yml** - Recursive improvements
4. **reports.yml** - Report generation

**Trigger:** Automatically runs on push/PR to any branch

### Self-Test Framework

**Location:** `self_optimization/self_test.py`

**Tests:**
- Python version check (3.11+)
- Dependencies installed
- Output directories writable
- DMAIC phases executable

**Run:**
```bash
python self_optimization/self_test.py
```

### Full Pipeline Orchestrator

**Location:** `DMAIC_V3/full_pipeline_orchestrator.py`

**Phases:**
- Phase 0: Initialization
- Phase 1: Define
- Phase 2: Measure
- Phase 3: Analyze
- Phase 4: Improve
- Phase 5: Control
- Phase 6: Knowledge
- Phase 7: Action Tracking ✅ NEW
- Phase 8: TODO Management ✅ NEW

**Options:**
```bash
# Run all phases
python DMAIC_V3/full_pipeline_orchestrator.py --iteration 3

# Quiet mode
python DMAIC_V3/full_pipeline_orchestrator.py --iteration 3 --quiet

# Disable git commits
python DMAIC_V3/full_pipeline_orchestrator.py --iteration 3 --no-git

# Disable idempotency
python DMAIC_V3/full_pipeline_orchestrator.py --iteration 3 --no-idempotency
```

### Deployment Summary

**Full documentation:** `DEPLOYMENT_SUMMARY.md`

**Status:** ✅ FULLY OPERATIONAL
- Self-test: 100% pass rate
- Phase 0: PASSED
- Phase 1: IN PROGRESS
- All components deployed and validated

### Troubleshooting

**Issue: Phase files not found**
- Solution: Ensure you're in the workspace root directory
- Check: `DMAIC_V3/phases/` directory exists

**Issue: Import errors**
- Solution: Install dependencies: `pip install -r DMAIC_V3/requirements.txt`
- Check: Python version 3.11+

**Issue: Permission errors**
- Solution: Ensure `DMAIC_V3_OUTPUT/` directory is writable
- Check: Run `python self_optimization/self_test.py`

### References

- **Deployment Summary:** `DEPLOYMENT_SUMMARY.md`
- **Phase 7 Source:** `DMAIC_V3/phases/phase7_action_tracking.py`
- **Phase 8 Source:** `DMAIC_V3/phases/phase8_todo_management.py`
- **Orchestrator:** `DMAIC_V3/full_pipeline_orchestrator.py`
- **CI/CD Config:** `.github/workflows/ci.yml`
- **Self-Test:** `self_optimization/self_test.py`
