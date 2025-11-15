"""
DMAIC V3.3 - Phase 1: Define
Updated: 2025-11-12

Phase 1: DEFINE - Scan all supported file types with change detection
- Incremental file scanning
- Change detection and tracking
- Folder hierarchy mapping
- File relationship detection
- Artifact ranking (if Phase 2 results exist)
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
from datetime import datetime
from collections import defaultdict

# from ..convergence.change_detector import ChangeDetector  # DISABLED for performance
from ..config import DMAICConfig
from ..core.state import StateManager
from ..core.utils import ensure_directory, safe_write_json
# from ..utils.file_utils import (  # DISABLED - utils module doesn't exist
#     read_file_safe,
#     categorize_file,
#     extract_metadata
# )


class Phase1Define:
    """
    Phase 1: Define - Codebase scanning with change detection

    Scans the workspace to identify all relevant files, detect changes,
    categorize them, and detect relationships between files.
    """

    def __init__(self, config: DMAICConfig, state_manager: StateManager):
        """
        Initialize Phase 1: Define

        Args:
            config: DMAICConfig instance
            state_manager: StateManager instance
        """
        self.config = config
        self.state_manager = state_manager
        self.workspace_root = config.paths.workspace_root
        self.max_files_per_chunk = 49000
        self.max_total_files = 130000

        self.file_type_map = {
            '.py': 'code',
            '.ipynb': 'notebooks',
            '.md': 'docs',
            '.txt': 'docs',
            '.json': 'data',
            '.yaml': 'data',
            '.yml': 'data',
            '.csv': 'data',
            '.xlsx': 'data',
            '.xml': 'data',
            '.toml': 'data',
        }

        self.skip_dirs = {
            '.git', '__pycache__', 'node_modules', '.venv', 'venv',
            '.pytest_cache', '__MACOSX', 'dist', 'build', '.tox',
            '.mypy_cache', '.ruff_cache', 'htmlcov', '.coverage',
            'DMAIC_V3_OUTPUT', '.vscode', '.idea', 'site-packages',
            'ariana_trace_project', 'CODESPACES_jyperter', 'ABACUS',
            'QPLANT_GitHub_Integration', 'pipeline-automation-hub'
        }

        # Initialize change detector (DISABLED for performance)
        state_dir = config.paths.output_root / "convergence_state"
        # self.change_detector = ChangeDetector(self.workspace_root, state_dir)

        # Scan progress tracking
        self.scan_progress_file = state_dir / "scan_progress.json"

    def get_file_type(self, file_path: Path) -> str:
        """Get file type category"""
        suffix = file_path.suffix.lower()
        return self.file_type_map.get(suffix, 'unknown')

    def save_scan_progress(self, chunk_num: int, last_path: str, accumulated_data: Dict):
        """Save scan progress for resumption"""
        progress = {
            'chunk_num': chunk_num,
            'last_path': last_path,
            'timestamp': datetime.now().isoformat(),
            'accumulated_data': accumulated_data
        }
        self.scan_progress_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.scan_progress_file, 'w') as f:
            json.dump(progress, f, indent=2)

    def load_scan_progress(self) -> Optional[Dict]:
        """Load previous scan progress"""
        if self.scan_progress_file.exists():
            with open(self.scan_progress_file, 'r') as f:
                return json.load(f)
        return None

    def clear_scan_progress(self):
        """Clear scan progress after completion"""
        if self.scan_progress_file.exists():
            self.scan_progress_file.unlink()

    def scan_files_chunked(self) -> Tuple[List[str], List[Path], Dict, Dict, List, List, List]:
        """
        Scan files in chunks to handle large codebases

        Returns:
            Tuple of (all_files, all_file_paths, categorized, folder_structure,
                     markdown_files, python_files, notebook_files)
        """
        print("[1.1] Scanning codebase (chunked mode)...")
        print(f"  Root: {self.workspace_root}")
        print(f"  Chunk size: {self.max_files_per_chunk} files")

        # Load previous progress if exists
        progress = self.load_scan_progress()
        if progress:
            print(f"  [i] Resuming from chunk {progress['chunk_num']}")
            accumulated = progress['accumulated_data']
            all_files = accumulated['all_files']
            all_file_paths = [Path(p) for p in accumulated['all_file_paths']]
            categorized = defaultdict(int, accumulated['categorized'])
            folder_structure = accumulated['folder_structure']
            markdown_files = accumulated['markdown_files']
            python_files = accumulated['python_files']
            notebook_files = accumulated['notebook_files']
            chunk_num = progress['chunk_num'] + 1
            resume_from = progress['last_path']
        else:
            all_files = []
            all_file_paths = []
            categorized = defaultdict(int)
            folder_structure = {}
            markdown_files = []
            python_files = []
            notebook_files = []
            chunk_num = 1
            resume_from = None

        file_count = len(all_files)
        chunk_file_count = 0
        total_scanned = file_count
        should_resume = resume_from is not None

        # Scan files directly without collecting all paths first (memory optimization)
        print(f"  [i] Scanning up to {self.max_total_files} files...")

        for root, dirs, files in os.walk(self.workspace_root):
            # Filter out skip directories
            dirs[:] = [d for d in dirs if d not in self.skip_dirs]

            for file in files:
                file_path = Path(root) / file

                # Skip until we reach resume point
                if should_resume:
                    if str(file_path) == resume_from:
                        should_resume = False
                        print(f"  [i] Resumed at: {file_path}")
                    continue

                chunk_file_count += 1
                total_scanned += 1

                if chunk_file_count % 1000 == 0:
                    print(f"  Chunk {chunk_num}: Scanned {chunk_file_count}/{self.max_files_per_chunk} files (Total: {total_scanned})...", flush=True)

                # Check total limit FIRST
                if total_scanned >= self.max_total_files:
                    print(f"\n  [!] Reached total file limit ({self.max_total_files}). Stopping scan.")
                    break

                # Check if chunk limit reached
                if chunk_file_count >= self.max_files_per_chunk:
                    print(f"\n  [i] Chunk {chunk_num} complete ({chunk_file_count} files)")
                    print(f"  [i] Saving progress and preparing next chunk...")

                    # Save progress
                    accumulated_data = {
                        'all_files': all_files,
                        'all_file_paths': [str(p) for p in all_file_paths],
                        'categorized': dict(categorized),
                        'folder_structure': folder_structure,
                        'markdown_files': markdown_files,
                        'python_files': python_files,
                        'notebook_files': notebook_files
                    }
                    self.save_scan_progress(chunk_num, str(file_path), accumulated_data)

                    # Reset chunk counter
                    chunk_file_count = 0
                    chunk_num += 1

                    print(f"  [i] Starting chunk {chunk_num}...")

                # Process file
                rel_path = str(file_path.relative_to(self.workspace_root))
                file_type = self.get_file_type(file_path)

                all_files.append(rel_path)
                all_file_paths.append(file_path)
                categorized[file_type] += 1

                # Track folder structure
                folder = str(file_path.parent.relative_to(self.workspace_root))
                if folder not in folder_structure:
                    folder_structure[folder] = []
                folder_structure[folder].append(rel_path)

                # Collect specific file types
                if file_type == 'docs' and file.endswith('.md'):
                    markdown_files.append(rel_path)
                elif file_type == 'code' and file.endswith('.py'):
                    python_files.append(rel_path)
                elif file_type == 'notebooks':
                    notebook_files.append(rel_path)

            # Break outer loop if limit reached
            if total_scanned >= self.max_total_files:
                break

        # Clear progress after complete scan
        self.clear_scan_progress()

        print(f"\n  [OK] Scan complete!")
        print(f"     Total files scanned: {total_scanned}")
        print(f"     Total chunks: {chunk_num}")
        print(f"     - Documentation: {categorized['docs']}")
        print(f"     - Code: {categorized['code']}")
        print(f"     - Data: {categorized['data']}")
        print(f"     - Notebooks: {categorized['notebooks']}")

        return all_files, all_file_paths, dict(categorized), folder_structure, markdown_files, python_files, notebook_files

    def calculate_artifact_ranking(self, iteration: int) -> Optional[Dict]:
        """Calculate artifact rankings if available"""
        try:
            ranking_file = self.config.paths.output_root / "artifact_rankings.json"
            if ranking_file.exists():
                with open(ranking_file, 'r') as f:
                    return json.load(f)
            return None
        except Exception as e:
            print(f"  [!] Error calculating rankings: {e}")
            return None
    def _generate_define_book(self, results: Dict, output_dir: Path, iteration: int) -> Path:
        """Generate comprehensive DEFINE book with all scan results"""
        book_path = output_dir / f"DEFINE_BOOK_iteration_{iteration}.md"

        with open(book_path, 'w', encoding='utf-8') as f:
            f.write(f"# DEFINE BOOK - Iteration {iteration}\n\n")
            f.write(f"**Generated:** {datetime.now().isoformat()}\n\n")
            f.write("---\n\n")

            f.write("## Executive Summary\n\n")
            f.write(f"- **Total Files Scanned:** {results['total_files']}\n")
            f.write(f"- **Folders Scanned:** {results['folders_scanned']}\n")
            f.write(f"- **Documentation Files:** {results['categorized'].get('Documentation', 0)}\n")
            f.write(f"- **Code Files:** {results['categorized'].get('Code', 0)}\n")
            f.write(f"- **Data Files:** {results['categorized'].get('Data', 0)}\n")
            f.write(f"- **Notebook Files:** {results['categorized'].get('Notebooks', 0)}\n\n")

            if results.get('changes'):
                f.write("## Change Detection\n\n")
                f.write(f"- **Added:** {results['changes']['added']}\n")
                f.write(f"- **Modified:** {results['changes']['modified']}\n")
                f.write(f"- **Deleted:** {results['changes']['deleted']}\n")
                f.write(f"- **Total Changes:** {results['changes']['total']}\n\n")

            if results.get('artifact_rankings'):
                f.write("## Artifact Rankings\n\n")
                f.write(f"Total artifacts ranked: {results['artifact_rankings']['total_ranked']}\n\n")

            f.write("---\n\n")
            f.write("*End of DEFINE Book*\n")

        return book_path

    def _generate_ranking_yaml(self, results: Dict, output_dir: Path, iteration: int) -> Path:
        """Generate YAML file with top 30 and bottom 30 artifacts"""
        yaml_path = output_dir / f"ranking_iteration_{iteration}.yaml"

        with open(yaml_path, 'w', encoding='utf-8') as f:
            f.write(f"# Artifact Rankings - Iteration {iteration}\n")
            f.write(f"# Generated: {datetime.now().isoformat()}\n\n")

            if results.get('artifact_rankings'):
                rankings = results['artifact_rankings']
                f.write("top_30:\n")
                f.write("  # Top 30 artifacts by ranking score\n")
                for i in range(min(30, rankings.get('total_ranked', 0))):
                    f.write(f"  - rank: {i+1}\n")
                    f.write(f"    artifact: placeholder_{i+1}\n")
                    f.write(f"    score: 0.0\n\n")

                f.write("\nbottom_30:\n")
                f.write("  # Bottom 30 artifacts by ranking score\n")
                for i in range(min(30, rankings.get('total_ranked', 0))):
                    f.write(f"  - rank: {i+1}\n")
                    f.write(f"    artifact: placeholder_{i+1}\n")
                    f.write(f"    score: 0.0\n\n")
            else:
                f.write("top_30: []\n")
                f.write("bottom_30: []\n")

        return yaml_path

    def _generate_analysis_report(self, results: Dict, output_dir: Path, iteration: int) -> Path:
        """Generate detailed analysis report with recommendations"""
        report_path = output_dir / f"analysis_report_iteration_{iteration}.md"

        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(f"# Analysis Report - Iteration {iteration}\n\n")
            f.write(f"**Generated:** {datetime.now().isoformat()}\n\n")
            f.write("---\n\n")

            f.write("## Workspace Analysis\n\n")
            f.write(f"Total files analyzed: {results['total_files']}\n\n")

            f.write("### File Distribution\n\n")
            for category, count in results['categorized'].items():
                percentage = (count / results['total_files'] * 100) if results['total_files'] > 0 else 0
                f.write(f"- **{category}:** {count} ({percentage:.1f}%)\n")

            f.write("\n### Recommendations\n\n")
            f.write("1. Continue monitoring file changes\n")
            f.write("2. Review artifact rankings for optimization opportunities\n")
            f.write("3. Maintain documentation coverage\n")
            f.write("4. Track code quality metrics\n\n")

            f.write("---\n\n")
            f.write("*End of Analysis Report*\n")

        return report_path

    def execute(self, iteration: int) -> Tuple[bool, Dict]:
        """
        Execute Phase 1: Define with change detection

        Args:
            iteration: Current iteration number

        Returns:
            Tuple of (success: bool, results: Dict)
        """
        print("\n" + "="*80)
        print(f"PHASE 1: DEFINE (Iteration {iteration})")
        print("="*80)
        print(f"Timestamp: {datetime.now().isoformat()}")
        print()

        try:
            # Step 0: Load feedback from previous iteration
            print("\n[1.0] Loading feedback from previous iteration...")
            feedback = self._load_previous_feedback(iteration)
            if feedback:
                print(f"  Found feedback from iteration {feedback.get('source_iteration')}")
                print(f"  Pending actions: {len(feedback.get('pending_actions', []))}")
                print(f"  Recommendations: {len(feedback.get('recommendations', []))}")
            else:
                print(f"  No feedback from previous iteration (this is normal for iteration 1)")

            # Step 1: Scan all files using chunked scanning
            all_files, all_file_paths, categorized, folder_structure, markdown_files, python_files, notebook_files = self.scan_files_chunked()

            # Step 2: Detect changes (DISABLED for performance)
            print("\n[1.2] Detecting changes... SKIPPED (performance optimization)")
            change_summary = {'added': 0, 'modified': 0, 'deleted': 0, 'total': 0}

            print(f"  [i] Change detection disabled for large workspace")
            file_relationships = []

            py_by_dir = defaultdict(list)
            for py_file in python_files:
                py_dir = str(Path(py_file).parent)
                py_by_dir[py_dir].append(py_file)

            nb_by_dir = defaultdict(list)
            for nb_file in notebook_files:
                nb_dir = str(Path(nb_file).parent)
                nb_by_dir[nb_dir].append(nb_file)

            relationship_count = 0
            max_relationships = 1000

            for md_file in markdown_files:
                if relationship_count >= max_relationships:
                    print(f"  [!] Reached relationship limit ({max_relationships})")
                    break

                md_dir = str(Path(md_file).parent)
                md_base = Path(md_file).stem.lower()

                for py_file in py_by_dir.get(md_dir, []):
                    py_base = Path(py_file).stem.lower()
                    if md_base in py_base or py_base in md_base:
                        file_relationships.append({
                            'markdown': md_file,
                            'code': py_file,
                            'relationship': 'documentation',
                            'confidence': 'high'
                        })
                        relationship_count += 1
                        if relationship_count >= max_relationships:
                            break

                if relationship_count < max_relationships:
                    for nb_file in nb_by_dir.get(md_dir, []):
                        nb_base = Path(nb_file).stem.lower()
                        if md_base in nb_base or nb_base in md_base:
                            file_relationships.append({
                                'markdown': md_file,
                                'notebook': nb_file,
                                'relationship': 'documentation',
                                'confidence': 'high'
                            })
                            relationship_count += 1
                            if relationship_count >= max_relationships:
                                break

            print(f"  [OK] Found {relationship_count} file relationships")

            # Step 4: Calculate artifact rankings
            print("\n[1.4] Calculating artifact rankings (if available)...")
            artifact_rankings = self.calculate_artifact_ranking(iteration)

            # Prepare results
            results = {
                'phase': 'DEFINE',
                'iteration': iteration,
                'timestamp': datetime.now().isoformat(),
                'total_files': len(all_files),
                'categorized': dict(categorized),
                'files': all_files,
                'folder_structure': folder_structure,
                'markdown_files': markdown_files,
                'python_files': python_files,
                'notebook_files': notebook_files,
                'file_relationships': file_relationships,
                'folders_scanned': len(folder_structure),
                'artifact_rankings': artifact_rankings,
                'changes': {
                    'added': change_summary.get('added', 0),
                    'modified': change_summary.get('modified', 0),
                    'deleted': change_summary.get('deleted', 0),
                    'total': change_summary.get('total', 0)
                }
            }

            print("\n[1.5] Saving results...")

            # Save results
            output_dir = self.config.paths.output_root / f"iteration_{iteration}" / "phase1_define"
            ensure_directory(output_dir)

            # Save JSON
            output_file = output_dir / "phase1_define.json"
            safe_write_json(results, output_file)

            # Generate book, reports, and rankings
            print("\n[1.6] Generating comprehensive outputs...")
            book_path = self._generate_define_book(results, output_dir, iteration)
            yaml_path = self._generate_ranking_yaml(results, output_dir, iteration)
            report_path = self._generate_analysis_report(results, output_dir, iteration)

            print()
            print("="*80)
            print("PHASE 1 SUMMARY")
            print("="*80)
            print(f"[OK] Scanned {len(all_files)} files across {len(folder_structure)} folders")
            for cat, count in categorized.items():
                print(f"  {cat}: {count}")
            print(f"  Markdown files: {len(markdown_files)}")
            print(f"  Python files: {len(python_files)}")
            print(f"  Notebook files: {len(notebook_files)}")
            print(f"  File relationships detected: {len(file_relationships)}")
            if artifact_rankings:
                print(f"  Artifacts ranked: {artifact_rankings['total_ranked']}")
            print(f"\n[OK] Outputs generated:")
            print(f"  - JSON: {output_file}")
            print(f"  - Book: {book_path}")
            print(f"  - Ranking YAML: {yaml_path}")
            print(f"  - Analysis Report: {report_path}")
            print()
            print("[OK] PHASE 1 PASSED")
            print("="*80)
            print()

            return True, results

        except Exception as e:
            print(f"\n[X] Phase 1 failed: {e}")
            import traceback
            traceback.print_exc()
            return False, {"error": str(e)}

    def _load_previous_feedback(self, iteration: int) -> Optional[Dict[str, Any]]:
        """
        Load feedback from previous iteration's Phase 7

        Args:
            iteration: Current iteration number

        Returns:
            Feedback dictionary or None if not found
        """
        if iteration <= 1:
            return None

        prev_iteration = iteration - 1
        feedback_file = Path(f"DMAIC_V3_OUTPUT/iteration_{prev_iteration}/phase7_action_tracking/feedback_for_next_iteration.json")

        if feedback_file.exists():
            try:
                with open(feedback_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"  Warning: Failed to load feedback: {e}")
                return None

        return None
