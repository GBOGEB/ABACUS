"""Lane A wave 12: DOW metadata injection agent."""

import json
import sys

import pytest

from tests.coverage_waves.lane_a._load import load

inj_mod = load("DMAIC_V3/local_mcp/agents/dow_metadata_injector.py")


def _write_json(path, data):
    path.write_bytes(json.dumps(data).encode("utf-8"))
    return path


@pytest.fixture
def injector():
    return inj_mod.DOWMetadataInjector()


def test_init_defaults(injector):
    assert injector.config_path == "orchestrator_config.yaml"


@pytest.mark.parametrize(
    "stem,expected",
    [
        ("out_phase1_define", "phase1"),
        ("phase2", "phase2"),
        ("x_phase3", "phase3"),
        ("phase4_improve", "phase4"),
        ("phase5_control", "phase5"),
        ("phase6_knowledge", "phase6"),
        ("summary", "unknown"),
    ],
)
def test_extract_phase(tmp_path, injector, stem, expected):
    assert injector._extract_phase(tmp_path / (stem + ".json")) == expected


def test_inject_metadata_adds_contract(tmp_path, injector):
    path = _write_json(tmp_path / "phase2_measure.json", {"value": 7})
    result = injector.inject_metadata(path, 2, "phase2")
    assert result == {"status": "success", "file": str(path)}
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["value"] == 7
    assert data["metadata"]["iteration"] == 2
    assert data["metadata"]["phase"] == "phase2"
    assert data["metadata"]["version"] == "3.3.0"
    assert data["lineage"]["artifact_path"] == str(path)
    assert data["lineage"]["iteration_lineage"] == [0, 1, 2]
    assert len(data["idempotency"]["input_hash"]) == 64
    assert len(data["idempotency"]["output_hash"]) == 64
    assert data["idempotency"]["input_hash"] != data["idempotency"]["output_hash"]


def test_inject_metadata_overrides_stale_hash(tmp_path, injector):
    path = _write_json(
        tmp_path / "a.json",
        {"idempotency": {"input_hash": "stale"}, "lineage": {"artifact_path": "old"}},
    )
    injector.inject_metadata(path, 0, "unknown")
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["idempotency"]["input_hash"] != "stale"
    assert data["lineage"]["artifact_path"] == str(path)


def test_inject_metadata_reports_errors(tmp_path, injector):
    bad = tmp_path / "bad.json"
    bad.write_bytes(b"{oops")
    result = injector.inject_metadata(bad, 1, "phase1")
    assert result["status"] == "error"
    assert result["error"]


def test_inject_batch_counts(tmp_path, injector):
    good = _write_json(tmp_path / "phase3_analyze.json", {})
    bad = tmp_path / "phase4.json"
    bad.write_bytes(b"[")
    summary = injector.inject_batch([good, bad], iteration=5)
    assert summary["total"] == 2
    assert summary["success"] == 1
    assert summary["failed"] == 1
    data = json.loads(good.read_text(encoding="utf-8"))
    assert data["metadata"]["phase"] == "phase3"
    assert data["metadata"]["iteration"] == 5


def _run_main(monkeypatch, *args):
    monkeypatch.setattr(sys, "argv", ["dow_metadata_injector.py", *args])
    return inj_mod.main()


def test_main_missing_target_exits_one(tmp_path, monkeypatch, capsys):
    with pytest.raises(SystemExit) as exc:
        _run_main(monkeypatch, "--target", str(tmp_path / "none"))
    assert exc.value.code == 1
    assert "Target directory not found" in capsys.readouterr().out


def test_main_no_json_exits_zero(tmp_path, monkeypatch, capsys):
    with pytest.raises(SystemExit) as exc:
        _run_main(monkeypatch, "--target", str(tmp_path), "--verbose")
    assert exc.value.code == 0
    assert "No JSON files found" in capsys.readouterr().out


def test_main_success_and_failure(tmp_path, monkeypatch, capsys):
    _write_json(tmp_path / "phase1.json", {})
    assert _run_main(monkeypatch, "--target", str(tmp_path), "--iteration", "3") is None
    assert "Success: 1" in capsys.readouterr().out
    data = json.loads((tmp_path / "phase1.json").read_text(encoding="utf-8"))
    assert data["metadata"]["iteration"] == 3
    (tmp_path / "phase2.json").write_bytes(b"{bad")
    with pytest.raises(SystemExit) as exc:
        _run_main(monkeypatch, "--target", str(tmp_path))
    assert exc.value.code == 1
    assert "Some files failed" in capsys.readouterr().out


def check_production_defect_generator_name_doubles_phase_prefix(tmp_path):
    # Pins a production_defect (dow_metadata_injector.py:38): the generator name is
    # built as f"phase{phase}_generator.py" while phase is already "phaseN"
    # (from _extract_phase), giving "phasephase1_generator.py". This check will
    # fail once the defect is fixed.
    path = _write_json(tmp_path / "phase1_define.json", {})
    inj_mod.DOWMetadataInjector().inject_batch([path], iteration=1)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["metadata"]["generator"] == "phasephase1_generator.py"
