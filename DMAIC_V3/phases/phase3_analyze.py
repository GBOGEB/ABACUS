"""
DMAIC V3.3 - Phase 3: Analyze
Created: 2024-11-12

Phase 3: ANALYZE - Root cause analysis and pattern detection
- Analyze metrics from Phase 2
- Identify bottlenecks and issues
- Detect code patterns and anti-patterns
- Generate root cause analysis report
"""

__version__ = "3.3.0"

import os
import json
from pathlib import Path
from typing import Dict, List, Tuple, Any
from datetime import datetime
from collections import defaultdict, Counter

from ..core.state import StateManager
from ..core.utils import ensure_directory, safe_write_json
from ..config import DMAICConfig


class Phase3Analyze:
    """
    Phase 3: Analyze - Root cause analysis

    Analyzes metrics from Phase 2 to identify issues, bottlenecks,
    and opportunities for improvement.
    """

    def __init__(self, config: DMAICConfig, state_manager: StateManager):
        """
        Initialize Phase 3: Analyze

        Args:
            config: DMAICConfig instance
            state_manager: StateManager instance
        """
        self.config = config
        self.state_manager = state_manager
        self.workspace_root = config.paths.workspace_root

        self.complexity_thresholds = {
            'low': 100,
            'medium': 300,
            'high': 500,
            'critical': 1000
        }

        self.loc_thresholds = {
            'small': 100,
            'medium': 300,
            'large': 500,
            'very_large': 1000
        }

    def analyze_complexity_distribution(self, metrics: Dict) -> Dict:
        """Analyze complexity distribution across files"""
        complexity_dist = {
            'low': 0,
            'medium': 0,
            'high': 0,
            'critical': 0
        }

        for file_path, file_metrics in metrics.items():
            if not file_metrics.get('success'):
                continue

            complexity = file_metrics.get('metrics', {}).get('complexity_score', 0)

            if complexity < self.complexity_thresholds['low']:
                complexity_dist['low'] += 1
            elif complexity < self.complexity_thresholds['medium']:
                complexity_dist['medium'] += 1
            elif complexity < self.complexity_thresholds['high']:
                complexity_dist['high'] += 1
            else:
                complexity_dist['critical'] += 1

        return complexity_dist

    def identify_high_complexity_files(self, metrics: Dict, top_n: int = 20) -> List[Dict]:
        """Identify files with highest complexity"""
        complexity_files = []

        for file_path, file_metrics in metrics.items():
            if not file_metrics.get('success'):
                continue

            complexity = file_metrics.get('metrics', {}).get('complexity_score', 0)
            loc = file_metrics.get('metrics', {}).get('lines_of_code', 0)

            functions_val = file_metrics.get('metrics', {}).get('functions', 0)
            classes_val = file_metrics.get('metrics', {}).get('classes', 0)

            complexity_files.append({
                'file': file_path,
                'complexity': complexity,
                'loc': loc,
                'functions': functions_val if isinstance(functions_val, int) else len(functions_val),
                'classes': classes_val if isinstance(classes_val, int) else len(classes_val)
            })

        complexity_files.sort(key=lambda x: x['complexity'], reverse=True)
        return complexity_files[:top_n]

    def analyze_file_size_distribution(self, metrics: Dict) -> Dict:
        """Analyze file size distribution"""
        size_dist = {
            'small': 0,
            'medium': 0,
            'large': 0,
            'very_large': 0
        }

        for file_path, file_metrics in metrics.items():
            if not file_metrics.get('success'):
                continue

            loc = file_metrics.get('metrics', {}).get('lines_of_code', 0)

            if loc < self.loc_thresholds['small']:
                size_dist['small'] += 1
            elif loc < self.loc_thresholds['medium']:
                size_dist['medium'] += 1
            elif loc < self.loc_thresholds['large']:
                size_dist['large'] += 1
            else:
                size_dist['very_large'] += 1

        return size_dist

    def detect_code_patterns(self, metrics: Dict) -> Dict:
        """Detect common code patterns and anti-patterns"""
        patterns = {
            'god_classes': [],
            'long_methods': [],
            'duplicate_imports': [],
            'low_documentation': []
        }

        for file_path, file_metrics in metrics.items():
            if not file_metrics.get('success'):
                continue

            m = file_metrics.get('metrics', {})
            classes = m.get('classes', [])
            functions = m.get('functions', [])
            loc = m.get('lines_of_code', 0)
            comment_lines = m.get('comment_lines', 0)

            # Handle both integer counts and list formats
            if isinstance(classes, int):
                classes = []
            if isinstance(functions, int):
                functions = []

            for cls in classes:
                if loc > 500:
                    patterns['god_classes'].append({
                        'file': file_path,
                        'class': cls.get('name', 'Unknown') if isinstance(cls, dict) else str(cls),
                        'loc': loc
                    })

            for func in functions:
                func_args = func.get('args', 0) if isinstance(func, dict) else 0
                if func_args > 5:
                    patterns['long_methods'].append({
                        'file': file_path,
                        'function': func.get('name', 'Unknown') if isinstance(func, dict) else str(func),
                        'args': func_args
                    })

            if loc > 50 and comment_lines / max(loc, 1) < 0.1:
                patterns['low_documentation'].append({
                    'file': file_path,
                    'loc': loc,
                    'comment_ratio': comment_lines / max(loc, 1)
                })

        return patterns

    def generate_root_causes(self, analysis: Dict) -> List[Dict]:
        """Generate root cause analysis"""
        root_causes = []

        if analysis['complexity_dist']['critical'] > 0:
            root_causes.append({
                'category': 'High Complexity',
                'severity': 'critical',
                'count': analysis['complexity_dist']['critical'],
                'description': f"{analysis['complexity_dist']['critical']} files have critical complexity",
                'recommendation': 'Refactor complex files into smaller modules'
            })

        if analysis['complexity_dist']['high'] > 10:
            root_causes.append({
                'category': 'High Complexity',
                'severity': 'high',
                'count': analysis['complexity_dist']['high'],
                'description': f"{analysis['complexity_dist']['high']} files have high complexity",
                'recommendation': 'Review and simplify high-complexity files'
            })

        if len(analysis['patterns']['god_classes']) > 0:
            root_causes.append({
                'category': 'God Classes',
                'severity': 'high',
                'count': len(analysis['patterns']['god_classes']),
                'description': f"{len(analysis['patterns']['god_classes'])} god classes detected",
                'recommendation': 'Split large classes into smaller, focused classes'
            })

        if len(analysis['patterns']['low_documentation']) > 20:
            root_causes.append({
                'category': 'Low Documentation',
                'severity': 'medium',
                'count': len(analysis['patterns']['low_documentation']),
                'description': f"{len(analysis['patterns']['low_documentation'])} files have low documentation",
                'recommendation': 'Add docstrings and comments to improve maintainability'
            })

        return root_causes

    def execute(self, iteration: int) -> Tuple[bool, Dict[str, Any]]:
        """
        Execute Phase 3: Analyze

        Args:
            iteration: Current iteration number

        Returns:
            Tuple of (success: bool, result: Dict)
        """
        result = self.run(iteration)
        success = 'error' not in result
        return success, result

    def run(self, iteration: int) -> Dict[str, Any]:
        """
        Execute Phase 3: Analyze

        Args:
            iteration: Current iteration number

        Returns:
            Dictionary with analysis results
        """
        print(f"\n{'='*60}")
        print(f"Phase 3: ANALYZE - Iteration {iteration}")
        print(f"{'='*60}\n")

        phase2_output = self.config.paths.output_root / f"iteration_{iteration}" / "phase2_metrics.json"

        if not phase2_output.exists():
            return {
                'phase': 'ANALYZE',
                'iteration': iteration,
                'timestamp': datetime.now().isoformat(),
                'version': __version__,
                'error': f"Phase 2 output not found: {phase2_output}",
                'input_source': str(phase2_output),
                'summary': {},
                'analysis': {},
                'complexity_distribution': {},
                'high_complexity_files': [],
                'size_distribution': {},
                'patterns': {},
                'root_causes': []
            }

        with open(phase2_output, 'r') as f:
            phase2_data = json.load(f)

        # Support both old and new Phase 2 formats
        metrics = phase2_data.get('file_metrics', {})
        if not metrics and 'measurements' in phase2_data:
            # Convert old format: build file_metrics from measurements
            metrics = {}
            for measurement in phase2_data['measurements']:
                file_path = measurement.get('file_path')
                if file_path and 'analysis' in measurement:
                    metrics[file_path] = measurement['analysis']

        print(f"[*] Analyzing {len(metrics)} files...")

        complexity_dist = self.analyze_complexity_distribution(metrics)
        high_complexity_files = self.identify_high_complexity_files(metrics)
        size_dist = self.analyze_file_size_distribution(metrics)
        patterns = self.detect_code_patterns(metrics)
        root_causes = self.generate_root_causes({
            'complexity_dist': complexity_dist,
            'size_dist': size_dist,
            'patterns': patterns
        })

        analysis_result = {
            'phase': 'ANALYZE',
            'iteration': iteration,
            'timestamp': datetime.now().isoformat(),
            'version': __version__,
            'input_source': str(phase2_output),
            'summary': {
                'total_files_analyzed': len(metrics),
                'critical_issues': len([rc for rc in root_causes if rc['severity'] == 'critical']),
                'high_issues': len([rc for rc in root_causes if rc['severity'] == 'high']),
                'medium_issues': len([rc for rc in root_causes if rc['severity'] == 'medium'])
            },
            'analysis': {
                'complexity_distribution': complexity_dist,
                'high_complexity_files': high_complexity_files,
                'size_distribution': size_dist,
                'patterns': patterns,
                'root_causes': root_causes
            },
            'complexity_distribution': complexity_dist,
            'high_complexity_files': high_complexity_files,
            'size_distribution': size_dist,
            'patterns': patterns,
            'root_causes': root_causes
        }

        output_dir = self.config.paths.output_root / f"iteration_{iteration}"
        ensure_directory(output_dir)
        output_file = output_dir / "phase3_analysis.json"

        safe_write_json(analysis_result, output_file)
        
        # Add output_file to result
        analysis_result['output_file'] = str(output_file)

        print(f"\n[*] Analysis Summary:")
        print(f"   Total files: {len(metrics)}")
        print(f"   Critical issues: {analysis_result['summary']['critical_issues']}")
        print(f"   High issues: {analysis_result['summary']['high_issues']}")
        print(f"   Medium issues: {analysis_result['summary']['medium_issues']}")
        print(f"\n[*] Output: {output_file}")

        return analysis_result


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))

    from DMAIC_V3.config import DMAICConfig
    from DMAIC_V3.core.state import StateManager

    config = DMAICConfig()
    state_manager = StateManager(config)
    phase3 = Phase3Analyze(config, state_manager)

    iteration = int(sys.argv[sys.argv.index('--iteration') + 1]) if '--iteration' in sys.argv else 1
    result = phase3.run(iteration)

    if not result['success']:
        print(f"[ERROR] Error: {result.get('error')}")
        sys.exit(1)
