"""
DMAIC V3.0 - Phase 2: Measure
Minimal Implementation - Static Analysis

Phase 2a: Baseline Measurement
- Analyze code metrics (LOC, functions, classes)
- Static complexity analysis
- File dependency detection
- KEB integration for parallel analysis
- 12-Cluster integration for distributed processing
"""

import os
import json
import ast
from pathlib import Path
from typing import Dict, List, Tuple, Any
from datetime import datetime
from collections import defaultdict

from ..core.state import StateManager
from ..core.utils import ensure_directory, safe_write_json
from ..config import DMAICConfig

try:
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from keb import KEB
    KEB_AVAILABLE = True
except ImportError:
    KEB_AVAILABLE = False
    print("Warning: KEB not available, falling back to sequential analysis")

try:
    from DMAIC_V3.core.twelve_cluster_orchestrator import TwelveClusterOrchestrator
    CLUSTER_AVAILABLE = True
except ImportError:
    CLUSTER_AVAILABLE = False
    print("Warning: 12-Cluster orchestrator not available")


class Phase2Measure:
    """
    Phase 2: Measure - Code metrics and static analysis

    Analyzes Python files to collect baseline metrics without execution.
    Supports parallel analysis via KEB and 12-Cluster orchestration.
    """

    def __init__(self, config: DMAICConfig, state_manager: StateManager,
                 use_keb: bool = False, use_12cluster: bool = True):
        """
        Initialize Phase 2: Measure

        Args:
            config: DMAICConfig instance
            state_manager: StateManager instance
            use_keb: Enable KEB parallel processing (default: False to avoid memory issues)
            use_12cluster: Enable 12-cluster parallel processing (default: True)
        """
        self.config = config
        self.state_manager = state_manager
        self.workspace_root = config.paths.workspace_root
        self.max_files_per_chunk = 5000
        self.use_keb = use_keb and KEB_AVAILABLE
        self.use_12cluster = use_12cluster and CLUSTER_AVAILABLE
        self.keb = None
        self.cluster_orchestrator = None

        if self.use_keb:
            print("[KEB] Initializing parallel analysis engine...")
            self.keb = KEB(max_workers=2, max_memory_mb=2048)

        if self.use_12cluster:
            print("[12-CLUSTER] Initializing distributed analysis...")
            self.cluster_orchestrator = TwelveClusterOrchestrator(
                max_workers=2,
                use_keb=False,
                use_gbogeb=True
            )

    def analyze_python_file(self, file_path: str) -> dict:
        """
        Analyze a single Python file statically

        Args:
            file_path: Path to Python file

        Returns:
            Dictionary with analysis results
        """
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            # Basic metrics
            lines = content.split('\n')
            loc = len([l for l in lines if l.strip() and not l.strip().startswith('#')])
            total_lines = len(lines)
            comment_lines = len([l for l in lines if l.strip().startswith('#')])

            # AST analysis
            try:
                tree = ast.parse(content)
                functions = []
                classes = []
                imports = []

                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        functions.append({
                            'name': node.name,
                            'line': node.lineno,
                            'args': len(node.args.args)
                        })
                    elif isinstance(node, ast.ClassDef):
                        classes.append({
                            'name': node.name,
                            'line': node.lineno
                        })
                    elif isinstance(node, (ast.Import, ast.ImportFrom)):
                        if isinstance(node, ast.Import):
                            for alias in node.names:
                                imports.append(alias.name)
                        else:
                            imports.append(node.module if node.module else '')

                # Calculate complexity score
                complexity = (
                    loc +
                    len(functions) * 2 +
                    len(classes) * 3 +
                    len(imports)
                )

                return {
                    'success': True,
                    'metrics': {
                        'total_lines': total_lines,
                        'lines_of_code': loc,
                        'comment_lines': comment_lines,
                        'functions': len(functions),
                        'classes': len(classes),
                        'imports': len(imports),
                        'complexity_score': complexity,
                    },
                    'details': {
                        'functions': functions[:10],  # Limit to first 10
                        'classes': classes[:10],
                        'imports': list(set(imports))[:20]  # Unique, limit 20
                    },
                    'error': None
                }

            except SyntaxError as e:
                return {
                    'success': False,
                    'metrics': {
                        'total_lines': total_lines,
                        'lines_of_code': loc,
                        'comment_lines': comment_lines,
                    },
                    'error': f'Syntax error: {str(e)[:100]}'
                }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)[:200]
            }

    def execute(self, iteration: int) -> Tuple[bool, dict]:
        """
        Execute Phase 2: Measure

        Args:
            iteration: Current iteration number

        Returns:
            Tuple of (success: bool, results: dict) with phase execution results
        """
        try:
            print("="*80)
            print(f"PHASE 2: MEASURE (Iteration {iteration})")
            print("="*80)
            print(f"Timestamp: {datetime.now().isoformat()}")
            print()

            # Load Phase 1 results
            phase1_file = self.config.paths.output_root / f"iteration_{iteration}" / "phase1_define" / "phase1_define.json"

            if not phase1_file.exists():
                raise FileNotFoundError(f"Phase 1 results not found: {phase1_file}")

            print(f"[2.1] Loading Phase 1 results...")
            with open(phase1_file, 'r', encoding='utf-8') as f:
                phase1_data = json.load(f)

            all_files = phase1_data.get('files', [])
            print(f"  Found {len(all_files)} files from Phase 1")
            print()

            # Filter Python files
            print("[2.2] Filtering Python files...")
            python_files = [f for f in all_files if f.endswith('.py')]
            print(f"  Python files to analyze: {len(python_files)}")
            print()

            # Analyze files with chunking
            print("[2.3] Analyzing Python files (chunked mode)...")
            measurements = []
            analyzed_count = 0
            error_count = 0

            total_files = len(python_files)
            chunk_size = self.max_files_per_chunk
            num_chunks = (total_files + chunk_size - 1) // chunk_size

            print(f"  Total files: {total_files}")
            print(f"  Chunk size: {chunk_size}")
            print(f"  Number of chunks: {num_chunks}")

            if self.use_12cluster:
                print(f"  [12-CLUSTER] Distributed analysis ENABLED (2 clusters)")
            elif self.use_keb:
                print(f"  [KEB] Parallel analysis ENABLED (2 workers)")
            else:
                print(f"  Sequential analysis mode")
            print()

            if self.use_12cluster and self.cluster_orchestrator:
                print(f"  [12-CLUSTER] Distributing analysis across clusters...")

                tasks = [
                    {
                        "func": self.analyze_python_file,
                        "args": (file_path,),
                        "file_path": file_path
                    }
                    for file_path in python_files
                ]

                cluster_results = self.cluster_orchestrator.execute_phase_parallel(
                    phase="phase2",
                    tasks=tasks,
                    iteration=iteration
                )

                executed = cluster_results.get("tasks_executed", len(cluster_results.get("results", [])))
                failed = cluster_results.get("tasks_failed", 0)
                print(f"  [12-CLUSTER] Analysis complete: {executed} files analyzed, {failed} failed")

                # Cluster orchestrator may already return results; prefer those if available
                results_map = cluster_results.get("results_map", {})
                for file_path in python_files:
                    # Prefer cluster returned result, fall back to local analysis if missing
                    result = results_map.get(file_path)
                    if result is None:
                        try:
                            result = self.analyze_python_file(file_path)
                        except Exception as e:
                            result = {'success': False, 'error': str(e)[:200]}
                    measurements.append({
                        'file_path': file_path,
                        'analysis': result
                    })
                    if result.get('success'):
                        analyzed_count += 1
                    else:
                        error_count += 1

            elif self.use_keb and self.keb:
                self.keb.start()
                analysis_results = {}

                for chunk_idx in range(num_chunks):
                    start_idx = chunk_idx * chunk_size
                    end_idx = min(start_idx + chunk_size, total_files)
                    chunk_files = python_files[start_idx:end_idx]

                    print(f"  [KEB] Scheduling chunk {chunk_idx + 1}/{num_chunks} ({len(chunk_files)} files)...")

                    for file_path in chunk_files:
                        task_id = f"analyze_{chunk_idx}_{file_path.replace('/', '_')[-50:]}"
                        self.keb.schedule_task(
                            task_id=task_id,
                            func=self.analyze_python_file,
                            priority=5,
                            args=(file_path,)
                        )

                print(f"  [KEB] Waiting for analysis to complete...")
                import time
                while not self.keb.task_queue.empty():
                    time.sleep(0.5)

                time.sleep(2)
                self.keb.stop()

                print(f"  [KEB] Analysis complete: {self.keb.tasks_executed} executed, {self.keb.tasks_failed} failed")

                for file_path in python_files:
                    result = self.analyze_python_file(file_path)
                    measurements.append({
                        'file_path': file_path,
                        'analysis': result
                    })
                    if result.get('success'):
                        analyzed_count += 1
                    else:
                        error_count += 1
            else:
                for chunk_idx in range(num_chunks):
                    start_idx = chunk_idx * chunk_size
                    end_idx = min(start_idx + chunk_size, total_files)
                    chunk_files = python_files[start_idx:end_idx]

                    print(f"  Processing chunk {chunk_idx + 1}/{num_chunks} ({len(chunk_files)} files)...")

                    for i, file_path in enumerate(chunk_files):
                        if i % 100 == 0 and i > 0:
                            print(f"    Analyzed {i}/{len(chunk_files)} files in chunk...")

                        result = self.analyze_python_file(file_path)

                        measurements.append({
                            'file_path': file_path,
                            'analysis': result
                        })

                        if result.get('success'):
                            analyzed_count += 1
                        else:
                            error_count += 1

                    print(f"  Chunk {chunk_idx + 1} complete: {analyzed_count} successful, {error_count} errors so far")
            print()

            # Calculate aggregate statistics
            print("[2.4] Calculating statistics...")
            total_loc = sum(m['analysis'].get('metrics', {}).get('lines_of_code', 0)
                          for m in measurements if m['analysis']['success'])
            total_functions = sum(m['analysis'].get('metrics', {}).get('functions', 0)
                                for m in measurements if m['analysis']['success'])
            total_classes = sum(m['analysis'].get('metrics', {}).get('classes', 0)
                              for m in measurements if m['analysis']['success'])

            # Prepare results - Convert measurements to file_metrics format for Phase 3
            file_metrics = {}
            for measurement in measurements:
                file_path = measurement['file_path']
                file_metrics[file_path] = measurement['analysis']

            results = {
                'phase': 'MEASURE',
                'iteration': iteration,
                'timestamp': datetime.now().isoformat(),
                'input_source': str(phase1_file),
                'statistics': {
                    'total_files': len(python_files),
                    'analyzed_successfully': analyzed_count,
                    'analysis_errors': error_count,
                    'total_lines_of_code': total_loc,
                    'total_functions': total_functions,
                    'total_classes': total_classes,
                },
                'file_metrics': file_metrics,
                'measurements': measurements,
            }

            # Save results
            print("[2.5] Saving results...")
            output_dir = self.config.paths.output_root / f"iteration_{iteration}" / "phase2_measure"
            ensure_directory(output_dir)

            # Save to phase2_measure directory for backward compatibility
            output_file = output_dir / "phase2_measure.json"
            safe_write_json(results, output_file)

            # Also save to phase2_metrics.json for Phase 3 compatibility
            metrics_file = self.config.paths.output_root / f"iteration_{iteration}" / "phase2_metrics.json"
            safe_write_json(results, metrics_file)

            # Print summary
            print()
            print("="*80)
            print("PHASE 2 SUMMARY")
            print("="*80)
            print(f"[OK] Analyzed {analyzed_count} Python files")
            print(f"  Total LOC: {total_loc:,}")
            print(f"  Total Functions: {total_functions:,}")
            print(f"  Total Classes: {total_classes:,}")
            print(f"  Analysis Errors: {error_count}")
            print(f"  Results saved: {output_file}")
            print()
            print("[OK] PHASE 2 PASSED")
            print("="*80)
            print()

            return True, results

        except Exception as e:
            print(f"\n[X] Phase 2 failed: {e}")
            import traceback
            traceback.print_exc()
            return False, {
                'phase': 'MEASURE',
                'iteration': iteration,
                'timestamp': datetime.now().isoformat(),
                'error': str(e),
                'input_source': '',
                'statistics': {},
                'file_metrics': {},
                'measurements': []
            }
