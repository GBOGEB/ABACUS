import sys
import json
import time
import hashlib
import subprocess
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field

from ..config import DMAICConfig
from .state import StateManager

# HandoverBridge is optional - only import if src/dmaic exists
try:
    from .handover_bridge import HandoverBridge
except ImportError:
    HandoverBridge = None


@dataclass
class TestExecutionResult:
    test_name: str
    returncode: int
    stdout: str
    stderr: str
    success: bool
    duration_seconds: float
    artifacts_found: List[str] = field(default_factory=list)
    artifacts_expected: List[str] = field(default_factory=list)
    artifacts_match: bool = False
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class DeploymentMetrics:
    version: str
    timestamp: str
    tests_total: int
    tests_passed: int
    tests_failed: int
    execution_time_seconds: float
    runtime_errors: List[Dict[str, Any]] = field(default_factory=list)
    static_analysis_passed: bool = True
    deployment_ready: bool = False


class MCPControlPoint:
    def __init__(self, mcp_dir: Path):
        self.mcp_dir = Path(mcp_dir)
        self.mcp_dir.mkdir(exist_ok=True)
        self.log_file = self.mcp_dir / 'monitor.log'
        
    def log_point(self, point_name: str, status: str = 'enter', metadata: Dict = None):
        log_entry = {
            'timestamp': time.time(),
            'iso_timestamp': datetime.now().isoformat(),
            'point': point_name,
            'status': status,
            'metadata': metadata or {}
        }
        with open(self.log_file, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')


class TestSystemBridge:
    def __init__(self, config: DMAICConfig, state_manager: StateManager, 
                 handover_bridge: Optional['HandoverBridge'] = None):
        self.config = config
        self.state_manager = state_manager
        self.handover_bridge = handover_bridge
        
        self.workspace_root = Path(config.paths.workspace_root)
        self.output_root = Path(config.paths.output_root)
        
        self.mcp = MCPControlPoint(self.workspace_root / '.mcp')
        
        self.test_results: Dict[str, TestExecutionResult] = {}
        self.deployment_metrics: Optional[DeploymentMetrics] = None
        
        self.version_file = self.workspace_root / 'DMAIC_V3' / 'VERSION'
        self.actions_file = self.workspace_root / 'actions.json'
        
        self.mcp.log_point('test_system_bridge_initialized', 'complete')
    
    def get_current_version(self) -> str:
        if self.version_file.exists():
            return self.version_file.read_text().strip()
        return "0.0.0"
    
    def update_version(self, new_version: str):
        self.version_file.write_text(new_version + '\n')
        self.mcp.log_point('version_updated', 'complete', {'version': new_version})
    
    def log_action(self, action_type: str, description: str, metadata: Dict = None):
        actions = []
        if self.actions_file.exists():
            try:
                content = self.actions_file.read_text()
                if content.strip():
                    parsed = json.loads(content)
                    if isinstance(parsed, list):
                        actions = parsed
                    else:
                        # If the file contains a JSON object or other type, reset to empty list
                        actions = []
            except Exception:
                # On any parsing/read error, fallback to empty list
                actions = []

        action_entry = {
            'timestamp': datetime.now().isoformat(),
            'type': action_type,
            'description': description,
            'metadata': metadata or {}
        }
        actions.append(action_entry)

        self.actions_file.write_text(json.dumps(actions, indent=2))
        self.mcp.log_point('action_logged', 'complete', {'action_type': action_type})
    
    def setup_test_environment(self, sut_path: Path) -> Path:
        self.mcp.log_point('setup_test_environment', 'enter', {'sut_path': str(sut_path)})
        
        test_env = Path(tempfile.mkdtemp(prefix='dmaic_test_'))
        
        if sut_path.is_dir():
            shutil.copytree(sut_path, test_env / 'sut', dirs_exist_ok=True)
        else:
            shutil.copy2(sut_path, test_env / 'sut')
        
        self.mcp.log_point('setup_test_environment', 'complete', {'test_env': str(test_env)})
        return test_env
    
    def run_test(self, test_name: str, command: List[str], 
                 expected_artifacts: List[str] = None,
                 cwd: Path = None, timeout: int = 300) -> TestExecutionResult:
        self.mcp.log_point(f'run_test_{test_name}', 'enter', {'command': ' '.join(command)})
        
        start_time = time.time()
        
        try:
            result = subprocess.run(
                command,
                cwd=cwd or self.workspace_root,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            duration = time.time() - start_time
            
            test_result = TestExecutionResult(
                test_name=test_name,
                returncode=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                success=result.returncode == 0,
                duration_seconds=duration
            )
            
            if expected_artifacts and cwd:
                artifacts_found = []
                for artifact in expected_artifacts:
                    if (cwd / artifact).exists():
                        artifacts_found.append(artifact)
                test_result.artifacts_found = artifacts_found
                test_result.artifacts_expected = expected_artifacts
                test_result.artifacts_match = set(artifacts_found) == set(expected_artifacts)
            
            self.test_results[test_name] = test_result
            
            self.mcp.log_point(f'run_test_{test_name}', 'complete', {
                'success': test_result.success,
                'duration': duration
            })
            
            return test_result
            
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            test_result = TestExecutionResult(
                test_name=test_name,
                returncode=-1,
                stdout='',
                stderr='Test timed out',
                success=False,
                duration_seconds=duration
            )
            self.test_results[test_name] = test_result
            
            self.mcp.log_point(f'run_test_{test_name}', 'timeout', {'duration': duration})
            
            return test_result
    
    def run_pytest_suite(self, test_path: str = None, markers: str = None) -> TestExecutionResult:
        self.mcp.log_point('run_pytest_suite', 'enter')
        
        command = [sys.executable, '-m', 'pytest']
        
        if test_path:
            command.append(test_path)
        
        if markers:
            command.extend(['-m', markers])
        
        command.extend(['-v', '--tb=short', '--maxfail=5'])
        
        return self.run_test('pytest_suite', command)
    
    def run_static_analysis(self) -> Dict[str, Any]:
        self.mcp.log_point('run_static_analysis', 'enter')
        
        results = {
            'flake8': None,
            'mypy': None,
            'pylint': None
        }
        
        try:
            flake8_result = subprocess.run(
                [sys.executable, '-m', 'flake8', 'DMAIC_V3', '--count', '--statistics'],
                cwd=self.workspace_root,
                capture_output=True,
                text=True,
                timeout=120
            )
            results['flake8'] = {
                'returncode': flake8_result.returncode,
                'output': flake8_result.stdout + flake8_result.stderr
            }
        except Exception as e:
            results['flake8'] = {'error': str(e)}
        
        self.mcp.log_point('run_static_analysis', 'complete', results)
        return results
    
    def detect_runtime_errors(self) -> List[Dict[str, Any]]:
        self.mcp.log_point('detect_runtime_errors', 'enter')
        
        runtime_errors = []
        
        for test_name, result in self.test_results.items():
            if not result.success:
                error_info = {
                    'test_name': test_name,
                    'returncode': result.returncode,
                    'stderr': result.stderr,
                    'timestamp': result.timestamp
                }
                
                if 'Traceback' in result.stderr or 'Error' in result.stderr:
                    runtime_errors.append(error_info)
        
        self.mcp.log_point('detect_runtime_errors', 'complete', {
            'errors_found': len(runtime_errors)
        })
        
        return runtime_errors
    
    def generate_deployment_metrics(self, skip_static: bool = False) -> DeploymentMetrics:
        self.mcp.log_point('generate_deployment_metrics', 'enter')
        
        version = self.get_current_version()
        
        tests_total = len(self.test_results)
        tests_passed = sum(1 for r in self.test_results.values() if r.success)
        tests_failed = tests_total - tests_passed
        
        total_time = sum(r.duration_seconds for r in self.test_results.values())
        
        runtime_errors = self.detect_runtime_errors()
        
        # Run static analysis unless skipped
        static_passed = True  # Default to True if skipped
        if not skip_static:
            static_analysis = self.run_static_analysis()
            static_passed = all(
                r.get('returncode', 1) == 0 
                for r in static_analysis.values() 
                if r and 'returncode' in r
            )
        
        deployment_ready = (
            tests_passed == tests_total and
            len(runtime_errors) == 0 and
            static_passed
        )
        
        metrics = DeploymentMetrics(
            version=version,
            timestamp=datetime.now().isoformat(),
            tests_total=tests_total,
            tests_passed=tests_passed,
            tests_failed=tests_failed,
            execution_time_seconds=total_time,
            runtime_errors=runtime_errors,
            static_analysis_passed=static_passed,
            deployment_ready=deployment_ready
        )
        
        self.deployment_metrics = metrics
        
        self.mcp.log_point('generate_deployment_metrics', 'complete', {
            'deployment_ready': deployment_ready
        })
        
        return metrics
    
    def save_deployment_report(self, output_path: Path = None):
        if not self.deployment_metrics:
            self.generate_deployment_metrics()
        
        if output_path is None:
            output_path = self.output_root / 'deployment_report.json'
        
        report = {
            'deployment_metrics': {
                'version': self.deployment_metrics.version,
                'timestamp': self.deployment_metrics.timestamp,
                'tests_total': self.deployment_metrics.tests_total,
                'tests_passed': self.deployment_metrics.tests_passed,
                'tests_failed': self.deployment_metrics.tests_failed,
                'execution_time_seconds': self.deployment_metrics.execution_time_seconds,
                'runtime_errors': self.deployment_metrics.runtime_errors,
                'static_analysis_passed': self.deployment_metrics.static_analysis_passed,
                'deployment_ready': self.deployment_metrics.deployment_ready
            },
            'test_results': {
                name: {
                    'test_name': result.test_name,
                    'success': result.success,
                    'returncode': result.returncode,
                    'duration_seconds': result.duration_seconds,
                    'timestamp': result.timestamp,
                    'artifacts_match': result.artifacts_match
                }
                for name, result in self.test_results.items()
            }
        }
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2))
        
        self.log_action('deployment_report_saved', f'Saved to {output_path}', {
            'deployment_ready': self.deployment_metrics.deployment_ready
        })
        
        self.mcp.log_point('save_deployment_report', 'complete', {
            'output_path': str(output_path)
        })
        
        return output_path
    
    def execute_full_test_cycle(self) -> bool:
        self.mcp.log_point('execute_full_test_cycle', 'enter')
        
        self.log_action('test_cycle_started', 'Beginning full test cycle')
        
        self.run_pytest_suite(markers='unit')
        
        self.run_pytest_suite(markers='integration')
        
        self.run_pytest_suite(markers='smoke')
        
        metrics = self.generate_deployment_metrics()
        
        self.save_deployment_report()
        
        self.log_action('test_cycle_completed', 'Test cycle finished', {
            'deployment_ready': metrics.deployment_ready,
            'tests_passed': metrics.tests_passed,
            'tests_total': metrics.tests_total
        })
        
        self.mcp.log_point('execute_full_test_cycle', 'complete', {
            'success': metrics.deployment_ready
        })
        
        return metrics.deployment_ready


class IdempotentPhase:
    def __init__(self, phase_name: str, bridge: TestSystemBridge):
        self.phase_name = phase_name
        self.bridge = bridge
        self.inputs_hash = None
        self.outputs_hash = None
    
    def __enter__(self):
        self.bridge.mcp.log_point(f'phase_{self.phase_name}', 'enter')
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        status = 'success' if exc_type is None else 'failed'
        self.bridge.mcp.log_point(f'phase_{self.phase_name}', status)
        return False
