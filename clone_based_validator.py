#!/usr/bin/env python3
"""
CLONE-BASED VALIDATION ORCHESTRATOR
Separate from Git workspace - validates code via fresh clone checksum
"""

import os
import sys
import json
import hashlib
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass, asdict
import tempfile
import shutil

os.environ['PYTHONIOENCODING'] = 'utf-8'
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

@dataclass
class DependencyNode:
    file_path: str
    imports: List[str]
    imported_by: List[str]
    checksum: str
    size_bytes: int
    last_modified: str

@dataclass
class CodeChecksum:
    total_files: int
    total_checksums: Dict[str, str]
    dependency_graph: Dict[str, DependencyNode]
    circular_dependencies: List[Tuple[str, str]]
    orphaned_files: List[str]
    entry_points: List[str]

class CloneBasedValidator:
    def __init__(self, repo_url: str, branch: str = "main"):
        self.repo_url = repo_url
        self.branch = branch
        self.clone_dir = None
        self.execution_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_dir = Path("DMAIC_INTEGRATION_OUTPUT/clone_validation")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def clone_repository(self) -> Path:
        """Clone repository to temporary directory"""
        print(f"\n[CLONE] Cloning repository from {self.repo_url}...")
        self.clone_dir = Path(tempfile.mkdtemp(prefix="cicd_clone_"))
        
        try:
            subprocess.run(
                ["git", "clone", "--branch", self.branch, "--depth", "1", self.repo_url, str(self.clone_dir)],
                check=True,
                capture_output=True,
                timeout=300
            )
            print(f"[OK] Repository cloned to {self.clone_dir}")
            return self.clone_dir
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] Clone failed: {e.stderr.decode('utf-8', errors='ignore')}")
            raise
        except subprocess.TimeoutExpired:
            print("[ERROR] Clone timeout after 300 seconds")
            raise
    
    def calculate_file_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum of file"""
        sha256 = hashlib.sha256()
        try:
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b''):
                    sha256.update(chunk)
            return sha256.hexdigest()[:16]
        except Exception as e:
            return f"ERROR:{str(e)[:20]}"
    
    def extract_imports(self, file_path: Path) -> List[str]:
        """Extract import statements from Python file"""
        imports = []
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('import ') or line.startswith('from '):
                        imports.append(line)
        except Exception:
            pass
        return imports
    
    def build_dependency_graph(self, clone_path: Path) -> Dict[str, DependencyNode]:
        """Build complete dependency graph from cloned repository"""
        print("\n[ANALYZE] Building dependency graph...")
        
        python_files = list(clone_path.rglob("*.py"))
        print(f"   Found {len(python_files)} Python files")
        
        dependency_graph = {}
        
        for idx, py_file in enumerate(python_files, 1):
            if idx % 500 == 0:
                print(f"   Progress: {idx}/{len(python_files)} files...")
            
            rel_path = str(py_file.relative_to(clone_path))
            imports = self.extract_imports(py_file)
            checksum = self.calculate_file_checksum(py_file)
            
            try:
                size = py_file.stat().st_size
                modified = datetime.fromtimestamp(py_file.stat().st_mtime).isoformat()
            except Exception:
                size = 0
                modified = "unknown"
            
            dependency_graph[rel_path] = DependencyNode(
                file_path=rel_path,
                imports=imports,
                imported_by=[],
                checksum=checksum,
                size_bytes=size,
                last_modified=modified
            )
        
        print(f"[OK] Dependency graph built: {len(dependency_graph)} nodes")
        return dependency_graph
    
    def detect_circular_dependencies(self, graph: Dict[str, DependencyNode]) -> List[Tuple[str, str]]:
        """Detect circular dependencies in the graph"""
        print("\n[ANALYZE] Detecting circular dependencies...")
        circular = []
        
        for file_path, node in graph.items():
            for import_stmt in node.imports:
                if 'from' in import_stmt:
                    parts = import_stmt.split()
                    if len(parts) >= 2:
                        module = parts[1].replace('.', '/')
                        potential_file = f"{module}.py"
                        
                        if potential_file in graph:
                            if file_path in [imp for imp in graph[potential_file].imports]:
                                circular.append((file_path, potential_file))
        
        print(f"[OK] Found {len(circular)} circular dependencies")
        return circular
    
    def find_orphaned_files(self, graph: Dict[str, DependencyNode]) -> List[str]:
        """Find files that are not imported by any other file"""
        print("\n[ANALYZE] Finding orphaned files...")
        
        imported_files = set()
        for node in graph.values():
            for import_stmt in node.imports:
                if 'from' in import_stmt:
                    parts = import_stmt.split()
                    if len(parts) >= 2:
                        module = parts[1].replace('.', '/')
                        imported_files.add(f"{module}.py")
        
        all_files = set(graph.keys())
        orphaned = list(all_files - imported_files)
        
        entry_points = [f for f in orphaned if '__main__' in open(Path(self.clone_dir) / f, 'r', encoding='utf-8', errors='ignore').read()]
        
        print(f"[OK] Found {len(orphaned)} orphaned files ({len(entry_points)} entry points)")
        return orphaned
    
    def calculate_code_checksum(self, clone_path: Path) -> CodeChecksum:
        """Calculate comprehensive code checksum"""
        print("\n[CHECKSUM] Calculating code checksums...")
        
        dependency_graph = self.build_dependency_graph(clone_path)
        circular_deps = self.detect_circular_dependencies(dependency_graph)
        orphaned = self.find_orphaned_files(dependency_graph)
        
        total_checksums = {
            file_path: node.checksum 
            for file_path, node in dependency_graph.items()
        }
        
        entry_points = [
            f for f in orphaned 
            if '__main__' in open(clone_path / f, 'r', encoding='utf-8', errors='ignore').read()
        ]
        
        checksum = CodeChecksum(
            total_files=len(dependency_graph),
            total_checksums=total_checksums,
            dependency_graph=dependency_graph,
            circular_dependencies=circular_deps,
            orphaned_files=orphaned,
            entry_points=entry_points
        )
        
        print(f"[OK] Code checksum calculated: {len(total_checksums)} files")
        return checksum
    
    def compare_with_workspace(self, workspace_path: Path) -> Dict:
        """Compare clone checksums with workspace checksums"""
        print("\n[COMPARE] Comparing clone with workspace...")
        
        workspace_files = list(workspace_path.rglob("*.py"))
        workspace_checksums = {}
        
        for py_file in workspace_files:
            rel_path = str(py_file.relative_to(workspace_path))
            workspace_checksums[rel_path] = self.calculate_file_checksum(py_file)
        
        clone_checksums = {
            file_path: node.checksum 
            for file_path, node in self.dependency_graph.items()
        }
        
        matching = sum(1 for f, cs in clone_checksums.items() if workspace_checksums.get(f) == cs)
        different = sum(1 for f, cs in clone_checksums.items() if workspace_checksums.get(f) != cs and f in workspace_checksums)
        clone_only = [f for f in clone_checksums if f not in workspace_checksums]
        workspace_only = [f for f in workspace_checksums if f not in clone_checksums]
        
        comparison = {
            "matching_files": matching,
            "different_files": different,
            "clone_only": clone_only,
            "workspace_only": workspace_only,
            "total_clone_files": len(clone_checksums),
            "total_workspace_files": len(workspace_checksums)
        }
        
        print(f"[OK] Comparison complete:")
        print(f"   Matching: {matching}")
        print(f"   Different: {different}")
        print(f"   Clone only: {len(clone_only)}")
        print(f"   Workspace only: {len(workspace_only)}")
        
        return comparison
    
    def save_results(self, checksum: CodeChecksum, comparison: Dict):
        """Save validation results"""
        output_file = self.output_dir / f"clone_validation_{self.execution_id}.json"
        
        results = {
            "execution_id": self.execution_id,
            "timestamp": datetime.now().isoformat(),
            "repo_url": self.repo_url,
            "branch": self.branch,
            "checksum": {
                "total_files": checksum.total_files,
                "total_checksums": checksum.total_checksums,
                "circular_dependencies": checksum.circular_dependencies,
                "orphaned_files": checksum.orphaned_files,
                "entry_points": checksum.entry_points
            },
            "comparison": comparison
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n[SAVE] Results saved to {output_file}")
    
    def cleanup(self):
        """Remove temporary clone directory"""
        if self.clone_dir and self.clone_dir.exists():
            print(f"\n[CLEANUP] Removing clone directory {self.clone_dir}...")
            shutil.rmtree(self.clone_dir, ignore_errors=True)
            print("[OK] Cleanup complete")
    
    def execute_validation(self, workspace_path: Path):
        """Execute complete clone-based validation"""
        print("\n" + "="*80)
        print("CLONE-BASED VALIDATION ORCHESTRATOR")
        print("="*80)
        print(f"Repository: {self.repo_url}")
        print(f"Branch: {self.branch}")
        print(f"Execution ID: {self.execution_id}")
        print("="*80 + "\n")
        
        try:
            clone_path = self.clone_repository()
            
            checksum = self.calculate_code_checksum(clone_path)
            self.dependency_graph = checksum.dependency_graph
            
            comparison = self.compare_with_workspace(workspace_path)
            
            self.save_results(checksum, comparison)
            
            print("\n" + "="*80)
            print("VALIDATION COMPLETE")
            print("="*80)
            
        except Exception as e:
            print(f"\n[ERROR] Validation failed: {e}")
            raise
        finally:
            self.cleanup()

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Clone-based validation orchestrator")
    parser.add_argument("--repo-url", required=True, help="Git repository URL")
    parser.add_argument("--branch", default="main", help="Branch to clone")
    parser.add_argument("--workspace", default=".", help="Workspace path to compare")
    
    args = parser.parse_args()
    
    validator = CloneBasedValidator(args.repo_url, args.branch)
    validator.execute_validation(Path(args.workspace))

if __name__ == "__main__":
    main()
