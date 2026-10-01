#!/usr/bin/env python3
"""Parallel execution authority tests for the current ABACUS runtime.

The retired rich_padding parallel_execution YAML must remain absent. Parallel
execution authority is the canonical TwelveClusterOrchestrator contract.
"""

from datetime import datetime
import json
from pathlib import Path

import pytest

from DMAIC_V3.core.twelve_cluster_orchestrator import TwelveClusterOrchestrator


@pytest.fixture
def parallel_config_path():
    """Retired legacy path retained only as a non-regression guard."""
    return (
        Path(__file__).parent.parent
        / "rich_padding"
        / "parallel_execution"
        / "parallel_execution_config.yaml"
    )


@pytest.fixture
def orchestrator():
    """Current parallel execution authority without optional external engines."""
    return TwelveClusterOrchestrator(
        max_workers=4,
        use_keb=False,
        use_gbogeb=False,
    )


@pytest.fixture
def temp_workspace(tmp_path):
    """Create temporary workspace."""
    workspace = tmp_path / "parallel_execution_workspace"
    workspace.mkdir()
    return workspace


class TestRetiredParallelConfig:
    """Guard the retirement boundary for the old configuration contract."""

    def test_config_file_remains_retired(self, parallel_config_path):
        assert not parallel_config_path.exists(), (
            "Legacy parallel_execution_config.yaml was reintroduced without "
            f"repository authority: {parallel_config_path}"
        )

    def test_current_authority_is_code_contract(self):
        assert TwelveClusterOrchestrator.PHASE_SEQUENCE == [
            "phase1",
            "phase2",
            "phase3",
            "phase4",
            "phase5",
            "phase6",
            "phase7",
            "phase8",
        ]


class TestCanonicalParallelContract:
    """Nine executable replacements for the nine legacy config-blocked tests."""

    def test_contract_has_exactly_twelve_clusters(self, orchestrator):
        contract = orchestrator.get_cluster_contract()
        assert len(contract) == 12
        assert [row["cluster_id"] for row in contract] == list(range(1, 13))

    def test_contract_covers_every_canonical_phase(self, orchestrator):
        phases = {row["phase"] for row in orchestrator.get_cluster_contract()}
        assert phases == set(TwelveClusterOrchestrator.PHASE_SEQUENCE)

    def test_define_phase_has_two_scanner_clusters(self, orchestrator):
        rows = [
            row
            for row in orchestrator.get_cluster_contract()
            if row["phase"] == "phase1"
        ]
        assert [row["cluster_id"] for row in rows] == [1, 2]
        assert all("Define-Scanner" in row["name"] for row in rows)

    def test_measure_phase_has_two_analyzer_clusters(self, orchestrator):
        rows = [
            row
            for row in orchestrator.get_cluster_contract()
            if row["phase"] == "phase2"
        ]
        assert [row["cluster_id"] for row in rows] == [3, 4]
        assert all("Measure-Analyzer" in row["name"] for row in rows)

    def test_knowledge_dow_cluster_is_phase6(self, orchestrator):
        row = next(
            row
            for row in orchestrator.get_cluster_contract()
            if row["cluster_id"] == 8
        )
        assert row == {
            "cluster_id": 8,
            "name": "Knowledge-DOW",
            "phase": "phase6",
            "priority": 7,
        }

    def test_priorities_are_bounded_and_phase_ordered(self, orchestrator):
        priorities = [row["priority"] for row in orchestrator.get_cluster_contract()]
        assert all(1 <= value <= 10 for value in priorities)
        assert priorities == sorted(priorities, reverse=True)

    def test_parallel_execution_preserves_each_task_result(self, orchestrator):
        tasks = [
            {
                "task_id": f"task-{index}",
                "func": (lambda value=index: {"value": value}),
            }
            for index in range(4)
        ]
        result = orchestrator.execute_phase_parallel(
            "phase2",
            tasks,
            iteration=1,
        )
        assert result["success"] is True
        assert result["tasks_executed"] == 4
        assert result["tasks_failed"] == 0
        assert set(result["results_map"]) == {
            "task-0",
            "task-1",
            "task-2",
            "task-3",
        }

    def test_unknown_phase_fails_closed(self, orchestrator):
        with pytest.raises(ValueError, match="Unknown or unmapped phase"):
            orchestrator.execute_phase_parallel(
                "phase99",
                [{"task_id": "invalid"}],
                iteration=1,
            )

    def test_cluster_status_is_complete_and_idle(self, orchestrator):
        status = orchestrator.get_cluster_status()
        assert status["total_clusters"] == 12
        assert len(status["clusters"]) == 12
        assert all(row["status"] == "idle" for row in status["clusters"])


class TestKnowledgeBridgePersistence:
    """Local persistence behavior retained independently of the retired YAML."""

    def test_knowledge_bridge_workspace_setup(self, temp_workspace):
        kb_path = temp_workspace / ".knowledge_bridge"
        kb_path.mkdir(exist_ok=True)
        assert kb_path.exists()
        assert kb_path.is_dir()

    def test_knowledge_bridge_state_persistence(self, temp_workspace):
        kb_path = temp_workspace / ".knowledge_bridge"
        kb_path.mkdir(exist_ok=True)

        state_file = kb_path / "bridge_state.json"
        test_state = {
            "timestamp": datetime.now().isoformat(),
            "status": "active",
            "executions": [],
        }
        state_file.write_text(json.dumps(test_state), encoding="utf-8")
        loaded_state = json.loads(state_file.read_text(encoding="utf-8"))
        assert loaded_state["status"] == "active"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
