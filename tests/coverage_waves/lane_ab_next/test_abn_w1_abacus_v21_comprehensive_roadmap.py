"""Behaviour tests for abacus_v21_comprehensive_roadmap.py."""

import json
import runpy

from tests.coverage_waves.lane_b._l2_loader import REPO_ROOT, load

mod = load("abacus_v21_comprehensive_roadmap.py", name="abn_comprehensive_roadmap")


class _FixedNow:
    def isoformat(self):
        return "2031-05-06T07:08:09"


class _FakeDatetime:
    @staticmethod
    def now():
        return _FixedNow()


def _run(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(mod, "datetime", _FakeDatetime)
    assert mod.generate_comprehensive_roadmap() is None
    return tmp_path / "ABACUS_V21_ROADMAP"


def test_roadmap_json_structure(tmp_path, monkeypatch):
    out_dir = _run(tmp_path, monkeypatch)

    data = json.loads((out_dir / "COMPREHENSIVE_ROADMAP.json").read_bytes())
    assert data["version"] == "2.1.0"
    assert data["timestamp"] == "2031-05-06T07:08:09"
    assert data["current_status"]["overall_progress"] == "65%"
    assert data["current_status"]["current_phase"] == "POST-CD Stage 2.6"

    phases = data["phases"]
    assert len(phases) == 6
    assert phases[0]["status"] == "COMPLETED"
    assert phases[0]["progress"] == "100%"
    assert all(s["status"] == "COMPLETED" for s in phases[0]["stages"])
    assert phases[1]["status"] == "IN_PROGRESS"
    assert [p["phase"].split(":")[0] for p in phases] == [
        "PHASE 1",
        "PHASE 2",
        "PHASE 3",
        "PHASE 4",
        "PHASE 5",
        "PHASE 6",
    ]

    matrix = data["priority_matrix"]
    assert {"HIGH", "MEDIUM", "LOW"} <= set(matrix)
    assert "Stage 5.1: Multi-Tenancy" in matrix["LOW"]["items"]

    steps = data["immediate_next_steps"]
    assert [s["step"] for s in steps] == list(range(1, len(steps) + 1))
    assert steps[0]["priority"] == "CRITICAL"

    assert set(data["resource_requirements"]) == {
        "Phase 2 (Remaining)",
        "Phase 3",
        "Phase 4",
        "Phase 5",
    }
    assert data["success_metrics"]["Phase 2"]["zero_downtime"] is True


def test_roadmap_markdown_and_console(tmp_path, monkeypatch, capsys):
    out_dir = _run(tmp_path, monkeypatch)

    report = (out_dir / "COMPREHENSIVE_ROADMAP.md").read_text(encoding="utf-8")
    assert report.startswith("# ABACUS v2.1 - Comprehensive Phase Roadmap")
    assert "**Generated**: 2031-05-06T07:08:09" in report
    assert "*Roadmap generated on 2031-05-06T07:08:09*" in report

    out = capsys.readouterr().out
    assert "COMPREHENSIVE ROADMAP GENERATED" in out
    assert "COMPREHENSIVE_ROADMAP.json" in out
    assert "COMPREHENSIVE_ROADMAP.md" in out
    assert "Total Phases: 6" in out
    assert "CRITICAL: Stage 2.6 - Production Deployment" in out


def test_roadmap_overwrites_existing_outputs(tmp_path, monkeypatch):
    out_dir = tmp_path / "ABACUS_V21_ROADMAP"
    out_dir.mkdir()
    (out_dir / "COMPREHENSIVE_ROADMAP.json").write_bytes(b"{}")

    _run(tmp_path, monkeypatch)

    data = json.loads((out_dir / "COMPREHENSIVE_ROADMAP.json").read_bytes())
    assert data["version"] == "2.1.0"


def test_main_block_generates_roadmap(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)

    runpy.run_path(
        str(REPO_ROOT / "abacus_v21_comprehensive_roadmap.py"), run_name="__main__"
    )

    assert (tmp_path / "ABACUS_V21_ROADMAP" / "COMPREHENSIVE_ROADMAP.md").is_file()
    assert "Immediate Priorities" in capsys.readouterr().out
