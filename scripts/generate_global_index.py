#!/usr/bin/env python3
"""
DMAIC V3 - GLOBAL Index Generator
Creates a single navigable index of all artifacts, versions, and dependencies
"""

import os
import json
import yaml
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import ast


@dataclass
class ArtifactInfo:
    id: str
    path: str
    maturity_level: int
    status: str
    hash_sha256: str
    stable_iterations: int
    size_bytes: int
    last_modified: str
    functions: List[str]
    classes: List[str]
    imports: List[str]
    tests: List[str]
    dependencies: List[str]
    
    def to_dict(self):
        return asdict(self)


class GlobalIndexGenerator:
    def __init__(self):
        self.workspace = Path('.')
        self.output_dir = Path('DMAIC_V3_OUTPUT')
        self.output_dir.mkdir(exist_ok=True)
        
        self.exclude_patterns = [
            '__pycache__',
            '.pyc',
            'DMAIC_V3_OUTPUT',
            'DMAIC_V23_OUTPUT',
            '.pytest_cache',
            'node_modules',
            '.venv',
            'temp_venv',
            '.log',
            '.git'
        ]
        
        self.maturity_mapping = self._load_maturity_mapping()
    
    def _load_maturity_mapping(self) -> Dict[str, int]:
        mapping = {
            'DMAIC_V3/core/': 1,
            'DMAIC_V3/phases/phase0': 1,
            'DMAIC_V3/phases/phase1': 1,
            'DMAIC_V3/config.py': 1,
            'DMAIC_V3/phases/phase2': 2,
            'DMAIC_V3/phases/phase3': 2,
            'DMAIC_V3/phases/phase4': 2,
            'DMAIC_V3/phases/phase5': 2,
            'DMAIC_V3/phases/phase6': 3,
            'DMAIC_V3/convergence/': 3,
            'DMAIC_V3/integrations/': 2,
        }
        return mapping
    
    def calculate_file_hash(self, file_path: Path) -> str:
        sha256 = hashlib.sha256()
        try:
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b''):
                    sha256.update(chunk)
            return sha256.hexdigest()
        except Exception:
            return "ERROR"
    
    def determine_maturity_level(self, file_path: str) -> int:
        for pattern, level in self.maturity_mapping.items():
            if pattern in file_path:
                return level
        return 0
    
    def get_stable_iterations(self, file_path: str) -> int:
        hash_file = self.output_dir / '.file_hashes.json'
        if not hash_file.exists():
            return 0
        
        try:
            with open(hash_file, 'r') as f:
                history = json.load(f)
                
                if len(history) < 2:
                    return 0
                
                current_hash = None
                stable_count = 0
                
                for entry in reversed(history):
                    file_hash = entry['hashes'].get(file_path)
                    if file_hash is None:
                        break
                    
                    if current_hash is None:
                        current_hash = file_hash
                        stable_count = 1
                    elif file_hash == current_hash:
                        stable_count += 1
                    else:
                        break
                
                return stable_count
        except Exception:
            return 0
    
    def extract_code_elements(self, file_path: Path) -> Dict[str, List[str]]:
        result = {
            'functions': [],
            'classes': [],
            'imports': []
        }
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read())
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        result['functions'].append(node.name)
                    elif isinstance(node, ast.ClassDef):
                        result['classes'].append(node.name)
                    elif isinstance(node, ast.Import):
                        for alias in node.names:
                            result['imports'].append(alias.name)
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            result['imports'].append(node.module)
        except Exception:
            pass
        
        return result
    
    def find_test_files(self, file_path: str) -> List[str]:
        tests = []
        file_name = Path(file_path).stem
        
        test_patterns = [
            f"tests/test_{file_name}.py",
            f"test_{file_name}.py",
            f"{file_name}_test.py"
        ]
        
        for pattern in test_patterns:
            test_file = self.workspace / pattern
            if test_file.exists():
                tests.append(str(test_file.relative_to(self.workspace)))
        
        return tests
    
    def analyze_dependencies(self, imports: List[str]) -> List[str]:
        dependencies = []
        
        for imp in imports:
            if imp.startswith('DMAIC_V3'):
                dependencies.append(imp)
        
        return dependencies
    
    def scan_artifacts(self) -> List[ArtifactInfo]:
        artifacts = []
        artifact_counter = 1
        
        for file in self.workspace.rglob('*.py'):
            if any(pattern in str(file) for pattern in self.exclude_patterns):
                continue
            
            if not file.is_file():
                continue
            
            file_str = str(file.relative_to(self.workspace))
            
            maturity_level = self.determine_maturity_level(file_str)
            stable_iterations = self.get_stable_iterations(file_str)
            
            status = "STABLE" if stable_iterations >= 3 else "ACTIVE" if stable_iterations > 0 else "NEW"
            
            code_elements = self.extract_code_elements(file)
            
            artifact = ArtifactInfo(
                id=f"ARTF_{datetime.now().strftime('%Y%m%d')}_{artifact_counter:04d}",
                path=file_str,
                maturity_level=maturity_level,
                status=status,
                hash_sha256=self.calculate_file_hash(file),
                stable_iterations=stable_iterations,
                size_bytes=file.stat().st_size,
                last_modified=datetime.fromtimestamp(file.stat().st_mtime).isoformat(),
                functions=code_elements['functions'],
                classes=code_elements['classes'],
                imports=code_elements['imports'],
                tests=self.find_test_files(file_str),
                dependencies=self.analyze_dependencies(code_elements['imports'])
            )
            
            artifacts.append(artifact)
            artifact_counter += 1
        
        return artifacts
    
    def get_convergence_metrics(self) -> Optional[Dict]:
        metrics_file = self.output_dir / '.convergence_history.json'
        if not metrics_file.exists():
            return None
        
        try:
            with open(metrics_file, 'r') as f:
                history = json.load(f)
                if history:
                    return history[-1]
        except Exception:
            return None
        
        return None
    
    def get_knowledge_summary(self) -> Dict[str, int]:
        knowledge_dir = self.output_dir / 'knowledge'
        if not knowledge_dir.exists():
            return {'total_packs': 0, 'total_iterations': 0}
        
        packs = list(knowledge_dir.glob('**/*.json'))
        iterations = set()
        
        for pack in packs:
            if 'ITERATION_' in str(pack):
                iteration = str(pack).split('ITERATION_')[1].split('/')[0]
                iterations.add(iteration)
        
        return {
            'total_packs': len(packs),
            'total_iterations': len(iterations)
        }
    
    def generate_index(self) -> Path:
        print("=" * 80)
        print("DMAIC V3 - GLOBAL INDEX GENERATOR")
        print("=" * 80)
        print()
        
        print("[1/4] Scanning workspace for artifacts...")
        artifacts = self.scan_artifacts()
        print(f"      Found {len(artifacts)} artifacts")
        
        print("[2/4] Loading convergence metrics...")
        convergence = self.get_convergence_metrics()
        if convergence:
            print(f"      Convergence score: {convergence['convergence_score']:.1f}%")
        else:
            print(f"      No convergence data available")
        
        print("[3/4] Loading knowledge summary...")
        knowledge = self.get_knowledge_summary()
        print(f"      Knowledge packs: {knowledge['total_packs']}")
        
        print("[4/4] Generating GLOBAL index...")
        
        maturity_stats = {0: 0, 1: 0, 2: 0, 3: 0}
        status_stats = {'NEW': 0, 'ACTIVE': 0, 'STABLE': 0}
        
        for artifact in artifacts:
            maturity_stats[artifact.maturity_level] += 1
            status_stats[artifact.status] += 1
        
        index = {
            'metadata': {
                'version': '3.2.0',
                'generated_at': datetime.now().isoformat(),
                'iteration': convergence['iteration'] if convergence else 1,
                'convergence_score': convergence['convergence_score'] if convergence else 0.0,
                'maturity_level': convergence['maturity_level'] if convergence else 0,
                'total_artifacts': len(artifacts),
                'total_knowledge_packs': knowledge['total_packs']
            },
            'statistics': {
                'by_maturity': {
                    'level_0_planning': maturity_stats[0],
                    'level_1_foundation': maturity_stats[1],
                    'level_2_development': maturity_stats[2],
                    'level_3_production': maturity_stats[3]
                },
                'by_status': status_stats,
                'total_functions': sum(len(a.functions) for a in artifacts),
                'total_classes': sum(len(a.classes) for a in artifacts),
                'total_tests': sum(len(a.tests) for a in artifacts)
            },
            'artifacts': {
                artifact.path: artifact.to_dict() for artifact in artifacts
            },
            'convergence': convergence,
            'knowledge': knowledge,
            'maturity_levels': {
                0: [a.path for a in artifacts if a.maturity_level == 0],
                1: [a.path for a in artifacts if a.maturity_level == 1],
                2: [a.path for a in artifacts if a.maturity_level == 2],
                3: [a.path for a in artifacts if a.maturity_level == 3]
            }
        }
        
        index_path = self.workspace / 'GLOBAL_index.json'
        with open(index_path, 'w', encoding='utf-8') as f:
            json.dump(index, f, indent=2)
        
        print()
        print("=" * 80)
        print("GLOBAL INDEX GENERATED")
        print("=" * 80)
        print(f"Path: {index_path}")
        print(f"Total Artifacts: {len(artifacts)}")
        print(f"Maturity Distribution:")
        print(f"  Level 0 (Planning):    {maturity_stats[0]}")
        print(f"  Level 1 (Foundation):  {maturity_stats[1]}")
        print(f"  Level 2 (Development): {maturity_stats[2]}")
        print(f"  Level 3 (Production):  {maturity_stats[3]}")
        print(f"Status Distribution:")
        print(f"  NEW:    {status_stats['NEW']}")
        print(f"  ACTIVE: {status_stats['ACTIVE']}")
        print(f"  STABLE: {status_stats['STABLE']}")
        print("=" * 80)
        
        return index_path


def main():
    generator = GlobalIndexGenerator()
    index_path = generator.generate_index()
    print(f"\nGLOBAL index saved to: {index_path}")
    return 0


if __name__ == "__main__":
    exit(main())
