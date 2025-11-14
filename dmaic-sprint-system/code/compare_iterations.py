#!/usr/bin/env python3
"""
DMAIC Iteration Comparison Tool
Compares metrics and results between different DMAIC iterations
"""

import json
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

class IterationComparator:
    def __init__(self, output_dir: Path = None):
        self.output_dir = output_dir or Path.cwd() / 'DMAIC_V3_OUTPUT' / 'sprints'
    
    def load_iteration_data(self, iteration: int) -> Dict[str, Any]:
        """Load all phase data for a specific iteration"""
        iter_dir = self.output_dir / f"iteration_{iteration}"
        
        if not iter_dir.exists():
            return None
        
        data = {
            'iteration': iteration,
            'phases': {}
        }
        
        # Load each phase output
        phase_files = {
            'phase0_setup': iter_dir / 'phase0_setup.json',
            'phase1_define': iter_dir / 'phase1_define' / 'phase1_define.json',
            'phase2_measure': iter_dir / 'phase2_measure' / 'phase2_measure.json',
            'phase3_analyze': iter_dir / 'phase3_analysis.json',
            'phase4_improve': iter_dir / 'phase4_improvements.json',
            'phase5_control': iter_dir / 'phase5_control' / 'phase5_control.json'
        }
        
        for phase_name, phase_file in phase_files.items():
            if phase_file.exists():
                try:
                    with open(phase_file, 'r', encoding='utf-8') as f:
                        data['phases'][phase_name] = json.load(f)
                except Exception as e:
                    print(f"[!] Error loading {phase_file}: {e}")
                    data['phases'][phase_name] = None
            else:
                data['phases'][phase_name] = None
        
        return data
    
    def extract_key_metrics(self, iteration_data: Dict) -> Dict[str, Any]:
        """Extract key metrics from iteration data"""
        if not iteration_data:
            return {}
        
        metrics = {
            'iteration': iteration_data['iteration'],
            'phases_completed': len([p for p in iteration_data['phases'].values() if p is not None])
        }
        
        # Phase 1 metrics
        phase1 = iteration_data['phases'].get('phase1_define')
        if phase1:
            metrics['files_scanned'] = phase1.get('total_files', 0)
            metrics['documentation_files'] = phase1.get('documentation_files', 0)
            metrics['code_files'] = phase1.get('code_files', 0)
            metrics['scan_duration'] = phase1.get('duration', 0)
        
        # Phase 2 metrics
        phase2 = iteration_data['phases'].get('phase2_measure')
        if phase2:
            metrics['metrics_collected'] = phase2.get('total_metrics', 0)
            metrics['measure_duration'] = phase2.get('duration', 0)
        
        # Phase 3 metrics
        phase3 = iteration_data['phases'].get('phase3_analyze')
        if phase3:
            summary = phase3.get('summary', {})
            metrics['critical_issues'] = summary.get('critical_issues', 0)
            metrics['high_issues'] = summary.get('high_issues', 0)
            metrics['medium_issues'] = summary.get('medium_issues', 0)
            metrics['total_issues'] = (
                metrics.get('critical_issues', 0) + 
                metrics.get('high_issues', 0) + 
                metrics.get('medium_issues', 0)
            )
        
        # Phase 4 metrics
        phase4 = iteration_data['phases'].get('phase4_improve')
        if phase4:
            metrics['improvements_planned'] = phase4.get('total_improvements', 0)
            metrics['improvements_applied'] = phase4.get('improvements_applied', 0)
        
        # Phase 5 metrics
        phase5 = iteration_data['phases'].get('phase5_control')
        if phase5:
            metrics['quality_gates'] = phase5.get('quality_gates_count', 0)
            metrics['validation_checkpoints'] = phase5.get('validation_checkpoints', 0)
        
        return metrics
    
    def compare_iterations(self, iter1: int, iter2: int) -> Dict[str, Any]:
        """Compare two iterations and generate comparison report"""
        print(f"\n{'='*80}")
        print(f"COMPARING ITERATION {iter1} vs ITERATION {iter2}")
        print(f"{'='*80}\n")
        
        data1 = self.load_iteration_data(iter1)
        data2 = self.load_iteration_data(iter2)
        
        if not data1:
            print(f"[!] Iteration {iter1} data not found")
            return None
        
        if not data2:
            print(f"[!] Iteration {iter2} data not found")
            return None
        
        metrics1 = self.extract_key_metrics(data1)
        metrics2 = self.extract_key_metrics(data2)
        
        comparison = {
            'comparison_date': datetime.now().isoformat(),
            'iteration_1': iter1,
            'iteration_2': iter2,
            'metrics_1': metrics1,
            'metrics_2': metrics2,
            'improvements': {}
        }
        
        # Calculate improvements
        for key in metrics1:
            if key == 'iteration':
                continue
            
            val1 = metrics1.get(key, 0)
            val2 = metrics2.get(key, 0)
            
            if isinstance(val1, (int, float)) and isinstance(val2, (int, float)):
                change = val2 - val1
                if val1 > 0:
                    pct_change = (change / val1) * 100
                else:
                    pct_change = 0 if change == 0 else float('inf')
                
                comparison['improvements'][key] = {
                    'iteration_1': val1,
                    'iteration_2': val2,
                    'change': change,
                    'percent_change': pct_change
                }
        
        return comparison
    
    def print_comparison(self, comparison: Dict):
        """Print comparison report in a readable format"""
        if not comparison:
            return
        
        print(f"\n{'='*80}")
        print(f"ITERATION COMPARISON REPORT")
        print(f"{'='*80}\n")
        
        print(f"Iteration {comparison['iteration_1']} vs Iteration {comparison['iteration_2']}")
        print(f"Generated: {comparison['comparison_date']}\n")
        
        print(f"{'Metric':<35s} {'Iter 1':>12s} {'Iter 2':>12s} {'Change':>12s} {'%':>10s}")
        print(f"{'-'*80}")
        
        for metric, data in comparison['improvements'].items():
            val1 = data['iteration_1']
            val2 = data['iteration_2']
            change = data['change']
            pct = data['percent_change']
            
            # Format values
            if isinstance(val1, float):
                val1_str = f"{val1:.2f}"
                val2_str = f"{val2:.2f}"
                change_str = f"{change:+.2f}"
            else:
                val1_str = f"{val1}"
                val2_str = f"{val2}"
                change_str = f"{change:+d}"
            
            if pct == float('inf'):
                pct_str = "N/A"
            else:
                pct_str = f"{pct:+.1f}%"
            
            # Color coding (for terminal)
            if change > 0 and 'issue' not in metric.lower():
                indicator = "↑"
            elif change < 0 and 'issue' in metric.lower():
                indicator = "↓"
            elif change < 0:
                indicator = "↓"
            else:
                indicator = "="
            
            print(f"{metric:<35s} {val1_str:>12s} {val2_str:>12s} {change_str:>12s} {pct_str:>10s} {indicator}")
        
        print(f"\n{'='*80}\n")
    
    def save_comparison(self, comparison: Dict, output_file: Path = None):
        """Save comparison report to JSON file"""
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = self.output_dir / f"iteration_comparison_{timestamp}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(comparison, f, indent=2)
        
        print(f"[*] Comparison report saved: {output_file}")
        return output_file

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Compare DMAIC iterations')
    parser.add_argument('--iter1', type=int, default=1, help='First iteration number')
    parser.add_argument('--iter2', type=int, default=2, help='Second iteration number')
    parser.add_argument('--output', type=str, help='Output file path')
    
    args = parser.parse_args()
    
    comparator = IterationComparator()
    comparison = comparator.compare_iterations(args.iter1, args.iter2)
    
    if comparison:
        comparator.print_comparison(comparison)
        
        output_file = Path(args.output) if args.output else None
        comparator.save_comparison(comparison, output_file)
        
        return 0
    else:
        print("[!] Comparison failed - check that both iterations exist")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())
