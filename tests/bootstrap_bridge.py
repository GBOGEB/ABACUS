"""
bootstrap_bridge.py
CI/CD Sprint: Sprint 6 - Bootstrap Integration
Version: 1.0.1
Last Updated: 2025-12-06
Status: Production
DMAIC Phase: Measure & Control
DOW Standard: Phase 0 Compliance

Purpose:
  Integration bridge for Bootstrap Statistical Tests (28 tests) with the
  DMAIC-based comprehensive test orchestration system. Provides bidirectional
  connectivity between bootstrap_eval.py statistical functions and the
  DOW-aligned test infrastructure.

Integration Points:
  - tests/test_bootstrap_eval.py: 28 comprehensive bootstrap tests
  - comprehensive_bridge_test_suite.py: DMAIC test orchestrator
  - bootstrap_eval.py: Core statistical functions
  - TEST_SUITE_BOOK.md: Documentation integration (Chapter 09)

Related Files:
  - tests/test_bootstrap_eval.py: Bootstrap test suite
  - tests/conftest.py: Shared fixtures and markers
  - pytest.ini: Test configuration and markers
  - bootstrap_eval.py: Implementation under test

Test Coverage:
  - bootstrap_ci_mean(): Bootstrap confidence intervals (6 tests)
  - normal_ci_mean(): Normal distribution CIs (3 tests)
  - bootstrap_ci_diff_means(): Group comparison (5 tests)
  - load_from_csv(): CSV data loading (2 tests)
  - load_from_folders(): Folder-based loading (2 tests)
  - sanitize_name(): Name normalization (2 tests)
  - run_analysis(): Integration workflow (4 tests)
  - Edge cases: Boundary conditions (8 tests)

DMAIC Alignment:
  - Define: Test objectives for statistical validation
  - Measure: Execute 28 bootstrap tests, collect metrics
  - Analyze: Evaluate statistical correctness and DOW compliance
  - Improve: Generate recommendations for coverage gaps
  - Control: Monitor test health and regression prevention

Changes in v1.0.1:
  - Fixed Unicode encoding errors (replaced emojis with ASCII)
  - Fixed pytest hook conflict (pytest_report_dir → report_dir)
  - Enhanced Python executable detection for pytest
"""

__version__ = "1.0.1"
__sprint__ = "Sprint 6 - Bootstrap Integration"
__status__ = "Production"
__dmaic_phase__ = "Measure & Control"
__test_count__ = 28

import sys
import subprocess
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Tuple

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent


class BootstrapBridge:
    """
    Bridge for integrating Bootstrap Statistical Tests with DMAIC orchestration
    
    Provides:
    - Test execution via pytest
    - Metrics collection and reporting
    - DOW compliance validation
    - DMAIC phase integration
    """
    
    def __init__(self, report_dir: Path = None):
        self.script_dir = SCRIPT_DIR
        self.project_root = PROJECT_ROOT
        self.test_file = SCRIPT_DIR / "test_bootstrap_eval.py"
        self.report_dir = report_dir or (PROJECT_ROOT / "test_reports" / "bootstrap")
        self.report_dir.mkdir(parents=True, exist_ok=True)
        
        self.test_results = {
            "bridge": "bootstrap_statistics",
            "version": __version__,
            "sprint": __sprint__,
            "test_count": __test_count__,
            "timestamp": datetime.now().isoformat(),
            "dmaic_phase": __dmaic_phase__,
            "status": "unknown",
            "metrics": {}
        }
    
    def validate_prerequisites(self) -> Tuple[bool, List[str]]:
        """
        Validate that all prerequisites are met

        Returns:
            (success, messages): Validation status and messages
        """
        messages = []
        success = True

        # Check test file exists
        if not self.test_file.exists():
            messages.append(f"[FAIL] Test file not found: {self.test_file}")
            success = False
        else:
            messages.append(f"[PASS] Test file found: {self.test_file}")

        # Check bootstrap_eval.py exists
        bootstrap_eval = PROJECT_ROOT / "bootstrap_eval.py"
        if not bootstrap_eval.exists():
            messages.append(f"[FAIL] bootstrap_eval.py not found: {bootstrap_eval}")
            success = False
        else:
            messages.append(f"[PASS] bootstrap_eval.py found")

        # Skip pytest version check on Windows (it can hang)
        # We'll just try to run tests and let it fail naturally if pytest isn't available
        messages.append(f"[PASS] pytest check skipped (Windows compatibility)")

        # Check conftest.py exists
        conftest = SCRIPT_DIR / "conftest.py"
        if not conftest.exists():
            messages.append(f"[WARN] conftest.py not found (fixtures unavailable): {conftest}")
        else:
            messages.append(f"[PASS] conftest.py found")

        return success, messages
    
    def run_tests(self, markers: str = None, verbose: bool = True) -> Dict[str, Any]:
        """
        Execute bootstrap tests via pytest
        
        Args:
            markers: Pytest marker expression (e.g., "bootstrap_stats", "integration")
            verbose: Enable verbose output
        
        Returns:
            Test execution results with metrics
        """
        print("\n" + "="*80)
        print("BOOTSTRAP BRIDGE: Running Tests")
        print("="*80 + "\n")
        
        # Build pytest command
        cmd = [
            sys.executable, "-m", "pytest",
            str(self.test_file),
            "-v" if verbose else "",
            "--tb=short",
            "--color=yes",
            f"--junit-xml={self.report_dir / 'junit.xml'}",
            f"--html={self.report_dir / 'report.html'}",
            "--self-contained-html"
        ]
        
        if markers:
            cmd.extend(["-m", markers])
        
        # Remove empty strings
        cmd = [c for c in cmd if c]
        
        print(f"Command: {' '.join(cmd)}\n")

        try:
            # Windows-specific kwargs
            kwargs = {
                "capture_output": True,
                "text": True,
                "timeout": 300,
                "cwd": str(PROJECT_ROOT)
            }

            # Prevent console window popup on Windows
            if sys.platform == "win32":
                kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

            result = subprocess.run(cmd, **kwargs)

            # Parse output
            output = result.stdout + result.stderr
            print(output)

            # Extract metrics from output
            metrics = self._parse_pytest_output(output)

            self.test_results["status"] = "passed" if result.returncode == 0 else "failed"
            self.test_results["metrics"] = metrics
            self.test_results["return_code"] = result.returncode

            return self.test_results

        except subprocess.TimeoutExpired:
            print("[ERROR] Test execution timed out (300s)")
            self.test_results["status"] = "timeout"
            return self.test_results
        except Exception as e:
            print(f"[ERROR] Test execution failed: {e}")
            self.test_results["status"] = "error"
            self.test_results["error"] = str(e)
            return self.test_results
    
    def _parse_pytest_output(self, output: str) -> Dict[str, Any]:
        """
        Parse pytest output to extract metrics
        
        Args:
            output: Pytest stdout/stderr
        
        Returns:
            Parsed metrics dictionary
        """
        metrics = {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "errors": 0,
            "duration": 0.0
        }
        
        # Parse test summary line
        # Example: "28 passed in 2.34s"
        import re
        
        summary_pattern = r"(\d+)\s+passed"
        failed_pattern = r"(\d+)\s+failed"
        skipped_pattern = r"(\d+)\s+skipped"
        duration_pattern = r"in\s+([\d.]+)s"
        
        if match := re.search(summary_pattern, output):
            metrics["passed"] = int(match.group(1))
        
        if match := re.search(failed_pattern, output):
            metrics["failed"] = int(match.group(1))
        
        if match := re.search(skipped_pattern, output):
            metrics["skipped"] = int(match.group(1))
        
        if match := re.search(duration_pattern, output):
            metrics["duration"] = float(match.group(1))
        
        metrics["total"] = metrics["passed"] + metrics["failed"] + metrics["skipped"]
        
        return metrics
    
    def run_by_marker(self, marker: str) -> Dict[str, Any]:
        """
        Run tests filtered by specific marker

        Args:
            marker: Pytest marker (bootstrap_stats, integration, edge_cases, data_loading)

        Returns:
            Test results for specified marker
        """
        print(f"\n[TEST] Running tests with marker: @pytest.mark.{marker}")
        return self.run_tests(markers=marker, verbose=True)

    def run_all_bootstrap_tests(self) -> Dict[str, Any]:
        """
        Run all 28 bootstrap tests

        Returns:
            Complete test results
        """
        print("\n[TEST] Running all 28 bootstrap statistical tests")
        return self.run_tests(markers=None, verbose=True)
    
    def generate_dmaic_report(self) -> Dict[str, Any]:
        """
        Generate DMAIC-aligned report for bootstrap tests
        
        Returns:
            DMAIC phase report
        """
        print("\n" + "="*80)
        print("DMAIC REPORT: Bootstrap Statistics")
        print("="*80 + "\n")
        
        dmaic_report = {
            "timestamp": datetime.now().isoformat(),
            "bridge": "bootstrap_statistics",
            "test_file": str(self.test_file),
            "phases": {}
        }
        
        # Phase 1: Define
        dmaic_report["phases"]["define"] = {
            "objectives": [
                "Validate bootstrap_ci_mean() for confidence interval computation",
                "Validate normal_ci_mean() for normal distribution CIs",
                "Validate bootstrap_ci_diff_means() for group comparisons",
                "Validate data loading functions (CSV, folders)",
                "Validate integration workflows",
                "Ensure edge case handling"
            ],
            "test_count": 28,
            "markers": ["bootstrap_stats", "data_loading", "integration", "edge_cases"]
        }
        
        # Phase 2: Measure (run tests)
        print("[DMAIC] Phase: Measure")
        measure_results = self.run_all_bootstrap_tests()
        dmaic_report["phases"]["measure"] = measure_results

        # Phase 3: Analyze
        print("\n[DMAIC] Phase: Analyze")
        analyze_results = self._analyze_results(measure_results)
        dmaic_report["phases"]["analyze"] = analyze_results

        # Phase 4: Improve
        print("\n[DMAIC] Phase: Improve")
        improve_results = self._generate_improvements(analyze_results)
        dmaic_report["phases"]["improve"] = improve_results

        # Phase 5: Control
        print("\n[DMAIC] Phase: Control")
        control_results = self._generate_control_plan(measure_results)
        dmaic_report["phases"]["control"] = control_results

        # Save report
        report_file = self.report_dir / f"dmaic_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(dmaic_report, f, indent=2)

        print(f"\n[SUCCESS] DMAIC report saved: {report_file}")
        
        return dmaic_report
    
    def _analyze_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze test results for DMAIC reporting"""
        metrics = results.get("metrics", {})
        total = metrics.get("total", 0)
        passed = metrics.get("passed", 0)
        
        pass_rate = (passed / total * 100) if total > 0 else 0
        
        analysis = {
            "pass_rate": pass_rate,
            "health_status": "excellent" if pass_rate >= 95 else "good" if pass_rate >= 80 else "poor",
            "coverage": "complete" if total >= 28 else "incomplete",
            "performance": "acceptable" if metrics.get("duration", 0) < 60 else "slow"
        }
        
        print(f"  Pass Rate: {pass_rate:.1f}% ({passed}/{total})")
        print(f"  Health: {analysis['health_status']}")
        print(f"  Coverage: {analysis['coverage']}")
        
        return analysis
    
    def _generate_improvements(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate improvement recommendations"""
        improvements = []
        
        if analysis.get("pass_rate", 0) < 100:
            improvements.append("Fix failing tests to achieve 100% pass rate")
        
        if analysis.get("coverage") == "incomplete":
            improvements.append("Add tests to achieve complete coverage (28 tests)")
        
        if analysis.get("performance") == "slow":
            improvements.append("Optimize test execution time")
        
        if not improvements:
            improvements.append("Maintain current excellent test health")
        
        print("  Recommendations:")
        for i, rec in enumerate(improvements, 1):
            print(f"    {i}. {rec}")
        
        return {"recommendations": improvements}
    
    def _generate_control_plan(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate control plan for continuous monitoring"""
        control_plan = {
            "monitoring": [
                "Run bootstrap tests on every commit",
                "Monitor test execution time (target < 60s)",
                "Track pass rate (target 100%)",
                "Review failed tests within 24h"
            ],
            "thresholds": {
                "min_pass_rate": 95.0,
                "max_duration": 60.0,
                "required_test_count": 28
            },
            "status": results.get("status", "unknown")
        }
        
        print("  Control Measures:")
        for measure in control_plan["monitoring"]:
            print(f"    - {measure}")
        
        return control_plan


def main():
    """Main execution for standalone bootstrap bridge testing"""
    print("\n" + "="*80)
    print("BOOTSTRAP STATISTICS BRIDGE - DMAIC Integration")
    print("="*80 + "\n")

    bridge = BootstrapBridge()

    # Validate prerequisites
    print("[CHECK] Validating Prerequisites...")
    success, messages = bridge.validate_prerequisites()
    for msg in messages:
        print(f"  {msg}")

    if not success:
        print("\n[FAIL] Prerequisites not met. Please fix issues above.")
        return 1

    print("\n[PASS] Prerequisites validated\n")

    # Generate DMAIC report
    dmaic_report = bridge.generate_dmaic_report()

    # Summary
    print("\n" + "="*80)
    print("BOOTSTRAP BRIDGE SUMMARY")
    print("="*80)
    print(f"Status: {dmaic_report['phases']['measure'].get('status', 'unknown').upper()}")
    print(f"Tests: {dmaic_report['phases']['measure'].get('metrics', {}).get('total', 0)}")
    print(f"Passed: {dmaic_report['phases']['measure'].get('metrics', {}).get('passed', 0)}")
    print(f"Pass Rate: {dmaic_report['phases']['analyze'].get('pass_rate', 0):.1f}%")
    print(f"Health: {dmaic_report['phases']['analyze'].get('health_status', 'unknown')}")
    print("="*80 + "\n")

    return 0 if dmaic_report['phases']['measure'].get('status') == 'passed' else 1


if __name__ == "__main__":
    sys.exit(main())
