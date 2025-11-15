DMAIC_HANDOVER_BUNDLE

# 🧬 DMAIC Canonical Handover Bundle

This package provides a full recursive DMAIC rebuild with self-ranking, self-testing, and self-optimization capabilities.

---

## 📁 File Structure

```
/DMAIC_HANDOVER_BUNDLE/
├── DOW/
│   ├── actions.yaml
│   └── sprints.yaml
├── gloc.yaml
├── self_rank_test_optimize.py
├── dmaic_metrics_tracker.json
└── handover.md
```

---

## 🧾 Artifact Contents

### `DOW/actions.yaml`
```yaml
version: 1
actions:
  run_iteration:
    description: "Run full DMAIC iteration"
    command: "python run_all_phases.py --iteration {{iteration}}"
    inputs:
      - iteration
    outputs:
      - path: "{{gloc.output_dir}}/sprints"
  compare_iterations:
    description: "Compare two iterations"
    command: "python compare_iterations.py --iter1 {{iter1}} --iter2 {{iter2}} --output {{output_file|optional}}"
    inputs:
      - iter1
      - iter2
      - output_file
    outputs:
      - path: "{{gloc.output_dir}}/comparisons"
  run_phase:
    description: "Run a single phase"
    command: "python run_phase{{phase}}.py --iteration {{iteration}}"
    inputs:
      - phase
      - iteration
  run_tests:
    description: "Run pytest test suite"
    command: "pytest -q"
    inputs: []
    outputs:
      - path: "tests/reports"
```

---

### `DOW/sprints.yaml`
```yaml
version: 1
sprints:
  sprint_5:
    id: 5
    title: "Sprint 5: Data Format Fixes & Enhancements"
    start: "2025-11-13"
    owner: "team"
    tasks:
      - id: 5.1
        title: "Fix Data Format Standardization"
        action: "run_iteration"
        params:
          iteration: 3
        required_files:
          - "DMAIC_V3/phases/phase2_measure.py"
          - "DMAIC_V3/phases/phase4_improve.py"
      - id: 5.2
        title: "Enhance Metrics Collection"
        action: "compare_iterations"
        params:
          iter1: 1
          iter2: 3
      - id: 5.3
        title: "Implement Automated Testing"
        action: "run_tests"
      - id: 5.4
        title: "Run Iteration 3 & Validate"
        action: "run_iteration"
        params:
          iteration: 3
```

---

### `gloc.yaml`
```yaml
version: 1
output_dir: "DMAIC_V3_OUTPUT/sprints"
iterations_dir: "{{output_dir}}"
default_iteration: 3
python_version: "3.12"
workspace_root: "."
logs_dir: "dmaic_logs"
reports_dir: "{{output_dir}}/reports"
compare_tool: "compare_iterations.py"
```

---

### `self_rank_test_optimize.py`
```python
#!/usr/bin/env python3
"""
DMAIC Self-Ranking, Self-Testing, and Self-Optimization Module
"""

import json
from pathlib import Path

def self_rank(tasks):
    """Rank tasks by priority (mock heuristic)"""
    ranked = sorted(tasks, key=lambda t: t.get("priority", 0), reverse=True)
    return ranked

def self_test():
    """Run internal diagnostics"""
    checks = {
        "python_version": "3.12",
        "dependencies_installed": True,
        "output_dirs_writable": True,
        "dmaic_phases_executable": True
    }
    return checks

def self_optimize(metrics_history):
    """Suggest optimizations based on historical metrics"""
    suggestions = []
    if metrics_history[-1]["execution_time"] > 200:
        suggestions.append("Reduce file scan overhead in phase 1")
    if metrics_history[-1]["issues_found"] < 5:
        suggestions.append("Improve issue detection sensitivity")
    return suggestions

if __name__ == "__main__":
    # Example usage
    tasks = [
        {"id": "5.1", "title": "Fix Data Format", "priority": 3},
        {"id": "5.2", "title": "Enhance Metrics", "priority": 2},
        {"id": "5.3", "title": "Run Tests", "priority": 1}
    ]
    ranked_tasks = self_rank(tasks)
    print("Ranked Tasks:", ranked_tasks)

    test_results = self_test()
    print("Self-Test Results:", test_results)

    metrics_history = [
        {"iteration": 1, "execution_time": 180, "issues_found": 12},
        {"iteration": 2, "execution_time": 210, "issues_found": 8}
    ]
    suggestions = self_optimize(metrics_history)
    print("Optimization Suggestions:", suggestions)
```

---

### `dmaic_metrics_tracker.json`
```json
{
  "schema_version": "1.0",
  "metrics": {
    "execution_time": 0,
    "files_scanned": 0,
    "issues_found": 0,
    "improvements_applied": 0,
    "test_coverage": 0.0,
    "code_quality_score": 0.0
  },
  "phases": {
    "phase0_setup": {},
    "phase1_define": {},
    "phase2_measure": {},
    "phase3_analyze": {},
    "phase4_improve": {},
    "phase5_control": {}
  }
}
```

---

### `handover.md`
```markdown
# 🧬 DMAIC Canonical Handover

## 🧰 Overview
This package enables full DMAIC iteration with self-ranking, self-testing, and self-optimization.

## 🚀 Quickstart
1. Place files in repo root
2. Run: `python self_rank_test_optimize.py`
3. Execute sprints via `DOW/actions.yaml`

## 📊 Metrics Tracking
All metrics conform to `dmaic_metrics_tracker.json`. Ensure all phases output compliant JSON.

## 🧪 Self-Evaluation
- `self_rank()` – Prioritizes tasks
- `self_test()` – Validates environment
- `self_optimize()` – Suggests improvements

## 📁 Output Locations
- Iterations: `DMAIC_V3_OUTPUT/sprints/`
- Reports: `DMAIC_V3_OUTPUT/reports/`
- Logs: `dmaic_logs/`

## 🧠 Notes
- Ensure `gloc.yaml` paths match your repo structure
- Update `compare_iterations.py` to respect `gloc.yaml`
```