import json

from DMAIC_V3.convergence.maturity_tracker import MaturityTracker


def test_convergence_loader_handles_missing_invalid_and_valid_data(tmp_path):
    tracker = MaturityTracker(tmp_path)

    assert tracker._load_convergence_score() == 0.0

    tracker.convergence_file.write_text("{bad json", encoding="utf-8")
    assert tracker._load_convergence_score() == 0.0

    tracker.convergence_file.write_text(json.dumps({"score": "82.5"}), encoding="utf-8")
    assert tracker._load_convergence_score() == 82.5


def test_level_selection_respects_convergence_and_required_tasks(tmp_path):
    tracker = MaturityTracker(tmp_path)
    level2_tasks = list(tracker.MATURITY_LEVELS[2].tasks_required)

    assert tracker._determine_level(55, level2_tasks) == 2
    assert tracker._determine_level(49, level2_tasks) == 1
    assert tracker._determine_level(29, level2_tasks) == 0


def test_completion_and_level_statuses_are_consistent(tmp_path):
    tracker = MaturityTracker(tmp_path)
    completed = ["phase0_init"]

    assert tracker._calculate_level_completion(0, completed) == 100.0
    assert tracker._calculate_level_completion(1, completed) == 50.0

    statuses = tracker._build_level_statuses(
        current_level=1,
        convergence_score=40,
        completed_tasks=completed,
    )
    by_level = {item.level: item for item in statuses}

    assert by_level[0].status == "COMPLETED"
    assert by_level[0].completion_percentage == 100.0
    assert by_level[1].status == "ACTIVE"
    assert by_level[1].completion_percentage == 50.0
    assert by_level[1].convergence_achieved is True
    assert by_level[2].status == "PENDING"
    assert by_level[2].convergence_achieved is False


def test_blockers_and_recommendations_describe_next_actions(tmp_path):
    tracker = MaturityTracker(tmp_path)
    pending = ["stability_monitor", "git_manager"]

    blockers = tracker._identify_blockers(4, 70, pending)
    recommendations = tracker._generate_recommendations(4, 70, pending, blockers)

    assert any("below minimum" in item for item in blockers)
    assert any("2 tasks pending" in item for item in blockers)
    assert recommendations[0] == "Address blockers listed above"
    assert any("Complete pending tasks" in item for item in recommendations)
    assert any("Target Level 5" in item for item in recommendations)
    assert "Focus on improving convergence metrics" in recommendations
