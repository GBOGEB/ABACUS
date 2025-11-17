Phase 0:     Initialization (12-agent orchestration)
Phases 1-5:  DMAIC Core (Define, Measure, Analyze, Improve, Control)
Phase 6:     KNOWLEDGE (Devour - AI getting smarter)
Phases 7-8+: ROOT expansion stubs
=============================================================================
Features:
- Visible terminal output for all phases
- Human-readable artifacts generated
- Recursive hooks and maturity tracking
- Git commits after each phase
- Historic tracking
- Everything tracked even if incomplete
=============================================================================
"""

import sys
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional
import subprocess

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from DMAIC_V3.config import DMAICConfig
from DMAIC_V3.core.state import StateManager
from DMAIC_V3.core.idempotency_wrapper import enable_idempotency, GLOBAL_IDEMPOTENCY
from DMAIC_V3.core.planning_matrix_tracker import PlanningMatrixTracker
from DMAIC_V3.phases.phase0_init import Phase0Init
from DMAIC_V3.phases.phase1_define import Phase1Define
from DMAIC_V3.phases.phase2_measure import Phase2Measure
from DMAIC_V3.phases.phase3_analyze import Phase3Analyze
from DMAIC_V3.phases.phase4_improve import Phase4Improve
from DMAIC_V3.phases.phase5_control import Phase5Control
from DMAIC_V3.phases.phase7_action_tracking import Phase7ActionTracking
from DMAIC_V3.phases.phase8_todo_management import Phase8TODOManagement
=======
#!/usr/bin/env python3
"""
DMAIC V3.3 - FULL PIPELINE ORCHESTRATOR
=============================================================================
Phase 0:     Initialization (12-agent orchestration)
Phases 1-5:  DMAIC Core (Define, Measure, Analyze, Improve, Control)
Phase 6:     KNOWLEDGE (Devour - AI getting smarter)
Phases 7-8+: ROOT expansion stubs
=============================================================================
Features:
- Visible terminal output for all phases
- Human-readable artifacts generated
- Recursive hooks and maturity tracking
- Git commits after each phase
- Historic tracking
- Everything tracked even if incomplete
- Background change detection (non-blocking)
=============================================================================
"""

import sys
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional
import subprocess

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from DMAIC_V3.config import DMAICConfig
from DMAIC_V3.core.state import StateManager
from DMAIC_V3.core.idempotency_wrapper import enable_idempotency, GLOBAL_IDEMPOTENCY
from DMAIC_V3.core.planning_matrix_tracker import PlanningMatrixTracker
from DMAIC_V3.convergence.background_change_detector import BackgroundChangeDetector
from DMAIC_V3.phases.phase0_init import Phase0Init
from DMAIC_V3.phases.phase1_define import Phase1Define
from DMAIC_V3.phases.phase2_measure import Phase2Measure
from DMAIC_V3.phases.phase3_analyze import Phase3Analyze
from DMAIC_V3.phases.phase4_improve import Phase4Improve
from DMAIC_V3.phases.phase5_control import Phase5Control
from DMAIC_V3.phases.phase7_action_tracking import Phase7ActionTracking
from DMAIC_V3.phases.phase8_todo_management import Phase8TODOManagement
=============================================================================
Phase 0:     Initialization (12-agent orchestration)
Phases 1-5:  DMAIC Core (Define, Measure, Analyze, Improve, Control)
Phase 6:     KNOWLEDGE (Devour - AI getting smarter)
Phases 7-8+: ROOT expansion stubs
=============================================================================
Features:
- Visible terminal output for all phases
- Human-readable artifacts generated
- Recursive hooks and maturity tracking
- Git commits after each phase
- Historic tracking
- Everything tracked even if incomplete
=============================================================================
"""

import sys
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional
import subprocess

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from DMAIC_V3.config import DMAICConfig
from DMAIC_V3.core.state import StateManager
from DMAIC_V3.core.idempotency_wrapper import enable_idempotency, GLOBAL_IDEMPOTENCY
from DMAIC_V3.core.planning_matrix_tracker import PlanningMatrixTracker
from DMAIC_V3.phases.phase0_init import Phase0Init
from DMAIC_V3.phases.phase1_define import Phase1Define
from DMAIC_V3.phases.phase2_measure import Phase2Measure
from DMAIC_V3.phases.phase3_analyze import Phase3Analyze
from DMAIC_V3.phases.phase4_improve import Phase4Improve
from DMAIC_V3.phases.phase5_control import Phase5Control
from DMAIC_V3.phases.phase7_action_tracking import Phase7ActionTracking
from DMAIC_V3.phases.phase8_todo_management import Phase8TODOManagement


class Phase6Knowledge:
    """
    Phase 6: KNOWLEDGE - Devour and Learn

    AI getting smarter by consuming:
    - All phase outputs
    - Convergence metrics
    - Historic data
    - Recursive self-ranking results

    Produces:
    - Knowledge index
    - Learning insights
    - Recommendations for next iteration
    - Maturity assessment
    """

    def __init__(self, config: DMAICConfig, state_mgr: StateManager):
        """TODO: Add function description"""

        self.config = config
        self.state_mgr = state_mgr

    def execute(self, iteration: int) -> Tuple[bool, Dict[str, Any]]:
        """
        Execute Phase 6: Knowledge acquisition and learning

        Args:
            iteration: Current iteration number

        Returns:
            Tuple of (success, results)
        """
        print("\n" + "="*80)
        print(f"DMAIC V3.3 - PHASE 6: KNOWLEDGE (Iteration {iteration})")
        print("="*80)
        print("AI DEVOUR MODE - Consuming all artifacts and learning...")

        results = {
            'phase': 'phase6_knowledge',
            'iteration': iteration,
            'timestamp': datetime.now().isoformat(),
            'knowledge_consumed': {},
            'insights_generated': [],
            'recommendations': [],
            'maturity_score': 0.0
        }

        try:
            # [6.1] Consume Phase 1-5 outputs
            print("\n[6.1] Devouring DMAIC phase outputs...")
            output_dir = Path(f"DMAIC_V3_OUTPUT/iteration_{iteration}")

            phase_data = {}
            for phase_num in range(1, 6):
                phase_name = f"phase{phase_num}"
                phase_file = output_dir / phase_name / f"{phase_name}.json"

                if phase_file.exists():
                    with open(phase_file, 'r') as f:
                        phase_data[phase_name] = json.load(f)
                    print(f"  [OK] Consumed {phase_name}")

            results['knowledge_consumed'] = phase_data

            # [6.2] Generate insights
            print("\n[6.2] Generating insights...")
            insights = self._generate_insights(phase_data)
            results['insights_generated'] = insights
            print(f"  [OK] Generated {len(insights)} insights")

            # [6.3] Generate recommendations
            print("\n[6.3] Generating recommendations...")
            recommendations = self._generate_recommendations(phase_data, insights)
            results['recommendations'] = recommendations
            print(f"  [OK] Generated {len(recommendations)} recommendations")

            # [6.4] Calculate maturity score
            print("\n[6.4] Calculating maturity score...")
            maturity_score = self._calculate_maturity(phase_data)
            results['maturity_score'] = maturity_score
            print(f"  [OK] Maturity score: {maturity_score}/100")

            # [6.5] Save knowledge index
            print("\n[6.5] Saving knowledge index...")
            knowledge_dir = output_dir / "phase6_knowledge"
            knowledge_dir.mkdir(parents=True, exist_ok=True)

            knowledge_file = knowledge_dir / "knowledge_index.json"
            with open(knowledge_file, 'w') as f:
                json.dump(results, f, indent=2)

            print(f"  [OK] Knowledge index saved: {knowledge_file}")

            # [6.6] Generate human-readable report
            report_file = knowledge_dir / "KNOWLEDGE_REPORT.md"
            self._generate_human_report(results, report_file)
            print(f"  [OK] Human report generated: {report_file}")

            print("\n" + "="*80)
            print("[OK] PHASE 6 COMPLETE - AI has learned and generated insights")
            print("="*80)

            return True, results

        except Exception as e:
            print(f"\n[X] Phase 6 failed: {e}")
            import traceback
            traceback.print_exc()
            results['error'] = str(e)
            return False, results

    def _generate_insights(self, phase_data: Dict) -> List[Dict]:
        """Generate insights from phase data"""
        insights = []

        if 'phase3' in phase_data:
            phase3 = phase_data['phase3']
            if 'high_complexity_files' in phase3:
                insights.append({
                    'type': 'complexity',
                    'message': f"Found {len(phase3['high_complexity_files'])} high complexity files",
                        
                        
                    'priority': 'high'
                })

        if 'phase4' in phase_data:
            phase4 = phase_data['phase4']
            if 'refactoring_tasks' in phase4:
                insights.append({
                    'type': 'improvement',
                    'message': f"Identified {len(phase4['refactoring_tasks'])} refactoring tasks",
                    'priority': 'medium'
                })

        return insights

    def _generate_recommendations(self, phase_data: Dict, insights: List[Dict]) -> List[str]:
        """Generate recommendations"""
        recommendations = []

        for insight in insights:
            if insight['priority'] == 'high':
                recommendations.append(f"Address {insight['type']}: {insight['message']}")

        return recommendations

    def _calculate_maturity(self, phase_data: Dict) -> float:
        """Calculate codebase maturity score"""
        score = 50.0

        if 'phase2' in phase_data:
            phase2 = phase_data['phase2']
            if phase2.get('documentation_coverage', 0) > 0.7:
                score += 10

        if 'phase3' in phase_data:
            phase3 = phase_data['phase3']
            if len(phase3.get('high_complexity_files', [])) < 10:
                score += 10

        return min(score, 100.0)

class Phase7AdvancedAnalytics:
    """Phase 7 STUB: Advanced Analytics (Future expansion) - DEPRECATED

    Use Phase7ActionTracking instead.
    """

    def __init__(self, config: DMAICConfig, state_mgr: StateManager):
        self.config = config
        self.state_mgr = state_mgr

    def execute(self, iteration: int) -> Tuple[bool, Dict]:
        """STUB: Execute Phase 7 - DEPRECATED"""
        print("\n[WARNING] Phase7AdvancedAnalytics is deprecated. Use Phase7ActionTracking instead.")
        return True, {
            'phase': 'phase7_advanced_analytics',
            'status': 'DEPRECATED',
            'iteration': iteration,
            'timestamp': datetime.now().isoformat()
        }


class Phase8RecursiveOptimization:
    """Phase 8 STUB: Recursive Optimization (Future expansion) - DEPRECATED

    Use Phase8TODOManagement instead.
    """

    def __init__(self, config: DMAICConfig, state_mgr: StateManager):
        self.config = config
        self.state_mgr = state_mgr

    def execute(self, iteration: int) -> Tuple[bool, Dict]:
        """STUB: Execute Phase 8 - DEPRECATED"""
        print("\n[WARNING] Phase8RecursiveOptimization is deprecated. Use Phase8TODOManagement instead.")
        return True, {
            'phase': 'phase8_recursive_optimization',
            'status': 'DEPRECATED',
            'iteration': iteration,
            'timestamp': datetime.now().isoformat()
        }


class FullPipelineOrchestrator:
    """
    Full Pipeline Orchestrator
    
    Executes complete DMAIC V3.3 pipeline:
    - Phase 0: Initialization
    - Phases 1-5: DMAIC Core
    - Phase 6: Knowledge (Devour/Learn)
    - Phases 7-8: Future expansion stubs
    
    With full tracking, artifacts, and recursive hooks
    """
    
    def __init__(self,
                 enable_idempotency_flag: bool = True,
                 enable_git_commits: bool = True,
                 verbose: bool = True):
        """Initialize the Full Pipeline Orchestrator"""

        self.config = DMAICConfig()
        self.state_mgr = StateManager(self.config.paths.state_dir)
        self.planning_tracker = PlanningMatrixTracker(workspace_root=Path("."))

        self.enable_idempotency_flag = enable_idempotency_flag
        self.enable_git_commits = enable_git_commits
        self.verbose = verbose

        self.execution_log: List[Dict] = []

        if self.enable_idempotency_flag:
            enable_idempotency(enabled=True)

        # Integration Point 2: Initialize background change detector
        state_dir = self.config.paths.output_root / "convergence_state"
        self.bg_change_detector = BackgroundChangeDetector(
            workspace_root=self.config.paths.workspace_root,
            state_dir=state_dir
        )
    
    def execute_full_pipeline(self, iteration: int = 1) -> bool:
        """
        Execute full pipeline for one iteration
        
        Args:
            iteration: Iteration number
            
        Returns:
            bool: Success status
        """
        print("\n" + "="*80)
        print("DMAIC V3.3 - FULL PIPELINE ORCHESTRATOR")
        print("="*80)
        print(f"Iteration: {iteration}")
        print(f"Start Time: {datetime.now().isoformat()}")
        print(f"Idempotency: {'ENABLED' if self.enable_idempotency_flag else 'DISABLED'}")
        print(f"Git Commits: {'ENABLED' if self.enable_git_commits else 'DISABLED'}")
        print("="*80)

        start_time = datetime.now()
        phases_executed = []

        # Integration Point 3: Start background change detection
        self.bg_change_detector.start()

        try:
            # Phase 0: Initialization
            success, results = self._execute_phase_with_tracking(
                Phase0Init(self.config, self.state_mgr),
                "Phase 0: Initialization",
                iteration
            )
            if not success:
                return False
            phases_executed.append('phase0_init')
            
            # Phase 1: Define
            success, results = self._execute_phase_with_tracking(
                Phase1Define(self.config, self.state_mgr),
                "Phase 1: Define",
                iteration
            )
            if not success:
                return False
            phases_executed.append('phase1_define')
            
            # Phase 2: Measure
            success, results = self._execute_phase_with_tracking(
                Phase2Measure(self.config, self.state_mgr),
                "Phase 2: Measure",
                iteration
            )
            if not success:
                return False
            phases_executed.append('phase2_measure')
            
            # Phase 3: Analyze
            success, results = self._execute_phase_with_tracking(
                Phase3Analyze(self.config, self.state_mgr),
                "Phase 3: Analyze",
                iteration
            )
            if not success:
                return False
            phases_executed.append('phase3_analyze')
            
            # Phase 4: Improve
            success, results = self._execute_phase_with_tracking(
                Phase4Improve(self.config, self.state_mgr),
                "Phase 4: Improve",
                iteration
            )
            if not success:
                return False
            phases_executed.append('phase4_improve')
            
            # Phase 5: Control
            success, results = self._execute_phase_with_tracking(
                Phase5Control(self.config, self.state_mgr),
                "Phase 5: Control",
                iteration
            )
            if not success:
                return False
            phases_executed.append('phase5_control')
            
            # Phase 6: Knowledge (Devour/Learn)
            success, results = self._execute_phase_with_tracking(
                Phase6Knowledge(self.config, self.state_mgr),
                "Phase 6: Knowledge (Devour/Learn)",
                iteration
            )
            if not success:
                print("[WARNING] Phase 6 failed but continuing...")
            phases_executed.append('phase6_knowledge')
            
            # Phase 7: Action Tracking
            success, results = self._execute_phase_with_tracking(
                Phase7ActionTracking(self.config, self.state_mgr),
                "Phase 7: Action Tracking",
                iteration
            )
            if not success:
                print("[WARNING] Phase 7 failed but continuing...")
            phases_executed.append('phase7_action_tracking')

            # Phase 8: TODO Management
            success, results = self._execute_phase_with_tracking(
                Phase8TODOManagement(self.config, self.state_mgr),
                "Phase 8: TODO Management",
                iteration
            )
            if not success:
                print("[WARNING] Phase 8 failed but continuing...")
            phases_executed.append('phase8_todo_management')
            
            # Update planning matrix
            print("\n[TRACKING] Updating planning matrix...")
            self.planning_tracker.scan_actual_state(Path("DMAIC_V3_OUTPUT"))
            self.planning_tracker.determine_current_state()
            self.planning_tracker.calculate_possible_next()
            self.planning_tracker.save_snapshot(iteration)
            
            # Generate execution summary
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            self._generate_execution_summary(
                iteration=iteration,
                phases_executed=phases_executed,
                duration=duration,
                success=True
            )
            
            # Commit to git
            if self.enable_git_commits:
                self._git_commit(iteration)
            
            print("\n" + "="*80)
            print(f"[SUCCESS] ITERATION {iteration} COMPLETE")
            print(f"Duration: {duration:.2f}s")
            print(f"Phases Executed: {len(phases_executed)}")
            print("="*80)

            return True

        except Exception as e:
            print(f"\n[ERROR] Pipeline failed: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            # Integration Point 4: Stop background change detection
            self.bg_change_detector.stop()

            # Integration Point 5: Get and display final summary
            change_summary = self.bg_change_detector.get_summary()
            print(f"\n{'='*80}")
            print("[Background Change Detection] Final Summary:")
            print(f"  Total changes detected: {change_summary.get('total', 0)}")
            print(f"  Files added: {change_summary.get('added', 0)}")
            print(f"  Files modified: {change_summary.get('modified', 0)}")
            print(f"  Files deleted: {change_summary.get('deleted', 0)}")
            if change_summary.get('timestamp'):
                print(f"  Last snapshot: {change_summary.get('timestamp')}")
            print(f"{'='*80}")
    
    def _execute_phase_with_tracking(self,
                                     phase_obj: Any,
                                     phase_name: str,
                                     iteration: int) -> Tuple[bool, Dict]:
        """Execute a phase with full tracking and visible output"""
        print(f"\n{'-'*80}")
        print(f"> EXECUTING: {phase_name}")
        print(f"{'-'*80}")

        start_time = datetime.now()
        
        try:
            result = phase_obj.execute(iteration=iteration)
            
            # Handle both tuple (old) and dict (new) return types
            if isinstance(result, tuple):
                success, results = result
            else:
                # Dict return - determine success from result
                results = result
                success = not results.get('error') and not results.get('skipped', False)
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            log_entry = {
                'phase': phase_name,
                'iteration': iteration,
                'success': success,
                'duration_seconds': duration,
                'timestamp': end_time.isoformat()
            }
            self.execution_log.append(log_entry)
            
            if success:
                print(f"\n[OK] {phase_name} completed in {duration:.2f}s")
            else:
                print(f"\n[FAIL] {phase_name} failed after {duration:.2f}s")
            
            return success, results
            
        except Exception as e:
            print(f"\n[FAIL] {phase_name} crashed: {e}")
            import traceback
            traceback.print_exc()
            return False, {'error': str(e)}
    
    def _generate_execution_summary(self, 
                                    iteration: int,
                                    phases_executed: List[str],
                                    duration: float,
                                    success: bool):
        """Generate execution summary"""
        summary_file = Path(f"DMAIC_V3_OUTPUT/iteration_{iteration}/EXECUTION_SUMMARY.md")
        summary_file.parent.mkdir(parents=True, exist_ok=True)
        
        summary = []
        summary.append(f"# DMAIC V3.3 - Iteration {iteration} Execution Summary\n")
        summary.append(f"**Status:** {'SUCCESS' if success else 'FAILED'}")
        summary.append(f"**Duration:** {duration:.2f} seconds")
        summary.append(f"**Timestamp:** {datetime.now().isoformat()}\n")
        
        summary.append("## Phases Executed\n")
        for idx, phase in enumerate(phases_executed, 1):
            log = next((l for l in self.execution_log if phase in l.get('phase', '')), None)
            if log:
                status = "[OK]" if log['success'] else "[FAIL]"
                summary.append(f"{idx}. {status} {phase} ({log['duration_seconds']:.2f}s)")
        
        summary.append("\n## Execution Log\n")
        summary.append("```json")
        summary.append(json.dumps(self.execution_log, indent=2))
        summary.append("```")
        
        with open(summary_file, 'w') as f:
            f.write('\n'.join(summary))
        
        print(f"\n[TRACKING] Execution summary saved: {summary_file}")
    
    def _git_commit(self, iteration: int):
        """Commit iteration results to git"""
        try:
            print("\n[GIT] Committing iteration results...")
            subprocess.run(['git', 'add', 'DMAIC_V3_OUTPUT/', 'planning_matrix.json'],
                          check=False)
            subprocess.run(['git', 'commit', '-m',
                          f'DMAIC V3.3 - Iteration {iteration} complete'],
                          check=False)
            print("[GIT] [OK] Committed")
        except Exception as e:
            print(f"[GIT] Warning: Commit failed: {e}")


def main() -> Any:
    """Main execution entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='DMAIC V3.3 Full Pipeline Orchestrator')
    parser.add_argument('--iteration', type=int, default=1, 
                       help='Iteration number (default: 1)')
    parser.add_argument('--no-idempotency', action='store_true',
                       help='Disable idempotency (force re-run)')
    parser.add_argument('--no-git', action='store_true',
                       help='Disable git commits')
    parser.add_argument('--quiet', action='store_true',
                       help='Reduce output verbosity')
    
    args = parser.parse_args()
    
    orchestrator = FullPipelineOrchestrator(
        enable_idempotency_flag=not args.no_idempotency,
        enable_git_commits=not args.no_git,
        verbose=not args.quiet
    )
    
    success = orchestrator.execute_full_pipeline(iteration=args.iteration)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
