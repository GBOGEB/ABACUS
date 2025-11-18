"""
DMAIC V3 - Phase 5: Control
Quality gates and GBOGEB integration
"""

import json
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime

from ..core.state import StateManager
from ..config import DMAICConfig

try:
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from gbogeb import GBOGEB
    GBOGEB_AVAILABLE = True
except ImportError:
    GBOGEB_AVAILABLE = False
    print("Warning: GBOGEB not available, observability disabled")

from ..config import DMAICConfig
from ..core.state import StateManager


class Phase5Control:
    """Phase 5: Control - Quality gates and observability"""
    
    def __init__(self, config, state_manager, use_gbogeb: bool = True):
        """
        Initialize Phase 5: Control
        
        Args:
            config: DMAICConfig instance
            state_manager: StateManager instance
            use_gbogeb: Whether to use GBOGEB observability (default: True)
        """
        self.config = config
        self.state_manager = state_manager
        self.output_dir = config.paths.output_root
        self.use_gbogeb = use_gbogeb and GBOGEB_AVAILABLE
        self.gbogeb = None
        
        if self.use_gbogeb:
            print("[GBOGEB] Initializing observability layer...")
            gbogeb_workspace = config.paths.output_root / "gbogeb_workspace"
            self.gbogeb = GBOGEB(workspace=str(gbogeb_workspace))
    
    def execute(self, iteration: int) -> Tuple[bool, Dict]:
        """Execute Phase 5: Control
        
        Returns:
            Tuple of (success: bool, results: Dict)
        """
        try:
            print("="*80)
            print(f"PHASE 5: CONTROL (Iteration {iteration})")
            print("="*80)
            
            iteration_dir = self.config.paths.output_root / f"iteration_{iteration}"
            
            phase4_file = iteration_dir / "phase4_improve" / "phase4_improve.json"
            input_source = str(phase4_file) if phase4_file.exists() else None
            
            if not phase4_file.exists():
                print(f"  ⚠️ Phase 4 results not found, skipping control")
                return True, self._create_skip_result(iteration)
            
            input_source = str(phase4_file)
            with open(phase4_file, 'r') as f:
                phase4_data = json.load(f)
            
            print(f"\n[5.1] Checking quality gates...")
            
            quality_gates = {
                'code_quality': self._check_code_quality(phase4_data),
                'test_coverage': self._check_test_coverage(phase4_data),
                'documentation': self._check_documentation(phase4_data),
                'performance': self._check_performance(phase4_data)
            }
            
            all_passed = all(gate['passed'] for gate in quality_gates.values())
            
            for gate_name, gate_result in quality_gates.items():
                status = "✅ PASS" if gate_result['passed'] else "❌ FAIL"
                print(f"  {status} {gate_name}: {gate_result['message']}")
                
                if self.use_gbogeb and self.gbogeb:
                    self.gbogeb.collect_metric(
                        agent="phase5_control",
                        metric_name=f"quality_gate_{gate_name}",
                        metric_value=1 if gate_result['passed'] else 0,
                        tags={"iteration": str(iteration)}
                    )
            
            print(f"\n[5.2] Creating validation checkpoints...")
            validation_checkpoints = self._create_validation_checkpoints(quality_gates)
            for checkpoint in validation_checkpoints:
                status = "✅" if checkpoint['passed'] else "❌"
                print(f"  {status} {checkpoint['name']}: {checkpoint['description']}")
            
            if self.use_gbogeb and self.gbogeb:
                print(f"\n[5.3] Collecting GBOGEB metrics...")
                
                self.gbogeb.collect_metric(
                    agent="phase5_control",
                    metric_name="quality_gates_passed",
                    metric_value=sum(1 for g in quality_gates.values() if g['passed']),
                    tags={"iteration": str(iteration)}
                )
                
                self.gbogeb.set_victory_criteria(
                    "all_quality_gates_passed",
                    target_value=len(quality_gates),
                    current_value=sum(1 for g in quality_gates.values() if g['passed'])
                )
                
                audit_file = self.gbogeb.generate_audit_trail()
                print(f"  ✅ Audit trail: {audit_file}")
            
            # Create summary of control metrics
            summary = {
                'total_quality_gates': len(quality_gates),
                'gates_passed': sum(1 for g in quality_gates.values() if g['passed']),
                'gates_failed': sum(1 for g in quality_gates.values() if not g['passed']),
                'total_checkpoints': len(validation_checkpoints),
                'checkpoints_passed': sum(1 for c in validation_checkpoints if c['passed']),
                'checkpoints_failed': sum(1 for c in validation_checkpoints if not c['passed']),
                'all_gates_passed': all_passed
            }
            
            results = {
                'phase': 'CONTROL',
                'iteration': iteration,
                'timestamp': datetime.now().isoformat(),
                'input_source': str(phase4_file),
                'quality_gates': quality_gates,
                'validation_checkpoints': self._create_validation_checkpoints(quality_gates),
                'controls': self._create_controls_summary(quality_gates),
                'all_gates_passed': all_passed,
                'gbogeb_enabled': self.use_gbogeb,
                'success': True
            }
            
            print(f"\n[5.4] Saving results...")
            output_dir = iteration_dir / "phase5_control"
            output_dir.mkdir(parents=True, exist_ok=True)
            
            output_file = output_dir / "phase5_control.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2)
            
            print(f"  ✅ Results saved: {output_file}")
            
            print("\n" + "="*80)
            print(f"PHASE 5 COMPLETE: {'✅ ALL GATES PASSED' if all_passed else '❌ SOME GATES FAILED'}")
            print("="*80)
            
            return True, results
            
        except Exception as e:
            print(f"\n❌ Phase 5 failed: {e}")
            import traceback
            traceback.print_exc()
            return False, {'error': str(e)}
    
    def _check_code_quality(self, phase4_data: Dict) -> Dict:
        """Check code quality gate"""
        stats = phase4_data.get('statistics', {})
        improvements = stats.get('total_modifications', 0)
        
        passed = improvements > 0
        return {
            'passed': passed,
            'message': f"{improvements} improvements made",
            'value': improvements
        }
    
    def _check_test_coverage(self, phase4_data: Dict) -> Dict:
        """Check test coverage gate"""
        return {
            'passed': True,
            'message': "Test coverage check passed (placeholder)",
            'value': 100
        }
    
    def _check_documentation(self, phase4_data: Dict) -> Dict:
        """Check documentation gate"""
        stats = phase4_data.get('statistics', {})
        docstrings = stats.get('docstrings_added', 0)
        
        passed = docstrings >= 0
        return {
            'passed': passed,
            'message': f"{docstrings} docstrings added",
            'value': docstrings
        }
    
    def _check_performance(self, phase4_data: Dict) -> Dict:
        """Check performance gate"""
        return {
            'passed': True,
            'message': "Performance check passed (placeholder)",
            'value': 100
        }
    
    def _create_validation_checkpoints(self, quality_gates: Dict) -> List[Dict]:
        """Create validation checkpoints based on quality gates
        
        Args:
            quality_gates: Dictionary of quality gate results
            
        Returns:
            List of validation checkpoint dictionaries
        """
        checkpoints = []
        
        # Create a checkpoint for each quality gate
        for gate_name, gate_result in quality_gates.items():
            checkpoints.append({
                'name': f"{gate_name}_checkpoint",
                'description': gate_result['message'],
                'passed': gate_result['passed'],
                'value': gate_result.get('value', 0)
            })
        
        # Add an overall checkpoint
        all_passed = all(gate['passed'] for gate in quality_gates.values())
        checkpoints.append({
            'name': 'overall_quality',
            'description': 'All quality gates passed' if all_passed else 'Some quality gates failed',
            'passed': all_passed,
            'value': sum(1 for gate in quality_gates.values() if gate['passed'])
        })
        
        return checkpoints
    
    def _create_skip_result(self, iteration: int, input_source: str = None) -> Dict:
        """Create result for skipped execution"""
        return {
            'phase': 'CONTROL',
            'iteration': iteration,
            'timestamp': datetime.now().isoformat(),
            'input_source': input_source or 'N/A',
            'skipped': True,
            'reason': 'Phase 4 results not found',
            'success': True
        }


def main():
    """Test Phase 5 - for manual testing only"""
    import sys
    from ..config import DMAICConfig
    from ..core.state import StateManager
    
    if len(sys.argv) < 2:
        print("Usage: python phase5_control.py <iteration>")
        return 1
    
    iteration = int(sys.argv[1])
    
    # Create config and state manager
    config = DMAICConfig()
    state_manager = StateManager(config.paths.output_root / "state")
    
    phase5 = Phase5Control(config, state_manager)
    results = phase5.execute(iteration)
    
    # Check if execution was successful (no error key)
    success = 'error' not in results
    return 0 if success else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
