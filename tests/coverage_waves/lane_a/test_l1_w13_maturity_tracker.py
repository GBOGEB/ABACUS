"""Lane A wave 13: DMAIC_V3.convergence.maturity_tracker behaviour."""

import json
import sys

import pytest

from DMAIC_V3.convergence import maturity_tracker as mt


@pytest.fixture
def ws(monkeypatch, tmp_path):
    # _load_completed_tasks probes cwd-relative paths, so run inside tmp_path.
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _touch(path, data=b"{}"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def _score(ws, value):
    _touch(ws / "convergence_report.json", json.dumps({"score": value}).encode())


def test_paths_and_alias(ws):
    tracker = mt.MaturityTracker(ws)
    assert tracker.workspace_path == ws
    assert tracker.maturity_file == ws / "maturity_assessment.json"


@pytest.mark.parametrize(
    "content,expected",
    [
        (None, 0.0),
        (b'{"score": "72.5"}', 72.5),
        (b'{"other": 1}', 0.0),
        (b"{bad", 0.0),
        (b'{"score": "high"}', 0.0),
        (b'{"score": null}', 0.0),
    ],
)
def test_load_convergence_score(ws, content, expected):
    if content is not None:
        _touch(ws / "convergence_report.json", content)
    assert mt.MaturityTracker(ws)._load_convergence_score() == expected


def test_load_completed_tasks_empty(ws):
    assert mt.MaturityTracker(ws)._load_completed_tasks() == []


def test_load_completed_tasks_detects_components(ws):
    out = ws / "DMAIC_V3_OUTPUT"
    _touch(out / "iteration_1" / "phase3" / "x.json")
    _touch(out / "iteration_2" / "phase0" / "a.json")
    _touch(out / "iteration_2" / "phase2" / "b.json")
    (out / "iteration_2" / "phase4").mkdir()
    _touch(ws / "DMAIC_V3" / "core" / "idempotency_wrapper.py", b"")
    _touch(ws / "GLOBAL_ARTIFACT_RANKING_SUMMARY.yaml", b"")
    _touch(ws / "recursive_self_ranking_system.py", b"")
    _touch(ws / "DMAIC_V3" / "convergence" / "maturity_tracker.py", b"")
    _score(ws, 10)
    assert mt.MaturityTracker(ws)._load_completed_tasks() == [
        "phase0_init",
        "phase2",
        "idempotency_system",
        "ranking_system",
        "recursive_ranking",
        "convergence_analyzer",
        "maturity_tracker",
    ]


def test_output_dir_without_iterations(ws):
    (ws / "DMAIC_V3_OUTPUT").mkdir()
    _touch(ws / "ranking.json")
    assert mt.MaturityTracker(ws)._load_completed_tasks() == ["ranking_system"]


def test_determine_level(ws):
    tracker = mt.MaturityTracker(ws)
    lvl2 = list(mt.MaturityTracker.MATURITY_LEVELS[2].tasks_required)
    lvl3 = list(mt.MaturityTracker.MATURITY_LEVELS[3].tasks_required)
    assert tracker._determine_level(100, []) == 0
    assert tracker._determine_level(55, lvl2) == 2
    assert tracker._determine_level(40, lvl2) == 1
    assert tracker._determine_level(70, lvl3) == 3
    every = [t for lvl in tracker.MATURITY_LEVELS.values() for t in lvl.tasks_required]
    assert tracker._determine_level(99, every) == 5


def test_level_completion(ws):
    tracker = mt.MaturityTracker(ws)
    assert tracker._calculate_level_completion(0, []) == 100.0
    assert tracker._calculate_level_completion(1, ["phase0_init"]) == 50.0
    assert tracker._calculate_level_completion(5, ["ci_cd_pipeline"]) == 33.33


def test_blockers_and_recommendations(ws):
    tracker = mt.MaturityTracker(ws)
    pending = ["a", "b", "c", "d"]
    blockers = tracker._identify_blockers(3, 10.0, pending)
    assert blockers == [
        "Convergence score (10.0) below minimum (65)",
        "4 tasks pending: a, b, c",
    ]
    recs = tracker._generate_recommendations(3, 10.0, pending, blockers)
    assert recs == [
        "Address blockers listed above",
        "Complete pending tasks: a, b, c",
        "Target Level 4 (Optimizing) - Convergence: 80+",
        "Focus on improving convergence metrics",
    ]
    assert tracker._identify_blockers(0, 0.0, []) == []
    assert tracker._generate_recommendations(5, 99.0, [], []) == []


def test_build_level_statuses(ws):
    tracker = mt.MaturityTracker(ws)
    statuses = tracker._build_level_statuses(1, 35.0, ["phase0_init", "phase1_define"])
    assert [s.status for s in statuses] == [
        "COMPLETED",
        "COMPLETED",
        "PENDING",
        "PENDING",
        "PENDING",
        "PENDING",
    ]
    assert statuses[0].completion_percentage == 100.0
    assert statuses[1].convergence_achieved is True
    assert statuses[2].convergence_achieved is False
    active = tracker._build_level_statuses(1, 35.0, ["phase0_init"])
    assert active[1].status == "ACTIVE"
    assert active[1].completion_percentage == 50.0


def test_assess_level_zero_and_history_dedupe(ws):
    tracker = mt.MaturityTracker(ws)
    first = tracker.assess_current_maturity()
    assert first.current_level == 0
    assert first.next_level == 1
    assert first.next_milestone == "Level 1 - Repeatable"
    assert first.tasks_pending == []
    data = json.loads(tracker.maturity_file.read_text(encoding="utf-8"))
    assert len(data["score_history"]) == 1

    tracker.assess_current_maturity()
    data = json.loads(tracker.maturity_file.read_text(encoding="utf-8"))
    assert len(data["score_history"]) == 1

    _score(ws, 20)
    tracker.assess_current_maturity()
    data = json.loads(tracker.maturity_file.read_text(encoding="utf-8"))
    assert [h["convergence_score"] for h in data["score_history"]] == [0.0, 20.0]


def test_save_assessment_recovers_and_caps_history(ws):
    tracker = mt.MaturityTracker(ws)
    _touch(tracker.maturity_file, b"not json")
    tracker.assess_current_maturity()
    data = json.loads(tracker.maturity_file.read_text(encoding="utf-8"))
    assert len(data["score_history"]) == 1

    old = [{"convergence_score": i} for i in range(60)]
    _touch(tracker.maturity_file, json.dumps({"score_history": old}).encode())
    tracker.assess_current_maturity()
    data = json.loads(tracker.maturity_file.read_text(encoding="utf-8"))
    assert len(data["score_history"]) == 50
    assert data["score_history"][-1]["current_level"] == 0


def test_assess_top_level(ws, monkeypatch):
    every = [
        t
        for lvl in mt.MaturityTracker.MATURITY_LEVELS.values()
        for t in lvl.tasks_required
    ]
    tracker = mt.MaturityTracker(ws)
    monkeypatch.setattr(tracker, "_load_completed_tasks", lambda: list(every))
    _score(ws, 99)
    assessment = tracker.generate_report()
    assert assessment.current_level == 5
    assert assessment.next_level is None
    assert assessment.next_milestone == "Production-ready"
    assert assessment.overall_completion == 100.0
    assert assessment.recommendations == []
    text = tracker.generate_text_report()
    assert "CURRENT LEVEL: 5 - Production-Ready" in text
    assert "NEXT LEVEL" not in text
    assert "... and" in text
    assert "RECOMMENDATIONS:" not in text


def test_text_report_with_pending_and_blockers(ws, monkeypatch):
    tracker = mt.MaturityTracker(ws)
    lvl3 = list(mt.MaturityTracker.MATURITY_LEVELS[3].tasks_required)
    lvl2 = list(mt.MaturityTracker.MATURITY_LEVELS[2].tasks_required)
    monkeypatch.setattr(tracker, "_determine_level", lambda score, done: 3)
    monkeypatch.setattr(tracker, "_load_completed_tasks", lambda: lvl2 + lvl3[:1])
    text = tracker.generate_text_report()
    assert "NEXT LEVEL: 4 - Optimizing" in text
    assert "TASKS PENDING:" in text
    assert "  [ ] ranking_system" in text
    assert "BLOCKERS:" in text
    assert "  1. Address blockers listed above" in text


def test_main_text_and_json(ws, monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["mt", "--workspace", str(ws)])
    mt.main()
    assert "MATURITY ASSESSMENT REPORT" in capsys.readouterr().out
    monkeypatch.setattr(sys, "argv", ["mt", "--workspace", str(ws), "--json"])
    mt.main()
    data = json.loads(capsys.readouterr().out)
    assert data["current_level"] == 0
    assert len(data["levels"]) == 6


def check_production_defect_phase_dirs_never_satisfy_level_one(monkeypatch, tmp_path):
    # Pins a production_defect (maturity_tracker.py:328): phase directories are
    # recorded as "phase1".."phase6", but levels 1-2 require "phase1_define" etc.,
    # so Level 1 is unreachable from real output. This fails once fixed.
    monkeypatch.chdir(tmp_path)
    for n in range(7):
        _touch(tmp_path / "DMAIC_V3_OUTPUT" / "iteration_1" / f"phase{n}" / "o.json")
    _score(tmp_path, 100)
    assessment = mt.MaturityTracker(tmp_path).assess_current_maturity()
    assert "phase1" in assessment.tasks_completed
    assert "phase1_define" not in assessment.tasks_completed
    assert assessment.current_level == 0
