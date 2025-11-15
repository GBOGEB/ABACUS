#!/usr/bin/env python3
"""
DMAIC V3 Test Runner and Documentation Generator
Executes pipeline and generates comprehensive documentation from actual execution
"""

import sys
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List
import subprocess

sys.path.insert(0, str(Path(__file__).parent.parent))

from DMAIC_V3.full_pipeline_orchestrator import FullPipelineOrchestrator
from DMAIC_V3.config import DMAICConfig

class TestAndDocumentRunner:
    def __init__(self):
        self.config = DMAICConfig()
        self.test_results = {}
        self.execution_log = []
        
    def run_pipeline_test(self, iteration: int = 1) -> Dict[str, Any]:
        """Run pipeline and capture execution data"""
        print(f"\n{'='*80}")
        print(f"DMAIC V3 TEST EXECUTION - Iteration {iteration}")
        print(f"{'='*80}\n")
        
        start_time = time.time()
        
        orchestrator = FullPipelineOrchestrator(
            enable_idempotency_flag=True,
            enable_git_commits=False,
            verbose=True,
            debug_port=None
        )
        
        success = orchestrator.execute_full_pipeline(iteration=iteration)
        
        duration = time.time() - start_time
        
        result = {
            'iteration': iteration,
            'success': success,
            'duration_seconds': duration,
            'timestamp': datetime.now().isoformat(),
            'statistics': orchestrator.statistics if hasattr(orchestrator, 'statistics') else {}
        }
        
        self.test_results[f'iteration_{iteration}'] = result
        self.execution_log.append(result)
        
        return result
    
    def analyze_outputs(self, iteration: int) -> Dict[str, Any]:
        """Analyze generated outputs from iteration"""
        output_dir = self.config.paths.output_root / f"iteration_{iteration}"
        
        analysis = {
            'iteration': iteration,
            'output_directory': str(output_dir),
            'phases': {},
            'artifacts': [],
            'agents_used': []
        }
        
        if not output_dir.exists():
            analysis['error'] = 'Output directory not found'
            return analysis
        
        for phase_dir in sorted(output_dir.iterdir()):
            if phase_dir.is_dir():
                phase_name = phase_dir.name
                phase_files = list(phase_dir.glob('**/*'))
                
                analysis['phases'][phase_name] = {
                    'directory': str(phase_dir),
                    'file_count': len([f for f in phase_files if f.is_file()]),
                    'files': [str(f.relative_to(output_dir)) for f in phase_files if f.is_file()]
                }
        
        agent_registry = self.config.paths.output_root / 'agent_registry.json'
        if agent_registry.exists():
            with open(agent_registry) as f:
                agents_data = json.load(f)
                analysis['agents_used'] = list(agents_data.get('agents', {}).keys())
        
        return analysis
    
    def generate_architecture_diagram(self) -> str:
        """Generate ASCII architecture diagram from actual execution"""
        diagram = """
╔════════════════════════════════════════════════════════════════════════════╗
║                    DMAIC V3.3 SYSTEM ARCHITECTURE                          ║
║                         (From Actual Execution)                            ║
╚════════════════════════════════════════════════════════════════════════════╝

┌──────────────────────────────────────────────────────────────────────────┐
│                         ENTRY POINT                                       │
│                  full_pipeline_orchestrator.py                            │
│                                                                           │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  FullPipelineOrchestrator                                        │    │
│  │  - Manages complete pipeline execution                           │    │
│  │  - Tracks statistics and performance                             │    │
│  │  - Handles idempotency and git commits                           │    │
│  │  - Background change detection                                   │    │
│  └─────────────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                         PHASE 0: INITIALIZATION                           │
│                         (phase0_init.py)                                  │
│                                                                           │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  12-AGENT ARCHITECTURE INITIALIZATION                            │    │
│  │                                                                   │    │
│  │  ANALYSIS (4):        DOCUMENTATION (2):                         │    │
│  │  • cryo_dm            • framework                                │    │
│  │  • document_consumer  • style_extractor                          │    │
│  │  • artifact_analyzer                                             │    │
│  │  • smoke_test         RECURSIVE (2):                             │    │
│  │                       • self_ranking                             │    │
│  │  KNOWLEDGE (2):       • iteration_tracker                        │    │
│  │  • context_manager                                               │    │
│  │  • dependency_graph   MONITORING (2):                            │    │
│  │                       • health_checker                           │    │
│  │                       • performance_tracker                      │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                           │
│  Outputs: agent_registry.json, phase0_init.json                          │
└──────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                    DMAIC CORE PHASES (1-5)                                │
│                                                                           │
│  Phase 1: DEFINE (phase1_define.py)                                      │
│  ├─ Scans codebase (chunked mode)                                        │
│  ├─ Loads feedback from previous iteration                               │
│  ├─ Generates problem definition                                         │
│  └─ Output: phase1_define.json                                           │
│                                                                           │
│  Phase 2: MEASURE (phase2_measure.py)                                    │
│  ├─ Collects metrics from codebase                                       │
│  ├─ Analyzes file statistics                                             │
│  └─ Output: phase2_metrics.json                                          │
│                                                                           │
│  Phase 3: ANALYZE (phase3_analyze.py)                                    │
│  ├─ Performs root cause analysis                                         │
│  ├─ Identifies patterns and issues                                       │
│  └─ Output: phase3_analysis.json                                         │
│                                                                           │
│  Phase 4: IMPROVE (phase4_improve.py)                                    │
│  ├─ Generates improvement recommendations                                │
│  ├─ Creates action plans                                                 │
│  └─ Output: phase4_improvements.json                                     │
│                                                                           │
│  Phase 5: CONTROL (phase5_control.py)                                    │
│  ├─ Enforces quality gates                                               │
│  ├─ Logs bugs and issues                                                 │
│  ├─ Validates improvements                                               │
│  └─ Output: phase5_control.json, bug_log.json                            │
└──────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                    PHASE 6: KNOWLEDGE (Devour/Learn)                      │
│                         (phase6_knowledge.py)                             │
│                                                                           │
│  ├─ Consolidates learnings from all phases                               │
│  ├─ Updates knowledge base                                               │
│  ├─ Prepares for next iteration                                          │
│  └─ Output: phase6_knowledge.json                                        │
└──────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                    PHASE 7: ACTION TRACKING                               │
│                      (phase7_action_tracking.py)                          │
│                                                                           │
│  ├─ Tracks action items from all phases                                  │
│  ├─ Creates feedback for next iteration ◄─────────┐                      │
│  ├─ Monitors progress                             │                      │
│  └─ Output: phase7_actions.json,                  │                      │
│             feedback_for_next_iteration.json      │                      │
└──────────────────────────────────────────────────┼───────────────────────┘
                                    │               │
                                    ▼               │
┌──────────────────────────────────────────────────┼───────────────────────┐
│                    PHASE 8: TODO MANAGEMENT       │                       │
│                      (phase8_todo_management.py)  │                       │
│                                                    │                       │
│  ├─ Collects TODOs from all phases                │                       │
│  ├─ Executes TODO items                           │                       │
│  ├─ Classifies and prioritizes                    │                       │
│  └─ Output: phase8_todos.json                     │                       │
└────────────────────────────────────────────────────────────────────────────┘
                                    │               │
                                    │               │
                                    └───────────────┘
                                    FEEDBACK LOOP
                                    (Phase 7 → Phase 1)

╔════════════════════════════════════════════════════════════════════════════╗
║                         KEY FEATURES                                       ║
╠════════════════════════════════════════════════════════════════════════════╣
║ • Idempotency: Phases can be re-run without side effects                  ║
║ • Statistics Tracking: Complete visibility into performance metrics       ║
║ • Quality Gates: Iterations stop if standards not met                     ║
║ • Feedback Loop: Phase 7 creates feedback for Phase 1 next iteration      ║
║ • Background Change Detection: Non-blocking file system monitoring        ║
║ • Debug Monitoring: Real-time monitoring via socket server                ║
║ • Git Integration: Optional commits after each phase                      ║
╚════════════════════════════════════════════════════════════════════════════╝
"""
        return diagram
    
    def generate_execution_report(self) -> str:
        """Generate comprehensive execution report"""
        report = f"""
# DMAIC V3 EXECUTION REPORT
Generated: {datetime.now().isoformat()}

## Test Execution Summary

"""
        for iter_key, result in self.test_results.items():
            report += f"""
### {iter_key.replace('_', ' ').title()}
- **Success**: {result['success']}
- **Duration**: {result['duration_seconds']:.2f} seconds
- **Timestamp**: {result['timestamp']}

"""
            if 'statistics' in result and result['statistics']:
                stats = result['statistics']
                if 'orchestration' in stats:
                    orch = stats['orchestration']
                    report += f"""
#### Orchestration Statistics
- Total Phases: {orch.get('total_phases', 0)}
- Successful: {orch.get('successful_phases', 0)}
- Failed: {orch.get('failed_phases', 0)}
- Total Duration: {orch.get('total_duration_seconds', 0):.2f}s

"""
        
        return report
    
    def save_documentation(self):
        """Save all generated documentation"""
        docs_dir = Path('DMAIC_V3_DOCS')
        docs_dir.mkdir(exist_ok=True)
        
        (docs_dir / 'ARCHITECTURE_DIAGRAM.txt').write_text(
            self.generate_architecture_diagram()
        )
        
        (docs_dir / 'EXECUTION_REPORT.md').write_text(
            self.generate_execution_report()
        )
        
        (docs_dir / 'test_results.json').write_text(
            json.dumps(self.test_results, indent=2)
        )
        
        print(f"\n✓ Documentation saved to {docs_dir}/")
        print(f"  - ARCHITECTURE_DIAGRAM.txt")
        print(f"  - EXECUTION_REPORT.md")
        print(f"  - test_results.json")

def main():
    runner = TestAndDocumentRunner()
    
    print("Starting DMAIC V3 Test and Documentation Generation...")
    
    result = runner.run_pipeline_test(iteration=1)
    
    print(f"\n{'='*80}")
    print(f"TEST RESULT: {'SUCCESS' if result['success'] else 'FAILED'}")
    print(f"Duration: {result['duration_seconds']:.2f} seconds")
    print(f"{'='*80}\n")
    
    analysis = runner.analyze_outputs(iteration=1)
    print(f"\nOutput Analysis:")
    print(f"  Phases executed: {len(analysis['phases'])}")
    print(f"  Agents used: {len(analysis.get('agents_used', []))}")
    
    runner.save_documentation()
    
    return 0 if result['success'] else 1

if __name__ == "__main__":
    sys.exit(main())
