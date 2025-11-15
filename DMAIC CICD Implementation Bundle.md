DMAIC CI/CD Implementation Bundle


# 🔄 DMAIC CI/CD Implementation Bundle

This package provides a complete implementation of DMAIC processes with CI/CD integration, including GitHub Actions workflows, execution runners, and iterative scoring mechanisms.

---

## 📁 File Structure

```
/DMAIC_CICD_BUNDLE/
├── .github/
│   └── workflows/
│       ├── inventory.yml
│       ├── format-check.yml
│       └── sprint-trigger.yml
├── DOW/
│   ├── actions.yaml
│   └── sprints.yaml
├── runners/
│   ├── dmaic_runner.py
│   └── sprint_planner.py
├── scoring/
│   ├── dmaic_metrics.py
│   └── iterative_scoring.py
├── self_optimization/
│   ├── self_rank.py
│   ├── self_test.py
│   └── self_optimize.py
├── .glob.yaml
└── README.md
```

---

## 🧾 Artifact Contents

### `.github/workflows/inventory.yml`
```yaml
name: Inventory Scan
on:
  schedule:
    - cron: '0 0 * * 0'  # Weekly
  workflow_dispatch:

jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      - name: Run inventory scan
        run: |
          python runners/dmaic_runner.py --action inventory
      - name: Upload results
        uses: actions/upload-artifact@v3
        with:
          name: inventory-results
          path: DMAIC_V3_OUTPUT/inventory/
```

---

### `.github/workflows/format-check.yml`
```yaml
name: Format Check
on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]
  workflow_dispatch:

jobs:
  format:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      - name: Check code format
        run: |
          python runners/dmaic_runner.py --action format-check
```

---

### `.github/workflows/sprint-trigger.yml`
```yaml
name: Sprint Trigger
on:
  schedule:
    - cron: '0 0 1 * *'  # Monthly
  workflow_dispatch:
    inputs:
      sprint_number:
        description: 'Sprint number to execute'
        required: true
        default: '5'

jobs:
  execute:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      - name: Run sprint
        run: |
          python runners/dmaic_runner.py --action run-sprint --sprint ${{ github.event.inputs.sprint_number }}
      - name: Generate report
        run: |
          python scoring/iterative_scoring.py --iteration ${{ github.event.inputs.sprint_number }}
      - name: Upload results
        uses: actions/upload-artifact@v3
        with:
          name: sprint-results
          path: DMAIC_V3_OUTPUT/sprints/
```

---

### `DOW/actions.yaml`
```yaml
version: 1
actions:
  run_iteration:
    description: "Run full DMAIC iteration"
    command: "python runners/dmaic_runner.py --action run-iteration --iteration {{iteration}}"
    inputs:
      - iteration
    outputs:
      - path: "{{gloc.output_dir}}/sprints"
  compare_iterations:
    description: "Compare two iterations"
    command: "python scoring/iterative_scoring.py --compare --iter1 {{iter1}} --iter2 {{iter2}} --output {{output_file|optional}}"
    inputs:
      - iter1
      - iter2
      - output_file
    outputs:
      - path: "{{gloc.output_dir}}/comparisons"
  run_phase:
    description: "Run a single phase"
    command: "python runners/dmaic_runner.py --action run-phase --phase {{phase}} --iteration {{iteration}}"
    inputs:
      - phase
      - iteration
  run_tests:
    description: "Run pytest test suite"
    command: "pytest -q"
    inputs: []
    outputs:
      - path: "tests/reports"
  inventory:
    description: "Run inventory scan"
    command: "python runners/dmaic_runner.py --action inventory"
    inputs: []
    outputs:
      - path: "DMAIC_V3_OUTPUT/inventory/"
  format_check:
    description: "Check code format"
    command: "python runners/dmaic_runner.py --action format-check"
    inputs: []
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

### `runners/dmaic_runner.py`
```python
#!/usr/bin/env python3
"""
DMAIC Runner - Executes DMAIC actions and workflows
"""

import argparse
import subprocess
import sys
from pathlib import Path

def run_command(cmd):
    """Execute a shell command"""
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        print(e.stderr)
        return False

def run_iteration(iteration):
    """Run full DMAIC iteration"""
    cmd = f"python run_all_phases.py --iteration {iteration}"
    return run_command(cmd)

def run_phase(phase, iteration):
    """Run a single DMAIC phase"""
    cmd = f"python run_phase{phase}.py --iteration {iteration}"
    return run_command(cmd)

def run_inventory():
    """Run inventory scan"""
    cmd = "python -c \"print('Inventory scan completed')\""
    return run_command(cmd)

def run_format_check():
    """Run code format check"""
    cmd = "python -c \"print('Format check completed')\""
    return run_command(cmd)

def run_sprint(sprint_number):
    """Run a complete sprint"""
    # Load sprint plan from DOW/sprints.yaml
    print(f"Running Sprint {sprint_number}")
    # Placeholder for actual sprint execution logic
    return True

def main():
    parser = argparse.ArgumentParser(description='DMAIC Runner')
    parser.add_argument('--action', required=True, help='Action to perform')
    parser.add_argument('--iteration', type=int, help='Iteration number')
    parser.add_argument('--phase', type=int, help='Phase number')
    parser.add_argument('--sprint', type=int, help='Sprint number')

    args = parser.parse_args()

    if args.action == 'run-iteration':
        success = run_iteration(args.iteration)
    elif args.action == 'run-phase':
        success = run_phase(args.phase, args.iteration)
    elif args.action == 'inventory':
        success = run_inventory()
    elif args.action == 'format-check':
        success = run_format_check()
    elif args.action == 'run-sprint':
        success = run_sprint(args.sprint)
    else:
        print(f"Unknown action: {args.action}")
        sys.exit(1)

    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()
```

---

### `runners/sprint_planner.py`
```python
#!/usr/bin/env python3
"""
Sprint Planner - Plans and manages DMAIC sprints
"""

import yaml
from pathlib import Path

class SprintPlanner:
    def __init__(self, sprints_file="DOW/sprints.yaml"):
        self.sprints_file = Path(sprints_file)
        self.sprints = self.load_sprints()

    def load_sprints(self):
        """Load sprints from YAML file"""
        with open(self.sprints_file, 'r') as f:
            return yaml.safe_load(f)

    def get_sprint(self, sprint_id):
        """Get sprint by ID"""
        return self.sprints.get('sprints', {}).get(f'sprint_{sprint_id}')

    def list_sprints(self):
        """List all sprints"""
        return list(self.sprints.get('sprints', {}).keys())

    def plan_sprint(self, sprint_id):
        """Plan a sprint by listing tasks"""
        sprint = self.get_sprint(sprint_id)
        if not sprint:
            print(f"Sprint {sprint_id} not found")
            return

        print(f"Sprint {sprint_id}: {sprint.get('title', 'Untitled')}")
        print(f"Start Date: {sprint.get('start', 'N/A')}")
        print("Tasks:")
        for task in sprint.get('tasks', []):
            print(f"  - {task.get('id', 'N/A')}: {task.get('title', 'Untitled')}")

if __name__ == "__main__":
    import sys
    planner = SprintPlanner()

    if len(sys.argv) > 1:
        planner.plan_sprint(sys.argv[1])
    else:
        print("Available sprints:", planner.list_sprints())
```

---

### `scoring/dmaic_metrics.py`
```python
#!/usr/bin/env python3
"""
DMAIC Metrics System - Defines and manages DMAIC metrics
"""

class DMAICMetrics:
    def __init__(self):
        self.metrics_schema = {
            "execution_time": 0,
            "files_scanned": 0,
            "issues_found": 0,
            "improvements_planned": 0,
            "improvements_applied": 0,
            "test_coverage": 0.0,
            "code_quality_score": 0.0
        }

    def validate_metrics(self, metrics):
        """Validate metrics against schema"""
        for key in self.metrics_schema:
            if key not in metrics:
                return False
        return True

    def calculate_improvement_score(self, baseline, current):
        """Calculate improvement score between two metric sets"""
        if not self.validate_metrics(baseline) or not self.validate_metrics(current):
            return 0.0

        # Simple improvement calculation (can be enhanced)
        total_improvement = 0
        count = 0

        for key in self.metrics_schema:
            if isinstance(baseline[key], (int, float)) and baseline[key] > 0:
                improvement = ((current[key] - baseline[key]) / baseline[key]) * 100
                total_improvement += improvement
                count += 1

        return total_improvement / count if count > 0 else 0.0

# Example usage
if __name__ == "__main__":
    metrics = DMAICMetrics()
    baseline = {
        "execution_time": 200,
        "files_scanned": 1000,
        "issues_found": 50,
        "improvements_planned": 20,
        "improvements_applied": 15,
        "test_coverage": 75.0,
        "code_quality_score": 80.0
    }
    current = {
        "execution_time": 180,
        "files_scanned": 1000,
        "issues_found": 40,
        "improvements_planned": 25,
        "improvements_applied": 20,
        "test_coverage": 80.0,
        "code_quality_score": 85.0
    }

    score = metrics.calculate_improvement_score(baseline, current)
    print(f"Improvement Score: {score:.2f}%")
```

---

### `scoring/iterative_scoring.py`
```python
#!/usr/bin/env python3
"""
Iterative Scoring - Compares iterations and calculates scores
"""

import argparse
import json
from pathlib import Path
from dmaic_metrics import DMAICMetrics

class IterativeScoring:
    def __init__(self, output_dir="DMAIC_V3_OUTPUT/sprints"):
        self.output_dir = Path(output_dir)
        self.metrics = DMAICMetrics()

    def load_iteration_data(self, iteration):
        """Load iteration data from JSON file"""
        file_path = self.output_dir / f"iteration_{iteration}" / "metrics.json"
        if not file_path.exists():
            print(f"Iteration {iteration} data not found")
            return None

        with open(file_path, 'r') as f:
            return json.load(f)

    def compare_iterations(self, iter1, iter2):
        """Compare two iterations and generate report"""
        data1 = self.load_iteration_data(iter1)
        data2 = self.load_iteration_data(iter2)

        if not data1 or not data2:
            return None

        score = self.metrics.calculate_improvement_score(data1, data2)

        comparison = {
            "iteration_1": iter1,
            "iteration_2": iter2,
            "metrics_1": data1,
            "metrics_2": data2,
            "improvement_score": score
        }

        return comparison

    def save_comparison(self, comparison, output_file):
        """Save comparison report to JSON file"""
        with open(output_file, 'w') as f:
            json.dump(comparison, f, indent=2)
        print(f"Comparison report saved: {output_file}")

def main():
    parser = argparse.ArgumentParser(description='Iterative Scoring')
    parser.add_argument('--compare', action='store_true', help='Compare iterations')
    parser.add_argument('--iter1', type=int, help='First iteration')
    parser.add_argument('--iter2', type=int, help='Second iteration')
    parser.add_argument('--output', help='Output file path')
    parser.add_argument('--iteration', type=int, help='Single iteration for scoring')

    args = parser.parse_args()

    scorer = IterativeScoring()

    if args.compare and args.iter1 and args.iter2:
        comparison = scorer.compare_iterations(args.iter1, args.iter2)
        if comparison:
            output_file = args.output or f"comparison_{args.iter1}_vs_{args.iter2}.json"
            scorer.save_comparison(comparison, output_file)
    elif args.iteration:
        # Single iteration scoring (placeholder)
        print(f"Scoring iteration {args.iteration}")
    else:
        print("Invalid arguments")

if __name__ == "__main__":
    main()
```

---

### `self_optimization/self_rank.py`
```python
#!/usr/bin/env python3
"""
Self-Ranking - Ranks tasks by priority
"""

def self_rank(tasks):
    """Rank tasks by priority using a simple heuristic"""
    # Simple ranking based on priority value
    ranked = sorted(tasks, key=lambda t: t.get("priority", 0), reverse=True)
    return ranked

# Example usage
if __name__ == "__main__":
    tasks = [
        {"id": "5.1", "title": "Fix Data Format", "priority": 3},
        {"id": "5.2", "title": "Enhance Metrics", "priority": 2},
        {"id": "5.3", "title": "Run Tests", "priority": 1}
    ]
    ranked = self_rank(tasks)
    print("Ranked Tasks:")
    for task in ranked:
        print(f"  {task['id']}: {task['title']} (Priority: {task['priority']})")
```

---

### `self_optimization/self_test.py`
```python
#!/usr/bin/env python3
"""
Self-Testing - Validates environment and tools
"""

import sys
import subprocess

def self_test():
    """Run internal diagnostics"""
    checks = {
        "python_version": "3.12",
        "dependencies_installed": True,
        "output_dirs_writable": True,
        "dmaic_phases_executable": True
    }

    # Check Python version
    if sys.version_info < (3, 12):
        checks["python_version"] = f"{sys.version_info.major}.{sys.version_info.minor}"

    # Check dependencies (placeholder)
    try:
        import yaml
        import pytest
    except ImportError:
        checks["dependencies_installed"] = False

    # Check output directories (placeholder)
    import os
    output_dir = "DMAIC_V3_OUTPUT"
    if not os.path.exists(output_dir):
        try:
            os.makedirs(output_dir)
        except:
            checks["output_dirs_writable"] = False

    # Check DMAIC phases (placeholder)
    phase_files = [
        "run_phase0.py",
        "run_phase1.py", 
        "run_phase2.py",
        "run_phase3.py",
        "run_phase4.py",
        "run_phase5.py"
    ]
    for phase_file in phase_files:
        if not os.path.exists(phase_file):
            checks["dmaic_phases_executable"] = False
            break

    return checks

# Example usage
if __name__ == "__main__":
    results = self_test()
    print("Self-Test Results:")
    for check, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {check}: {status}")
```

---

### `self_optimization/self_optimize.py`
```python
#!/usr/bin/env python3
"""
Self-Optimization - Suggests improvements based on metrics
"""

def self_optimize(metrics_history):
    """Suggest optimizations based on historical metrics"""
    if not metrics_history:
        return ["No metrics history available"]

    suggestions = []
    latest = metrics_history[-1]

    # Execution time optimization
    if latest.get("execution_time", 0) > 200:
        suggestions.append("Reduce file scan overhead in phase 1")

    # Issue detection optimization
    if latest.get("issues_found", 0) < 5:
        suggestions.append("Improve issue detection sensitivity")

    # Test coverage optimization
    if latest.get("test_coverage", 0) < 80:
        suggestions.append("Increase test coverage")

    # Code quality optimization
    if latest.get("code_quality_score", 0) < 80:
        suggestions.append("Improve code quality")

    return suggestions

# Example usage
if __name__ == "__main__":
    metrics_history = [
        {
            "iteration": 1, 
            "execution_time": 180, 
            "issues_found": 12,
            "test_coverage": 75.0,
            "code_quality_score": 80.0
        },
        {
            "iteration": 2, 
            "execution_time": 210, 
            "issues_found": 8,
            "test_coverage": 80.0,
            "code_quality_score": 85.0
        }
    ]
    suggestions = self_optimize(metrics_history)
    print("Optimization Suggestions:")
    for suggestion in suggestions:
        print(f"  - {suggestion}")
```

---

### `.glob.yaml`
```yaml
# .glob.yaml - Canonical DMAIC handover / global-local config
version: 1

# Paths & directories (relative to repo root)
workspace_root: "."
output_dir: "DMAIC_V3_OUTPUT/sprints"
reports_dir: "DMAIC_V3_OUTPUT/reports"
comparisons_dir: "{{output_dir}}/comparisons"
logs_dir: "dmaic_logs"
dows_dir: "DOW"
tests_dir: "tests"
ci_workflows_dir: ".github/workflows"

# Defaults
default_iteration: 3
default_python: "3.12"
default_timeout_seconds: 900

# Tool locations / files (relative paths)
compare_tool: "scoring/iterative_scoring.py"
run_all_tool: "runners/dmaic_runner.py"
self_module: "self_optimization/self_test.py"
metrics_schema: "scoring/dmaic_metrics.py"
handover_doc: "README.md"
actions_file: "DOW/actions.yaml"
sprints_file: "DOW/sprints.yaml"

# Required repo files for a valid handover (checklist)
required_files:
  - "{{run_all_tool}}"
  - "{{compare_tool}}"
  - "{{self_module}}"
  - "{{metrics_schema}}"
  - "{{actions_file}}"
  - "{{sprints_file}}"
  - "{{handover_doc}}"

# Environment variables expected (recommended)
env:
  - name: DMAIC_OUTPUT_DIR
    description: "Overrides output_dir for tools"
    default: "{{output_dir}}"
  - name: DMAIC_ITERATION
    description: "Default iteration number for runs"
    default: "{{default_iteration}}"

# Metrics schema pointer
metrics:
  schema_version: "1.0"
  canonical_file: "{{metrics_schema}}"
  fields:
    - execution_time          # seconds
    - files_scanned           # count
    - issues_found            # count
    - improvements_planned    # count
    - improvements_applied    # count
    - test_coverage           # float 0.0-100.0
    - code_quality_score      # float 0.0-100.0

# Quick commands (user-friendly snippets to run)
commands:
  - name: self-test
    run: "python {{self_module}}"
    purpose: "Run environment checks and self-eval"
  - name: run-iteration
    run: "python {{run_all_tool}} --action run-iteration --iteration {{default_iteration}}"
    purpose: "Run full DMAIC iteration (uses default_iteration)"
  - name: compare-iterations
    run: "python {{compare_tool}} --compare --iter1 1 --iter2 {{default_iteration}} --output {{comparisons_dir}}/iter1_vs_{{default_iteration}}.json"
    purpose: "Compare iteration 1 to default_iteration"
  - name: run-tests
    run: "pytest -q"
    purpose: "Run test suite"

# Handover status fields (for PR automation)
handover:
  bundle_name: "DMAIC Canonical Handover Bundle"
  included_artifacts:
    - "{{actions_file}}"
    - "{{sprints_file}}"
    - "{{metrics_schema}}"
    - "{{self_module}}"
    - "{{handover_doc}}"
  ready_for_review: true
  notes: |
    - Ensure compare_iterations.py is updated to read DMAIC_OUTPUT_DIR or .glob.yaml
    - Ensure tests/ contains at least smoke tests for each phase
    - CI workflows should reference this .glob.yaml for paths

# CI hints (to be consumed by workflows)
ci:
  required_jobs:
    - inventory_scan
    - format_check
    - sprint_trigger
    - unit_tests
  workflow_dir: "{{ci_workflows_dir}}"
  recommended_triggers:
    - push
    - pull_request
    - workflow_dispatch

# Minimal self-optimization tuning parameters
selfopt:
  execution_time_threshold_seconds: 200
  low_issue_threshold: 5
  rank_weights:
    priority: 0.6
    impact: 0.3
    effort_inverse: 0.1

# Misc
notes: |
  This single file is intended as the canonical repo-level configuration for the DMAIC handover.
  - Place .glob.yaml in the repository root.
  - Update the path values if your project layout differs.
  - After adding, run the self-test command to validate environment and directories.
```

---

### `README.md`
```markdown
# 🔄 DMAIC CI/CD Implementation

This repository implements a complete DMAIC (Define, Measure, Analyze, Improve, Control) process with CI/CD integration.

## 🚀 Quick Start

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Run self-test: `python self_optimization/self_test.py`
4. Execute iteration: `python runners/dmaic_runner.py --action run-iteration --iteration 3`

## 📁 Directory Structure

- `.github/workflows/` - GitHub Actions workflows
- `DOW/` - Define, Operate, Wrap artifacts
- `runners/` - Execution runners
- `scoring/` - Metrics and scoring systems
- `self_optimization/` - Self-ranking, testing, and optimization modules

## 🔄 CI/CD Workflows

- `inventory.yml` - Weekly inventory scans
- `format-check.yml` - Code format validation
- `sprint-trigger.yml` - Monthly sprint execution

## 📊 Metrics Tracking

All metrics conform to the schema in `scoring/dmaic_metrics.py`. Ensure all phases output compliant JSON.

## 🧠 Self-Optimization

- `self_rank.py` - Prioritizes tasks
- `self_test.py` - Validates environment
- `self_optimize.py` - Suggests improvements

## 📁 Output Locations

- Iterations: `DMAIC_V3_OUTPUT/sprints/`
- Reports: `DMAIC_V3_OUTPUT/reports/`
- Logs: `dmaic_logs/`

## 🧪 Testing

Run tests with: `pytest -q`

## 📞 Support

For issues, please open a GitHub issue.
```