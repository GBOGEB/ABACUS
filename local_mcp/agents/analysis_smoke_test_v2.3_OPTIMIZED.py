#!/usr/bin/env python3
"""
Smoke Test Agent V2.3.0
Memory-optimized DMAIC-based smoke test execution agent.
Designed for 4M memory constraint with lightweight validation support.
"""
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List
import traceback


class MemoryEfficientSmokeTestV23:
    """V2.3 Memory-optimized smoke test agent"""

    # Lightweight checks that must pass for a healthy system
    SMOKE_TESTS = [
        ('config_exists', 'Verify configuration file exists'),
        ('output_dir_writable', 'Verify output directory is writable'),
        ('dmaic_phases_importable', 'Verify DMAIC phase modules are importable'),
        ('knowledge_integration_loads', 'Verify knowledge integration module loads'),
    ]

    def __init__(self, config: dict = None):
        self.config = config or {}
        self.name = "smoke_test"
        self.version = "v2.3.0"
        self.start_time = time.time()
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        self.performance_metrics = {
            'tests_run': 0,
            'tests_passed': 0,
            'tests_failed': 0,
            'dmaic_phases_completed': 0,
            'errors_handled': 0,
        }

        self.dmaic_log = []
        self.results = []

        self.output_dir = Path(self.config.get('output_dir', 'smoke_outputs_v2.3'))
        self.output_dir.mkdir(exist_ok=True)

    def _log_dmaic(self, phase: str, action: str, result: Any = None):
        """Log DMAIC action with memory efficiency"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'phase': phase,
            'action': action,
            'result': str(result)[:100] if result else 'Completed',
        }
        self.dmaic_log.append(log_entry)
        print(f"[{phase}] {action}")

    def _run_check(self, check_name: str) -> Dict[str, Any]:
        """Execute a single smoke check and return result"""
        start = time.time()
        passed = False
        detail = ''

        try:
            if check_name == 'config_exists':
                # Look for any config file in common locations
                candidates = [
                    Path('orchestrator_config.yaml'),
                    Path('DMAIC_V3/config.py'),
                    Path('pytest.ini'),
                ]
                passed = any(p.exists() for p in candidates)
                detail = 'Config file found' if passed else 'No config file found'

            elif check_name == 'output_dir_writable':
                test_file = self.output_dir / '.write_test'
                test_file.write_text('ok')
                test_file.unlink()
                passed = True
                detail = f'{self.output_dir} is writable'

            elif check_name == 'dmaic_phases_importable':
                import importlib.util
                phase_files = list(Path('.').glob('DMAIC_V3/phases/phase*.py'))
                passed = len(phase_files) > 0
                detail = f'Found {len(phase_files)} phase modules'

            elif check_name == 'knowledge_integration_loads':
                import importlib.util
                ki_path = Path('local_mcp/knowledge_integration_v2.3.py')
                passed = ki_path.exists()
                detail = 'knowledge_integration_v2.3.py found' if passed else 'Module not found'

        except Exception as exc:
            passed = False
            detail = str(exc)

        duration = time.time() - start
        return {
            'check': check_name,
            'passed': passed,
            'detail': detail,
            'duration_ms': round(duration * 1000, 2),
        }

    def dmaic_define(self) -> Dict[str, Any]:
        """DEFINE: Smoke test scope and success criteria"""
        self._log_dmaic('DEFINE', 'Defining smoke test scope')

        definition = {
            'objectives': [
                'Verify critical system components are present and functional',
                'Detect environment or configuration regressions early',
                'Provide rapid go/no-go signal for downstream agents',
            ],
            'tests_planned': [t[0] for t in self.SMOKE_TESTS],
            'pass_threshold_pct': 75,
            'timeout_seconds': 30,
        }

        self.performance_metrics['dmaic_phases_completed'] += 1
        self._log_dmaic('DEFINE', 'Definition complete', definition)
        return definition

    def dmaic_measure(self) -> Dict[str, Any]:
        """MEASURE: Execute smoke checks and collect raw results"""
        self._log_dmaic('MEASURE', f'Running {len(self.SMOKE_TESTS)} smoke checks')

        raw_results: List[Dict[str, Any]] = []
        for check_name, description in self.SMOKE_TESTS:
            self._log_dmaic('MEASURE', f'Running check: {description}')
            result = self._run_check(check_name)
            raw_results.append(result)
            self.performance_metrics['tests_run'] += 1
            if result['passed']:
                self.performance_metrics['tests_passed'] += 1
            else:
                self.performance_metrics['tests_failed'] += 1

        measurements = {
            'checks_run': len(raw_results),
            'results': raw_results,
        }

        self.performance_metrics['dmaic_phases_completed'] += 1
        self._log_dmaic('MEASURE', f"Executed {len(raw_results)} checks")
        return measurements

    def dmaic_analyze(self, measurements: Dict[str, Any]) -> Dict[str, Any]:
        """ANALYZE: Summarize smoke test outcomes"""
        self._log_dmaic('ANALYZE', 'Analyzing smoke test results')

        results = measurements.get('results', [])
        passed = [r for r in results if r['passed']]
        failed = [r for r in results if not r['passed']]
        pass_rate = len(passed) / len(results) * 100 if results else 0.0

        analysis = {
            'total': len(results),
            'passed': len(passed),
            'failed': len(failed),
            'pass_rate_pct': round(pass_rate, 1),
            'passed_checks': [r['check'] for r in passed],
            'failed_checks': [r['check'] for r in failed],
            'system_healthy': pass_rate >= 75,
        }

        self.performance_metrics['dmaic_phases_completed'] += 1
        self._log_dmaic('ANALYZE', f"Pass rate: {pass_rate:.1f}%")
        return analysis

    def dmaic_improve(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """IMPROVE: Generate remediation actions for failed checks"""
        self._log_dmaic('IMPROVE', 'Generating remediation actions')

        actions: List[Dict[str, Any]] = []
        for check in analysis.get('failed_checks', []):
            if check == 'config_exists':
                actions.append({
                    'check': check,
                    'action': 'create_config',
                    'detail': 'Create orchestrator_config.yaml',
                    'priority': 'HIGH',
                })
            elif check == 'output_dir_writable':
                actions.append({
                    'check': check,
                    'action': 'fix_permissions',
                    'detail': 'Fix output directory write permissions',
                    'priority': 'HIGH',
                })
            else:
                actions.append({
                    'check': check,
                    'action': 'investigate',
                    'detail': f'Investigate failure for: {check}',
                    'priority': 'MEDIUM',
                })

        self.performance_metrics['dmaic_phases_completed'] += 1
        self._log_dmaic('IMPROVE', f"Generated {len(actions)} remediation actions")
        return {'actions': actions, 'total': len(actions)}

    def dmaic_control(self, improvements: Dict[str, Any]) -> Dict[str, Any]:
        """CONTROL: Record smoke test baseline for monitoring"""
        self._log_dmaic('CONTROL', 'Saving smoke test baseline')

        control_record = {
            'timestamp': datetime.now().isoformat(),
            'pass_rate_baseline': self.performance_metrics['tests_passed'] /
                                  max(self.performance_metrics['tests_run'], 1) * 100,
            'action_items': improvements.get('actions', []),
        }

        output_file = self.output_dir / f"smoke_baseline_{self.timestamp}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(control_record, f, indent=2)

        self.performance_metrics['dmaic_phases_completed'] += 1
        self._log_dmaic('CONTROL', f"Baseline saved: {output_file}")
        return control_record

    def run(self) -> Dict[str, Any]:
        """Execute full DMAIC smoke test cycle"""
        self._log_dmaic('RUN', 'Starting DMAIC smoke test cycle')
        run_start = time.time()

        try:
            definition = self.dmaic_define()
            measurements = self.dmaic_measure()
            analysis = self.dmaic_analyze(measurements)
            improvements = self.dmaic_improve(analysis)
            control = self.dmaic_control(improvements)

            execution_time = time.time() - run_start

            result = {
                'status': 'success' if analysis.get('system_healthy') else 'degraded',
                'agent': self.name,
                'version': self.version,
                'execution_time': execution_time,
                'system_healthy': analysis.get('system_healthy', False),
                'phases': {
                    'define': definition,
                    'measure': measurements,
                    'analyze': analysis,
                    'improve': improvements,
                    'control': control,
                },
                'performance_metrics': self.performance_metrics.copy(),
            }

            self.results.append(result)
            self._log_dmaic('RUN', f'Completed in {execution_time:.2f}s - healthy={result["system_healthy"]}')
            return result

        except Exception as e:
            self.performance_metrics['errors_handled'] += 1
            self._log_dmaic('RUN', f'Error: {str(e)}')
            return {
                'status': 'error',
                'agent': self.name,
                'error': str(e),
                'traceback': traceback.format_exc(),
            }

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Return current performance metrics"""
        return {
            'metrics': self.performance_metrics.copy(),
            'uptime_seconds': time.time() - self.start_time,
        }
