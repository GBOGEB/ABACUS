#!/usr/bin/env python3
"""
DMAIC V4.0 - INDIVIDUAL PHASE RUNNER WITH TEMPORAL ENGINE
Executes individual phases with full temporal tracking and DOW integration
"""

import sys
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
import argparse

sys.path.insert(0, str(Path(__file__).parent.parent))

from DMAIC_V3.config import DMAICConfig
from DMAIC_V3.core.state import StateManager
from DMAIC_V3.core.idempotency_wrapper import enable_idempotency
from DMAIC_V3.phases.phase0_init import Phase0Init
from DMAIC_V3.phases.phase1_define import Phase1Define
from DMAIC_V3.phases.phase2_measure import Phase2Measure
from DMAIC_V3.phases.phase3_analyze import Phase3Analyze
from DMAIC_V3.phases.phase4_improve import Phase4Improve
from DMAIC_V3.phases.phase5_control import Phase5Control
from DMAIC_V3.phases.phase6_knowledge import Phase6Knowledge
from DMAIC_V3.phases.phase7_action_tracking import Phase7ActionTracking
from DMAIC_V3.phases.phase8_todo_management import Phase8TODOManagement

class TemporalPhaseRunner:
    """
    Individual Phase Runner with Temporal Engine Integration
    
    Features:
    - Run any phase independently
    - Full temporal tracking
    - DOW (Devour-Optimize-Win) integration
    - Task-level execution
    - Performance metrics
    """
    
    PHASE_MAP = {
        0: ("Phase 0: Initialization", Phase0Init),
        1: ("Phase 1: Define", Phase1Define),
        2: ("Phase 2: Measure", Phase2Measure),
        3: ("Phase 3: Analyze", Phase3Analyze),
        4: ("Phase 4: Improve", Phase4Improve),
        5: ("Phase 5: Control", Phase5Control),
        6: ("Phase 6: Knowledge (DEVOUR)", Phase6Knowledge),
        7: ("Phase 7: Action Tracking", Phase7ActionTracking),
        8: ("Phase 8: TODO Management", Phase8TODOManagement),
    }
    
    def __init__(self, enable_temporal: bool = True, enable_dow: bool = True):
        self.config = DMAICConfig()
        self.state_mgr = StateManager(self.config.paths.state_dir)
        self.enable_temporal = enable_temporal
        self.enable_dow = enable_dow
        
        self.execution_log = []
        self.temporal_snapshots = []
        
        enable_idempotency(enabled=True)
        
    def run_phase(self, phase_num: int, iteration: int = 1, task_filter: Optional[str] = None) -> Dict[str, Any]:
        """
        Run a specific phase with temporal tracking
        
        Args:
            phase_num: Phase number (0-8)
            iteration: Iteration number
            task_filter: Optional task filter (e.g., "1.1", "2.3")
        """
        if phase_num not in self.PHASE_MAP:
            raise ValueError(f"Invalid phase number: {phase_num}. Must be 0-8.")
        
        phase_name, phase_class = self.PHASE_MAP[phase_num]
        
        print(f"\n{'='*80}")
        print(f"TEMPORAL PHASE RUNNER - {phase_name}")
        print(f"{'='*80}")
        print(f"Iteration: {iteration}")
        print(f"Temporal Tracking: {'ENABLED' if self.enable_temporal else 'DISABLED'}")
        print(f"DOW Integration: {'ENABLED' if self.enable_dow else 'DISABLED'}")
        if task_filter:
            print(f"Task Filter: {task_filter}")
        print(f"{'='*80}\n")
        
        # Temporal snapshot - BEFORE
        if self.enable_temporal:
            self._take_temporal_snapshot("BEFORE", phase_num, iteration)
        
        start_time = time.time()
        
        try:
            # Initialize phase - try different parameter names for compatibility
            try:
                phase_obj = phase_class(config=self.config, state_manager=self.state_mgr)
            except TypeError:
                try:
                    # Some phases use 'state' instead of 'state_manager'
                    phase_obj = phase_class(config=self.config, state=self.state_mgr)
                except TypeError:
                    # Some phases use 'state_mgr'
                    phase_obj = phase_class(config=self.config, state_mgr=self.state_mgr)

            # Execute phase
            print(f"\n[EXECUTING] {phase_name}...")
            exec_result = phase_obj.execute(iteration=iteration)
            
            # Handle both tuple (success, result) and dict returns
            if isinstance(exec_result, tuple):
                success, result = exec_result
            else:
                # Assume dict return - success determined by presence of 'phase' field
                result = exec_result
                success = 'phase' in result
            
            duration = time.time() - start_time
            
            # Temporal snapshot - AFTER
            if self.enable_temporal:
                self._take_temporal_snapshot("AFTER", phase_num, iteration)
            
            # DOW Integration - Devour phase outputs
            if self.enable_dow and success:
                self._devour_phase_output(phase_num, iteration, result)
            
            execution_record = {
                'phase': phase_num,
                'phase_name': phase_name,
                'iteration': iteration,
                'success': success,
                'duration_seconds': duration,
                'timestamp': datetime.now().isoformat(),
                'result': result
            }
            
            self.execution_log.append(execution_record)
            
            print(f"\n{'='*80}")
            print(f"PHASE {phase_num} RESULT: {'✅ SUCCESS' if success else '❌ FAILED'}")
            print(f"Duration: {duration:.2f}s")
            print(f"{'='*80}\n")
            
            return execution_record
            
        except Exception as e:
            duration = time.time() - start_time
            print(f"\n{'='*80}")
            print(f"PHASE {phase_num} ERROR: {str(e)}")
            print(f"Duration: {duration:.2f}s")
            print(f"{'='*80}\n")
            
            execution_record = {
                'phase': phase_num,
                'phase_name': phase_name,
                'iteration': iteration,
                'success': False,
                'duration_seconds': duration,
                'timestamp': datetime.now().isoformat(),
                'error': str(e)
            }
            
            self.execution_log.append(execution_record)
            return execution_record
    
    def run_all_phases(self, iteration: int = 1) -> Dict[str, Any]:
        """Run all phases sequentially with temporal tracking"""
        print(f"\n{'='*80}")
        print(f"RUNNING ALL PHASES - ITERATION {iteration}")
        print(f"{'='*80}\n")
        
        results = []
        for phase_num in range(9):
            result = self.run_phase(phase_num, iteration)
            results.append(result)
            
            if not result['success']:
                print(f"\n⚠️  Phase {phase_num} failed. Stopping execution.")
                break
        
        summary = {
            'iteration': iteration,
            'total_phases': len(results),
            'successful_phases': sum(1 for r in results if r['success']),
            'failed_phases': sum(1 for r in results if not r['success']),
            'total_duration': sum(r['duration_seconds'] for r in results),
            'results': results,
            'temporal_snapshots': self.temporal_snapshots
        }
        
        self._save_execution_summary(summary)
        
        return summary
    
    def _take_temporal_snapshot(self, stage: str, phase_num: int, iteration: int):
        """Take a temporal snapshot of the system state"""
        snapshot = {
            'stage': stage,
            'phase': phase_num,
            'iteration': iteration,
            'timestamp': datetime.now().isoformat(),
            'output_dir_size': self._get_dir_size(self.config.paths.output_root),
            'file_count': self._count_files(self.config.paths.output_root)
        }
        
        self.temporal_snapshots.append(snapshot)
        print(f"  [TEMPORAL] Snapshot taken: {stage} - Phase {phase_num}")
    
    def _devour_phase_output(self, phase_num: int, iteration: int, result: Dict[str, Any]):
        """
        DOW Integration: Devour phase outputs for learning
        
        This is the "Devour" part of Devour-Optimize-Win
        """
        print(f"\n  [DOW] Devouring Phase {phase_num} outputs...")
        
        devour_data = {
            'phase': phase_num,
            'iteration': iteration,
            'timestamp': datetime.now().isoformat(),
            'insights': [],
            'patterns': [],
            'improvements': []
        }
        
        # Extract insights from result
        if isinstance(result, dict):
            if 'metrics' in result:
                devour_data['insights'].append(f"Metrics collected: {len(result['metrics'])} items")
            if 'improvements' in result:
                devour_data['insights'].append(f"Improvements identified: {len(result['improvements'])} items")
            if 'quality_gates' in result:
                devour_data['insights'].append(f"Quality gates: {len(result['quality_gates'])} gates")
        
        # Save devoured knowledge
        devour_file = self.config.paths.output_root / f"iteration_{iteration}" / f"devoured_phase{phase_num}.json"
        devour_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(devour_file, 'w') as f:
            json.dump(devour_data, f, indent=2)
        
        print(f"  [DOW] ✅ Devoured {len(devour_data['insights'])} insights")
    
    def _get_dir_size(self, path: Path) -> int:
        """Get total size of directory in bytes"""
        if not path.exists():
            return 0
        return sum(f.stat().st_size for f in path.rglob('*') if f.is_file())
    
    def _count_files(self, path: Path) -> int:
        """Count total files in directory"""
        if not path.exists():
            return 0
        return len([f for f in path.rglob('*') if f.is_file()])
    
    def _save_execution_summary(self, summary: Dict[str, Any]):
        """Save execution summary to file"""
        output_file = self.config.paths.output_root / f"temporal_execution_iteration_{summary['iteration']}.json"
        
        with open(output_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"\n✅ Execution summary saved: {output_file}")

def main():
    parser = argparse.ArgumentParser(description="DMAIC V4.0 Individual Phase Runner")
    parser.add_argument('--phase', type=int, choices=range(9), help='Phase number to run (0-8)')
    parser.add_argument('--iteration', type=int, default=1, help='Iteration number')
    parser.add_argument('--all', action='store_true', help='Run all phases')
    parser.add_argument('--no-temporal', action='store_true', help='Disable temporal tracking')
    parser.add_argument('--no-dow', action='store_true', help='Disable DOW integration')
    parser.add_argument('--task', type=str, help='Task filter (e.g., "1.1", "2.3")')
    
    args = parser.parse_args()
    
    runner = TemporalPhaseRunner(
        enable_temporal=not args.no_temporal,
        enable_dow=not args.no_dow
    )
    
    if args.all:
        result = runner.run_all_phases(iteration=args.iteration)
        print(f"\n{'='*80}")
        print(f"ALL PHASES COMPLETED")
        print(f"{'='*80}")
        print(f"Total Phases: {result['total_phases']}")
        print(f"Successful: {result['successful_phases']}")
        print(f"Failed: {result['failed_phases']}")
        print(f"Total Duration: {result['total_duration']:.2f}s")
        print(f"{'='*80}\n")
        
        return 0 if result['failed_phases'] == 0 else 1
    
    elif args.phase is not None:
        result = runner.run_phase(args.phase, args.iteration, args.task)
        return 0 if result['success'] else 1
    
    else:
        parser.print_help()
        return 1

if __name__ == "__main__":
    sys.exit(main())
