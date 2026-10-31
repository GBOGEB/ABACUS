"""Behaviour tests for abacus_v21_system_feedback.py (gap lines and branches)."""

import json
import runpy

import pytest

from tests.coverage_waves.lane_b._l2_loader import load

mod = load("abacus_v21_system_feedback.py", name="abn_w6_abacus_v21_system_feedback")

REPORTS = {
    "smoke": (
        "ABACUS_V21_SMOKE_TEST_OUTPUT",
        "abacus_v21_smoke_test_report.json",
    ),
    "dry": ("ABACUS_V21_DRY_RUN_OUTPUT", "abacus_v21_dry_run_report.json"),
    "bridge": (
        "ABACUS_V21_BRIDGE_VALIDATION_OUTPUT",
        "abacus_v21_bridge_validation_report.json",
    ),
    "knowledge": (
        "ABACUS_V21_KNOWLEDGE_BASE",
        "abacus_v21_knowledge_preservation_report.json",
    ),
}


def _summary(total, ok, failed, status="PASS"):
    return dict(total_tests=total, passed=ok, failed=failed, status=status)


def _write(root, key, data):
    folder, name = REPORTS[key]
    path = root / folder
    path.mkdir(exist_ok=True)
    (path / name).write_text(json.dumps(data), encoding="utf-8")


@pytest.fixture
def gen(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return mod.SystemFeedbackGenerator()


def test_log_uses_colour_and_unknown_level_default(gen, capsys):
    gen.log("hi", "SUCCESS")
    gen.log("plain", "ODD")
    out = capsys.readouterr().out
    assert "[SUCCESS] \033[92mhi" in out
    assert "[ODD] \033[0mplain" in out


def test_collect_test_results_empty(gen):
    res = gen.collect_test_results()
    assert res == {
        "stage_1_3_smoke": {},
        "stage_1_4_dry_run": {},
        "stage_1_5_bridge": {},
        "stage_1_6_knowledge": {},
    }


def test_collect_test_results_reads_all_reports(gen, tmp_path):
    for i, key in enumerate(REPORTS):
        _write(tmp_path, key, {"marker": i})
    res = gen.collect_test_results()
    assert res["stage_1_3_smoke"] == {"marker": 0}
    assert res["stage_1_4_dry_run"] == {"marker": 1}
    assert res["stage_1_5_bridge"] == {"marker": 2}
    assert res["stage_1_6_knowledge"] == {"marker": 3}


@pytest.mark.parametrize(
    "ok, expected",
    [(10, "EXCELLENT"), (9, "GOOD"), (8, "FAIR"), (5, "POOR")],
)
def test_analyze_system_health_grades(gen, ok, expected):
    results = {"a": {"summary": _summary(10, ok, 10 - ok)}, "b": {}}
    health = gen.analyze_system_health(results)
    assert health["health_status"] == expected
    assert health["total_tests"] == 10
    assert health["total_failed"] == 10 - ok
    assert health["stages_completed"] == 1
    assert health["stages_total"] == 4


def test_analyze_system_health_task_fallback_and_zero(gen):
    results = {"k": {"summary": {"total_tasks": 4, "completed": 4}}}
    health = gen.analyze_system_health(results)
    assert health["total_tests"] == 4
    assert health["total_passed"] == 4
    assert health["pass_rate"] == 100
    empty = gen.analyze_system_health({"x": {}})
    assert empty["pass_rate"] == 0
    assert empty["health_status"] == "POOR"


def test_generate_recommendations_full_branches(gen):
    results = {
        "stage_1_3_smoke": {
            "tests": [
                {"validation": {"dry_run_tests": 6}},
                {"validation": {"dry_run_tests": 12}},
                {"validation": {}},
                {},
            ]
        },
        "stage_1_5_bridge": {
            "tests": [
                {"test_id": "1.5.1", "bridge_score": 30},
                {"test_id": "1.5.1", "bridge_score": 90},
                {"test_id": "1.5.1"},
                {"test_id": "1.5.2", "bridge_score": 10},
            ]
        },
    }
    recs = gen.generate_recommendations(results, {"pass_rate": 100})
    titles = [r["title"] for r in recs]
    assert titles == [
        "Ready for POST-CD Phase",
        "Expand DOW Test Coverage",
        "Improve DMAIC-DOW Bridge Coverage",
        "Establish Production Monitoring",
        "Maintain Knowledge Base",
    ]
    assert "6" in recs[1]["description"]
    assert "30%" in recs[2]["description"]


def test_generate_recommendations_minimal(gen):
    recs = gen.generate_recommendations({}, {"pass_rate": 50})
    assert [r["category"] for r in recs] == ["MONITORING", "DOCUMENTATION"]


def test_generate_stage_summary_fallbacks(gen):
    results = {
        "stage_1_3_smoke": {"summary": _summary(6, 6, 0)},
        "stage_1_4_dry_run": {
            "summary": {"total_tasks": 3, "completed": 2, "success_rate": 66.0}
        },
        "stage_1_5_bridge": {},
        "stage_1_6_knowledge": {"other": 1},
        "unknown_stage": {"summary": {}},
    }
    summaries = gen.generate_stage_summary(results)
    assert [s["stage"] for s in summaries] == ["1.3", "1.4", "1.6"]
    assert summaries[0]["status"] == "PASS"
    assert summaries[1]["tests"] == 3
    assert summaries[1]["passed"] == 2
    assert summaries[1]["pass_rate"] == 66.0
    assert summaries[2]["status"] == "UNKNOWN"
    assert summaries[2]["tests"] == 0


def test_generate_feedback_report_all_pass(gen, tmp_path, capsys):
    smoke = {"summary": _summary(6, 6, 0), "tests": []}
    smoke["summary"]["pass_rate"] = 100.0
    _write(tmp_path, "smoke", smoke)
    dry = {
        "summary": _summary(4, 4, 0, status="COMPLETE"),
        "tests": [
            {"test_id": "1.4.4", "metrics": {"memory_mb": 42}},
            {"test_id": "1.4.4"},
            {"test_id": "1.4.1", "metrics": {}},
        ],
    }
    dry["summary"]["pass_rate"] = 100.0
    _write(tmp_path, "dry", dry)
    bridge = {
        "summary": _summary(2, 2, 0),
        "tests": [
            {"test_id": "1.5.4", "total_artifacts": 17, "directories_exist": 3},
            {"test_id": "1.5.4"},
            {"test_id": "1.5.2"},
        ],
    }
    bridge["summary"]["pass_rate"] = 100.0
    _write(tmp_path, "bridge", bridge)
    report = gen.generate_feedback_report()
    out = capsys.readouterr().out
    assert report["system_health"]["health_status"] == "EXCELLENT"
    assert report["system_health"]["total_tests"] == 12
    assert "Memory Usage: 42 MB" in out
    assert "Execution Time: N/A seconds" in out
    assert "Total Artifacts: 17" in out
    out_dir = tmp_path / "ABACUS_V21_SYSTEM_FEEDBACK"
    saved = json.loads(
        (out_dir / "ABACUS_V21_SYSTEM_FEEDBACK_REPORT.json").read_text(encoding="utf-8")
    )
    assert saved["report_metadata"]["phase"] == "PRE-CD"
    md = (out_dir / "ABACUS_V21_SYSTEM_FEEDBACK_REPORT.md").read_text(encoding="utf-8")
    assert "The system is ready for production" in md
    assert "### Stage 1.4: Dry-Run Tests" in md
    assert "Ready for POST-CD Phase" in md


def test_generate_feedback_report_failures_and_low_priority(
    gen, tmp_path, monkeypatch, capsys
):
    smoke = {"summary": _summary(10, 7, 3, status="FAIL")}
    smoke["summary"]["pass_rate"] = 70.0
    _write(tmp_path, "smoke", smoke)
    low = dict(priority="LOW", category="C", title="Tidy", description="d", action="a")
    monkeypatch.setattr(gen, "generate_recommendations", lambda r, h: [low])
    report = gen.generate_feedback_report()
    out = capsys.readouterr().out
    assert report["system_health"]["health_status"] == "POOR"
    assert "Tests Failed: 3" in out
    assert "[INFO] \033[0m\n1. [LOW] Tidy" in out
    md = (
        tmp_path / "ABACUS_V21_SYSTEM_FEEDBACK" / "ABACUS_V21_SYSTEM_FEEDBACK_REPORT.md"
    )
    text = md.read_text(encoding="utf-8")
    assert "The system is nearly ready for production" in text
    assert "### 1. [LOW] Tidy" in text


def test_main_block_exits_zero(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit) as exc:
        runpy.run_path(mod.__file__, run_name="__main__")
    assert exc.value.code == 0
    assert "SYSTEM HEALTH OVERVIEW" in capsys.readouterr().out
    assert (tmp_path / "ABACUS_V21_SYSTEM_FEEDBACK").is_dir()
