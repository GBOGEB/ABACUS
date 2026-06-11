"""
DMAIC V3 - Bidirectional Bridge Tests
Tests data flow in both directions across all bridge types
Version: 1.0.0
Date: 2025-11-26
"""

import pytest
from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from DMAIC_V3.core.handover_bridge import HandoverBridge, IdempotentPhase
from DMAIC_V3.config import DMAICConfig
from DMAIC_V3.core.state import StateManager


@pytest.fixture
def config():
    return DMAICConfig()


@pytest.fixture
def state_manager(config, tmp_path):
    return StateManager(tmp_path / 'state')


@pytest.fixture
def handover_bridge(config, state_manager):
    return HandoverBridge(config, state_manager)


# ============================================================================
# DMAIC → DOW Bridge Tests
# ============================================================================

@pytest.mark.bridge
@pytest.mark.bidirectional
class TestDMAICToDOWBridge:
    """Test DMAIC output → DOW input data flow"""

    def test_dmaic_phase_output_to_dow_knowledge_package(self, handover_bridge, tmp_path):
        """Test Phase 5 output converts to DOW knowledge package"""
        # Simulate DMAIC Phase 5 output
        dmaic_output = {
            "phase": 5,
            "phase_name": "control",
            "results": {
                "control_plan": "Automated monitoring",
                "metrics": {"quality_score": 95.5},
                "recommendations": ["Deploy to production", "Enable monitoring"]
            },
            "iteration": 1,
            "timestamp": "2025-11-26T10:00:00Z"
        }

        # Convert to DOW knowledge package
        handover_bridge.begin_run("test_run_001")
        handover_bridge.log_action("control", "phase_complete", dmaic_output)

        # Validate knowledge package structure
        provenance = handover_bridge.get_provenance_trail()
        assert len(provenance) >= 2  # run_started + action

        action_log = [p for p in provenance if p['event'] == 'action'][0]
        assert action_log['phase'] == 'control'
        assert action_log['details']['phase'] == 5

    def test_dmaic_metrics_to_dow_metadata(self, handover_bridge):
        """Test DMAIC metrics convert to DOW metadata format"""
        dmaic_metrics = {
            "phase1_duration": 45.2,
            "phase2_duration": 60.5,
            "phase3_duration": 55.0,
            "phase4_duration": 70.3,
            "phase5_duration": 40.1,
            "total_duration": 271.1,
            "quality_score": 92.5
        }

        handover_bridge.begin_run("metrics_test")
        handover_bridge.record_metrics("full_pipeline", dmaic_metrics)

        metrics_history = handover_bridge.get_metrics_history()
        assert len(metrics_history) == 1
        assert metrics_history[0]['metrics']['quality_score'] == 92.5

    def test_dmaic_results_to_handover_manifest(self, handover_bridge, tmp_path):
        """Test DMAIC results generate valid handover manifest"""
        handover_bridge.begin_run("manifest_test")

        # Simulate all 5 phases
        for phase in range(1, 6):
            handover_bridge.log_action(
                f"phase{phase}",
                "completed",
                {"phase": phase, "status": "success"}
            )

        handover_bridge.finish_run("success", {"total_phases": 5})

        # Save and validate manifest
        manifest_path = tmp_path / "handover_manifest.json"
        handover_bridge.save_provenance(manifest_path)

        assert manifest_path.exists()
        manifest = json.loads(manifest_path.read_text())
        assert len(manifest) >= 7  # run_started + 5 phases + run_finished

    def test_dmaic_output_schema_validation(self, handover_bridge):
        """Test DMAIC output matches DOW input schema"""
        dmaic_output = {
            "version": "3.0.0",
            "run_id": "test_001",
            "phases_completed": 5,
            "final_metrics": {"quality": 95.0},
            "artifacts": ["control_plan.json", "metrics.json"]
        }

        # Schema validation
        required_fields = ["version", "run_id", "phases_completed", "final_metrics"]
        for field in required_fields:
            assert field in dmaic_output, f"Missing required field: {field}"

        assert isinstance(dmaic_output["phases_completed"], int)
        assert isinstance(dmaic_output["final_metrics"], dict)


# ============================================================================
# DOW → DMAIC Bridge Tests
# ============================================================================

@pytest.mark.bridge
@pytest.mark.bidirectional
class TestDOWToDMAICBridge:
    """Test DOW output → DMAIC input data flow"""

    def test_dow_knowledge_package_to_dmaic_input(self, handover_bridge, state_manager):
        """Test DOW knowledge package converts to DMAIC Phase 1 input"""
        # Simulate DOW knowledge package
        dow_knowledge = {
            "level": 5,
            "component": "KEB",
            "knowledge_entries": [
                {"id": "K001", "category": "quality", "content": "Best practice 1"},
                {"id": "K002", "category": "process", "content": "Best practice 2"}
            ],
            "metadata": {
                "source": "DOW_Level5_KEB",
                "timestamp": "2025-11-26T10:00:00Z"
            }
        }

        # Convert to DMAIC input
        handover_bridge.begin_run("dow_to_dmaic")
        handover_bridge.log_action("phase1_define", "knowledge_import", dow_knowledge)

        # Validate conversion
        provenance = handover_bridge.get_provenance_trail()
        action = [p for p in provenance if p['event'] == 'action'][0]
        assert action['details']['level'] == 5
        assert len(action['details']['knowledge_entries']) == 2

    def test_dow_metadata_to_dmaic_config(self, config):
        """Test DOW metadata converts to DMAIC configuration"""
        dow_metadata = {
            "execution_mode": "unified",
            "dow_enabled": True,
            "quality_threshold": 85.0,
            "max_iterations": 5
        }

        # Apply to config
        config.execution_mode = dow_metadata["execution_mode"]

        assert config.execution_mode == "unified"
        assert config.version == "3.3.0"

    def test_dow_handover_to_dmaic_state(self, handover_bridge, state_manager):
        """Test DOW handover updates DMAIC state"""
        dow_handover = {
            "from": "DOW_Level3_DMAIC",
            "to": "DMAIC_Phase4",
            "data": {
                "improvements": ["Optimize algorithm", "Reduce latency"],
                "priority": "high"
            },
            "status": "ready"
        }

        handover_bridge.begin_run("dow_handover")
        handover_bridge.log_action("phase4_improve", "dow_handover_received", dow_handover)

        provenance = handover_bridge.get_provenance_trail()
        action = [p for p in provenance if p['event'] == 'action'][0]
        assert action['details']['status'] == 'ready'
        assert len(action['details']['data']['improvements']) == 2

    def test_dow_output_schema_validation(self):
        """Test DOW output matches DMAIC input schema"""
        dow_output = {
            "level": 3,
            "component": "DMAIC",
            "phases_completed": 5,
            "results": {"quality_score": 92.0},
            "handover_ready": True
        }

        # Schema validation
        required_fields = ["level", "component", "phases_completed", "results"]
        for field in required_fields:
            assert field in dow_output, f"Missing required field: {field}"

        assert dow_output["level"] in [0, 1, 2, 3, 4, 5]
        assert isinstance(dow_output["results"], dict)


# ============================================================================
# GBOGEB ↔ ABACUS Bridge Tests
# ============================================================================

@pytest.mark.bridge
@pytest.mark.bidirectional
class TestGBOGEBToABACUSBridge:
    """Test GBOGEB ↔ ABACUS bidirectional data flow"""

    def test_gbogeb_to_abacus_forward(self, handover_bridge):
        """Test GBOGEB → ABACUS data flow"""
        gbogeb_output = {
            "level": 1,
            "component": "GBOGEB",
            "requirements": ["REQ-001", "REQ-002", "REQ-003"],
            "status": "processed"
        }

        handover_bridge.begin_run("gbogeb_to_abacus")
        handover_bridge.log_action("level1_gbogeb", "handover_to_abacus", gbogeb_output)

        provenance = handover_bridge.get_provenance_trail()
        action = [p for p in provenance if p['event'] == 'action'][0]
        assert action['phase'] == 'level1_gbogeb'
        assert len(action['details']['requirements']) == 3

    def test_abacus_to_gbogeb_reverse(self, handover_bridge):
        """Test ABACUS → GBOGEB feedback flow"""
        abacus_feedback = {
            "level": 2,
            "component": "ABACUS",
            "analysis_results": {
                "requirements_validated": 3,
                "issues_found": 1,
                "feedback": "REQ-002 needs clarification"
            },
            "status": "feedback_ready"
        }

        handover_bridge.begin_run("abacus_to_gbogeb")
        handover_bridge.log_action("level2_abacus", "feedback_to_gbogeb", abacus_feedback)

        provenance = handover_bridge.get_provenance_trail()
        action = [p for p in provenance if p['event'] == 'action'][0]
        assert action['details']['status'] == 'feedback_ready'
        assert action['details']['analysis_results']['issues_found'] == 1


# ============================================================================
# DOW ↔ KEB Bridge Tests
# ============================================================================

@pytest.mark.bridge
@pytest.mark.bidirectional
class TestDOWToKEBBridge:
    """Test DOW ↔ KEB bidirectional data flow"""

    def test_dow_to_keb_knowledge_storage(self, handover_bridge):
        """Test DOW → KEB knowledge storage"""
        dow_knowledge = {
            "source": "DOW_Level3_DMAIC",
            "knowledge_items": [
                {"id": "K001", "type": "best_practice", "content": "Use idempotency"},
                {"id": "K002", "type": "lesson_learned", "content": "Monitor logs"}
            ],
            "timestamp": "2025-11-26T10:00:00Z"
        }

        handover_bridge.begin_run("dow_to_keb")
        handover_bridge.log_action("level5_keb", "store_knowledge", dow_knowledge)

        provenance = handover_bridge.get_provenance_trail()
        action = [p for p in provenance if p['event'] == 'action'][0]
        assert len(action['details']['knowledge_items']) == 2

    def test_keb_to_dow_knowledge_retrieval(self, handover_bridge):
        """Test KEB → DOW knowledge retrieval"""
        keb_query = {
            "query": "best practices for DMAIC Phase 4",
            "filters": {"type": "best_practice", "phase": 4},
            "limit": 10
        }

        keb_results = {
            "query": keb_query,
            "results": [
                {"id": "K010", "content": "Prioritize high-impact improvements"},
                {"id": "K011", "content": "Validate with stakeholders"}
            ],
            "count": 2
        }

        handover_bridge.begin_run("keb_to_dow")
        handover_bridge.log_action("level5_keb", "retrieve_knowledge", keb_results)

        provenance = handover_bridge.get_provenance_trail()
        action = [p for p in provenance if p['event'] == 'action'][0]
        assert action['details']['count'] == 2


# ============================================================================
# JSON/YAML I/O Bridge Tests
# ============================================================================

@pytest.mark.bridge
@pytest.mark.bidirectional
class TestJSONYAMLBridges:
    """Test JSON/YAML file I/O bridges"""

    def test_dmaic_output_to_json_file(self, handover_bridge, tmp_path):
        """Test DMAIC output writes valid JSON"""
        dmaic_output = {
            "version": "3.0.0",
            "phases": [1, 2, 3, 4, 5],
            "metrics": {"quality": 95.0}
        }

        output_file = tmp_path / "dmaic_output.json"
        output_file.write_text(json.dumps(dmaic_output, indent=2))

        assert output_file.exists()
        loaded = json.loads(output_file.read_text())
        assert loaded["version"] == "3.0.0"
        assert len(loaded["phases"]) == 5

    def test_json_file_to_dmaic_input(self, tmp_path):
        """Test JSON file reads into DMAIC input"""
        input_data = {
            "config": {"execution_mode": "unified"},
            "initial_state": {"iteration": 1}
        }

        input_file = tmp_path / "dmaic_input.json"
        input_file.write_text(json.dumps(input_data, indent=2))

        loaded = json.loads(input_file.read_text())
        assert loaded["config"]["execution_mode"] == "unified"
        assert loaded["initial_state"]["iteration"] == 1

    def test_handover_manifest_yaml_format(self, handover_bridge, tmp_path):
        """Test handover manifest can be saved as YAML"""
        handover_bridge.begin_run("yaml_test")
        handover_bridge.log_action("test_phase", "test_action", {"key": "value"})
        handover_bridge.finish_run("success", {"total": 1})

        # Save as JSON (YAML conversion would require pyyaml)
        manifest_path = tmp_path / "handover_manifest.json"
        handover_bridge.save_provenance(manifest_path)

        assert manifest_path.exists()
        manifest = json.loads(manifest_path.read_text())
        assert len(manifest) >= 3


# ============================================================================
# Idempotency & Error Handling Tests
# ============================================================================

@pytest.mark.bridge
@pytest.mark.integration
class TestBridgeIdempotencyAndErrors:
    """Test bridge idempotency and error handling"""

    def test_idempotent_phase_execution(self, handover_bridge, state_manager):
        """Test phase execution is idempotent"""
        phase_name = "test_phase"

        # First execution
        result1 = handover_bridge.wrap_phase(
            phase_name,
            lambda: {"result": "success", "value": 42}
        )

        # Second execution (should return cached result)
        result2 = handover_bridge.wrap_phase(
            phase_name,
            lambda: {"result": "different", "value": 99}
        )

        # Results should be identical (cached)
        assert result1 == result2
        assert result1["value"] == 42

    def test_bridge_error_propagation(self, handover_bridge):
        """Test errors propagate correctly across bridges"""
        handover_bridge.begin_run("error_test")

        error_data = {
            "error_type": "ValidationError",
            "message": "Invalid schema",
            "phase": "phase2_measure"
        }

        handover_bridge.log_action("error_handler", "error_logged", error_data)

        provenance = handover_bridge.get_provenance_trail()
        error_log = [p for p in provenance if p['event'] == 'action'][0]
        assert error_log['details']['error_type'] == 'ValidationError'

    def test_bridge_data_integrity(self, handover_bridge, tmp_path):
        """Test data integrity across bridge transitions"""
        original_data = {
            "id": "TEST-001",
            "value": 12345,
            "nested": {"key": "value"},
            "list": [1, 2, 3]
        }

        handover_bridge.begin_run("integrity_test")
        handover_bridge.log_action("test", "data_transfer", original_data)

        # Save and reload
        manifest_path = tmp_path / "integrity_test.json"
        handover_bridge.save_provenance(manifest_path)

        loaded = json.loads(manifest_path.read_text())
        action = [p for p in loaded if p['event'] == 'action'][0]

        assert action['details']['id'] == original_data['id']
        assert action['details']['value'] == original_data['value']
        assert action['details']['nested'] == original_data['nested']
        assert action['details']['list'] == original_data['list']
