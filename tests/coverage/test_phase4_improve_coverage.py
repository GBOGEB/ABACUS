from DMAIC_V3.phases.phase4_improve import CodeImprover, Phase4Improve


def test_code_improver_adds_docstrings_and_type_hints(tmp_path):
    source = tmp_path / "sample.py"
    source.write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    improver = CodeImprover(tmp_path)

    doc = improver.add_missing_docstrings(source)
    hints = improver.add_type_hints(source)
    text = source.read_text(encoding="utf-8")

    assert doc["success"] is True
    assert doc["modifications"] == 1
    assert hints["success"] is True
    assert "TODO: Add function description" in text
    assert "-> Any" in text


def test_code_improver_reports_noop_when_nothing_to_change(tmp_path):
    source = tmp_path / "sample.py"
    source.write_text('def ok() -> int:\n    """doc"""\n    return 1\n', encoding="utf-8")
    improver = CodeImprover(tmp_path)

    assert improver.add_missing_docstrings(source)["success"] is False
    assert improver.add_type_hints(source)["success"] is False


def test_refactoring_plan_priority_and_roadmap_are_deterministic():
    phase = object.__new__(Phase4Improve)
    roots = [
        {"category": "High Complexity", "severity": "critical", "count": 2},
        {"category": "God Classes", "severity": "high", "count": 1},
        {"category": "Low Documentation", "severity": "medium", "count": 4},
    ]

    tasks = phase.generate_refactoring_plan(roots)
    ranked = phase.prioritize_improvements(tasks)
    roadmap = phase.generate_implementation_roadmap(ranked)
    metrics = phase.generate_improvement_metrics(roadmap)

    assert [t["task_id"] for t in tasks] == ["REFACTOR-1", "REFACTOR-2", "REFACTOR-3"]
    assert ranked[0]["priority"] == "critical"
    assert all("roi_score" in task for task in ranked)
    assert len(roadmap["phase_1_immediate"]) == 3
    assert metrics["total_improvements"] == 3
    assert metrics["immediate_actions"] == 3
