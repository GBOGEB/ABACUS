"""
Iterative Controller for DMAIC V3.3
Manages iterative execution with convergence detection
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import json

from .change_detector import ChangeDetector


@dataclass
class IterationMetrics:
    """Metrics for a single iteration"""
    iteration: int
    files_processed: int = 0
    changes_detected: int = 0
    phases_executed: List[str] = field(default_factory=list)
    convergence_score: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class IterativeController:
    """
    Controls iterative execution of DMAIC phases
    
    Features:
    - Automatic iteration management
    - Convergence detection
    - Change-based triggering
    - Maturity assessment
    """
    
    def __init__(self, workspace_root: Path, output_root: Path, max_iterations: int = 3):
        """
        Initialize iterative controller
        
        Args:
            workspace_root: Root directory of workspace
            output_root: Root directory for outputs
            max_iterations: Maximum number of iterations (default: 3)
        """
        self.workspace_root = workspace_root
        self.output_root = output_root
        self.max_iterations = max_iterations
        
        self.state_dir = output_root / "convergence_state"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        
        self.metrics_file = self.state_dir / "iteration_metrics.json"
        self.convergence_file = self.state_dir / "convergence_status.json"
        
        self.change_detector = ChangeDetector(workspace_root, self.state_dir)
        self.iteration_history: List[IterationMetrics] = []
        
    def should_continue_iteration(self, current_iteration: int) -> Tuple[bool, str]:
        """
        Determine if another iteration should be executed
        
        Args:
            current_iteration: Current iteration number
            
        Returns:
            Tuple of (should_continue, reason)
        """
        # Check max iterations
        if current_iteration >= self.max_iterations:
            return False, f"Maximum iterations ({self.max_iterations}) reached"
        
        # First iteration always runs
        if current_iteration == 1:
            return True, "Initial iteration"
        
        # Check for changes
        if not self.change_detector.has_changes():
            return False, "No changes detected since last iteration"
        
        # Check convergence
        if self._is_converged():
            return False, "System has converged"
        
        return True, f"Changes detected, continuing iteration {current_iteration}"
    
    def _is_converged(self) -> bool:
        """
        Check if system has converged
        
        Convergence criteria:
        - Less than 5% file changes between iterations
        - Maturity level is 'mature' or 'converged'
        - At least 2 iterations completed
        """
        if len(self.iteration_history) < 2:
            return False
        
        last_iteration = self.iteration_history[-1]
        
        # Check maturity level
        if last_iteration.maturity_level in ['mature', 'converged']:
            return True
        
        # Check change rate
        if last_iteration.files_processed > 0:
            change_rate = last_iteration.changes_detected / last_iteration.files_processed
            if change_rate < 0.05:  # Less than 5% changes
                return True
        
        return False
    
    def calculate_convergence_score(self, 
                                    files_processed: int,
                                    changes_detected: int,
                                    phases_executed: List[str]) -> float:
        """
        Calculate convergence score (0.0 to 1.0)
        
        Higher score = closer to convergence
        
        Args:
            files_processed: Number of files processed
            changes_detected: Number of changes detected
            phases_executed: List of phases executed
            
        Returns:
            Convergence score between 0.0 and 1.0
        """
        score = 0.0
        
        # Factor 1: Change rate (40% weight)
        if files_processed > 0:
            change_rate = changes_detected / files_processed
            # Lower change rate = higher score
            change_score = max(0, 1.0 - (change_rate * 2))
            score += change_score * 0.4
        else:
            score += 0.4  # No files = converged
        
        # Factor 2: Phase completion (30% weight)
        expected_phases = ['phase0_init', 'phase1_define', 'phase2_measure', 
                          'phase3_analyze', 'phase4_improve', 'phase5_control']
        phase_completion = len(phases_executed) / len(expected_phases)
        score += phase_completion * 0.3
        
        # Factor 3: Iteration history (30% weight)
        if len(self.iteration_history) >= 2:
            # Compare with previous iteration
            prev = self.iteration_history[-1]
            if prev.files_processed > 0:
                prev_change_rate = prev.changes_detected / prev.files_processed
                curr_change_rate = changes_detected / files_processed if files_processed > 0 else 0
                
                # If change rate is decreasing, score increases
                if curr_change_rate < prev_change_rate:
                    score += 0.3
                else:
                    score += 0.15
        else:
            score += 0.15  # First iteration gets partial credit
        
        return min(1.0, max(0.0, score))
    
    def determine_maturity_level(self, convergence_score: float, iteration: int) -> str:
        """
        Determine maturity level based on convergence score
        
        Args:
            convergence_score: Convergence score (0.0 to 1.0)
            iteration: Current iteration number
            
        Returns:
            Maturity level string
        """
        if convergence_score >= 0.9:
            return 'converged'
        elif convergence_score >= 0.7:
            return 'mature'
        elif convergence_score >= 0.4:
            return 'developing'
        else:
            return 'initial'
    
    def record_iteration(self,
                        iteration: int,
                        files_processed: int,
                        changes_detected: int,
                        phases_executed: List[str],
                        execution_time: float):
        """
        Record metrics for completed iteration
        
        Args:
            iteration: Iteration number
            files_processed: Number of files processed
            changes_detected: Number of changes detected
            phases_executed: List of phases executed
            execution_time: Execution time in seconds
        """
        convergence_score = self.calculate_convergence_score(
            files_processed, changes_detected, phases_executed
        )
        
        maturity_level = self.determine_maturity_level(convergence_score, iteration)
        
        metrics = IterationMetrics(
            iteration=iteration,
            timestamp=datetime.now().isoformat(),
            files_processed=files_processed,
            changes_detected=changes_detected,
            phases_executed=phases_executed,
            execution_time_seconds=execution_time,
            convergence_score=convergence_score,
            maturity_level=maturity_level
        )
        
        self.iteration_history.append(metrics)
        self._save_metrics()
        self._update_convergence_status()
        
        print(f"\n[Iteration {iteration}] Metrics:")
        print(f"  - Files processed: {files_processed}")
        print(f"  - Changes detected: {changes_detected}")
        print(f"  - Convergence score: {convergence_score:.2f}")
        print(f"  - Maturity level: {maturity_level}")
        print(f"  - Execution time: {execution_time:.2f}s")
    
    def _save_metrics(self):
        """Save iteration metrics to disk"""
        try:
            data = {
                'total_iterations': len(self.iteration_history),
                'max_iterations': self.max_iterations,
                'iterations': [asdict(m) for m in self.iteration_history]
            }
            
            with open(self.metrics_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            print(f"  [!] Error saving metrics: {e}")
    
    def _update_convergence_status(self):
        """Update convergence status file"""
        if not self.iteration_history:
            return
            
        last_iteration = self.iteration_history[-1]
        
        try:
            status = {
                'timestamp': datetime.now().isoformat(),
                'current_iteration': last_iteration.iteration,
                'max_iterations': self.max_iterations,
                'is_converged': self._is_converged(),
                'convergence_score': last_iteration.convergence_score,
                'maturity_level': last_iteration.maturity_level,
                'total_files_processed': sum(m.files_processed for m in self.iteration_history),
                'total_changes_detected': sum(m.changes_detected for m in self.iteration_history),
                'total_execution_time': sum(m.execution_time_seconds for m in self.iteration_history)
            }
            
            with open(self.convergence_file, 'w', encoding='utf-8') as f:
                json.dump(status, f, indent=2)
                
        except Exception as e:
            print(f"  [!] Error updating convergence status: {e}")
    
    def load_history(self):
        """Load iteration history from disk"""
        if not self.metrics_file.exists():
            return
            
        try:
            with open(self.metrics_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            self.iteration_history = [
                IterationMetrics(**m) for m in data.get('iterations', [])
            ]
            
        except Exception as e:
            print(f"  [!] Error loading history: {e}")
    
    def get_convergence_status(self) -> Dict[str, Any]:
        """Get current convergence status"""
        if not self.convergence_file.exists():
            return {'is_converged': False, 'maturity_level': 'initial'}
            
        try:
            with open(self.convergence_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {'is_converged': False, 'maturity_level': 'initial'}
    
    def generate_convergence_report(self) -> str:
        """Generate human-readable convergence report"""
        if not self.iteration_history:
            return "No iterations completed yet."
        
        report = []
        report.append("=" * 60)
        report.append("DMAIC V3.3 - Convergence Report")
        report.append("=" * 60)
        report.append("")
        
        status = self.get_convergence_status()
        report.append(f"Status: {'CONVERGED' if status.get('is_converged') else 'IN PROGRESS'}")
        report.append(f"Maturity Level: {status.get('maturity_level', 'unknown').upper()}")
        report.append(f"Iterations Completed: {len(self.iteration_history)}/{self.max_iterations}")
        report.append("")
        
        report.append("Iteration History:")
        report.append("-" * 60)
        for metrics in self.iteration_history:
            report.append(f"Iteration {metrics.iteration}:")
            report.append(f"  Files: {metrics.files_processed}, Changes: {metrics.changes_detected}")
            report.append(f"  Convergence: {metrics.convergence_score:.2f}, Maturity: {metrics.maturity_level}")
            report.append(f"  Time: {metrics.execution_time_seconds:.2f}s")
            report.append("")
        
        report.append("=" * 60)
        
        return "\n".join(report)
