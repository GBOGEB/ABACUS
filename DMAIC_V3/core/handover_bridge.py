"""
DMAIC V3 - Handover Bridge Module
Bridges handover pipeline (src/dmaic/) with DMAIC V3 structure (DMAIC_V3/)
"""

import sys
from pathlib import Path
from typing import Dict, List, Any, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from dmaic import idempotency, provenance, metrics as handover_metrics, recursion
from dmaic.config import load_config as load_handover_config
from .metrics import MetricsAggregator
from .state import StateManager


class HandoverBridge:
    """
    Bridge between handover pipeline and V3 architecture

    Provides:
    - Idempotency wrapping for V3 phases
    - Provenance tracking integration
    - Action tracking coordination
    - Recursive iteration support
    """

    def __init__(self, config, state_manager: StateManager):
        """
        Initialize handover bridge

        Args:
            config: DMAICConfig instance
            state_manager: StateManager instance
        """
        self.config = config
        self.state_manager = state_manager
        self.run_id = None

        # Initialize handover components
        provenance.ensure_schema()

    def begin_run(self, inputs_hash: str = "default") -> str:
        """
        Begin a new run in the handover ledger

        Args:
            inputs_hash: Hash of input data

        Returns:
            run_id: Unique run identifier (timestamp__git_sha)
        """
        config_dict = {
            'workspace_root': str(self.config.paths.workspace_root),
            'output_root': str(self.config.paths.output_root),
            'execution_mode': self.config.execution_mode.value if hasattr(self.config.execution_mode, 'value') else str(self.config.execution_mode),
            'max_iterations': self.config.max_iterations
        }
        config_hash = idempotency.hash_json(config_dict)
        self.run_id = provenance.begin_run(config_hash, inputs_hash)
        return self.run_id

    def finish_run(self, status: str, total_metrics: dict):
        """
        Finish the current run

        Args:
            status: Run status (success/failed)
            total_metrics: Aggregated metrics across all phases
        """
        if self.run_id:
            provenance.finish_run(self.run_id, status, total_metrics)

    def record_phase(self, phase_name: str, iteration: int, status: str,
                     inputs_hash: str, outputs_hash: str, metrics: Dict[str, Any]):
        """Record phase execution in provenance"""
        provenance.record_phase(
            self.run_id,
            phase_name,
            iteration,
            status,
            inputs_hash,
            outputs_hash,
            metrics
        )

    def record_artifact(self, phase: str, kind: str, path: str,
                       bytes_hash: str, meta: dict = None):
        """
        Record artifact in handover ledger

        Args:
            phase: Phase that created artifact
            kind: Artifact type (e.g., "charter", "analysis", "action_plan")
            path: File path to artifact
            bytes_hash: SHA256 hash of artifact content
            meta: Optional metadata dictionary

        Returns:
            artifact_id: Unique artifact identifier
        """
        if self.run_id:
            return provenance.record_artifact(
                self.run_id, phase, kind, path, bytes_hash, meta
            )
        return None

    def make_idempotent(self, phase_name: str):
        """
        Create idempotent decorator for a phase

        Args:
            phase_name: Name of the phase

        Returns:
            Decorator function
        """
        def run_key_fn(**kwargs):
            params = kwargs.get('params', {})
            iteration = kwargs.get('iteration', 1)
            return f"{phase_name}::{iteration}::{idempotency.hash_json(params)}"

        return idempotency.idempotent(run_key_fn)

    def get_recent_runs(self, limit: int = 10):
        """
        Get recent runs from ledger

        Args:
            limit: Maximum number of runs to return

        Returns:
            List of recent runs
        """
        return provenance.get_recent_runs(limit)

    def should_stop_iteration(self, history: List[Dict[str, Any]],
                             rules: List[Dict[str, Any]]) -> Tuple[bool, str]:
        """
        Determine if iteration should stop based on rules

        Args:
            history: List of iteration metrics
            rules: List of stop rules

        Returns:
            Tuple of (should_stop, reason)
        """
        from src.dmaic.recursion import should_stop
        return should_stop(history, rules)

    def analyze_convergence(self, history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze convergence from iteration history

        Args:
            history: List of iteration metrics

        Returns:
            Convergence analysis results
        """
        from src.dmaic.recursion import analyze_convergence
        return analyze_convergence(history)


class IdempotentPhase:
    """
    Wrapper to make V3 phases idempotent

    Usage:
        bridge = HandoverBridge(config, state_manager)
        phase = Phase4Improve(config, state_manager)
        idempotent_phase = IdempotentPhase(phase, bridge, "improve")
        result = idempotent_phase.execute(iteration=1)
    """

    def __init__(self, phase, bridge: HandoverBridge, phase_name: str):
        """
        Initialize idempotent phase wrapper

        Args:
            phase: V3 phase instance
            bridge: HandoverBridge instance
            phase_name: Name of the phase
        """
        self.phase = phase
        self.bridge = bridge
        self.phase_name = phase_name
        self.idempotent_decorator = bridge.make_idempotent(phase_name)

    def execute(self, iteration: int, **kwargs):
        """
        Execute phase with idempotency

        Args:
            iteration: Iteration number
            **kwargs: Additional arguments

        Returns:
            Phase execution results (tuple of success, results)
        """
        @self.idempotent_decorator
        def _execute(**exec_kwargs):
            result = self.phase.execute(iteration)

            if isinstance(result, tuple):
                success, results = result
                metrics = results.get('metrics', {}) if isinstance(results, dict) else {}
            else:
                success = True
                results = result
                metrics = result.get('metrics', {}) if isinstance(result, dict) else {}

            inputs_hash = idempotency.hash_json({'iteration': iteration, **kwargs})
            outputs_hash = idempotency.hash_json(results if isinstance(results, dict) else str(results))

            self.bridge.record_phase(
                self.phase_name,
                iteration,
                "success" if success else "failed",
                inputs_hash,
                outputs_hash,
                metrics
            )

            return result

        return _execute(iteration=iteration, params=kwargs)


def integrate_phase4_opportunities(phase4_instance, opportunities_path: Path):
    """
    Integrate Phase 4 opportunities from markdown document

    Args:
        phase4_instance: Phase4Improve instance
        opportunities_path: Path to CORRECTED_PHASE4_OPPORTUNITIES.md

    Returns:
        Enhanced phase instance with opportunities integrated
    """
    if not opportunities_path.exists():
        print(f"Warning: Opportunities file not found: {opportunities_path}")
        return phase4_instance

    # Parse opportunities from markdown
    opportunities = _parse_opportunities(opportunities_path)

    # Add opportunities to phase instance
    phase4_instance.opportunities = opportunities

    # Create method to integrate opportunities with recommendations
    def integrate_with_recommendations(recommendations):
        integrated = []

        for opp in opportunities:
            integrated.append({
                'opportunity_id': opp['id'],
                'title': opp['title'],
                'priority': opp['priority'],
                'actions': opp['actions'],
                'related_recommendations': [
                    r for r in recommendations
                    if _matches_opportunity(r, opp)
                ]
            })

        return integrated

    phase4_instance.integrate_opportunities_with_recommendations = integrate_with_recommendations

    return phase4_instance


def _parse_opportunities(path: Path) -> list:
    """Parse opportunities from markdown file"""
    opportunities = []
    content = path.read_text(encoding='utf-8')

    # Simple parsing - extract opportunity sections
    lines = content.split('\n')
    current_opp = None

    for line in lines:
        if line.startswith('## OPP-') or line.startswith('### OPP-'):
            if current_opp:
                opportunities.append(current_opp)

            opp_id = line.split(':')[0].strip('#').strip()
            title = line.split(':')[1].strip() if ':' in line else ''
            current_opp = {
                'id': opp_id,
                'title': title,
                'priority': 'MEDIUM',
                'actions': [],
                'success_criteria': []
            }
        elif current_opp and line.startswith('**Priority:**'):
            current_opp['priority'] = line.split('**Priority:**')[1].strip()
        elif current_opp and line.strip().startswith('-'):
            current_opp['actions'].append(line.strip()[1:].strip())

    if current_opp:
        opportunities.append(current_opp)

    return opportunities


def _matches_opportunity(recommendation: dict, opportunity: dict) -> bool:
    """Check if recommendation matches opportunity"""
    # Simple matching based on keywords
    opp_keywords = opportunity['title'].lower().split()
    rec_keywords = recommendation.get('issue_type', '').lower().split('_')

    return any(k in rec_keywords for k in opp_keywords)
