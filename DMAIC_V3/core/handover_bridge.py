"""
# Version: 1.0.0
# Date: 2025-11-25
# Description: Auto-generated version header
"""

"""
DMAIC V3 - Handover Bridge Module
Bridges handover pipeline with DMAIC V3 structure
"""

import sys
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime
import json

from .metrics import MetricsAggregator
from .state import StateManager


class IdempotentPhase:
    """Idempotent phase wrapper for DMAIC phases"""

    def __init__(self, phase_name: str, state_manager: StateManager):
        self.phase_name = phase_name
        self.state_manager = state_manager
        self.execution_id = None
        self._cached_result = None
        self._executed = False

    def execute(self, func, *args, **kwargs):
        # Check if already executed in this instance
        if self._executed:
            return self._cached_result

        # Execute the function
        result = func(*args, **kwargs)

        # Cache the result
        self._cached_result = result
        self._executed = True

        return result




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
        self.provenance_log = []
        self.metrics_log = []
        self._phase_cache = {}  # Cache for idempotent phase results

    def begin_run(self, inputs_hash: str = "default") -> str:
        """
        Begin a new run in the handover ledger

        Args:
            inputs_hash: Hash of input data

        Returns:
            run_id: Unique run identifier (timestamp__git_sha)
        """
        self.run_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{inputs_hash[:8]}"
        self.provenance_log.append({
            'event': 'run_started',
            'run_id': self.run_id,
            'timestamp': datetime.now().isoformat(),
            'inputs_hash': inputs_hash
        })
        return self.run_id

    def finish_run(self, status: str, total_metrics: dict):
        """
        Finish the current run

        Args:
            status: Run status (success/failed)
            total_metrics: Aggregated metrics across all phases
        """
        self.provenance_log.append({
            'event': 'run_finished',
            'run_id': self.run_id,
            'status': status,
            'metrics': total_metrics,
            'timestamp': datetime.now().isoformat()
        })

    def wrap_phase(self, phase_name: str, phase_func, *args, **kwargs):
        """
        Wrap a phase function with idempotency

        Args:
            phase_name: Name of the phase
            phase_func: Phase function to wrap
            *args, **kwargs: Arguments to pass to phase function

        Returns:
            Phase execution result
        """
        # Check cache first
        if phase_name in self._phase_cache:
            return self._phase_cache[phase_name]

        # Execute phase
        idempotent_phase = IdempotentPhase(phase_name, self.state_manager)
        result = idempotent_phase.execute(phase_func, *args, **kwargs)

        # Cache result
        self._phase_cache[phase_name] = result

        return result

    def log_action(self, phase_name: str, action: str, details: Dict[str, Any]):
        """
        Log an action in the provenance trail

        Args:
            phase_name: Name of the phase
            action: Action being performed
            details: Action details
        """
        self.provenance_log.append({
            'event': 'action',
            'run_id': self.run_id,
            'phase': phase_name,
            'action': action,
            'details': details,
            'timestamp': datetime.now().isoformat()
        })

    def record_metrics(self, phase_name: str, metrics: Dict[str, Any]):
        """
        Record metrics for a phase

        Args:
            phase_name: Name of the phase
            metrics: Metrics dictionary
        """
        self.metrics_log.append({
            'run_id': self.run_id,
            'phase': phase_name,
            'metrics': metrics,
            'timestamp': datetime.now().isoformat()
        })

    def get_provenance_trail(self) -> List[Dict[str, Any]]:
        """Get the complete provenance trail"""
        return self.provenance_log

    def get_metrics_history(self) -> List[Dict[str, Any]]:
        """Get the complete metrics history"""
        return self.metrics_log

    def save_provenance(self, output_path: Path):
        """Save provenance trail to file"""
        with open(output_path, 'w') as f:
            json.dump(self.provenance_log, f, indent=2)

    def save_metrics(self, output_path: Path):
        """Save metrics history to file"""
        with open(output_path, 'w') as f:
            json.dump(self.metrics_log, f, indent=2)

    def make_idempotent(self, phase_name: str):
        """
        Create an idempotent decorator for a phase

        Args:
            phase_name: Name of the phase

        Returns:
            Decorator function
        """
        def decorator(func):
            def wrapper(*args, **kwargs):
                return self.wrap_phase(phase_name, func, *args, **kwargs)
            return wrapper
        return decorator

    def get_recent_runs(self, limit: int = 10):
        """
        Get recent runs from ledger

        Args:
            limit: Maximum number of runs to return

        Returns:
            List of recent runs
        """
        return self.provenance_log[-limit:] if len(self.provenance_log) > limit else self.provenance_log

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
        if not history:
            return False, "No history available"

        for rule in rules:
            rule_type = rule.get('type')

            if rule_type == 'max_iterations':
                if len(history) >= rule.get('value', 10):
                    return True, f"Max iterations reached: {len(history)}"

            elif rule_type == 'convergence':
                threshold = rule.get('threshold', 0.01)
                if len(history) >= 2:
                    last_score = history[-1].get('quality_score', 0)
                    prev_score = history[-2].get('quality_score', 0)
                    if abs(last_score - prev_score) < threshold:
                        return True, f"Converged: score change < {threshold}"

        return False, "Continue iteration"

    def analyze_convergence(self, history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze convergence from iteration history

        Args:
            history: List of iteration metrics

        Returns:
            Convergence analysis results
        """
        if not history:
            return {'converged': False, 'reason': 'No history'}

        scores = [h.get('quality_score', 0) for h in history]

        if len(scores) < 2:
            return {'converged': False, 'reason': 'Insufficient data'}

        changes = [abs(scores[i] - scores[i-1]) for i in range(1, len(scores))]
        avg_change = sum(changes) / len(changes)

        return {
            'converged': avg_change < 0.01,
            'avg_change': avg_change,
            'iterations': len(history),
            'final_score': scores[-1]
        }


class IdempotentPhaseExecutor:
    """
    Wrapper to make V3 phases idempotent

    Usage:
        bridge = HandoverBridge(config, state_manager)
        phase = Phase4Improve(config, state_manager)
        idempotent_phase = IdempotentPhaseExecutor(phase, bridge, "improve")
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
