# DMAIC TEST SYSTEM DOCUMENTATION

**Document Version:** 1.0  
**Last Updated:** November 14, 2025  
**Status:** Planning Phase (Implementation Sprint 6)

---

## 📋 PURPOSE

This document clearly separates and documents:
1. **Test System** - The testing environment, tools, and infrastructure
2. **System Under Test (SUT)** - The actual DMAIC code and workspace being tested

---

## 🔵 SYSTEM UNDER TEST (SUT)

### What is Being Tested

The System Under Test is the DMAIC V3 Sprint System, consisting of:

#### Core Components

**1. DMAIC Phase Scripts**
- Location: `DMAIC_V3/phases/`
- Components:
  - `phase0_setup.py` - System initialization and validation
  - `phase1_define.py` - Codebase scanning and categorization
  - `phase2_measure.py` - Metrics collection and baseline establishment
  - `phase3_analyze.py` - Issue identification and root cause analysis
  - `phase4_improve.py` - Improvement generation and application
  - `phase5_control.py` - Validation and control mechanisms

**2. Phase Executors**
- Location: `DMAIC_V3/`
- Components:
  - `run_all_phases.py` - Unified phase executor
  - `run_phase3.py` - Individual Phase 3 executor
  - `run_phase4.py` - Individual Phase 4 executor
  - `run_phase5.py` - Individual Phase 5 executor

**3. Supporting Tools**
- Location: `DMAIC_V3/` and `code/`
- Components:
  - `dmaic_sprint_runner.py` - Sprint orchestration
  - `compare_iterations.py` - Iteration comparison tool
  - `dmaic_progress_visualizer.py` - Progress visualization

**4. Configuration & Utilities**
- Location: `DMAIC_V3/`
- Components:
  - Configuration management
  - File I/O utilities
  - Logging utilities
  - Data validation utilities

#### Data Structures

**Phase Outputs:**
- Phase 0: System validation results (JSON)
- Phase 1: File scan results (JSON, ~7 MB)
- Phase 2: Metrics and measurements (JSON)
- Phase 3: Issue analysis (JSON)
- Phase 4: Improvement plan (JSON)
- Phase 5: Control mechanisms (JSON)

**Data Contracts:**
```json
{
  "phase2_output": {
    "file_metrics": {
      "file_path": {
        "complexity": number,
        "lines_of_code": number,
        "issues": array
      }
    },
    "measurements": array,
    "statistics": object
  }
}
```

#### Functional Requirements

**FR1: Phase Execution**
- Each phase must execute independently
- Phases must execute sequentially in order
- Each phase must produce expected output format
- Each phase must complete within reasonable time

**FR2: Data Handoff**
- Phase N output must be consumable by Phase N+1
- Data format must be consistent and validated
- Output files must be in expected locations
- Metadata must be preserved

**FR3: Error Handling**
- Graceful failure on errors
- Detailed error messages
- Logging of all errors
- Recovery mechanisms where possible

**FR4: Performance**
- Phase 1: Scan 129K files in < 120 seconds
- Phase 2: Analyze 11K files in < 90 seconds
- Phases 3-5: Complete in < 60 seconds total
- Total cycle: < 300 seconds

#### Non-Functional Requirements

**NFR1: Reliability**
- 100% success rate for valid inputs
- Consistent results across iterations
- No data loss or corruption

**NFR2: Maintainability**
- Well-documented code
- Modular design
- Clear separation of concerns
- Versioned components

**NFR3: Scalability**
- Handle codebases up to 500K files
- Memory-efficient processing (chunked)
- Configurable chunk sizes

**NFR4: Usability**
- Clear command-line interface
- Helpful error messages
- Progress indicators
- Comprehensive documentation

---

## 🧪 TEST SYSTEM

### Test Infrastructure

#### Test Framework: pytest

**Why pytest:**
- Powerful and flexible
- Great fixture support
- Excellent reporting
- Large ecosystem of plugins
- Industry standard for Python

**Version:** pytest >= 7.0.0

**Configuration:** `pytest.ini`
```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    -v
    --strict-markers
    --cov=DMAIC_V3
    --cov-report=html
    --cov-report=term-missing
    --cov-branch
markers =
    unit: Unit tests
    integration: Integration tests
    slow: Slow-running tests
    fast: Fast-running tests
```

#### Test Structure

```
tests/
├── __init__.py
├── conftest.py              # Shared fixtures
├── unit/                    # Unit tests
│   ├── test_phase0_setup.py
│   ├── test_phase1_define.py
│   ├── test_phase2_measure.py
│   ├── test_phase3_analyze.py
│   ├── test_phase4_improve.py
│   └── test_phase5_control.py
├── integration/             # Integration tests
│   ├── test_phase_handoffs.py
│   ├── test_full_cycle.py
│   └── test_multi_iteration.py
├── functional/              # Functional tests
│   ├── test_compare_iterations.py
│   └── test_sprint_runner.py
├── fixtures/                # Test data
│   ├── sample_codebase/
│   ├── expected_outputs/
│   └── test_data.json
└── utils/                   # Test utilities
    ├── helpers.py
    └── validators.py
```

#### Test Data

**Location:** `tests/fixtures/`

**Sample Codebase:**
- Small codebase (100 files) for fast tests
- Medium codebase (1,000 files) for integration tests
- Mock large codebase (10K+ files) for scalability tests

**Expected Outputs:**
- Golden files for each phase
- Known good outputs for comparison
- Edge case outputs

**Test Configuration:**
```json
{
  "test_workspace": "/tmp/dmaic_test_workspace",
  "sample_codebases": {
    "small": "tests/fixtures/sample_codebase/small/",
    "medium": "tests/fixtures/sample_codebase/medium/",
    "large": "tests/fixtures/sample_codebase/large/"
  },
  "expected_outputs": "tests/fixtures/expected_outputs/",
  "timeout_seconds": 60
}
```

---

## 🎯 TEST CATEGORIES

### 1. Unit Tests

**Purpose:** Test individual components in isolation

**Scope:**
- Individual phase functions
- Utility functions
- Data validation functions
- Configuration handling

**Example: test_phase2_measure.py**
```python
import pytest
from DMAIC_V3.phases.phase2_measure import Phase2Measure

class TestPhase2Measure:
    """Unit tests for Phase 2 (Measure)"""
    
    def test_file_metrics_conversion(self):
        """Test measurements to file_metrics conversion"""
        phase2 = Phase2Measure()
        measurements = [
            {
                'file_path': '/test/file1.py',
                'analysis': {'complexity': 5, 'loc': 100}
            },
            {
                'file_path': '/test/file2.py',
                'analysis': {'complexity': 10, 'loc': 200}
            }
        ]
        
        file_metrics = phase2.convert_to_file_metrics(measurements)
        
        assert len(file_metrics) == 2
        assert '/test/file1.py' in file_metrics
        assert file_metrics['/test/file1.py']['complexity'] == 5
    
    def test_dual_output_locations(self, tmp_path):
        """Test that Phase 2 saves to both locations"""
        phase2 = Phase2Measure(output_dir=tmp_path)
        result = {'file_metrics': {}, 'measurements': []}
        
        phase2.save_output(result, iteration=1)
        
        # Check both locations exist
        assert (tmp_path / "phase2_measure.json").exists()
        assert (tmp_path / "phase2_metrics.json").exists()
    
    def test_backward_compatibility(self):
        """Test that old format is still supported"""
        phase2 = Phase2Measure()
        old_format = {'measurements': [...]}
        
        # Should not crash, should add file_metrics
        result = phase2.ensure_backward_compatible(old_format)
        
        assert 'measurements' in result
        assert 'file_metrics' in result
```

**Coverage Target:** > 80% for unit tests

---

### 2. Integration Tests

**Purpose:** Test interactions between components

**Scope:**
- Phase handoffs (Phase N → Phase N+1)
- Data flow through multiple phases
- End-to-end scenarios
- Error propagation

**Example: test_phase_handoffs.py**
```python
import pytest
from pathlib import Path

class TestPhaseHandoffs:
    """Integration tests for phase handoffs"""
    
    @pytest.fixture
    def test_workspace(self, tmp_path):
        """Create test workspace"""
        workspace = tmp_path / "test_workspace"
        workspace.mkdir()
        return workspace
    
    def test_phase2_to_phase3_handoff(self, test_workspace):
        """Test Phase 2 → Phase 3 data handoff"""
        from DMAIC_V3.phases.phase2_measure import Phase2Measure
        from DMAIC_V3.phases.phase3_analyze import Phase3Analyze
        
        # Run Phase 2
        phase2 = Phase2Measure(output_dir=test_workspace)
        phase2_result = phase2.run(iteration=1)
        
        # Verify Phase 2 output
        assert 'file_metrics' in phase2_result
        assert len(phase2_result['file_metrics']) > 0
        
        # Run Phase 3 (should consume Phase 2 output)
        phase3 = Phase3Analyze(output_dir=test_workspace)
        phase3_result = phase3.run(iteration=1)
        
        # Verify Phase 3 received and processed data
        assert phase3_result['total_files_analyzed'] > 0
        assert phase3_result['total_files_analyzed'] == len(phase2_result['file_metrics'])
    
    def test_phase4_to_phase5_handoff(self, test_workspace):
        """Test Phase 4 → Phase 5 data handoff"""
        from DMAIC_V3.phases.phase4_improve import Phase4Improve
        from DMAIC_V3.phases.phase5_control import Phase5Control
        
        # Run Phase 4
        phase4 = Phase4Improve(output_dir=test_workspace)
        phase4_result = phase4.run(iteration=1)
        
        # Verify Phase 4 output locations
        assert (test_workspace / "phase4_improvements.json").exists()
        assert (test_workspace / "phase4_improve" / "phase4_improve.json").exists()
        
        # Run Phase 5 (should find Phase 4 output)
        phase5 = Phase5Control(output_dir=test_workspace)
        phase5_result = phase5.run(iteration=1)
        
        # Verify Phase 5 found and validated improvements
        assert 'quality_gates' in phase5_result
        assert phase5_result['quality_gates'] > 0
```

**Coverage Target:** > 70% for integration tests

---

### 3. Functional Tests

**Purpose:** Test complete user workflows

**Scope:**
- Full DMAIC cycle execution
- Multiple iteration execution
- Comparison tool functionality
- Sprint runner functionality

**Example: test_full_cycle.py**
```python
import pytest
import subprocess
import json
from pathlib import Path

class TestFullCycle:
    """Functional tests for complete DMAIC cycle"""
    
    @pytest.fixture
    def sample_workspace(self, tmp_path):
        """Create sample workspace with code"""
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        
        # Create sample Python files
        for i in range(10):
            (workspace / f"file_{i}.py").write_text(f"# Sample file {i}\nprint('hello')\n")
        
        return workspace
    
    @pytest.mark.slow
    def test_full_dmaic_cycle(self, sample_workspace):
        """Test complete DMAIC cycle execution"""
        # Run full cycle
        result = subprocess.run(
            ["python", "run_all_phases.py", "--iteration", "1"],
            cwd=str(sample_workspace.parent),
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0
        
        # Verify all phase outputs exist
        iteration_dir = sample_workspace.parent / "DMAIC_V3_OUTPUT" / "sprints" / "iteration_1"
        
        assert (iteration_dir / "phase0_setup.json").exists()
        assert (iteration_dir / "phase1_define" / "phase1_define.json").exists()
        assert (iteration_dir / "phase2_metrics.json").exists()
        assert (iteration_dir / "phase3_analysis.json").exists()
        assert (iteration_dir / "phase4_improvements.json").exists()
        assert (iteration_dir / "phase5_control" / "phase5_control.json").exists()
        
        # Verify data quality
        with open(iteration_dir / "phase2_metrics.json") as f:
            phase2_data = json.load(f)
            assert 'file_metrics' in phase2_data
            assert len(phase2_data['file_metrics']) > 0
        
        with open(iteration_dir / "phase3_analysis.json") as f:
            phase3_data = json.load(f)
            assert phase3_data['total_files_analyzed'] > 0
    
    @pytest.mark.slow
    def test_multi_iteration(self, sample_workspace):
        """Test multiple iteration execution"""
        # Run Iteration 1
        subprocess.run(["python", "run_all_phases.py", "--iteration", "1"], check=True)
        
        # Run Iteration 2
        subprocess.run(["python", "run_all_phases.py", "--iteration", "2"], check=True)
        
        # Run comparison
        result = subprocess.run(
            ["python", "compare_iterations.py", "--iter1", "1", "--iter2", "2"],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0
        assert "Iteration 1 vs Iteration 2" in result.stdout
```

**Coverage Target:** > 60% for functional tests

---

### 4. Performance Tests

**Purpose:** Validate system performance

**Scope:**
- Execution time within limits
- Memory usage within bounds
- Scalability to large codebases
- Concurrent execution

**Example: test_performance.py**
```python
import pytest
import time
import psutil
import os

class TestPerformance:
    """Performance tests for DMAIC system"""
    
    @pytest.mark.slow
    def test_phase1_scan_performance(self, large_codebase):
        """Test Phase 1 scan performance"""
        from DMAIC_V3.phases.phase1_define import Phase1Define
        
        phase1 = Phase1Define()
        
        start_time = time.time()
        start_memory = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024
        
        result = phase1.run(workspace=large_codebase)
        
        end_time = time.time()
        end_memory = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024
        
        duration = end_time - start_time
        memory_used = end_memory - start_memory
        
        # Performance assertions
        assert duration < 120  # Must complete in < 2 minutes
        assert memory_used < 500  # Must use < 500 MB
        assert result['total_files'] > 100000  # Should scan large codebase
        
        files_per_second = result['total_files'] / duration
        assert files_per_second > 1000  # Must scan > 1000 files/sec
    
    def test_memory_efficiency_chunked_processing(self):
        """Test that chunked processing prevents memory overflow"""
        from DMAIC_V3.phases.phase1_define import Phase1Define
        
        phase1 = Phase1Define(chunk_size=10000)
        
        # Monitor memory during processing
        memory_samples = []
        
        def memory_monitor():
            while True:
                memory_samples.append(psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024)
                time.sleep(0.1)
        
        # Start monitoring (would use threading in real implementation)
        phase1.run()
        
        # Check memory didn't spike
        max_memory = max(memory_samples)
        avg_memory = sum(memory_samples) / len(memory_samples)
        
        assert max_memory < avg_memory * 2  # No more than 2x average
```

**Coverage Target:** Key performance scenarios covered

---

### 5. Regression Tests

**Purpose:** Ensure fixes don't reintroduce old bugs

**Scope:**
- Previously fixed bugs
- Edge cases
- Known failure scenarios
- Backward compatibility

**Example: test_regression.py**
```python
import pytest

class TestRegressions:
    """Regression tests for previously fixed bugs"""
    
    def test_sprint5_issue_phase2_file_metrics(self):
        """
        Regression test for Sprint 5 critical finding
        
        Issue: Phase 2 wasn't outputting file_metrics key
        Result: Phase 3 received 0 files, analyzed nothing
        
        This test ensures the fix remains in place
        """
        from DMAIC_V3.phases.phase2_measure import Phase2Measure
        
        phase2 = Phase2Measure()
        result = phase2.run(iteration=1)
        
        # MUST have file_metrics key
        assert 'file_metrics' in result, "Phase 2 must output file_metrics key"
        
        # MUST be a dictionary
        assert isinstance(result['file_metrics'], dict), "file_metrics must be a dictionary"
        
        # Should also have measurements for backward compat
        assert 'measurements' in result, "Phase 2 should keep measurements for backward compatibility"
    
    def test_sprint1_issue_unicode_encoding(self):
        """
        Regression test for Sprint 1 UTF-8 encoding fix
        
        Issue: Windows console couldn't display Unicode characters
        Result: UnicodeEncodeError when printing progress
        
        This test ensures UTF-8 encoding is configured
        """
        import sys
        
        # Verify stdout is UTF-8 encoded
        assert sys.stdout.encoding.lower() in ['utf-8', 'utf8'], \
            "stdout must be UTF-8 encoded"
        
        # Test that Unicode characters can be printed
        test_string = "✅ Test ✓ Complete 🎯 Success"
        
        # Should not raise UnicodeEncodeError
        try:
            print(test_string)
            success = True
        except UnicodeEncodeError:
            success = False
        
        assert success, "System must handle Unicode characters"
    
    def test_sprint3_issue_phase3_import(self):
        """
        Regression test for Sprint 3 module import fix
        
        Issue: subprocess with -m flag caused import warnings
        Result: Phase 3 failed to execute
        
        This test ensures direct imports work
        """
        # Should be able to import directly
        try:
            from DMAIC_V3.phases.phase3_analyze import Phase3Analyze
            import_success = True
        except ImportError:
            import_success = False
        
        assert import_success, "Phase 3 must be directly importable"
        
        # Should be able to instantiate
        phase3 = Phase3Analyze()
        assert phase3 is not None
```

**Coverage Target:** All critical bugs covered

---

## 🎯 TEST EXECUTION

### Running Tests

**Run all tests:**
```bash
pytest
```

**Run specific category:**
```bash
pytest tests/unit/               # Unit tests only
pytest tests/integration/        # Integration tests only
pytest tests/functional/         # Functional tests only
```

**Run specific test file:**
```bash
pytest tests/unit/test_phase2_measure.py
```

**Run specific test:**
```bash
pytest tests/unit/test_phase2_measure.py::TestPhase2Measure::test_file_metrics_conversion
```

**Run with markers:**
```bash
pytest -m unit              # Run only unit tests
pytest -m "not slow"        # Skip slow tests
pytest -m "fast and unit"   # Fast unit tests only
```

**Run with coverage:**
```bash
pytest --cov=DMAIC_V3 --cov-report=html
```

**Run in parallel:**
```bash
pytest -n auto  # Use all available CPUs
```

---

## 📊 TEST COVERAGE TARGETS

### Overall Target: > 70%

| Component | Target | Current | Status |
|-----------|--------|---------|--------|
| **Phase 0 (Setup)** | 80% | 0% | ⏳ Sprint 6 |
| **Phase 1 (Define)** | 75% | 0% | ⏳ Sprint 6 |
| **Phase 2 (Measure)** | 85% | 0% | ⏳ Sprint 6 |
| **Phase 3 (Analyze)** | 80% | 0% | ⏳ Sprint 6 |
| **Phase 4 (Improve)** | 75% | 0% | ⏳ Sprint 6 |
| **Phase 5 (Control)** | 75% | 0% | ⏳ Sprint 6 |
| **Utilities** | 70% | 0% | ⏳ Sprint 6 |
| **Integration** | 60% | 0% | ⏳ Sprint 6 |
| **Overall** | **>70%** | **0%** | ⏳ Sprint 6 |

### Priority Areas

**High Priority (Must have > 80% coverage):**
1. Phase 2 (Measure) - Data format critical
2. Phase handoffs - Integration points
3. Data validation - Quality critical
4. Error handling - Robustness critical

**Medium Priority (Target > 70% coverage):**
5. Phase 1 (Define) - File scanning
6. Phase 3 (Analyze) - Issue identification
7. Configuration management
8. Comparison tool

**Lower Priority (Target > 60% coverage):**
9. Phase 4 (Improve) - Improvement generation
10. Phase 5 (Control) - Validation
11. Progress visualization
12. Reporting utilities

---

## 🔍 TEST VALIDATION

### Continuous Integration (CI)

**Planned for Sprint 6:**

```yaml
# .github/workflows/test.yml
name: DMAIC Test Suite

on: [push, pull_request]

jobs:
  test:
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
        pip install pytest pytest-cov
    
    - name: Run tests
      run: |
        pytest --cov=DMAIC_V3 --cov-report=xml --cov-report=term
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
```

---

## 📝 TEST DOCUMENTATION

### Test Case Documentation Template

```python
def test_descriptive_name(self):
    """
    Brief description of what is being tested
    
    Given: Initial state/setup
    When: Action being performed
    Then: Expected outcome
    
    Related: Issue/Sprint/Document reference
    """
    # Arrange
    setup_code()
    
    # Act
    result = execute_test()
    
    # Assert
    assert result == expected
```

### Test Report Format

**Generated after each test run:**

```
DMAIC Test Report
=================
Date: 2025-11-14
Duration: 45.2 seconds

Summary:
--------
Total Tests: 127
Passed: 125
Failed: 2
Skipped: 0
Success Rate: 98.4%

Coverage:
---------
Overall: 72.3%
Phase 2: 85.1%
Phase 3: 78.9%
Integration: 65.4%

Failed Tests:
-------------
1. test_phase4_large_codebase - Timeout exceeded
2. test_comparison_edge_case - Assertion failed

Performance:
------------
Fastest: test_utils_validation (0.01s)
Slowest: test_full_cycle (12.3s)
Average: 0.36s
```

---

## 🔗 RELATED DOCUMENTS

- [Workspace State](workspace/WORKSPACE_STATE.md)
- [Operational Excellence](OPERATIONAL_EXCELLENCE.md)
- [Versioning Standards](VERSIONING_STANDARDS.md)
- [Sprint Tracker](SPRINT_TRACKER.md)
- [Action Tracker](ACTION_TRACKER.md)

---

**Document Version:** 1.0  
**Last Updated:** November 14, 2025  
**Implementation Sprint:** Sprint 6 Task 2  
**Maintained By:** DMAIC Sprint System
