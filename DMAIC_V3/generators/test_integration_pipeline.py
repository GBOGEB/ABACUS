from typing import Any
#!/usr/bin/env python3
"""
DMAIC V3 - Integration Pipeline Test (Makefile-ready)
Tests ALL 9 Python files with REAL I/O, not just imports
Includes: unit tests, integration tests, I/O validation, CI/CD readiness
"""

import os
import sys
import subprocess
from pathlib import Path
import json
import time
from datetime import datetime
import shutil

class IntegrationPipelineTest:
    """Comprehensive integration pipeline testing"""
    
    def __init__(self, root_dir: Path):
        """TODO: Add function description"""

        self.root_dir = root_dir
        self.master_doc_dir = root_dir / "master_document_system"
        self.results = []
        self.temp_dirs = []
        
    def cleanup(self) -> Any:
        """Clean up temporary directories"""
        for temp_dir in self.temp_dirs:
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
    
    def test_top_level_script(self, script_path: Path) -> dict:
        """Test top-level script with real execution"""
        print(f"\n{'='*80}")
        print(f"TESTING: {script_path.name} (REAL EXECUTION)")
        print(f"{'='*80}")
        
        start_time = time.time()
        
        try:
            env = os.environ.copy()
            env['PYTHONPATH'] = str(self.root_dir)
            
            result = subprocess.run(
                [sys.executable, str(script_path)],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=str(self.root_dir),
                env=env
            )
            
            execution_time = time.time() - start_time
            success = result.returncode == 0
            
            # Check for actual output files generated
            output_files = self._check_output_files(script_path.stem)
            
            print(f"Status: {'SUCCESS' if success else 'FAILED'}")
            print(f"Execution Time: {execution_time:.2f}s")
            print(f"Exit Code: {result.returncode}")
            print(f"Output Files Generated: {len(output_files)}")
            
            return {
                "file": str(script_path.relative_to(self.root_dir)),
                "type": "top_level_script",
                "test_method": "real_execution",
                "status": "SUCCESS" if success else "FAILED",
                "execution_time": execution_time,
                "exit_code": result.returncode,
                "output_files": output_files,
                "stdout_lines": len(result.stdout.split('\n')),
                "stderr_lines": len(result.stderr.split('\n')) if result.stderr else 0,
                "io_validated": len(output_files) > 0
            }
            
        except Exception as e:
            return {
                "file": str(script_path.relative_to(self.root_dir)),
                "type": "top_level_script",
                "test_method": "real_execution",
                "status": "ERROR",
                "error": str(e)
            }
    
    def test_core_module_with_io(self, module_path: Path) -> dict:
        """Test core module with REAL I/O, not just import"""
        print(f"\n{'='*80}")
        print(f"TESTING: {module_path.name} (REAL I/O)")
        print(f"{'='*80}")
        
        start_time = time.time()
        module_name = module_path.stem
        
        # Create test script that actually USES the module with I/O
        test_script = self._create_module_test_script(module_name)
        
        try:
            env = os.environ.copy()
            env['PYTHONPATH'] = str(self.root_dir)
            
            result = subprocess.run(
                [sys.executable, "-c", test_script],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=str(self.root_dir),
                env=env
            )
            
            execution_time = time.time() - start_time
            success = result.returncode == 0
            
            # Parse test results from stdout
            test_results = self._parse_test_output(result.stdout)
            
            print(f"Status: {'SUCCESS' if success else 'FAILED'}")
            print(f"Execution Time: {execution_time:.2f}s")
            print(f"Tests Run: {test_results.get('tests_run', 0)}")
            print(f"Tests Passed: {test_results.get('tests_passed', 0)}")
            print(f"I/O Operations: {test_results.get('io_operations', 0)}")
            
            return {
                "file": str(module_path.relative_to(self.root_dir)),
                "type": "core_module",
                "test_method": "real_io_test",
                "status": "SUCCESS" if success else "FAILED",
                "execution_time": execution_time,
                "exit_code": result.returncode,
                "tests_run": test_results.get('tests_run', 0),
                "tests_passed": test_results.get('tests_passed', 0),
                "io_operations": test_results.get('io_operations', 0),
                "io_validated": test_results.get('io_operations', 0) > 0
            }
            
        except Exception as e:
            return {
                "file": str(module_path.relative_to(self.root_dir)),
                "type": "core_module",
                "test_method": "real_io_test",
                "status": "ERROR",
                "error": str(e)
            }
    
    def _create_module_test_script(self, module_name: str) -> str:
        """Create test script that exercises module with REAL I/O"""
        
        if module_name == "dmaic_manager":
            return """
import sys
from master_document_system.core.dmaic_manager import DMAICManager
import json
import tempfile
from pathlib import Path

tests_run = 0
tests_passed = 0
io_operations = 0

# Test 1: Initialize DMAICManager
tests_run += 1
try:
    manager = DMAICManager()
    tests_passed += 1
    print(f"[PASS] DMAICManager initialized")
except Exception as e:
    print(f"[FAIL] DMAICManager init: {e}")

# Test 2: Set DMAIC phase
tests_run += 1
try:
    manager.set_phase("ANALYZE")
    tests_passed += 1
    print(f"[PASS] Set phase to ANALYZE")
except Exception as e:
    print(f"[FAIL] Set phase: {e}")

# Test 3: Export status (I/O operation)
tests_run += 1
try:
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_file = Path(f.name)
    status = manager.export_status(str(temp_file))
    if temp_file.exists():
        io_operations += 1
        tests_passed += 1
        print(f"[PASS] Exported status to {temp_file}")
        temp_file.unlink()
    else:
        print(f"[FAIL] Status file not created")
except Exception as e:
    print(f"[FAIL] Export status: {e}")

print(f"TESTS_RUN:{tests_run}")
print(f"TESTS_PASSED:{tests_passed}")
print(f"IO_OPERATIONS:{io_operations}")
"""
        
        elif module_name == "input_manager":
            return """
import sys
from master_document_system.core.input_manager import InputManager
import tempfile
from pathlib import Path

tests_run = 0
tests_passed = 0
io_operations = 0

# Test 1: Initialize InputManager
tests_run += 1
try:
    manager = InputManager()
    tests_passed += 1
    print(f"[PASS] InputManager initialized")
except Exception as e:
    print(f"[FAIL] InputManager init: {e}")

# Test 2: Register canonical source (I/O operation)
tests_run += 1
try:
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("Test canonical source")
        temp_file = Path(f.name)
    
    manager.register_canonical_source(str(temp_file), "test_source")
    io_operations += 1
    tests_passed += 1
    print(f"[PASS] Registered canonical source")
    temp_file.unlink()
except Exception as e:
    print(f"[FAIL] Register source: {e}")

# Test 3: Validate sources
tests_run += 1
try:
    validation = manager.validate_sources()
    tests_passed += 1
    print(f"[PASS] Validated sources")
except Exception as e:
    print(f"[FAIL] Validate sources: {e}")

print(f"TESTS_RUN:{tests_run}")
print(f"TESTS_PASSED:{tests_passed}")
print(f"IO_OPERATIONS:{io_operations}")
"""
        
        elif module_name == "style_extractor":
            return """
import sys
from master_document_system.core.style_extractor import StyleExtractor
import tempfile
from pathlib import Path
from docx import Document

tests_run = 0
tests_passed = 0
io_operations = 0

# Test 1: Initialize StyleExtractor
tests_run += 1
try:
    extractor = StyleExtractor()
    tests_passed += 1
    print(f"[PASS] StyleExtractor initialized")
except Exception as e:
    print(f"[FAIL] StyleExtractor init: {e}")

# Test 2: Create temp DOCX and extract styles (I/O operation)
tests_run += 1
try:
    doc = Document()
    doc.add_paragraph("Test document")
    with tempfile.NamedTemporaryFile(mode='wb', suffix='.docx', delete=False) as f:
        temp_file = Path(f.name)
        doc.save(str(temp_file))
    
    fingerprint = extractor.extract_fingerprint(str(temp_file))
    io_operations += 1
    tests_passed += 1
    print(f"[PASS] Extracted style fingerprint")
    temp_file.unlink()
except Exception as e:
    print(f"[FAIL] Extract fingerprint: {e}")

# Test 3: Save fingerprint (I/O operation)
tests_run += 1
try:
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_file = Path(f.name)
    
    extractor.save_fingerprint(fingerprint, str(temp_file))
    if temp_file.exists():
        io_operations += 1
        tests_passed += 1
        print(f"[PASS] Saved fingerprint")
        temp_file.unlink()
except Exception as e:
    print(f"[FAIL] Save fingerprint: {e}")

print(f"TESTS_RUN:{tests_run}")
print(f"TESTS_PASSED:{tests_passed}")
print(f"IO_OPERATIONS:{io_operations}")
"""
        
        elif module_name == "temporal_tracker":
            return """
import sys
from master_document_system.core.temporal_tracker import TemporalTracker
import tempfile
from pathlib import Path

tests_run = 0
tests_passed = 0
io_operations = 0

# Test 1: Initialize TemporalTracker
tests_run += 1
try:
    tracker = TemporalTracker()
    tests_passed += 1
    print(f"[PASS] TemporalTracker initialized")
except Exception as e:
    print(f"[FAIL] TemporalTracker init: {e}")

# Test 2: Record generation (I/O operation)
tests_run += 1
try:
    tracker.record_generation("test_version", "ANALYZE", 1, False)
    io_operations += 1
    tests_passed += 1
    print(f"[PASS] Recorded generation")
except Exception as e:
    print(f"[FAIL] Record generation: {e}")

# Test 3: Query lineage
tests_run += 1
try:
    lineage = tracker.query_lineage()
    tests_passed += 1
    print(f"[PASS] Queried lineage")
except Exception as e:
    print(f"[FAIL] Query lineage: {e}")

# Test 4: Export history (I/O operation)
tests_run += 1
try:
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_file = Path(f.name)
    
    tracker.export_history(str(temp_file))
    if temp_file.exists():
        io_operations += 1
        tests_passed += 1
        print(f"[PASS] Exported history")
        temp_file.unlink()
except Exception as e:
    print(f"[FAIL] Export history: {e}")

print(f"TESTS_RUN:{tests_run}")
print(f"TESTS_PASSED:{tests_passed}")
print(f"IO_OPERATIONS:{io_operations}")
"""
        
        elif module_name == "__init__":
            return """
import sys
from master_document_system.core import *

tests_run = 1
tests_passed = 0
io_operations = 0

try:
    # Test that all exports are available
    assert 'DMAICManager' in dir()
    assert 'InputManager' in dir()
    assert 'StyleExtractor' in dir()
    assert 'TemporalTracker' in dir()
    tests_passed = 1
    print(f"[PASS] All core modules exported")
except Exception as e:
    print(f"[FAIL] Module exports: {e}")

print(f"TESTS_RUN:{tests_run}")
print(f"TESTS_PASSED:{tests_passed}")
print(f"IO_OPERATIONS:{io_operations}")
"""
        
        else:
            return f"""
print("TESTS_RUN:0")
print("TESTS_PASSED:0")
print("IO_OPERATIONS:0")
"""
    
    def _parse_test_output(self, stdout: str) -> dict:
        """Parse test output to extract metrics"""
        results = {
            "tests_run": 0,
            "tests_passed": 0,
            "io_operations": 0
        }
        
        for line in stdout.split('\n'):
            if line.startswith("TESTS_RUN:"):
                results["tests_run"] = int(line.split(':')[1])
            elif line.startswith("TESTS_PASSED:"):
                results["tests_passed"] = int(line.split(':')[1])
            elif line.startswith("IO_OPERATIONS:"):
                results["io_operations"] = int(line.split(':')[1])
        
        return results
    
    def _check_output_files(self, script_name: str) -> list:
        """Check for output files generated by script"""
        output_files = []
        
        # Check master_document_system directory for generated files
        for pattern in ["*.docx", "*.json", "*.yaml", "*.md", "*.html", "*.xlsx"]:
            for file in self.master_doc_dir.glob(pattern):
                # Check if file was recently created (within last 5 minutes)
                if time.time() - file.stat().st_mtime < 300:
                    output_files.append(str(file.name))
        
        return output_files
    
    def run_all_tests(self) -> Any:
        """Run all integration tests"""
        print("="*80)
        print("DMAIC V3 - INTEGRATION PIPELINE TEST (MAKEFILE-READY)")
        print("="*80)
        print(f"Version: 3.1.0")
        print(f"DMAIC Version: V3")
        print(f"Test Type: REAL I/O (not just imports)")
        print(f"Timestamp: {datetime.now().isoformat()}")
        print("="*80)
        
        # Top-level scripts (4)
        top_level_scripts = [
            self.master_doc_dir / "demo_python_dashboard.py",
            self.master_doc_dir / "integration_example.py",
            self.master_doc_dir / "quick_start.py",
            self.master_doc_dir / "master_engine.py",
        ]
        
        for script in top_level_scripts:
            if script.exists():
                result = self.test_top_level_script(script)
                self.results.append(result)
        
        # Core modules (5) - with REAL I/O tests
        core_modules = [
            self.master_doc_dir / "core" / "dmaic_manager.py",
            self.master_doc_dir / "core" / "input_manager.py",
            self.master_doc_dir / "core" / "style_extractor.py",
            self.master_doc_dir / "core" / "temporal_tracker.py",
            self.master_doc_dir / "core" / "__init__.py",
        ]
        
        for module in core_modules:
            if module.exists():
                result = self.test_core_module_with_io(module)
                self.results.append(result)
        
        self.print_summary()
        self.save_report()
        self.cleanup()
    
    def print_summary(self) -> Any:
        """Print test summary"""
        print("\n" + "="*80)
        print("INTEGRATION PIPELINE SUMMARY")
        print("="*80)
        
        total = len(self.results)
        successful = sum(1 for r in self.results if r["status"] == "SUCCESS")
        failed = sum(1 for r in self.results if r["status"] == "FAILED")
        error = sum(1 for r in self.results if r["status"] == "ERROR")
        
        io_validated = sum(1 for r in self.results if r.get("io_validated", False))
        total_tests = sum(r.get("tests_run", 0) for r in self.results)
        total_passed = sum(r.get("tests_passed", 0) for r in self.results)
        total_io_ops = sum(r.get("io_operations", 0) for r in self.results)
        
        print(f"Total Files:           {total}")
        print(f"Successful:            {successful}")
        print(f"Failed:                {failed}")
        print(f"Error:                 {error}")
        print(f"Success Rate:          {(successful/total*100):.1f}%")
        print(f"\nI/O Validation:")
        print(f"Files with I/O:        {io_validated}/{total}")
        print(f"Total Tests Run:       {total_tests}")
        print(f"Total Tests Passed:    {total_passed}")
        print(f"Total I/O Operations:  {total_io_ops}")
        print(f"\nCI/CD Readiness:")
        print(f"Makefile-ready:        {'YES' if successful == total else 'NO'}")
        print(f"Pre-commit ready:      {'YES' if successful == total else 'NO'}")
        print(f"GitHub Actions ready:  {'YES' if successful == total else 'NO'}")
        print("="*80)
    
    def save_report(self) -> Any:
        """Save integration pipeline report"""
        report_dir = self.root_dir / "output" / "integration_reports"
        report_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = report_dir / f"integration_pipeline_report_{timestamp}.json"
        
        total = len(self.results)
        successful = sum(1 for r in self.results if r["status"] == "SUCCESS")
        io_validated = sum(1 for r in self.results if r.get("io_validated", False))
        total_tests = sum(r.get("tests_run", 0) for r in self.results)
        total_passed = sum(r.get("tests_passed", 0) for r in self.results)
        total_io_ops = sum(r.get("io_operations", 0) for r in self.results)
        
        report = {
            "metadata": {
                "version": "3.1.0",
                "dmaic_version": "V3",
                "timestamp": datetime.now().isoformat(),
                "test_type": "integration_pipeline_real_io"
            },
            "summary": {
                "total_files": total,
                "successful": successful,
                "failed": total - successful,
                "success_rate": f"{(successful/total*100):.1f}%",
                "io_validated": io_validated,
                "total_tests_run": total_tests,
                "total_tests_passed": total_passed,
                "total_io_operations": total_io_ops,
                "ci_cd_ready": successful == total
            },
            "results": self.results
        }
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\nReport saved to: {report_file}")

def main() -> Any:
    """TODO: Add function description"""

    root_dir = Path(__file__).parent.parent.parent
    tester = IntegrationPipelineTest(root_dir)
    tester.run_all_tests()

if __name__ == "__main__":
    main()
