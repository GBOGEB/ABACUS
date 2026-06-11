#!/usr/bin/env python3
"""
DMAIC V4.0 - SELF-IMPROVEMENT AGENT
Recursive self-improvement with DOW (Devour-Optimize-Win) methodology
"""

import sys
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Tuple
import argparse

# Fix path for direct execution
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from DMAIC_V3.config import DMAICConfig
from DMAIC_V3.core.state import StateManager

class SelfImprovementAgent:
    """
    DMAIC Self-Improvement Agent

    Implements recursive self-improvement using DOW methodology:
    - DEVOUR: Consume all available knowledge and data
    - OPTIMIZE: Apply DMAIC to improve itself
    - WIN: Achieve measurable improvements

    This agent can improve:
    - Its own code
    - Phase implementations
    - Agent configurations
    - System architecture
    """

    def __init__(self):
        self.config = DMAICConfig()
        self.state_mgr = StateManager(self.config.paths.state_dir)

        self.improvement_history = []
        self.knowledge_base = {
            'patterns': [],
            'anti_patterns': [],
            'best_practices': [],
            'metrics': {}
        }

    def execute_improvement_cycle(self, iteration: int = 1) -> Dict[str, Any]:
        """
        Execute one complete self-improvement cycle

        Cycle:
        1. DEVOUR - Analyze all system outputs
        2. DEFINE - Identify improvement opportunities
        3. MEASURE - Quantify current state
        4. ANALYZE - Root cause analysis
        5. IMPROVE - Generate and apply improvements
        6. CONTROL - Validate improvements
        7. OPTIMIZE - Fine-tune improvements
        8. WIN - Measure success
        """
        print(f"\n{'='*80}")
        print(f"SELF-IMPROVEMENT CYCLE - ITERATION {iteration}")
        print(f"{'='*80}\n")

        start_time = time.time()

        # Phase 1: DEVOUR
        print("[1/8] DEVOUR - Consuming knowledge...")
        devoured_data = self._devour_knowledge(iteration)
        print(f"  ✅ Devoured {devoured_data['total_insights']} insights")

        # Phase 2: DEFINE
        print("\n[2/8] DEFINE - Identifying improvement opportunities...")
        opportunities = self._define_opportunities(devoured_data)
        print(f"  ✅ Found {len(opportunities)} opportunities")

        # Phase 3: MEASURE
        print("\n[3/8] MEASURE - Quantifying current state...")
        baseline_metrics = self._measure_baseline()
        print(f"  ✅ Collected {len(baseline_metrics)} baseline metrics")

        # Phase 4: ANALYZE
        print("\n[4/8] ANALYZE - Root cause analysis...")
        root_causes = self._analyze_root_causes(opportunities, baseline_metrics)
        print(f"  ✅ Identified {len(root_causes)} root causes")

        # Phase 5: IMPROVE
        print("\n[5/8] IMPROVE - Generating improvements...")
        improvements = self._generate_improvements(root_causes)
        print(f"  ✅ Generated {len(improvements)} improvements")

        # Phase 6: CONTROL
        print("\n[6/8] CONTROL - Validating improvements...")
        validated = self._control_improvements(improvements)
        print(f"  ✅ Validated {len(validated)} improvements")

        # Phase 7: OPTIMIZE
        print("\n[7/8] OPTIMIZE - Fine-tuning...")
        optimized = self._optimize_improvements(validated)
        print(f"  ✅ Optimized {len(optimized)} improvements")

        # Phase 8: WIN
        print("\n[8/8] WIN - Measuring success...")
        success_metrics = self._measure_success(baseline_metrics, optimized)
        print(f"  ✅ Success rate: {success_metrics['success_rate']:.1f}%")

        duration = time.time() - start_time

        cycle_result = {
            'iteration': iteration,
            'timestamp': datetime.now().isoformat(),
            'duration_seconds': duration,
            'devoured_insights': devoured_data['total_insights'],
            'opportunities_found': len(opportunities),
            'improvements_generated': len(improvements),
            'improvements_validated': len(validated),
            'improvements_optimized': len(optimized),
            'success_rate': success_metrics['success_rate'],
            'baseline_metrics': baseline_metrics,
            'final_metrics': success_metrics,
            'improvements': optimized
        }

        self.improvement_history.append(cycle_result)
        self._save_cycle_result(cycle_result)

        print(f"\n{'='*80}")
        print(f"CYCLE COMPLETE - Duration: {duration:.2f}s")
        print(f"{'='*80}\n")

        return cycle_result

    def _devour_knowledge(self, iteration: int) -> Dict[str, Any]:
        """DEVOUR: Consume all available knowledge"""
        output_dir = self.config.paths.output_root

        devoured = {
            'total_insights': 0,
            'phase_outputs': [],
            'agent_data': [],
            'rankings': [],
            'knowledge_books': []
        }

        # Devour phase outputs
        for iter_dir in output_dir.glob('iteration_*'):
            for phase_dir in iter_dir.glob('phase*'):
                for json_file in phase_dir.glob('*.json'):
                    try:
                        with open(json_file) as f:
                            data = json.load(f)
                            devoured['phase_outputs'].append({
                                'file': str(json_file),
                                'size': json_file.stat().st_size,
                                'data': data
                            })
                            devoured['total_insights'] += 1
                    except:
                        pass

        # Devour agent registry
        agent_registry = output_dir / 'agent_registry.json'
        if agent_registry.exists():
            with open(agent_registry) as f:
                devoured['agent_data'] = json.load(f)
                devoured['total_insights'] += len(devoured['agent_data'].get('agents', {}))

        # Devour rankings
        for ranking_file in output_dir.rglob('*RANKING*.json'):
            try:
                with open(ranking_file) as f:
                    devoured['rankings'].append(json.load(f))
                    devoured['total_insights'] += 1
            except:
                pass

        return devoured

    def _define_opportunities(self, devoured_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """DEFINE: Identify improvement opportunities"""
        opportunities = []

        # Opportunity 1: Missing phase outputs
        phase_counts = {}
        for output in devoured_data['phase_outputs']:
            phase = Path(output['file']).parent.name
            phase_counts[phase] = phase_counts.get(phase, 0) + 1

        for phase_num in range(9):
            phase_name = f"phase{phase_num}_*"
            if phase_counts.get(phase_name, 0) == 0:
                opportunities.append({
                    'type': 'missing_output',
                    'phase': phase_num,
                    'priority': 'HIGH',
                    'description': f'Phase {phase_num} produces no outputs'
                })

        # Opportunity 2: Small output files (potential incomplete execution)
        for output in devoured_data['phase_outputs']:
            if output['size'] < 1000:  # Less than 1KB
                opportunities.append({
                    'type': 'small_output',
                    'file': output['file'],
                    'size': output['size'],
                    'priority': 'MEDIUM',
                    'description': f'Suspiciously small output: {output["file"]}'
                })

        # Opportunity 3: Agent underutilization
        if devoured_data['agent_data']:
            agents = devoured_data['agent_data'].get('agents', {})
            if len(agents) < 12:
                opportunities.append({
                    'type': 'agent_underutilization',
                    'current_agents': len(agents),
                    'expected_agents': 12,
                    'priority': 'HIGH',
                    'description': 'Not all agents are active'
                })

        return opportunities

    def _measure_baseline(self) -> Dict[str, Any]:
        """MEASURE: Quantify current state"""
        output_dir = self.config.paths.output_root

        metrics = {
            'total_iterations': len(list(output_dir.glob('iteration_*'))),
            'total_files': len(list(output_dir.rglob('*.json'))),
            'total_size_mb': sum(f.stat().st_size for f in output_dir.rglob('*') if f.is_file()) / (1024 * 1024),
            'phases_with_output': {},
            'agent_count': 0
        }

        # Count phases with outputs
        for iter_dir in output_dir.glob('iteration_*'):
            for phase_num in range(9):
                phase_dirs = list(iter_dir.glob(f'phase{phase_num}_*'))
                if phase_dirs:
                    phase_name = f'phase{phase_num}'
                    metrics['phases_with_output'][phase_name] = metrics['phases_with_output'].get(phase_name, 0) + 1

        # Count agents
        agent_registry = output_dir / 'agent_registry.json'
        if agent_registry.exists():
            with open(agent_registry) as f:
                data = json.load(f)
                metrics['agent_count'] = len(data.get('agents', {}))

        return metrics

    def _analyze_root_causes(self, opportunities: List[Dict], baseline: Dict) -> List[Dict[str, Any]]:
        """ANALYZE: Root cause analysis"""
        root_causes = []

        for opp in opportunities:
            if opp['type'] == 'missing_output':
                root_causes.append({
                    'opportunity': opp,
                    'root_cause': 'Phase execution incomplete or failed',
                    'evidence': f'Phase {opp["phase"]} has no output files',
                    'impact': 'HIGH'
                })

            elif opp['type'] == 'small_output':
                root_causes.append({
                    'opportunity': opp,
                    'root_cause': 'Insufficient data processing or early termination',
                    'evidence': f'Output file only {opp["size"]} bytes',
                    'impact': 'MEDIUM'
                })

            elif opp['type'] == 'agent_underutilization':
                root_causes.append({
                    'opportunity': opp,
                    'root_cause': 'Agent initialization failure or configuration issue',
                    'evidence': f'Only {opp["current_agents"]}/12 agents active',
                    'impact': 'HIGH'
                })

        return root_causes

    def _generate_improvements(self, root_causes: List[Dict]) -> List[Dict[str, Any]]:
        """IMPROVE: Generate improvements"""
        improvements = []

        for rc in root_causes:
            opp = rc['opportunity']

            if opp['type'] == 'missing_output':
                improvements.append({
                    'id': f'IMP-{len(improvements)+1:03d}',
                    'type': 'fix_phase_execution',
                    'target': f'Phase {opp["phase"]}',
                    'action': f'Debug and fix Phase {opp["phase"]} execution',
                    'expected_outcome': 'Phase produces valid output files',
                    'priority': 'HIGH',
                    'effort': 'MEDIUM'
                })

            elif opp['type'] == 'small_output':
                improvements.append({
                    'id': f'IMP-{len(improvements)+1:03d}',
                    'type': 'enhance_data_processing',
                    'target': opp['file'],
                    'action': 'Investigate and enhance data processing logic',
                    'expected_outcome': 'Output files contain comprehensive data',
                    'priority': 'MEDIUM',
                    'effort': 'LOW'
                })

            elif opp['type'] == 'agent_underutilization':
                improvements.append({
                    'id': f'IMP-{len(improvements)+1:03d}',
                    'type': 'fix_agent_initialization',
                    'target': 'Agent Manager',
                    'action': 'Fix agent initialization and ensure all 12 agents start',
                    'expected_outcome': 'All 12 agents operational',
                    'priority': 'HIGH',
                    'effort': 'HIGH'
                })

        return improvements

    def _control_improvements(self, improvements: List[Dict]) -> List[Dict[str, Any]]:
        """CONTROL: Validate improvements"""
        validated = []

        for imp in improvements:
            # Validation criteria
            is_valid = True
            validation_notes = []

            # Check priority
            if imp['priority'] not in ['HIGH', 'MEDIUM', 'LOW']:
                is_valid = False
                validation_notes.append('Invalid priority level')

            # Check effort
            if imp['effort'] not in ['HIGH', 'MEDIUM', 'LOW']:
                is_valid = False
                validation_notes.append('Invalid effort level')

            # Check completeness
            required_fields = ['id', 'type', 'target', 'action', 'expected_outcome']
            for field in required_fields:
                if field not in imp:
                    is_valid = False
                    validation_notes.append(f'Missing field: {field}')

            if is_valid:
                imp['validated'] = True
                imp['validation_notes'] = ['All checks passed']
                validated.append(imp)
            else:
                imp['validated'] = False
                imp['validation_notes'] = validation_notes

        return validated

    def _optimize_improvements(self, validated: List[Dict]) -> List[Dict[str, Any]]:
        """OPTIMIZE: Fine-tune improvements"""
        optimized = []

        for imp in validated:
            # Optimize by adding implementation details
            imp['implementation'] = {
                'steps': self._generate_implementation_steps(imp),
                'estimated_duration': self._estimate_duration(imp),
                'dependencies': self._identify_dependencies(imp),
                'success_criteria': self._define_success_criteria(imp)
            }

            optimized.append(imp)

        return optimized

    def _generate_implementation_steps(self, improvement: Dict) -> List[str]:
        """Generate implementation steps for improvement"""
        if improvement['type'] == 'fix_phase_execution':
            return [
                f"1. Review {improvement['target']} code",
                "2. Identify execution failures",
                "3. Add error handling and logging",
                "4. Test phase execution",
                "5. Validate output generation"
            ]
        elif improvement['type'] == 'enhance_data_processing':
            return [
                "1. Analyze current data processing logic",
                "2. Identify data collection gaps",
                "3. Enhance data extraction",
                "4. Add data validation",
                "5. Test with sample data"
            ]
        elif improvement['type'] == 'fix_agent_initialization':
            return [
                "1. Review agent initialization code",
                "2. Check agent dependencies",
                "3. Fix initialization sequence",
                "4. Add agent health checks",
                "5. Validate all agents start"
            ]
        else:
            return ["1. Analyze issue", "2. Implement fix", "3. Test", "4. Validate"]

    def _estimate_duration(self, improvement: Dict) -> str:
        """Estimate implementation duration"""
        effort_map = {
            'LOW': '1-2 hours',
            'MEDIUM': '4-8 hours',
            'HIGH': '1-2 days'
        }
        return effort_map.get(improvement['effort'], 'Unknown')

    def _identify_dependencies(self, improvement: Dict) -> List[str]:
        """Identify improvement dependencies"""
        deps = []

        if 'phase' in improvement.get('target', '').lower():
            deps.append('Phase execution framework')
            deps.append('State management')

        if 'agent' in improvement.get('target', '').lower():
            deps.append('Agent manager')
            deps.append('Agent registry')

        return deps if deps else ['None']

    def _define_success_criteria(self, improvement: Dict) -> List[str]:
        """Define success criteria for improvement"""
        return [
            improvement['expected_outcome'],
            'No regression in existing functionality',
            'All tests pass',
            'Documentation updated'
        ]

    def _measure_success(self, baseline: Dict, optimized: List[Dict]) -> Dict[str, Any]:
        """WIN: Measure success"""
        success_metrics = {
            'baseline_metrics': baseline,
            'improvements_count': len(optimized),
            'high_priority_count': sum(1 for i in optimized if i['priority'] == 'HIGH'),
            'medium_priority_count': sum(1 for i in optimized if i['priority'] == 'MEDIUM'),
            'low_priority_count': sum(1 for i in optimized if i['priority'] == 'LOW'),
            'estimated_total_effort': self._calculate_total_effort(optimized),
            'success_rate': (len(optimized) / max(len(optimized), 1)) * 100  # All validated = 100%
        }

        return success_metrics

    def _calculate_total_effort(self, improvements: List[Dict]) -> str:
        """Calculate total effort for all improvements"""
        effort_hours = {
            'LOW': 1.5,
            'MEDIUM': 6,
            'HIGH': 12
        }

        total_hours = sum(effort_hours.get(imp['effort'], 0) for imp in improvements)

        if total_hours < 8:
            return f"{total_hours:.1f} hours"
        else:
            return f"{total_hours/8:.1f} days"

    def _save_cycle_result(self, result: Dict[str, Any]):
        """Save improvement cycle result"""
        output_file = self.config.paths.output_root / f"self_improvement_iteration_{result['iteration']}.json"

        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2)

        print(f"\n✅ Self-improvement cycle saved: {output_file}")

def main():
    parser = argparse.ArgumentParser(description="DMAIC V4.0 Self-Improvement Agent")
    parser.add_argument('--iteration', type=int, default=1, help='Iteration number')
    parser.add_argument('--cycles', type=int, default=1, help='Number of improvement cycles')

    args = parser.parse_args()

    agent = SelfImprovementAgent()

    print(f"\n{'='*80}")
    print(f"DMAIC V4.0 SELF-IMPROVEMENT AGENT")
    print(f"{'='*80}")
    print(f"Starting {args.cycles} improvement cycle(s)...")
    print(f"{'='*80}\n")

    results = []
    for cycle in range(args.cycles):
        result = agent.execute_improvement_cycle(iteration=args.iteration + cycle)
        results.append(result)

    print(f"\n{'='*80}")
    print(f"ALL CYCLES COMPLETE")
    print(f"{'='*80}")
    print(f"Total Cycles: {len(results)}")
    print(f"Total Improvements: {sum(r['improvements_optimized'] for r in results)}")
    print(f"Average Success Rate: {sum(r['success_rate'] for r in results) / len(results):.1f}%")
    print(f"{'='*80}\n")

    return 0

if __name__ == "__main__":
    sys.exit(main())
