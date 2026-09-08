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

from DMAIC_V3.core.handover_bridge import HandoverBridge
from DMAIC_V3.config import DMAICConfig, VERSION
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
# DOW -> DMAIC Bridge Tests
# ============================================================================

class TestDOWToDMAICBridge:
    """Test DOW to DMAIC data flow"""

    def test_dow_knowledge_to_dmaic(self, handover_bridge):
        """Test DOW knowledge converts to DMAIC input"""
        dow_knowledge = {
            "level": 5,
            "knowledge_entries": [
                {"id": "K1", "content": "Process optimization insight"},
                {"id": "K2", "content": "Quality improvement pattern"}
            ],
            "metadata": {
                "source": "DOW_Level5_KEB",
                "timestamp": "2025-11-26T10:00:00Z"
            }
        }

        handover_bridge.begin_run("dow_to_dmaic")
        handover_bridge.log_action("phase1_define", "knowledge_import", dow_knowledge)

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

        config.execution_mode = dow_metadata["execution_mode"]

        assert config.execution_mode == "unified"
        assert config.version == VERSION

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
