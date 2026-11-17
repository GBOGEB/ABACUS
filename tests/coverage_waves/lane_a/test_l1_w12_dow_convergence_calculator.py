"""Lane A wave 12: DOW convergence metrics calculator agent."""

import json
import sys

import pytest

from tests.coverage_waves.lane_a._load import load

calc_mod = load("DMAIC_V3/local_mcp/agents/dow_convergence_calculator.py")


def _write_json(path, data):
    path.write_bytes(json.dumps(data).encode("utf-8"))
    return path


@pytest.fixture
def calc():
    return calc_mod.DOWConvergenceCalculator()


def test_init_defaults(calc):
    assert calc.config_path == "orchestrator_config.yaml"
    assert calc_mod.DOWConvergenceCalculator("x.yaml").config_path == "x.yaml"


def test_quality_score_components(calc):
    assert calc._calculate_quality_score({}) == 0.0
    three = {"metadata": 1, "recursive_hooks": 1, "knowledge_gain": 1}
    assert calc._calculate_quality_score(three) == pytest.approx(0.6)
    eleven = {"k" + str(i): i for i in range(11)}
    assert calc._calculate_quality_score(eleven) == pytest.approx(0.2)
    many = {"k" + str(i): i for i in range(21)}
    assert calc._calculate_quality_score(many) == pytest.approx(0.3)
    big = {"blob": "x" * 10001}
    assert calc._calculate_quality_score(big) == pytest.approx(0.1)
    full = dict(three)
    full.update(many)
    full["blob"] = "y" * 10001
    assert calc._calculate_quality_score(full) == 1.0


def test_completeness_fraction(calc):
    assert calc._calculate_completeness({}) == 0.0
    assert calc._calculate_completeness({"metadata": 1, "knowledge_gain": 2}) == 0.5


def test_improvement_and_status(calc):
    assert calc._calculate_improvement({"metadata": 1}, None) == 0.0
    assert calc._calculate_improvement({"metadata": 1}, {}) == 0.0
    imp = calc._calculate_improvement({"metadata": 1}, {"other": 1})
    assert imp == pytest.approx(0.2)
    assert calc._determine_convergence_status(0.5) == "improving"
    assert calc._determine_convergence_status(0.05) == "stable"
    assert calc._determine_convergence_status(0) == "converged"
    assert calc._determine_convergence_status(-0.2) == "degrading"


def test_calculate_convergence_writes_metrics(tmp_path, calc):
    current = _write_json(
        tmp_path / "phase1.json",
        {"metadata": {"iteration": "3", "phase": "phase1"}, "payload": [1, 2]},
    )
    previous = _write_json(tmp_path / "prev.json", {"metadata": {}})
    result = calc.calculate_convergence(current, previous)
    assert result["status"] == "success"
    assert result["file"] == str(current)
    metrics = result["metrics"]
    assert metrics["completeness"] == 1.0
    assert metrics["improvement_from_previous"] == pytest.approx(0.4)
    assert metrics["convergence_status"] == "improving"
    saved = json.loads(current.read_text(encoding="utf-8"))
    assert saved["convergence_metrics"]["quality_score"] == metrics["quality_score"]
    assert saved["metadata"]["iteration"] == "3"
    assert saved["lineage"]["iteration_lineage"] == [0, 1, 2, 3]
    assert len(saved["idempotency"]["output_hash"]) == 64
    assert saved["payload"] == [1, 2]


def test_calculate_convergence_without_previous_is_converged(tmp_path, calc):
    current = _write_json(tmp_path / "a.json", {})
    result = calc.calculate_convergence(current, tmp_path / "missing.json")
    assert result["metrics"]["convergence_status"] == "converged"
    saved = json.loads(current.read_text(encoding="utf-8"))
    assert saved["metadata"]["generator"] == "DOWConvergenceCalculator"
    assert saved["metadata"]["phase"] == "unknown"


def test_calculate_convergence_reports_errors(tmp_path, calc):
    broken = tmp_path / "broken.json"
    broken.write_bytes(b"{nope")
    result = calc.calculate_convergence(broken)
    assert result["status"] == "error"
    assert result["error"]
    missing = calc.calculate_convergence(tmp_path / "absent.json")
    assert missing["status"] == "error"


def test_calculate_batch_counts(tmp_path, calc):
    good = _write_json(tmp_path / "good.json", {})
    bad = tmp_path / "bad.json"
    bad.write_bytes(b"[")
    prev_dir = tmp_path / "prev"
    prev_dir.mkdir()
    _write_json(prev_dir / "good.json", {"metadata": {}})
    summary = calc.calculate_batch([good, bad], prev_dir)
    assert summary["total"] == 2
    assert summary["success"] == 1
    assert summary["failed"] == 1
    first = summary["results"][0]["metrics"]
    assert first["convergence_status"] == "improving"
    no_prev = calc.calculate_batch([good], tmp_path / "nowhere")
    assert no_prev["results"][0]["metrics"]["improvement_from_previous"] == 0.0


def _run_main(monkeypatch, *args):
    monkeypatch.setattr(sys, "argv", ["dow_convergence_calculator.py", *args])
    return calc_mod.main()


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
    target = tmp_path / "out"
    target.mkdir()
    _write_json(target / "p.json", {})
    prev = tmp_path / "prev"
    prev.mkdir()
    assert (
        _run_main(monkeypatch, "--target", str(target), "--previous", str(prev)) is None
    )
    out = capsys.readouterr().out
    assert "Success: 1" in out
    (target / "q.json").write_bytes(b"{bad")
    with pytest.raises(SystemExit) as exc:
        _run_main(monkeypatch, "--target", str(target))
    assert exc.value.code == 1
    assert "Some files failed" in capsys.readouterr().out


def check_production_defect_completeness_always_full(tmp_path):
    # Pins a production_defect (dow_convergence_calculator.py:47-49): metrics are
    # computed after ensure_contract() pads the payload with every required field,
    # so completeness is always 1.0 and an unchanged artifact compared with its own
    # raw previous version is reported as "improving". This check will fail once
    # the metrics are computed on the original input.
    current = _write_json(tmp_path / "same.json", {"x": 1})
    previous = _write_json(tmp_path / "prev.json", {"x": 1})
    result = calc_mod.DOWConvergenceCalculator().calculate_convergence(
        current, previous
    )
    assert result["metrics"]["completeness"] == 1.0
    assert result["metrics"]["convergence_status"] == "improving"
