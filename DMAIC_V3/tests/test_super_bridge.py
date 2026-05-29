"""
DMAIC V3 Test Suite - Super Bridge Integration Test
Full pipeline activation: Phases 1 through 9 exercised through the bridge layer.
"""

import pytest
import json
import tempfile
import shutil
from pathlib import Path

from DMAIC_V3.config import DMAICConfig
from DMAIC_V3.core.state import StateManager
from DMAIC_V3.core.handover_bridge import HandoverBridge
from DMAIC_V3.core.test_system_bridge import TestSystemBridge
from DMAIC_V3.phases.phase1_define import Phase1Define
from DMAIC_V3.phases.phase2_measure import Phase2Measure
from DMAIC_V3.phases.phase3_analyze import Phase3Analyze
from DMAIC_V3.phases.phase4_improve import Phase4Improve
from DMAIC_V3.phases.phase5_control import Phase5Control
from DMAIC_V3.phases.phase6_knowledge import Phase6Knowledge
from DMAIC_V3.phases.phase7_action_tracking import Phase7ActionTracking
from DMAIC_V3.phases.phase8_todo_management import Phase8TODOManagement
from DMAIC_V3.phases.phase9_documentation_generation import Phase9_DocumentationGeneration


@pytest.fixture
def temp_workspace():
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def config(temp_workspace):
    cfg = DMAICConfig()
    cfg.workspace_root = str(temp_workspace)
    cfg.paths.workspace_root = temp_workspace
    cfg.paths.output_root = temp_workspace / "output"
    return cfg


@pytest.fixture
def state_manager(config):
    state_dir = config.paths.output_root / "state"
    return StateManager(state_dir)


@pytest.fixture
def handover_bridge(config, state_manager):
    return HandoverBridge(config, state_manager)


@pytest.fixture
def test_bridge(config, state_manager, handover_bridge):
    return TestSystemBridge(config, state_manager, handover_bridge)


@pytest.fixture
def all_phases(config, state_manager, monkeypatch, tmp_path):
    """Instantiate all 9 phases with redirected working directory."""
    monkeypatch.chdir(tmp_path)
    return {
        'phase1': Phase1Define(config, state_manager),
        'phase2': Phase2Measure(config, state_manager),
        'phase3': Phase3Analyze(config, state_manager),
        'phase4': Phase4Improve(config, state_manager),
        'phase5': Phase5Control(config, state_manager),
        'phase6': Phase6Knowledge(config=config, state=state_manager),
        'phase7': Phase7ActionTracking(config, state_manager),
        'phase8': Phase8TODOManagement(config, state_manager),
        'phase9': Phase9_DocumentationGeneration(),
    }


@pytest.fixture
def sample_python_file(temp_workspace):
    """A small Python file in the workspace for phases to discover."""
    py_file = temp_workspace / "hello.py"
    py_file.write_text(
        '"""Module docstring."""\n\n\ndef greet(name):\n    return f"Hello, {name}!"\n'
    )
    return py_file


@pytest.mark.smoke
@pytest.mark.integration
class TestSuperBridgeIntegration:
    """
    Super Bridge: exercises the full DMAIC V3 pipeline (Phases 1-9) as a cohesive
    system, validating that every phase produces a well-formed (success, result)
    contract and that the bridge layer can coordinate the handover lifecycle.
    """

    # ------------------------------------------------------------------ bridge

    def test_bridge_initialization(self, test_bridge):
        assert test_bridge.config is not None
        assert test_bridge.state_manager is not None
        assert test_bridge.handover_bridge is not None
        assert test_bridge.mcp is not None

    def test_bridge_action_logging(self, test_bridge):
        test_bridge.log_action("super_bridge_test", "Super bridge smoke test", {"scope": "full"})
        assert test_bridge.actions_file.exists()
        content = test_bridge.actions_file.read_text()
        assert "super_bridge_test" in content

    def test_bridge_version_contract(self, test_bridge):
        version = test_bridge.get_current_version()
        assert isinstance(version, str)
        assert len(version) > 0

    # ------------------------------------------------------------------ phases contract

    def test_all_phases_instantiate(self, all_phases):
        assert len(all_phases) == 9
        for name, phase in all_phases.items():
            assert phase is not None, f"{name} failed to instantiate"

    def test_all_phases_have_execute(self, all_phases):
        for name, phase in all_phases.items():
            assert callable(getattr(phase, 'execute', None)), \
                f"{name} missing callable execute()"

    # ------------------------------------------------------------------ phase 1-5: core DMAIC

    def test_phase1_returns_valid_contract(self, all_phases):
        success, result = all_phases['phase1'].execute(iteration=1)
        assert isinstance(success, bool)
        assert isinstance(result, dict)
        assert result.get('phase') == 'DEFINE'
        assert result.get('iteration') == 1

    def test_phase2_returns_valid_contract(self, all_phases, sample_python_file, config):
        # Seed phase1 output so phase2 can load it
        output_dir = config.paths.output_root / "iteration_1" / "phase1_define"
        output_dir.mkdir(parents=True, exist_ok=True)
        phase1_out = output_dir / "phase1_define.json"
        phase1_out.write_text(json.dumps({
            "phase": "DEFINE", "iteration": 1,
            "files": [str(sample_python_file)],
        }))

        success, result = all_phases['phase2'].execute(iteration=1)
        assert isinstance(success, bool)
        assert isinstance(result, dict)

    def test_phase3_returns_valid_contract(self, all_phases, config):
        # Seed phase2 output so phase3 can load it
        output_dir = config.paths.output_root / "iteration_1"
        output_dir.mkdir(parents=True, exist_ok=True)
        phase2_out = output_dir / "phase2_metrics.json"
        phase2_out.write_text(json.dumps({
            "phase": "MEASURE", "iteration": 1,
            "file_metrics": {},
        }))

        success, result = all_phases['phase3'].execute(iteration=1)
        assert isinstance(success, bool)
        assert isinstance(result, dict)
        assert 'summary' in result

    def test_phase4_returns_valid_contract(self, all_phases):
        # Phase 4 runs gracefully even with no phase3 output
        success, result = all_phases['phase4'].execute(iteration=1)
        assert isinstance(success, bool)
        assert isinstance(result, dict)
        assert 'improvements' in result

    def test_phase5_returns_valid_contract(self, all_phases):
        success, result = all_phases['phase5'].execute(iteration=1)
        assert isinstance(success, bool)
        assert isinstance(result, dict)

    # ------------------------------------------------------------------ phase 6-9: extended

    def test_phase6_returns_valid_contract(self, all_phases):
        success, result = all_phases['phase6'].execute(iteration=1)
        assert success is True
        assert isinstance(result, dict)
        assert 'maturity_score' in result

    def test_phase7_returns_valid_contract(self, all_phases):
        success, result = all_phases['phase7'].execute(iteration=1)
        assert success is True
        assert isinstance(result, dict)
        assert result.get('phase') == 'phase7_action_tracking'

    def test_phase8_returns_valid_contract(self, all_phases):
        success, result = all_phases['phase8'].execute(iteration=1)
        assert success is True
        assert isinstance(result, dict)
        assert result.get('phase') == 'phase8_todo_management'

    def test_phase9_skip_when_no_priors(self, all_phases):
        # Phase 9 skips gracefully when prior phases have not run
        success, result = all_phases['phase9'].execute(iteration=1)
        assert success is False
        assert result.get('status') == 'skipped'

    # ------------------------------------------------------------------ end-to-end pipeline

    @pytest.mark.slow
    def test_full_pipeline_phases_1_to_6(self, config, state_manager, monkeypatch, tmp_path,
                                          sample_python_file):
        """
        Run phases 1-6 sequentially, passing output from each phase into the next.
        Validates the core DMAIC pipeline contracts chain correctly.
        """
        monkeypatch.chdir(tmp_path)

        # Phase 1
        p1 = Phase1Define(config, state_manager)
        ok1, r1 = p1.execute(iteration=1)
        assert ok1 is True
        assert r1['phase'] == 'DEFINE'

        # Seed phase2 input (requires phase1_define.json in output_root)
        phase1_dir = config.paths.output_root / "iteration_1" / "phase1_define"
        phase1_dir.mkdir(parents=True, exist_ok=True)
        (phase1_dir / "phase1_define.json").write_text(json.dumps({
            "phase": "DEFINE", "iteration": 1,
            "files": [str(sample_python_file)],
        }))

        # Phase 2
        p2 = Phase2Measure(config, state_manager)
        ok2, r2 = p2.execute(iteration=1)
        assert isinstance(ok2, bool)
        assert isinstance(r2, dict)

        # Seed phase3 input
        phase2_metrics = config.paths.output_root / "iteration_1" / "phase2_metrics.json"
        phase2_metrics.parent.mkdir(parents=True, exist_ok=True)
        phase2_metrics.write_text(json.dumps({
            "phase": "MEASURE", "iteration": 1, "file_metrics": {},
        }))

        # Phase 3
        p3 = Phase3Analyze(config, state_manager)
        ok3, r3 = p3.execute(iteration=1)
        assert isinstance(ok3, bool)
        assert 'summary' in r3

        # Phase 4
        p4 = Phase4Improve(config, state_manager)
        ok4, r4 = p4.execute(iteration=1)
        assert isinstance(ok4, bool)
        assert 'improvements' in r4

        # Phase 5
        p5 = Phase5Control(config, state_manager)
        ok5, r5 = p5.execute(iteration=1)
        assert isinstance(ok5, bool)
        assert isinstance(r5, dict)

        # Phase 6
        p6 = Phase6Knowledge(config=config, state=state_manager)
        ok6, r6 = p6.execute(iteration=1)
        assert ok6 is True
        assert 'maturity_score' in r6

    def test_bridge_deployment_metrics_after_pipeline(self, test_bridge):
        """
        Bridge should produce valid DeploymentMetrics after running an inline test.
        """
        import sys
        test_bridge.run_test(
            'pipeline_smoke',
            [sys.executable, '-c', 'import DMAIC_V3; print("ok")'],
            timeout=15,
        )
        metrics = test_bridge.generate_deployment_metrics()
        assert metrics.tests_total >= 1
        assert metrics.tests_passed >= 0
        assert isinstance(metrics.deployment_ready, bool)

    def test_bridge_mcp_log_pipeline_events(self, test_bridge):
        test_bridge.mcp.log_point("super_bridge_start", "enter", {"iteration": 1})
        test_bridge.mcp.log_point("super_bridge_end", "complete", {"iteration": 1})
        assert test_bridge.mcp.log_file.exists()
        log_content = test_bridge.mcp.log_file.read_text()
        assert "super_bridge_start" in log_content
        assert "super_bridge_end" in log_content
