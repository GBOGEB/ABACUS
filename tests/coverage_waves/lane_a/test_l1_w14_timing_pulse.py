"""Lane A wave 14: mission_control_lite.timing_pulse reconcile, measure and CLI."""

import json
import sys
from types import SimpleNamespace

import pytest

from mission_control_lite import timing_pulse as tp

SHA = "c" * 40


def _run(**over):
    run = {
        "id": 11,
        "status": "completed",
        "head_sha": SHA,
        "created_at": "2026-01-01T00:00:00Z",
        "run_started_at": "2026-01-01T00:00:10Z",
        "updated_at": "2026-01-01T00:01:40Z",
    }
    run.update(over)
    return run


def _job(**over):
    job = {
        "id": 22,
        "run_id": 11,
        "status": "completed",
        "started_at": "2026-01-01T00:00:20Z",
        "completed_at": "2026-01-01T00:01:30Z",
        "steps": [
            {
                "name": "a",
                "started_at": "2026-01-01T00:00:20Z",
                "completed_at": "2026-01-01T00:00:50Z",
                "conclusion": "success",
            },
            {"name": "skipped", "started_at": None, "completed_at": None},
            {"name": "half", "started_at": "2026-01-01T00:00:50Z"},
        ],
    }
    job.update(over)
    return job


def test_instant_and_seconds_errors():
    with pytest.raises(ValueError, match="missing"):
        tp._instant(None)
    with pytest.raises(ValueError, match="invalid timestamp"):
        tp._instant("not a time")
    with pytest.raises(ValueError, match="naive"):
        tp._seconds("2026-01-01T00:00:00", "2026-01-01T00:00:01Z")
    with pytest.raises(ValueError, match="non-monotone"):
        tp._seconds("2026-01-01T00:00:05Z", "2026-01-01T00:00:01Z")
    assert tp._seconds("2026-01-01T00:00:00+00:00", "2026-01-01T00:00:01.5Z") == 1.5


def test_completed_run_metrics_happy():
    out = tp.completed_run_metrics(_run(), _job())
    assert out["schema"] == tp.SCHEMA
    assert out["run_id"] == "11" and out["job_id"] == "22"
    assert out["wall_seconds"] == 100.0
    assert out["run_queue_seconds"] == 10.0
    assert out["run_to_job_seconds"] == 10.0
    assert out["job_seconds"] == 70.0
    assert out["finalization_seconds"] == 10.0
    assert out["non_job_seconds"] == 30.0
    assert out["runner_fraction"] == 0.7
    assert out["steps"] == [{"name": "a", "seconds": 30.0, "conclusion": "success"}]
    assert out["merge_admission"] == "HOLD"


def test_zero_wall_runner_fraction_none():
    t = "2026-01-01T00:00:00Z"
    run = _run(created_at=t, run_started_at=t, updated_at=t)
    job = _job(started_at=t, completed_at=t, steps=[])
    assert tp.completed_run_metrics(run, job)["runner_fraction"] is None


@pytest.mark.parametrize(
    "run,job,msg",
    [
        (_run(status="in_progress"), _job(), "nonterminal"),
        (_run(), _job(status="queued"), "nonterminal"),
        (_run(), _job(run_id=99), "provenance"),
        (_run(head_sha="XYZ"), _job(), "SHA"),
        (_run(head_sha=None), _job(), "SHA"),
    ],
)
def test_completed_run_metrics_rejects(run, job, msg):
    with pytest.raises(ValueError, match=msg):
        tp.completed_run_metrics(run, job)


def test_timeline_must_reconcile(monkeypatch):
    calls = iter([100.0, 10.0, 10.0, 70.0, 20.0])
    monkeypatch.setattr(tp, "_seconds", lambda a, b: next(calls))
    with pytest.raises(ValueError, match="reconcile"):
        tp.completed_run_metrics(_run(), _job())


def test_measure_appends_and_rejects_duplicates(tmp_path, monkeypatch):
    seen = []

    def fake_run(cmd, check):
        seen.append(cmd)
        return SimpleNamespace(returncode=3)

    monkeypatch.setattr("subprocess.run", fake_run)
    out = tmp_path / "sub" / "m.json"
    assert tp.measure(out, "unit", ["echo", "x"]) == 3
    rows = json.loads(out.read_text())
    assert rows[0]["phase"] == "unit" and rows[0]["exit_code"] == 3
    assert seen == [["echo", "x"]]
    with pytest.raises(ValueError, match="duplicate"):
        tp.measure(out, "unit", ["echo"])


def test_measure_oserror_and_validation(tmp_path, monkeypatch):
    def broken(cmd, check):
        raise OSError("no such exe")

    monkeypatch.setattr("subprocess.run", broken)
    out = tmp_path / "m.json"
    assert tp.measure(out, "lint", ["missing-tool"]) == 127
    with pytest.raises(ValueError, match="required"):
        tp.measure(out, "", ["x"])
    with pytest.raises(ValueError, match="required"):
        tp.measure(out, "p", [])
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"not": "a list"}))
    with pytest.raises(ValueError, match="invalid metrics"):
        tp.measure(bad, "p", ["x"])
    bad.write_text(json.dumps(["str"]))
    with pytest.raises(ValueError, match="invalid metrics"):
        tp.measure(bad, "p", ["x"])


def test_main_measure_strips_separator(tmp_path, monkeypatch):
    seen = []

    def fake_measure(output, phase, cmd):
        seen.append((output.name, phase, cmd))
        return 4

    monkeypatch.setattr(tp, "measure", fake_measure)
    out = str(tmp_path / "o.json")
    argv = ["tp", "measure", "--output", out, "--phase", "p", "--", "run", "x"]
    monkeypatch.setattr(sys, "argv", argv)
    with pytest.raises(SystemExit) as exc:
        tp.main()
    assert exc.value.code == 4
    argv = ["tp", "measure", "--output", out, "--phase", "q", "go"]
    monkeypatch.setattr(sys, "argv", argv)
    with pytest.raises(SystemExit):
        tp.main()
    assert seen == [("o.json", "p", ["run", "x"]), ("o.json", "q", ["go"])]


def test_main_reconcile(tmp_path, monkeypatch, capsys):
    run_json = tmp_path / "run.json"
    job_json = tmp_path / "job.json"
    out = tmp_path / "out.json"
    run_json.write_text(json.dumps(_run()))
    job_json.write_text(json.dumps(_job()))
    argv = [
        "tp",
        "reconcile",
        "--run-json",
        str(run_json),
        "--job-json",
        str(job_json),
        "--output",
        str(out),
    ]
    monkeypatch.setattr(sys, "argv", argv)
    tp.main()
    printed = json.loads(capsys.readouterr().out)
    assert printed == {
        "source_sha": SHA,
        "wall_seconds": 100.0,
        "non_job_seconds": 30.0,
        "job_seconds": 70.0,
    }
    assert json.loads(out.read_text())["run_id"] == "11"
