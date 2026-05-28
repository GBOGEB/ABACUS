from DMAIC_V3.core.twelve_cluster_orchestrator import TwelveClusterOrchestrator


def test_cluster_contract_is_canonical_12_cluster():
    orchestrator = TwelveClusterOrchestrator(use_keb=False, use_gbogeb=False)
    contract = orchestrator.get_cluster_contract()

    assert len(contract) == 12
    assert {entry["cluster_id"] for entry in contract} == set(range(1, 13))
    assert next(c for c in contract if c["cluster_id"] == 8)["phase"] == "phase6"
    assert next(c for c in contract if c["cluster_id"] == 10)["phase"] == "phase7"


def test_execute_phase_parallel_builds_results_map():
    orchestrator = TwelveClusterOrchestrator(use_keb=False, use_gbogeb=False)

    tasks = [
        {
            "file_path": f"/tmp/sample_{idx}.py",
            "func": (lambda value=idx: {"success": True, "value": value}),
        }
        for idx in range(5)
    ]

    result = orchestrator.execute_phase_parallel("phase2", tasks, iteration=1)
    assert result["success"] is True
    assert result["tasks_executed"] == 5
    assert len(result["results_map"]) == 5
    assert "/tmp/sample_0.py" in result["results_map"]


def test_end_to_end_12_cluster_with_sample_cryo_data_emits_temporal_hooks():
    orchestrator = TwelveClusterOrchestrator(use_keb=False, use_gbogeb=False)
    sample_cryo = [
        {"cryo_id": "CRYO-A", "temperature_k": 4.5, "pressure_bar": 1.2},
        {"cryo_id": "CRYO-B", "temperature_k": 5.1, "pressure_bar": 1.1},
        {"cryo_id": "CRYO-C", "temperature_k": 4.9, "pressure_bar": 1.3},
    ]

    def phase_task_factory(phase):
        return [
            {
                "task_id": f"{phase}-{entry['cryo_id']}",
                "func": (
                    lambda payload=entry, phase_name=phase: {
                        "success": True,
                        "phase": phase_name,
                        "cryo_id": payload["cryo_id"],
                        "temperature_k": payload["temperature_k"],
                    }
                ),
            }
            for entry in sample_cryo
        ]

    result = orchestrator.run_phases_with_hooks(iteration=7, phase_task_factory=phase_task_factory)

    assert result["success"] is True
    assert result["final_status"] == "completed"
    assert result["phases_run"] == TwelveClusterOrchestrator.PHASE_SEQUENCE
    assert result["total_tasks_executed"] == len(sample_cryo) * len(TwelveClusterOrchestrator.PHASE_SEQUENCE)

    temporal_events = result["temporal_events"]
    assert len(temporal_events) == len(TwelveClusterOrchestrator.PHASE_SEQUENCE) * 2
    start_events = [evt for evt in temporal_events if evt["event"] == "phase_start"]
    end_events = [evt for evt in temporal_events if evt["event"] == "phase_end"]
    assert len(start_events) == 8
    assert len(end_events) == 8
    assert all(evt["iteration"] == 7 for evt in temporal_events)
    assert all(evt["status"] in {"started", "completed"} for evt in temporal_events)
    assert any(set(evt["clusters"]) == {9, 10} for evt in start_events if evt["phase"] == "phase7")
    assert all(evt["artifacts"] for evt in end_events)
