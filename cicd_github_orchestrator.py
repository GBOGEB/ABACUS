"""
CI/CD GITHUB ROUNDTRIP ORCHESTRATOR
====================================

Complete CI/CD pipeline with pre/post metrics, refactoring, and GitHub roundtrip validation.

Features:
- Pre-CD metrics collection
- Code refactoring and reorganization
- GitHub push/pull roundtrip
- Post-CD validation and comparison
- Automated improvement detection

Version: 1.0.0
Date: 2025-01-24
"""

import sys
import os

os.environ['PYTHONIOENCODING'] = 'utf-8'

import json
import subprocess
import hashlib
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
from importlib import import_module

@dataclass
class MetricsSnapshot:
    """Snapshot of codebase metrics"""
    timestamp: str
    total_files: int
    total_lines: int
    python_files: int
    duplicate_files: int
    import_issues: int
    version_headers: int
    file_hashes: Dict[str, str]
    directory_structure: Dict[str, int]
    
@dataclass
class RefactoringPlan:
    """Plan for code refactoring and reorganization"""
    moves: List[Dict[str, str]]
    renames: List[Dict[str, str]]
    consolidations: List[Dict[str, List[str]]]
    deletions: List[str]

class CICDGitHubOrchestrator:
    """Orchestrates complete CI/CD pipeline with GitHub roundtrip"""
    
    def __init__(self, workspace: Path):
        self.workspace = Path(workspace)
        self.output_dir = self.workspace / "DMAIC_INTEGRATION_OUTPUT" / "cicd_github"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.execution_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.pre_metrics: Optional[MetricsSnapshot] = None
        self.post_metrics: Optional[MetricsSnapshot] = None
        
        sys.path.insert(0, str(self.workspace))
    
    def collect_metrics(self, label: str) -> MetricsSnapshot:
        """Collect comprehensive codebase metrics (optimized for large codebases)"""
        import random

        print(f"\n[METRICS] Collecting {label} metrics...")

        py_files = list(self.workspace.rglob("*.py"))
        py_files = [f for f in py_files if not any(skip in str(f) for skip in ['.git', '__pycache__', 'venv', 'BACKUPS', 'node_modules'])]

        print(f"   Found {len(py_files)} Python files")

        total_lines = 0
        file_hashes = {}
        version_headers = 0

        batch_size = 500
        for idx, py_file in enumerate(py_files):
            if idx % batch_size == 0 and idx > 0:
                print(f"   Progress: {idx}/{len(py_files)} files...")

            try:
                content = py_file.read_text(encoding='utf-8', errors='ignore')
                lines = content.count('\n')
                total_lines += lines

                file_hash = hashlib.sha256(content.encode('utf-8', errors='ignore')).hexdigest()[:12]
                file_hashes[str(py_file.relative_to(self.workspace))] = file_hash

                if '__version__' in content or 'Version:' in content:
                    version_headers += 1
            except Exception:
                pass

        hash_counts = {}
        for file_hash in file_hashes.values():
            hash_counts[file_hash] = hash_counts.get(file_hash, 0) + 1
        duplicate_files = sum(count - 1 for count in hash_counts.values() if count > 1)

        import_issues = 0
        old_patterns = ["from DMAIC_V3.core", "from ranking_engine import"]

        sample_size = min(300, len(py_files))
        random.seed(42)
        sample_files = random.sample(py_files, sample_size) if len(py_files) > sample_size else py_files

        for py_file in sample_files:
            try:
                content = py_file.read_text(encoding='utf-8', errors='ignore')
                if any(pattern in content for pattern in old_patterns):
                    import_issues += 1
            except Exception:
                pass

        if len(py_files) > sample_size:
            import_issues = int(import_issues * (len(py_files) / sample_size))

        dir_structure = {}
        for py_file in py_files:
            try:
                parent = str(py_file.parent.relative_to(self.workspace))
                dir_structure[parent] = dir_structure.get(parent, 0) + 1
            except Exception:
                pass

        all_files = []
        for ext in ['*.py', '*.md', '*.json', '*.txt', '*.yaml', '*.yml']:
            all_files.extend(self.workspace.rglob(ext))
        all_files = [f for f in all_files if not any(skip in str(f) for skip in ['.git', '__pycache__', 'venv', 'BACKUPS', 'node_modules'])]

        metrics = MetricsSnapshot(
            timestamp=datetime.now().isoformat(),
            total_files=len(all_files),
            total_lines=total_lines,
            python_files=len(py_files),
            duplicate_files=duplicate_files,
            import_issues=import_issues,
            version_headers=version_headers,
            file_hashes=file_hashes,
            directory_structure=dir_structure
        )

        print(f"   [OK] Total files: {metrics.total_files}")
        print(f"   [OK] Python files: {metrics.python_files}")
        print(f"   [OK] Total lines: {metrics.total_lines:,}")
        print(f"   [OK] Duplicates: {metrics.duplicate_files}")
        print(f"   [OK] Import issues (est): {metrics.import_issues}")
        print(f"   [OK] Version headers: {metrics.version_headers}")

        return metrics
    
    def save_metrics(self, metrics: MetricsSnapshot, label: str):
        """Save metrics to JSON"""
        output_file = self.output_dir / f"metrics_{label}_{self.execution_id}.json"
        
        metrics_dict = asdict(metrics)
        if len(str(metrics_dict.get('file_hashes', {}))) > 100000:
            metrics_dict['file_hashes'] = f"<{len(metrics.file_hashes)} files>"
        
        output_file.write_text(json.dumps(metrics_dict, indent=2), encoding='utf-8')
        print(f"   [OK] Saved: {output_file.relative_to(self.workspace)}")
    
    def analyze_refactoring_needs(self) -> RefactoringPlan:
        """Analyze codebase and create refactoring plan"""
        print("\n[SCAN] Analyzing refactoring needs...")
        
        plan = RefactoringPlan(
            moves=[],
            renames=[],
            consolidations=[],
            deletions=[]
        )
        
        misc_dir = self.workspace / "12_ORGANIZED_BY_CATEGORY" / "MISC_SCRIPTS"
        if misc_dir.exists():
            misc_scripts = list(misc_dir.glob("*.py"))
            for script in misc_scripts:
                if "test" in script.name.lower():
                    plan.moves.append({
                        "from": str(script.relative_to(self.workspace)),
                        "to": f"12_ORGANIZED_BY_CATEGORY/TEST_SUITES/{script.name}",
                        "reason": "Move test files to TEST_SUITES"
                    })
                elif "validate" in script.name.lower():
                    plan.moves.append({
                        "from": str(script.relative_to(self.workspace)),
                        "to": f"12_ORGANIZED_BY_CATEGORY/VALIDATION/{script.name}",
                        "reason": "Move validation files to VALIDATION"
                    })
        
        ranking_engines = list(self.workspace.rglob("ranking_engine.py"))
        ranking_engines = [f for f in ranking_engines if "13_CORE_SYSTEMS" not in str(f) and ".git" not in str(f) and "BACKUPS" not in str(f)]
        
        if len(ranking_engines) > 0:
            primary = self.workspace / "13_CORE_SYSTEMS/DMAIC/DMAIC_V3/core/ranking_engine.py"
            if primary.exists():
                for dup in ranking_engines:
                    plan.deletions.append(str(dup.relative_to(self.workspace)))
        
        print(f"   Moves planned: {len(plan.moves)}")
        print(f"   Renames planned: {len(plan.renames)}")
        print(f"   Consolidations planned: {len(plan.consolidations)}")
        print(f"   Deletions planned: {len(plan.deletions)}")
        
        return plan
    
    def execute_refactoring(self, plan: RefactoringPlan, dry_run: bool = False) -> Dict:
        """Execute refactoring plan"""
        print(f"\n[REFACTOR] Executing refactoring {'(DRY RUN)' if dry_run else '(LIVE)'}...")
        
        results = {
            "moves_executed": [],
            "renames_executed": [],
            "consolidations_executed": [],
            "deletions_executed": [],
            "errors": []
        }
        
        for move in plan.moves:
            try:
                src = self.workspace / move["from"]
                dst = self.workspace / move["to"]
                
                if src.exists():
                    if not dry_run:
                        dst.parent.mkdir(parents=True, exist_ok=True)
                        src.rename(dst)
                    
                    results["moves_executed"].append(move)
                    print(f"   [OK] Moved: {move['from']} -> {move['to']}")
            except Exception as e:
                error = f"Move failed: {move['from']} - {str(e)}"
                results["errors"].append(error)
                print(f"   [ERROR] {error}")
        
        for deletion in plan.deletions:
            try:
                file_path = self.workspace / deletion
                if file_path.exists():
                    if not dry_run:
                        file_path.unlink()
                    
                    results["deletions_executed"].append(deletion)
                    print(f"   [OK] Deleted: {deletion}")
            except Exception as e:
                error = f"Deletion failed: {deletion} - {str(e)}"
                results["errors"].append(error)
                print(f"   [ERROR] {error}")
        
        return results
    
    def git_status(self) -> Dict:
        """Get git status"""
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.workspace,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            lines = result.stdout.strip().split('\n') if result.stdout.strip() else []
            
            return {
                "has_changes": len(lines) > 0,
                "modified": [l[3:] for l in lines if l.startswith(' M')],
                "added": [l[3:] for l in lines if l.startswith('A ')],
                "deleted": [l[3:] for l in lines if l.startswith(' D')],
                "untracked": [l[3:] for l in lines if l.startswith('??')]
            }
        except Exception as e:
            return {"error": str(e), "has_changes": False}
    
    def git_commit_push(self, message: str) -> Dict:
        """Commit and push changes to GitHub"""
        print(f"\n[PUSH] Committing and pushing to GitHub...")
        
        try:
            subprocess.run(["git", "add", "."], cwd=self.workspace, check=True, timeout=30)
            print("   [OK] Staged changes")
            
            subprocess.run(
                ["git", "commit", "-m", message],
                cwd=self.workspace,
                check=True,
                timeout=30
            )
            print("   [OK] Committed changes")
            
            result = subprocess.run(
                ["git", "push"],
                cwd=self.workspace,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode == 0:
                print("   [OK] Pushed to GitHub")
                return {"success": True, "output": result.stdout}
            else:
                print(f"   [ERROR] Push failed: {result.stderr}")
                return {"success": False, "error": result.stderr}
        
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Git operation timed out"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def git_pull(self) -> Dict:
        """Pull latest changes from GitHub"""
        print(f"\n[PULL] Pulling from GitHub...")
        
        try:
            result = subprocess.run(
                ["git", "pull"],
                cwd=self.workspace,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode == 0:
                print("   [OK] Pulled from GitHub")
                return {"success": True, "output": result.stdout}
            else:
                print(f"   [ERROR] Pull failed: {result.stderr}")
                return {"success": False, "error": result.stderr}
        
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Git pull timed out"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def compare_metrics(self) -> Dict:
        """Compare pre and post metrics"""
        print("\n[METRICS] Comparing metrics...")
        
        if not self.pre_metrics or not self.post_metrics:
            return {"error": "Missing metrics"}
        
        comparison = {
            "files_changed": self.post_metrics.total_files - self.pre_metrics.total_files,
            "lines_changed": self.post_metrics.total_lines - self.pre_metrics.total_lines,
            "duplicates_removed": self.pre_metrics.duplicate_files - self.post_metrics.duplicate_files,
            "import_issues_fixed": self.pre_metrics.import_issues - self.post_metrics.import_issues,
            "version_headers_added": self.post_metrics.version_headers - self.pre_metrics.version_headers,
            "improvements": []
        }
        
        if comparison["duplicates_removed"] > 0:
            comparison["improvements"].append(f"Removed {comparison['duplicates_removed']} duplicate files")
        
        if comparison["import_issues_fixed"] > 0:
            comparison["improvements"].append(f"Fixed {comparison['import_issues_fixed']} import issues")
        
        if comparison["version_headers_added"] > 0:
            comparison["improvements"].append(f"Added {comparison['version_headers_added']} version headers")
        
        print(f"   Files: {comparison['files_changed']:+d}")
        print(f"   Lines: {comparison['lines_changed']:+d}")
        print(f"   Duplicates removed: {comparison['duplicates_removed']}")
        print(f"   Import issues fixed: {comparison['import_issues_fixed']}")
        print(f"   Version headers added: {comparison['version_headers_added']}")
        
        return comparison
    
    def validate_post_roundtrip(self) -> Dict:
        """Validate codebase after GitHub roundtrip"""
        print("\n[OK] Validating post-roundtrip...")
        
        validations = {
            "imports_valid": False,
            "no_duplicates": False,
            "structure_intact": False,
            "errors": []
        }
        
        try:
            ranking_module = import_module("13_CORE_SYSTEMS.DMAIC.DMAIC_V3.core.ranking_engine")
            if hasattr(ranking_module, 'RankingEngine'):
                validations["imports_valid"] = True
                print("   [OK] Imports valid")
        except Exception as e:
            validations["errors"].append(f"Import validation failed: {str(e)}")
            print(f"   [ERROR] Import validation failed")
        
        if self.post_metrics and self.post_metrics.duplicate_files == 0:
            validations["no_duplicates"] = True
            print("   [OK] No duplicates")
        else:
            print(f"   [WARN] {self.post_metrics.duplicate_files if self.post_metrics else 0} duplicates found")
        
        critical_dirs = [
            "13_CORE_SYSTEMS/DMAIC",
            "13_CORE_SYSTEMS/CENTRAL_LIBRARY",
            "12_ORGANIZED_BY_CATEGORY"
        ]
        
        all_exist = all((self.workspace / d).exists() for d in critical_dirs)
        if all_exist:
            validations["structure_intact"] = True
            print("   [OK] Structure intact")
        else:
            print("   [ERROR] Structure compromised")
        
        return validations
    
    def execute_full_pipeline(self, dry_run: bool = False) -> Dict:
        """Execute complete CI/CD pipeline"""
        print("\n" + "=" * 80)
        print("CI/CD GITHUB ROUNDTRIP PIPELINE")
        print("=" * 80)
        print(f"Workspace: {self.workspace}")
        print(f"Mode: {'DRY RUN' if dry_run else 'LIVE EXECUTION'}")
        print(f"Execution ID: {self.execution_id}")
        print("=" * 80)
        
        pipeline_results = {
            "execution_id": self.execution_id,
            "timestamp": datetime.now().isoformat(),
            "dry_run": dry_run,
            "stages": {}
        }
        
        self.pre_metrics = self.collect_metrics("PRE")
        self.save_metrics(self.pre_metrics, "pre")
        pipeline_results["stages"]["pre_metrics"] = {
            "total_files": self.pre_metrics.total_files,
            "python_files": self.pre_metrics.python_files,
            "total_lines": self.pre_metrics.total_lines,
            "duplicates": self.pre_metrics.duplicate_files,
            "import_issues": self.pre_metrics.import_issues
        }
        
        git_status = self.git_status()
        pipeline_results["stages"]["git_status_before"] = git_status
        print(f"\n[METRICS] Git status: {git_status.get('has_changes', False)}")
        
        refactoring_plan = self.analyze_refactoring_needs()
        pipeline_results["stages"]["refactoring_plan"] = asdict(refactoring_plan)
        
        refactoring_results = self.execute_refactoring(refactoring_plan, dry_run=dry_run)
        pipeline_results["stages"]["refactoring_results"] = refactoring_results
        
        if not dry_run and git_status.get('has_changes', False):
            commit_msg = f"CI/CD: Refactoring and reconciliation - {self.execution_id}"
            push_result = self.git_commit_push(commit_msg)
            pipeline_results["stages"]["git_push"] = push_result
            
            if push_result.get("success"):
                pull_result = self.git_pull()
                pipeline_results["stages"]["git_pull"] = pull_result
        
        self.post_metrics = self.collect_metrics("POST")
        self.save_metrics(self.post_metrics, "post")
        pipeline_results["stages"]["post_metrics"] = {
            "total_files": self.post_metrics.total_files,
            "python_files": self.post_metrics.python_files,
            "total_lines": self.post_metrics.total_lines,
            "duplicates": self.post_metrics.duplicate_files,
            "import_issues": self.post_metrics.import_issues
        }
        
        comparison = self.compare_metrics()
        pipeline_results["stages"]["metrics_comparison"] = comparison
        
        validation = self.validate_post_roundtrip()
        pipeline_results["stages"]["post_validation"] = validation
        
        report_file = self.output_dir / f"cicd_pipeline_{self.execution_id}.json"
        report_file.write_text(json.dumps(pipeline_results, indent=2), encoding='utf-8')
        
        print("\n" + "=" * 80)
        print("PIPELINE COMPLETE")
        print("=" * 80)
        print(f"Report: {report_file.relative_to(self.workspace)}")
        print(f"Improvements: {len(comparison.get('improvements', []))}")
        print("=" * 80)
        
        if comparison.get('improvements'):
            print("\n[SUCCESS] IMPROVEMENTS DETECTED:")
            for improvement in comparison['improvements']:
                print(f"   - {improvement}")
        
        return pipeline_results


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="CI/CD GitHub Roundtrip Orchestrator")
    parser.add_argument("--dry-run", action="store_true", help="Run in dry-run mode")
    parser.add_argument("--workspace", default=".", help="Workspace directory")
    
    args = parser.parse_args()
    
    workspace = Path(args.workspace).resolve()
    
    orchestrator = CICDGitHubOrchestrator(workspace)
    
    results = orchestrator.execute_full_pipeline(dry_run=args.dry_run)
    
    if not args.dry_run:
        print("\n[OK] CI/CD pipeline executed successfully")
    else:
        print("\n[OK] DRY RUN complete - no changes made")
        print("Run without --dry-run to execute changes")


if __name__ == "__main__":
    main()
