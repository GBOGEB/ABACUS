#!/usr/bin/env python3
"""
# Version: 1.0.0
# Date: 2025-11-25
# Description: Auto-generated version header
"""

"""
FAST PRE-CD METRICS COLLECTOR
Optimized for large codebases - collects essential metrics quickly
"""

import os
import sys
import json
import hashlib
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import re

os.environ['PYTHONIOENCODING'] = 'utf-8'
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

class FastMetricsCollector:
    def __init__(self, workspace_path: Path, output_suffix: str = "pre"):
        self.workspace = workspace_path
        self.execution_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_suffix = output_suffix
        self.output_dir = Path("DMAIC_INTEGRATION_OUTPUT/cicd_github")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def collect_fast_metrics(self):
        """Collect essential metrics quickly"""
        print("\n" + "="*80)
        print("FAST PRE-CD METRICS COLLECTION")
        print("="*80)
        print(f"Workspace: {self.workspace}")
        print(f"Execution ID: {self.execution_id}")
        print("="*80 + "\n")
        
        metrics = {
            "execution_id": self.execution_id,
            "timestamp": datetime.now().isoformat(),
            "workspace": str(self.workspace),
            "files": {},
            "duplicates": {},
            "import_issues": [],
            "version_headers": {},
            "summary": {}
        }
        
        # Collect file statistics
        print("[SCAN] Collecting file statistics...")
        python_files = list(self.workspace.rglob("*.py"))
        print(f"   Found {len(python_files)} Python files")
        
        file_hashes = defaultdict(list)
        files_with_headers = 0
        total_lines = 0
        
        for idx, py_file in enumerate(python_files, 1):
            if idx % 1000 == 0:
                print(f"   Progress: {idx}/{len(python_files)} files...")
            
            try:
                rel_path = str(py_file.relative_to(self.workspace))
                
                # Calculate hash
                with open(py_file, 'rb') as f:
                    file_hash = hashlib.md5(f.read()).hexdigest()[:12]
                file_hashes[file_hash].append(rel_path)
                
                # Count lines and check for version header
                with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    lines = content.count('\n')
                    total_lines += lines
                    
                    # Check for version header
                    if re.search(r'__version__|VERSION|@version', content[:500]):
                        files_with_headers += 1
                
                metrics["files"][rel_path] = {
                    "hash": file_hash,
                    "lines": lines,
                    "size": py_file.stat().st_size
                }
                
            except Exception as e:
                continue
        
        # Identify duplicates
        print("\n[ANALYZE] Identifying duplicates...")
        duplicates = {h: files for h, files in file_hashes.items() if len(files) > 1}
        print(f"   Found {len(duplicates)} duplicate groups")
        
        metrics["duplicates"] = duplicates
        
        # Sample import issues (check 500 files)
        print("\n[ANALYZE] Sampling import issues (500 files)...")
        sample_files = python_files[:500] if len(python_files) > 500 else python_files
        import_issues = []
        
        for py_file in sample_files:
            try:
                with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    # Look for common import issues
                    if re.search(r'from\s+\.\.\.|import\s+\.\.\.', content):
                        rel_path = str(py_file.relative_to(self.workspace))
                        import_issues.append(rel_path)
            except Exception:
                continue
        
        print(f"   Found {len(import_issues)} potential import issues in sample")
        metrics["import_issues"] = import_issues
        
        # Summary
        metrics["summary"] = {
            "total_files": len(python_files),
            "total_lines": total_lines,
            "duplicate_groups": len(duplicates),
            "duplicate_files": sum(len(files) - 1 for files in duplicates.values()),
            "files_with_version_headers": files_with_headers,
            "version_header_percentage": round(files_with_headers / len(python_files) * 100, 2) if python_files else 0,
            "estimated_import_issues": int(len(import_issues) * (len(python_files) / len(sample_files)))
        }
        
        print("\n[SUMMARY]")
        print(f"   Total Python files: {metrics['summary']['total_files']}")
        print(f"   Total lines: {metrics['summary']['total_lines']:,}")
        print(f"   Duplicate groups: {metrics['summary']['duplicate_groups']}")
        print(f"   Duplicate files: {metrics['summary']['duplicate_files']}")
        print(f"   Version headers: {files_with_headers} ({metrics['summary']['version_header_percentage']}%)")
        print(f"   Estimated import issues: {metrics['summary']['estimated_import_issues']}")
        
        # Save metrics
        output_file = self.output_dir / f"metrics_{self.output_suffix}_{self.execution_id}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(metrics, f, indent=2)
        
        print(f"\n[SAVE] Metrics saved to {output_file}")
        
        return metrics

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Fast PRE-CD metrics collector")
    parser.add_argument("--workspace", default=".", help="Workspace path")
    parser.add_argument("--output-suffix", default="pre", help="Output file suffix (pre/post)")

    args = parser.parse_args()

    collector = FastMetricsCollector(Path(args.workspace), output_suffix=args.output_suffix)
    metrics = collector.collect_fast_metrics()
    
    print("\n" + "="*80)
    print("METRICS COLLECTION COMPLETE")
    print("="*80)

if __name__ == "__main__":
    main()
