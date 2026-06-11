from dataclasses import dataclass
from typing import List, Dict, Any, Tuple
from datetime import datetime
from pathlib import Path
import json
import sys

from ..core.models import PhaseMetrics
from ..core.state import StateManager
from ..config import DMAICConfig

try:
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "master_document_system"))
    from core.temporal_tracker import TemporalTracker
    TEMPORAL_AVAILABLE = True
except ImportError:
    TEMPORAL_AVAILABLE = False

@dataclass
class KnowledgeReference:
    book_name: str
    category: str
    document_count: int
    size_bytes: int
    book_path: str

class Phase6Knowledge:
    """
    Phase 6: Knowledge Management - Integrates with Canonical Knowledge Books

    References canonical knowledge books instead of creating duplicates.
    Registers recursive hooks for backward compatibility.
    """

    def __init__(self, config=None, state: StateManager = None):
        self.config = config or DMAICConfig()
        self.state = state or StateManager(self.config)
        self.output_dir = Path(self.config.paths.output_root)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.canonical_dir = Path("CANONICAL_KNOWLEDGE")
        self.temporal_tracker = None
        if TEMPORAL_AVAILABLE:
            try:
                self.temporal_tracker = TemporalTracker()
            except Exception as e:
                print(f"[WARNING] Could not initialize temporal tracker: {e}")

    def execute(self, iteration: int) -> Tuple[bool, Dict[str, Any]]:
        """Execute Phase 6: Knowledge Management"""
        start_time = datetime.now()

        try:
            print("\n" + "="*80)
            print("PHASE 6: KNOWLEDGE MANAGEMENT - CANONICAL INTEGRATION")
            print("="*80)

            # Load canonical knowledge books
            print("\n[6.1] Loading canonical knowledge books...")
            knowledge_refs = self._load_canonical_books()
            print(f"  [OK] Loaded {len(knowledge_refs)} knowledge books")

            # Register recursive hooks
            print("\n[6.2] Registering recursive hooks...")
            hooks_registered = 0
            if self.temporal_tracker:
                try:
                    hook_id = self.temporal_tracker.register_recursive_hook(
                        hook_name=f"DMAIC_Iteration_{iteration}_Knowledge",
                        hook_type="knowledge_preservation",
                        trigger_condition=f"iteration=={iteration}",
                        target_phase="Phase6_Knowledge",
                        target_version=f"v{iteration}",
                        enabled=True
                    )
                    hooks_registered = 1
                except Exception as e:
                    print(f"  [WARNING] Could not register hooks: {e}")
            print(f"  [OK] Registered {hooks_registered} recursive hooks")

            # Calculate maturity
            print("\n[6.3] Calculating maturity score...")
            maturity_score = min(50 + (len(knowledge_refs) * 5), 100)
            print(f"  [OK] Maturity score: {maturity_score}/100")

            # Generate report
            print("\n[6.4] Extracting knowledge from improvements...")
            improvement_knowledge = self._extract_improvement_knowledge(iteration)
            print(f"  [OK] Extracted {len(improvement_knowledge)} improvement patterns")

            print("\n[6.5] Generating knowledge report...")
            report_path = self._generate_knowledge_report(
                iteration, knowledge_refs, maturity_score, improvement_knowledge
            )
            print(f"  [OK] Report generated: {report_path}")

            # NEW: Unrelenting Hunger - Continuous knowledge acquisition
            print("\n[6.6] Activating unrelenting hunger for knowledge...")
            hunger_metrics = self._activate_knowledge_hunger(iteration, knowledge_refs)
            print(f"  [OK] Knowledge depth: {hunger_metrics['depth_level']}")
            print(f"  [OK] New insights discovered: {hunger_metrics['insights_count']}")
            print(f"  [OK] Knowledge gaps identified: {hunger_metrics['gaps_count']}")

            results = {
                'success': True,
                'iteration': iteration,
                'start_time': start_time.isoformat(),
                'end_time': datetime.now().isoformat(),
                'duration_seconds': (datetime.now() - start_time).total_seconds(),
                'canonical_books_count': len(knowledge_refs),
                'recursive_hooks_registered': hooks_registered,
                'maturity_score': maturity_score,
                'improvement_patterns_extracted': len(improvement_knowledge),
                'report_path': str(report_path),
                'temporal_integration': TEMPORAL_AVAILABLE
            }

            print("\n" + "="*80)
            print("PHASE 6: COMPLETED SUCCESSFULLY")
            print(f"Books: {len(knowledge_refs)} | Hooks: {hooks_registered} | Maturity: {maturity_score}/100")
            print("="*80)

            return True, results

        except Exception as e:
            print(f"\n[ERROR] Phase 6 failed: {e}")
            import traceback
            traceback.print_exc()

            return False, {
                'success': False,
                'error': str(e),
                'iteration': iteration,
                'duration_seconds': (datetime.now() - start_time).total_seconds()
            }

    def _load_canonical_books(self) -> List[KnowledgeReference]:
        """Load references to canonical knowledge books"""
        refs = []

        if not self.canonical_dir.exists():
            print(f"  [WARNING] Canonical directory not found: {self.canonical_dir}")
            return refs

        # Scan for knowledge books
        for category in ['DMAIC', 'Architecture', 'Planning', 'Reference',
                       'Changelog', 'Execution_Logs', 'Assessment', 'Uncategorized']:
            category_dir = self.canonical_dir / category
            if category_dir.exists():
                books = list(category_dir.glob(f"{category}_BOOK_*.md"))
                for book in books:
                    refs.append(KnowledgeReference(
                        book_name=book.stem,  # Add book_name from filename
                        category=category,
                        document_count=0,
                        size_bytes=book.stat().st_size,
                        book_path=str(book)
                    ))

        return refs

    def _extract_improvement_knowledge(self, iteration: int) -> List[Dict[str, Any]]:
        """Extract knowledge patterns from Phase 4 improvements"""
        knowledge = []

        phase4_file = self.output_dir / f"iteration_{iteration}" / "phase4_improvements.json"
        if not phase4_file.exists():
            print(f"  [WARNING] Phase 4 output not found: {phase4_file}")
            return knowledge

        try:
            with open(phase4_file, 'r') as f:
                phase4_data = json.load(f)

            impl_results = phase4_data.get('implementation_results', {})

            for category in ['docstrings_added', 'long_lines_fixed', 'type_hints_added', 'unused_imports_removed']:
                items = impl_results.get(category, [])
                if items:
                    knowledge.append({
                        'pattern': category,
                        'count': len(items),
                        'files_affected': [item.get('file', 'unknown') for item in items if isinstance(item, dict)],
                        'total_modifications': sum(item.get('modifications', 0) for item in items if isinstance(item, dict))
                    })

        except Exception as e:
            print(f"  [WARNING] Could not extract improvement knowledge: {e}")

        return knowledge

    def _generate_knowledge_report(
        self,
        iteration: int,
        knowledge_refs: List[KnowledgeReference],
        maturity_score: int,
        improvement_knowledge: List[Dict[str, Any]] = None
    ) -> Path:
        """Generate human-readable knowledge report"""
        report_path = self.output_dir / f"phase6_knowledge" / f"KNOWLEDGE_REPORT_iter{iteration}.md"
        report_path.parent.mkdir(parents=True, exist_ok=True)

        improvement_knowledge = improvement_knowledge or []

        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(f"# Phase 6: Knowledge Management Report\n\n")
            f.write(f"**Iteration:** {iteration}\n")
            f.write(f"**Generated:** {datetime.now().isoformat()}\n")
            f.write(f"**Maturity Score:** {maturity_score}/100\n\n")
            f.write("---\n\n")

            # Canonical Knowledge Books
            f.write("## Canonical Knowledge Books\n\n")
            f.write(f"**Total Books:** {len(knowledge_refs)}\n\n")

            if knowledge_refs:
                f.write("| Category | Book Name | Size |\n")
                f.write("|----------|-----------|------|\n")
                for ref in knowledge_refs:
                    size_mb = ref.size_bytes / (1024 * 1024)
                    f.write(f"| {ref.category} | {ref.book_name} | {size_mb:.2f} MB |\n")
                f.write("\n")

            # Improvement Knowledge Patterns
            if improvement_knowledge:
                f.write("## Improvement Knowledge Patterns\n\n")
                f.write(f"**Total Patterns Extracted:** {len(improvement_knowledge)}\n\n")

                for pattern in improvement_knowledge:
                    f.write(f"### {pattern['pattern'].replace('_', ' ').title()}\n\n")
                    f.write(f"- **Count:** {pattern['count']}\n")
                    f.write(f"- **Total Modifications:** {pattern['total_modifications']}\n")
                    f.write(f"- **Files Affected:** {len(pattern['files_affected'])}\n\n")

                f.write("\n")

            # Integration Status
            f.write("## Integration Status\n\n")
            f.write(f"- **Temporal Tracker:** {'[OK] Available' if TEMPORAL_AVAILABLE else '[FAIL] Not Available'}\n")
            f.write(f"- **Canonical Books:** {'[OK] Loaded' if knowledge_refs else '[FAIL] Not Found'}\n")
            f.write(f"- **Recursive Hooks:** {'[OK] Registered' if self.temporal_tracker else '[FAIL] Disabled'}\n")
            f.write(f"- **Improvement Patterns:** {'[OK] Extracted' if improvement_knowledge else '[FAIL] None Found'}\n\n")

            f.write("---\n\n")
            f.write("*This report integrates with canonical knowledge books for unified documentation*\n")

        def _generate_knowledge_report(
            self,
            iteration: int,
            knowledge_refs: List[KnowledgeReference],
            maturity_score: int
        ) -> Path:
            """Generate human-readable knowledge report"""
            report_path = self.output_dir / f"phase6_knowledge" / f"KNOWLEDGE_REPORT_iter{iteration}.md"
            report_path.parent.mkdir(parents=True, exist_ok=True)

            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(f"# Phase 6: Knowledge Management Report\n\n")
                f.write(f"**Iteration:** {iteration}\n")
                f.write(f"**Generated:** {datetime.now().isoformat()}\n")
                f.write(f"**Maturity Score:** {maturity_score}/100\n\n")
                f.write("---\n\n")

                # Canonical Knowledge Books
                f.write("## Canonical Knowledge Books\n\n")
                f.write(f"**Total Books:** {len(knowledge_refs)}\n\n")

                if knowledge_refs:
                    f.write("| Category | Book Name | Size |\n")
                    f.write("|----------|-----------|------|\n")
                    for ref in knowledge_refs:
                        size_mb = ref.size_bytes / (1024 * 1024)
                        f.write(f"| {ref.category} | {ref.book_name} | {size_mb:.2f} MB |\n")
                    f.write("\n")

                # Integration Status
                f.write("## Integration Status\n\n")
                f.write(f"- **Temporal Tracker:** {'[OK] Available' if TEMPORAL_AVAILABLE else '[FAIL] Not Available'}\n")
                f.write(f"- **Canonical Books:** {'[OK] Loaded' if knowledge_refs else '[FAIL] Not Found'}\n")
                f.write(f"- **Recursive Hooks:** {'[OK] Registered' if self.temporal_tracker else '[FAIL] Disabled'}\n\n")

                f.write("---\n\n")
                f.write("*This report integrates with canonical knowledge books for unified documentation*\n")

            return report_path

    def _calculate_maturity_score(self, knowledge_refs: List[KnowledgeReference]) -> int:
        """Calculate a maturity score based on available canonical knowledge"""
        base = 50
        per_book = 5
        score = base + len(knowledge_refs) * per_book
        return max(0, min(score, 100))

    def _generate_human_report(self, results: Dict[str, Any], report_file: Path):
        """Generate human-readable report (orchestrator compatibility)"""
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("# Phase 6: Knowledge Management Report\n\n")
            f.write(f"**Generated:** {datetime.now().isoformat()}\n")
            f.write(f"**Iteration:** {results.get('iteration', 'N/A')}\n")
            f.write(f"**Duration:** {results.get('duration_seconds', 0):.2f}s\n\n")
            f.write("---\n\n")

            if 'canonical_books_count' in results:
                f.write("## Canonical Knowledge Books\n\n")
                f.write(f"**Books Referenced:** {results['canonical_books_count']}\n\n")

            if 'recursive_hooks_registered' in results:
                f.write("## Recursive Hooks\n\n")
                f.write(f"**Hooks Registered:** {results['recursive_hooks_registered']}\n\n")

            if 'maturity_score' in results:
                f.write("## Maturity Assessment\n\n")
                f.write(f"**Current Maturity Score:** {results['maturity_score']}/100\n\n")

            f.write("---\n\n")
            f.write("*Integrated with canonical knowledge books and temporal tracker*\n")

    def _activate_knowledge_hunger(self, iteration: int, knowledge_refs: List[KnowledgeReference]) -> Dict[str, Any]:
        """
        Activate unrelenting hunger for knowledge - continuous acquisition and deepening

        This method implements the "DEVOUR" phase of DOW methodology:
        - Analyzes existing knowledge depth
        - Identifies knowledge gaps
        - Discovers new insights from patterns
        """
        metrics = {
            'depth_level': 0,
            'insights_count': 0,
            'gaps_count': 0
        }

        # Calculate knowledge depth based on book count and size
        total_size = sum(ref.size_bytes for ref in knowledge_refs)
        # depth_level factors book count and total size (MB), capped at 10
        size_mb = total_size / (1024 * 1024) if total_size else 0
        metrics['depth_level'] = min(10, int(len(knowledge_refs) + (size_mb // 50)))  # +1 depth per ~50MB

        # Identify gaps by checking for missing categories
        expected_categories = ['DMAIC', 'Architecture', 'Planning', 'Reference']
        existing_categories = set(ref.category for ref in knowledge_refs)
        metrics['gaps_count'] = len(set(expected_categories) - existing_categories)

        # Count insights from improvement patterns (phase4)
        phase4_file = self.output_dir / f"iteration_{iteration}" / "phase4_improvements.json"
        if phase4_file.exists():
            try:
                with open(phase4_file, 'r', encoding='utf-8') as f:
                    phase4_data = json.load(f)
                impl_results = phase4_data.get('implementation_results', {})
                metrics['insights_count'] = sum(len(items) for items in impl_results.values() if isinstance(items, list))
            except Exception:
                # If extraction fails, leave insights_count as 0 but warn
                print(f"  [WARNING] Could not analyze Phase 4 improvements for insights: {phase4_file}")
        else:
            # If no phase4 data, attempt to look for any improvement notes in canonical books
            insights = 0
            for ref in knowledge_refs:
                try:
                    path = Path(ref.book_path)
                    if path.exists() and path.suffix.lower() in ('.md', '.txt'):
                        with open(path, 'r', encoding='utf-8') as bf:
                            content = bf.read()
                        # Simple heuristic: count occurrences of the word "improve" or "refactor"
                        insights += content.lower().count('improve')
                        insights += content.lower().count('refactor')
                except Exception:
                    continue
            metrics['insights_count'] = insights

        return metrics
