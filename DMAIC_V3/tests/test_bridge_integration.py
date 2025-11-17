import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from DMAIC_V3.core.test_system_bridge import TestSystemBridge, MCPControlPoint
from DMAIC_V3.config import DMAICConfig
from DMAIC_V3.core.state import StateManager

# HandoverBridge is optional
try:
    from DMAIC_V3.core.handover_bridge import HandoverBridge
except ImportError:
    HandoverBridge = None


@pytest.fixture
def config():
    return DMAICConfig()


@pytest.fixture
def state_manager(config, tmp_path):
    return StateManager(tmp_path / 'state')


@pytest.fixture
def handover_bridge(config, state_manager):
    if HandoverBridge is not None:
        try:
            return HandoverBridge(config, state_manager)
        except Exception:
            return None
    return None


@pytest.fixture
def test_bridge(config, state_manager, handover_bridge):
    return TestSystemBridge(config, state_manager, handover_bridge)


@pytest.mark.smoke
def test_mcp_control_point_initialization(tmp_path):
    mcp = MCPControlPoint(tmp_path / '.mcp')
    assert mcp.mcp_dir.exists()
    assert mcp.log_file.parent.exists()


@pytest.mark.smoke
def test_mcp_logging(tmp_path):
    mcp = MCPControlPoint(tmp_path / '.mcp')
    mcp.log_point('test_point', 'enter', {'key': 'value'})
    
    assert mcp.log_file.exists()
    log_content = mcp.log_file.read_text()
    assert 'test_point' in log_content
    assert 'enter' in log_content


@pytest.mark.smoke
def test_test_bridge_initialization(test_bridge):
    assert test_bridge.config is not None
    assert test_bridge.state_manager is not None
    # handover_bridge is optional
    assert test_bridge.mcp is not None


@pytest.mark.smoke
def test_version_management(test_bridge):
    current_version = test_bridge.get_current_version()
    assert isinstance(current_version, str)
    
    test_bridge.update_version('1.2.3')
    assert test_bridge.get_current_version() == '1.2.3'


@pytest.mark.smoke
def test_action_logging(test_bridge):
    test_bridge.log_action('test_action', 'Test description', {'meta': 'data'})
    
    assert test_bridge.actions_file.exists()
    actions = test_bridge.actions_file.read_text()
    assert 'test_action' in actions
    assert 'Test description' in actions


@pytest.mark.unit
def test_test_execution_result_creation():
    from DMAIC_V3.core.test_system_bridge import TestExecutionResult
    
    result = TestExecutionResult(
        test_name='test_example',
        returncode=0,
        stdout='output',
        stderr='',
        success=True,
        duration_seconds=1.5
    )
    
    assert result.test_name == 'test_example'
    assert result.success is True
    assert result.duration_seconds == 1.5


@pytest.mark.unit
def test_deployment_metrics_creation():
    from DMAIC_V3.core.test_system_bridge import DeploymentMetrics
    
    metrics = DeploymentMetrics(
        version='1.0.0',
        timestamp='2025-01-01T00:00:00',
        tests_total=10,
        tests_passed=8,
        tests_failed=2,
        execution_time_seconds=30.0
    )
    
    assert metrics.version == '1.0.0'
    assert metrics.tests_total == 10
    assert metrics.tests_passed == 8
    assert metrics.deployment_ready is False


@pytest.mark.integration
def test_run_simple_command(test_bridge):
    result = test_bridge.run_test(
        'echo_test',
        [sys.executable, '-c', 'print("Hello World")'],
        timeout=10
    )
    
    assert result.success is True
    assert 'Hello World' in result.stdout


@pytest.mark.integration
def test_detect_runtime_errors(test_bridge):
    test_bridge.run_test(
        'failing_test',
        [sys.executable, '-c', 'raise ValueError("Test error")'],
        timeout=10
    )
    
    errors = test_bridge.detect_runtime_errors()
    assert len(errors) > 0
    assert errors[0]['test_name'] == 'failing_test'


@pytest.mark.integration
def test_deployment_report_generation(test_bridge, tmp_path):
    test_bridge.run_test(
        'simple_test',
        [sys.executable, '-c', 'print("test")'],
        timeout=10
    )
    
    metrics = test_bridge.generate_deployment_metrics()
    assert metrics.tests_total == 1
    
    report_path = test_bridge.save_deployment_report(tmp_path / 'report.json')
    assert report_path.exists()
    
    import json
    report = json.loads(report_path.read_text())
    assert 'deployment_metrics' in report
    assert 'test_results' in report
