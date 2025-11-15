#!/usr/bin/env python3
"""
DMAIC V3 - Real Execution Test (ALL 9 Python Files)
Tests Python code execution in real environment with venv and requirements.txt
Includes top-level scripts AND core modules
"""

import os
import sys
import subprocess
from pathlib import Path
import json
import time
from datetime import datetime

def run_python_file(file_path: Path, root_dir: Path) -> dict:
    """Run a Python file and capture results."""
    print(f"\n{'='*80}")
    print(f"EXECUTING: {file_path.relative_to(root_dir)}")
    print(f"{'='*80}")
    
    start_time = time.time()
    
    try:
        env = os.environ.copy()
        python_path_parts = []
        if root_dir:
            python_path_parts.append(str(root_dir.resolve()))
        python_path_parts.append(str(file_path.parent.resolve()))
        existing_py = env.get('PYTHONPATH', '')
        if existing_py:
            python_path_parts.insert(0, existing_py)
        env['PYTHONPATH'] = os.pathsep.join(python_path_parts)
        
        if "core" in str(file_path):
            module_name = file_path.stem
            if module_name == "__init__":
                module_path = "master_document_system.core"
            else:
                module_path = f"master_document_system.core.{module_name}"
            
            print(f"Testing import: {module_path}")
            result = subprocess.run(
                [sys.executable, "-c", f"import {module_path}; print('Module imported successfully')"],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=str(root_dir.resolve()),
                env=env
            )
        else:
            result = subprocess.run(
                [sys.executable, str(file_path.resolve())],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=str(root_dir.resolve()),
                env=env
            )
        
        execution_time = time.time() - start_time
        success = result.returncode == 0
        
        print(f"Status: {'SUCCESS' if success else 'FAILED'}")
        print(f"Execution Time: {execution_time:.2f}s")
        print(f"Exit Code: {result.returncode}")
        
        if result.stdout:
            print(f"\nSTDOUT:\n{result.stdout[:500]}")
        
        if result.stderr and not success:
            print(f"\nSTDERR:\n{result.stderr[:500]}")
        
        return {
            "file_path": str(file_path.relative_to(root_dir)),
            "status": "SUCCESS" if success else "FAILED",
            "execution_time": execution_time,
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "error": None if success else result.stderr
        }
    
    except subprocess.TimeoutExpired:
        execution_time = time.time() - start_time
        print(f"Status: TIMEOUT")
        print(f"Execution Time: {execution_time:.2f}s")
        return {
            "file_path": str(file_path.relative_to(root_dir)),
            "status": "TIMEOUT",
            "execution_time": execution_time,
            "exit_code": -1,
            "error": "Execution timeout (60s)"
        }
    
    except Exception as e:
        execution_time = time.time() - start_time
        print(f"Status: ERROR")
        print(f"Error: {str(e)}")
        return {
            "file_path": str(file_path.relative_to(root_dir)),
            "status": "ERROR",
            "execution_time": execution_time,
            "exit_code": -1,
            "error": str(e)
        }

def main():
    print("="*80)
    print("DMAIC V3 - REAL EXECUTION TEST (ALL 9 PYTHON FILES)")
    print("="*80)
    print(f"Version: 3.1.0")
    print(f"DMAIC Version: V3")
    print(f"Integration Mode: BIDIRECTIONAL")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("="*80)
    
    root_dir = Path(__file__).parent.parent.parent
    master_doc_dir = root_dir / "master_document_system"
    
    python_files = [
        master_doc_dir / "demo_python_dashboard.py",
        master_doc_dir / "integration_example.py",
        master_doc_dir / "quick_start.py",
        master_doc_dir / "master_engine.py",
        master_doc_dir / "core" / "dmaic_manager.py",
        master_doc_dir / "core" / "input_manager.py",
        master_doc_dir / "core" / "style_extractor.py",
        master_doc_dir / "core" / "temporal_tracker.py",
        master_doc_dir / "core" / "__init__.py",
    ]
    
    python_files = [f for f in python_files if f.exists()]
    
    print(f"\nFound {len(python_files)} Python files to execute")
    print(f"Root Directory: {root_dir}")
    print(f"Master Document Directory: {master_doc_dir}")
    
    results = []
    for py_file in python_files:
        result = run_python_file(py_file, root_dir)
        results.append(result)
    
    print("\n" + "="*80)
    print("EXECUTION SUMMARY")
    print("="*80)
    
    total = len(results)
    successful = sum(1 for r in results if r["status"] == "SUCCESS")
    failed = sum(1 for r in results if r["status"] == "FAILED")
    timeout = sum(1 for r in results if r["status"] == "TIMEOUT")
    error = sum(1 for r in results if r["status"] == "ERROR")
    
    print(f"Total Files:    {total}")
    print(f"Successful:     {successful}")
    print(f"Failed:         {failed}")
    print(f"Timeout:        {timeout}")
    print(f"Error:          {error}")
    print(f"Success Rate:   {(successful/total*100):.1f}%")
    print("="*80)
    
    report_dir = root_dir / "output" / "execution_reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = report_dir / f"real_execution_report_{timestamp}.json"
    
    report = {
        "metadata": {
            "version": "3.1.0",
            "dmaic_version": "V3",
            "timestamp": datetime.now().isoformat(),
            "total_files": total,
            "python_files": total
        },
        "summary": {
            "successful": successful,
            "failed": failed,
            "timeout": timeout,
            "error": error,
            "success_rate": f"{(successful/total*100):.1f}%"
        },
        "results": results
    }
    
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\nReport saved to: {report_file}")
    
    sys.exit(0 if successful == total else 1)

if __name__ == "__main__":
    main()
