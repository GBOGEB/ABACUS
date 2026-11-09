"""Gap tests for abacus_v21_bridge_validation_tests.py (bridge checks, summary)."""

import json
import runpy

import pytest

from tests.coverage_waves.lane_b._l2_loader import load

# Accessed only through ``mod`` so pytest never collects the suite's own
# ``test_*`` methods from this namespace.
mod = load("abacus_v21_bridge_validation_tests.py", name="abn_w6_bridge_validation")
MOD_PATH = mod.__file__
REPORT_NAME = "abacus_v21_bridge_validation_report.json"


def _raise_path(*_args, **_kwargs):
    raise RuntimeError("path layer down")


@pytest.fixture
def suite(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return mod.BridgeValidationSuite()


def _read_report(suite):
    with open(suite.output_dir / REPORT_NAME, encoding="utf-8") as fh:
        return json.load(fh)


def test_dmaic_dow_missing_tracker_fails(suite, tmp_path, capsys):
    (tmp_path / "DMAIC_V3_OUTPUT").mkdir()
    assert suite.test_dmaic_dow_bridge() is False
    assert suite.results[-1]["message"] == "DOW tracker not found"
    assert suite.failed == 1
    assert "[ERROR]" in capsys.readouterr().out


def test_dmaic_dow_counts_phase_connections(suite, tmp_path):
    out = tmp_path / "DMAIC_V3_OUTPUT"
    for phase in ("Define", "Measure"):
        (out / phase).mkdir(parents=True)
    tracker = tmp_path / "DOW_IMPLEMENTATION_TRACKER.json"
    tracker.write_text(json.dumps({"stages": {"s1": {}}}), encoding="utf-8")
    assert suite.test_dmaic_dow_bridge() is True
    entry = suite.results[-1]
    assert entry["connections"] == 2
    assert entry["bridge_score"] == 40.0
    assert entry["dow_stages"] == 1


def test_recursive_temporal_creates_dirs_and_counts_markdown(suite, tmp_path, capsys):
    assert suite.test_recursive_temporal_bridge() is True
    assert (tmp_path / "ABACUS_V21_MIGRATION_OUTPUT").is_dir()
    assert (tmp_path / "ABACUS_SESSION_ANALYSIS").is_dir()
    assert suite.results[-1]["total_artifacts"] == 0
    assert "Created migration output directory" in capsys.readouterr().out


def test_recursive_temporal_with_existing_artifacts(suite, tmp_path, capsys):
    mig = tmp_path / "ABACUS_V21_MIGRATION_OUTPUT"
    ses = tmp_path / "ABACUS_SESSION_ANALYSIS"
    mig.mkdir()
    ses.mkdir()
    (mig / "a.md").write_bytes(b"x")
    (ses / "b.md").write_bytes(b"x")
    (ses / "c.txt").write_bytes(b"x")
    assert suite.test_recursive_temporal_bridge() is True
    entry = suite.results[-1]
    assert entry["migration_artifacts"] == 1
    assert entry["session_artifacts"] == 1
    assert entry["bridge_active"] is True
    assert "Created" not in capsys.readouterr().out


def test_recursive_temporal_exception_records_fail(suite, monkeypatch):
    monkeypatch.setattr(mod, "Path", _raise_path)
    assert suite.test_recursive_temporal_bridge() is False
    assert suite.results[-1]["message"] == "path layer down"


def test_state_configuration_none_present(suite):
    assert suite.test_state_configuration_bridge() is True
    entry = suite.results[-1]
    assert entry["configs_found"] == 0
    assert entry["bridge_score"] == 0.0


def test_state_configuration_valid_json_and_yaml(suite, tmp_path):
    (tmp_path / "DOW_IMPLEMENTATION_TRACKER.json").write_text("{}", encoding="utf-8")
    (tmp_path / "ABACUS_V21_PROGRESS_TRACKER.yaml").write_text("a: 1", encoding="utf-8")
    assert suite.test_state_configuration_bridge() is True
    entry = suite.results[-1]
    assert entry["configs_found"] == 2
    assert entry["configs_valid"] == 2
    assert entry["bridge_score"] == 100.0


def test_state_configuration_invalid_json_warns(suite, tmp_path, capsys):
    (tmp_path / "DOW_IMPLEMENTATION_TRACKER.json").write_text("{bad", encoding="utf-8")
    assert suite.test_state_configuration_bridge() is True
    entry = suite.results[-1]
    assert entry["configs_found"] == 1
    assert entry["configs_valid"] == 0
    assert "[WARNING]" in capsys.readouterr().out


def test_state_configuration_exception_records_fail(suite, monkeypatch):
    monkeypatch.setattr(mod, "Path", _raise_path)
    assert suite.test_state_configuration_bridge() is False
    assert suite.results[-1]["status"] == "FAIL"


def test_output_artifact_counts_existing_dirs(suite, tmp_path):
    smoke = tmp_path / "SPRINT_EXECUTION"
    smoke.mkdir()
    (smoke / "one").write_bytes(b"1")
    (smoke / "two").write_bytes(b"2")
    assert suite.test_output_artifact_bridge() is True
    entry = suite.results[-1]
    assert entry["directories_exist"] == 1
    assert entry["total_artifacts"] == 2
    assert entry["bridge_score"] == pytest.approx(100 / 6)


def test_output_artifact_exception_records_fail(suite, monkeypatch):
    monkeypatch.setattr(mod, "Path", _raise_path)
    assert suite.test_output_artifact_bridge() is False
    assert suite.failed == 1


def test_run_all_tests_all_pass(suite, tmp_path, capsys):
    (tmp_path / "DMAIC_V3_OUTPUT" / "Define").mkdir(parents=True)
    (tmp_path / "DOW_IMPLEMENTATION_TRACKER.json").write_text(
        json.dumps({"stages": {"a": 1}}), encoding="utf-8"
    )
    assert suite.run_all_tests() is True
    assert "ALL BRIDGES VALIDATED" in capsys.readouterr().out
    summary = _read_report(suite)["summary"]
    assert summary["total_tests"] == 4
    assert summary["pass_rate"] == 100.0
    assert summary["status"] == "PASS"


def test_run_all_tests_with_failure(suite, capsys):
    assert suite.run_all_tests() is False
    out = capsys.readouterr().out
    assert "SOME BRIDGES FAILED" in out
    report = _read_report(suite)
    assert report["summary"]["failed"] == 1
    assert report["summary"]["pass_rate"] == 75.0
    assert report["tests"][0]["message"] == "DMAIC output directory not found"


def test_run_all_tests_no_tests_zero_rate(suite, monkeypatch):
    for name in (
        "test_dmaic_dow_bridge",
        "test_recursive_temporal_bridge",
        "test_state_configuration_bridge",
        "test_output_artifact_bridge",
    ):
        monkeypatch.setattr(suite, name, lambda: None)
    assert suite.run_all_tests() is True
    assert _read_report(suite)["summary"]["pass_rate"] == 0


def test_main_entrypoint_exits_nonzero_without_inputs(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit) as excinfo:
        runpy.run_path(MOD_PATH, run_name="__main__")
    assert excinfo.value.code == 1
    assert "BRIDGE VALIDATION SUMMARY" in capsys.readouterr().out
