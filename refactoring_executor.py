#!/usr/bin/env python3
"""
# Version: 1.0.0
# Date: 2025-11-25
# Description: Auto-generated version header
"""

"""
REFACTORING EXECUTOR
Executes refactoring plan based on PRE-CD metrics
"""

import os
import sys
import json
import shutil
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List

os.environ['PYTHONIOENCODING'] = 'utf-8'
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

class RefactoringExecutor:
    def __init__(self, metrics_file: Path, dry_run: bool = False, batch_size: int = 1000):
        self.metrics_file = metrics_file
        self.dry_run = dry_run
        self.batch_size = batch_size
        self.execution_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.backup_dir = Path(f"BACKUPS/refactoring_{self.execution_id}")
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        with open(metrics_file, 'r', encoding='utf-8') as f:
            self.metrics = json.load(f)

        self.stats = {
            "duplicates_removed": 0,
            "imports_fixed": 0,
            "headers_added": 0,
            "batches_processed": 0,
            "errors": []
        }
    
    def backup_file(self, file_path: Path):
        """Backup file before modification"""
        if not self.dry_run:
            backup_path = self.backup_dir / file_path
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file_path, backup_path)
            print(f"   [BACKUP] {file_path} -> {backup_path}")
    
    def remove_duplicates(self):
        """Remove duplicate files in batches, keeping primary with smart selection"""
        print("\n[REFACTOR] Removing duplicates with smart selection (batched)...")

        duplicates = self.metrics.get("duplicates", {})

        files_to_remove = []
        for file_hash, files in duplicates.items():
            if len(files) <= 1:
                continue

            primary = None

            for f in files:
                file_path = Path(f)
                if not file_path.exists():
                    continue

                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as fp:
                        content = fp.read()

                    if any(marker in content[:500] for marker in ['__version__', 'VERSION', '@version', '# Version:']):
                        primary = f
                        print(f"   [PRESERVE] {f} (has version header)")
                        break
                except Exception:
                    continue

            if not primary:
                for f in files:
                    if "13_CORE_SYSTEMS" in f:
                        primary = f
                        break

            if not primary:
                primary = files[0]

            for f in files:
                if f != primary:
                    files_to_remove.append((f, primary))

        total_files = len(files_to_remove)
        print(f"   Total duplicates to remove: {total_files}")

        for batch_num in range(0, total_files, self.batch_size):
            batch = files_to_remove[batch_num:batch_num + self.batch_size]
            batch_id = batch_num // self.batch_size + 1
            total_batches = (total_files - 1) // self.batch_size + 1

            print(f"\n[BATCH {batch_id}/{total_batches}] Processing {len(batch)} files...")

            for f, primary in batch:
                file_path = Path(f)
                if file_path.exists():
                    print(f"   [REMOVE] {f} (duplicate of {primary})")

                    if not self.dry_run:
                        try:
                            self.backup_file(file_path)
                            file_path.unlink()
                            self.stats["duplicates_removed"] += 1
                        except Exception as e:
                            error_msg = f"Error removing {f}: {str(e)}"
                            print(f"   [ERROR] {error_msg}")
                            self.stats["errors"].append(error_msg)
                    else:
                        self.stats["duplicates_removed"] += 1

            self.stats["batches_processed"] += 1
            print(f"[OK] Batch {batch_id}/{total_batches} complete ({self.stats['duplicates_removed']} removed so far)")

            if not self.dry_run and batch_id < total_batches:
                time.sleep(0.5)

        print(f"\n[OK] Removed {self.stats['duplicates_removed']} duplicate files in {self.stats['batches_processed']} batches")
        return self.stats["duplicates_removed"]
    
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
    
    def add_version_headers(self, max_files: int = 5000):
        """Add version headers to files missing them (batched)"""
        print(f"\n[REFACTOR] Adding version headers (target: {max_files} files)...")

        files = self.metrics.get("files", {})

        # Collect files without version headers
        files_to_update = []
        for file_path_str, file_info in files.items():
            file_path = Path(file_path_str)
            if file_path.exists():
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()

                    if not any(marker in content[:500] for marker in ['__version__', 'VERSION', '@version', '# Version:']):
                        files_to_update.append(file_path)

                        if len(files_to_update) >= max_files:
                            break
                except Exception:
                    continue

        total_files = len(files_to_update)
        print(f"   Total files to update: {total_files}")

        # Process in batches
        for batch_num in range(0, total_files, self.batch_size):
            batch = files_to_update[batch_num:batch_num + self.batch_size]
            batch_id = batch_num // self.batch_size + 1
            total_batches = (total_files - 1) // self.batch_size + 1

            print(f"\n[BATCH {batch_id}/{total_batches}] Processing {len(batch)} files...")

            for file_path in batch:
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()

                    # Add version header after shebang/encoding if present
                    lines = content.split('\n')
                    insert_pos = 0

                    for i, line in enumerate(lines[:5]):
                        if line.startswith('#!') or 'coding' in line or 'encoding' in line:
                            insert_pos = i + 1

                    version_header = f'''"""
# Version: 1.0.0
# Date: {datetime.now().strftime("%Y-%m-%d")}
# Description: Auto-generated version header
"""
'''

                    lines.insert(insert_pos, version_header)
                    new_content = '\n'.join(lines)

                    print(f"   [ADD] Version header to {file_path}")

                    if not self.dry_run:
                        try:
                            self.backup_file(file_path)
                            with open(file_path, 'w', encoding='utf-8') as f:
                                f.write(new_content)
                            self.stats["headers_added"] += 1
                        except Exception as e:
                            error_msg = f"Error adding header to {file_path}: {str(e)}"
                            print(f"   [ERROR] {error_msg}")
                            self.stats["errors"].append(error_msg)
                    else:
                        self.stats["headers_added"] += 1

                except Exception as e:
                    error_msg = f"Error processing {file_path}: {str(e)}"
                    print(f"   [ERROR] {error_msg}")
                    self.stats["errors"].append(error_msg)

            self.stats["batches_processed"] += 1
            print(f"[OK] Batch {batch_id}/{total_batches} complete ({self.stats['headers_added']} headers added so far)")

            # Small delay between batches
            if not self.dry_run and batch_id < total_batches:
                time.sleep(0.5)

        print(f"\n[OK] Added {self.stats['headers_added']} version headers in {self.stats['batches_processed']} batches")
        return self.stats["headers_added"]

    def execute_refactoring(self, actions: List[str] = None, max_headers: int = 5000):
        """Execute complete refactoring plan"""
        print("\n" + "="*80)
        print("REFACTORING EXECUTOR V3 - SMART DUPLICATE HANDLING")
        print("="*80)
        print(f"Metrics File: {self.metrics_file}")
        print(f"Mode: {'DRY RUN' if self.dry_run else 'LIVE'}")
        print(f"Batch Size: {self.batch_size}")
        print(f"Execution ID: {self.execution_id}")
        print(f"Backup Dir: {self.backup_dir}")
        print("="*80)

        if actions is None:
            actions = ["headers", "duplicates", "imports"]

        start_time = time.time()

        if "headers" in actions:
            self.add_version_headers(max_files=max_headers)

        if "duplicates" in actions:
            self.remove_duplicates()

        if "imports" in actions:
            self.fix_import_paths()

        elapsed_time = time.time() - start_time

        output_dir = Path("DMAIC_INTEGRATION_OUTPUT/cicd_github")
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"refactoring_{self.execution_id}.json"

        results = {
            "execution_id": self.execution_id,
            "timestamp": datetime.now().isoformat(),
            "metrics_file": str(self.metrics_file),
            "dry_run": self.dry_run,
            "batch_size": self.batch_size,
            "elapsed_time_seconds": round(elapsed_time, 2),
            "actions_executed": actions,
            "stats": self.stats
        }

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2)

        print(f"\n[SAVE] Results saved to {output_file}")

        print("\n" + "="*80)
        print("REFACTORING COMPLETE")
        print("="*80)
        print(f"Duplicates removed: {self.stats['duplicates_removed']}")
        print(f"Imports fixed: {self.stats['imports_fixed']}")
        print(f"Headers added: {self.stats['headers_added']}")
        print(f"Batches processed: {self.stats['batches_processed']}")
        print(f"Errors: {len(self.stats['errors'])}")
        print(f"Elapsed time: {elapsed_time:.2f} seconds")
        print("="*80)

        return results

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Refactoring executor v3 - smart duplicate handling")
    parser.add_argument("--metrics", required=True, help="Path to PRE-CD metrics JSON file")
    parser.add_argument("--dry-run", action="store_true", help="Dry run mode (no changes)")
    parser.add_argument("--batch-size", type=int, default=1000, help="Batch size for processing (default: 1000)")
    parser.add_argument("--actions", nargs="+", choices=["duplicates", "imports", "headers"],
                        default=["headers", "duplicates", "imports"],
                        help="Actions to execute (default: headers, duplicates, imports)")
    parser.add_argument("--max-headers", type=int, default=60000, help="Maximum headers to add (default: 60000)")

    args = parser.parse_args()

    executor = RefactoringExecutor(Path(args.metrics), args.dry_run, args.batch_size)
    executor.execute_refactoring(actions=args.actions, max_headers=args.max_headers)

if __name__ == "__main__":
    main()
