#!/usr/bin/env python3
"""
REFACTORING EXECUTOR
Executes refactoring plan based on PRE-CD metrics
"""

import os
import sys
import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List

os.environ['PYTHONIOENCODING'] = 'utf-8'
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

class RefactoringExecutor:
    def __init__(self, metrics_file: Path, dry_run: bool = False):
        self.metrics_file = metrics_file
        self.dry_run = dry_run
        self.execution_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.backup_dir = Path(f"BACKUPS/refactoring_{self.execution_id}")
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        with open(metrics_file, 'r', encoding='utf-8') as f:
            self.metrics = json.load(f)
    
    def backup_file(self, file_path: Path):
        """Backup file before modification"""
        if not self.dry_run:
            backup_path = self.backup_dir / file_path
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file_path, backup_path)
            print(f"   [BACKUP] {file_path} -> {backup_path}")
    
    def remove_duplicates(self):
        """Remove duplicate files, keeping primary in 13_CORE_SYSTEMS"""
        print("\n[REFACTOR] Removing duplicates...")
        
        duplicates = self.metrics.get("duplicates", {})
        removed_count = 0
        
        for file_hash, files in duplicates.items():
            if len(files) <= 1:
                continue
            
            # Prioritize files in 13_CORE_SYSTEMS
            primary = None
            for f in files:
                if "13_CORE_SYSTEMS" in f:
                    primary = f
                    break
            
            if not primary:
                primary = files[0]
            
            # Remove duplicates
            for f in files:
                if f != primary:
                    file_path = Path(f)
                    if file_path.exists():
                        print(f"   [REMOVE] {f} (duplicate of {primary})")
                        
                        if not self.dry_run:
                            self.backup_file(file_path)
                            file_path.unlink()
                        
                        removed_count += 1
        
        print(f"[OK] Removed {removed_count} duplicate files")
        return removed_count
    
    def fix_import_paths(self):
        """Fix import paths to use canonical paths"""
        print("\n[REFACTOR] Fixing import paths...")
        
        import_issues = self.metrics.get("import_issues", [])
        fixed_count = 0
        
        for file_path_str in import_issues:
            file_path = Path(file_path_str)
            if not file_path.exists():
                continue
            
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                # Fix relative imports
                original_content = content
                content = content.replace('from ...', 'from 13_CORE_SYSTEMS.')
                content = content.replace('from ..', 'from 13_CORE_SYSTEMS.')
                
                if content != original_content:
                    print(f"   [FIX] {file_path}")
                    
                    if not self.dry_run:
                        self.backup_file(file_path)
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(content)
                    
                    fixed_count += 1
            
            except Exception as e:
                print(f"   [ERROR] Failed to fix {file_path}: {e}")
        
        print(f"[OK] Fixed {fixed_count} import paths")
        return fixed_count
    
    def add_version_headers(self):
        """Add version headers to files missing them"""
        print("\n[REFACTOR] Adding version headers...")
        
        added_count = 0
        files = self.metrics.get("files", {})
        
        # Sample: add headers to first 100 files without them
        files_to_update = []
        for file_path_str, file_info in files.items():
            file_path = Path(file_path_str)
            if file_path.exists():
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    
                    if not any(marker in content[:500] for marker in ['__version__', 'VERSION', '@version']):
                        files_to_update.append(file_path)
                        
                        if len(files_to_update) >= 100:
                            break
                except Exception:
                    continue
        
        for file_path in files_to_update:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                # Add version header after shebang/encoding if present
                lines = content.split('\n')
                insert_pos = 0
                
                for i, line in enumerate(lines[:5]):
                    if line.startswith('#!') or 'coding' in line or 'encoding' in line:
                        insert_pos = i + 1
                
                version_header = f'"""\nVersion: 1.0.0\nLast Modified: {datetime.now().strftime("%Y-%m-%d")}\n"""\n'
                lines.insert(insert_pos, version_header)
                
                new_content = '\n'.join(lines)
                
                print(f"   [ADD] Version header to {file_path}")
                
                if not self.dry_run:
                    self.backup_file(file_path)
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                
                added_count += 1
            
            except Exception as e:
                print(f"   [ERROR] Failed to add header to {file_path}: {e}")
        
        print(f"[OK] Added {added_count} version headers")
        return added_count
    
    def execute_refactoring(self):
        """Execute complete refactoring plan"""
        print("\n" + "="*80)
        print("REFACTORING EXECUTOR")
        print("="*80)
        print(f"Metrics File: {self.metrics_file}")
        print(f"Mode: {'DRY RUN' if self.dry_run else 'LIVE'}")
        print(f"Execution ID: {self.execution_id}")
        print(f"Backup Dir: {self.backup_dir}")
        print("="*80)
        
        results = {
            "execution_id": self.execution_id,
            "timestamp": datetime.now().isoformat(),
            "metrics_file": str(self.metrics_file),
            "dry_run": self.dry_run,
            "actions": {}
        }
        
        # Execute refactoring actions
        results["actions"]["duplicates_removed"] = self.remove_duplicates()
        results["actions"]["imports_fixed"] = self.fix_import_paths()
        results["actions"]["headers_added"] = self.add_version_headers()
        
        # Save results
        output_dir = Path("DMAIC_INTEGRATION_OUTPUT/cicd_github")
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"refactoring_{self.execution_id}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n[SAVE] Results saved to {output_file}")
        
        print("\n" + "="*80)
        print("REFACTORING COMPLETE")
        print("="*80)
        print(f"Duplicates removed: {results['actions']['duplicates_removed']}")
        print(f"Imports fixed: {results['actions']['imports_fixed']}")
        print(f"Headers added: {results['actions']['headers_added']}")
        print("="*80)
        
        return results

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Refactoring executor")
    parser.add_argument("--metrics", required=True, help="Path to PRE-CD metrics JSON file")
    parser.add_argument("--dry-run", action="store_true", help="Dry run mode (no changes)")
    
    args = parser.parse_args()
    
    executor = RefactoringExecutor(Path(args.metrics), args.dry_run)
    executor.execute_refactoring()

if __name__ == "__main__":
    main()
