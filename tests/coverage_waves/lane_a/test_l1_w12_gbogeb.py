"""Lane A wave 12: core/gbogeb/gbogeb.py metric store and compliance checker."""

import json

from core.gbogeb import gbogeb as gmod


def _engine(tmp_path):
    return gmod.GBOGEB(workspace=str(tmp_path / "nested" / "ws"))


def test_init_creates_nested_workspace(tmp_path, capsys):
    engine = _engine(tmp_path)
    assert engine.workspace.is_dir()
    assert "Initialized workspace" in capsys.readouterr().out
    expected = dict(
        total_metrics=0,
        agents_tracked=[],
        compliance_checks=0,
        compliance_pass=0,
        compliance_fail=0,
    )
    assert engine.get_summary() == expected


def test_collect_metric_records_entries(tmp_path, capsys):
    engine = _engine(tmp_path)
    engine.collect_metric("phase2", "files", 3, tags={"k": "v"})
    engine.collect_metric("phase1", "files", 4)
    assert "metric phase1.files=4" in capsys.readouterr().out
    summary = engine.get_summary()
    assert summary["total_metrics"] == 2
    assert summary["agents_tracked"] == ["phase1", "phase2"]
    assert engine._metrics[0]["tags"] == {"k": "v"}
    assert engine._metrics[1]["tags"] == {}


def test_check_compliance_pass_fail_and_exception(tmp_path, capsys):
    engine = _engine(tmp_path)

    def boom():
        raise RuntimeError("bad")

    assert engine.check_compliance("r1", lambda: 1, severity="critical") is True
    assert engine.check_compliance("r2", lambda: []) is False
    assert engine.check_compliance("r3", boom) is False
    out = capsys.readouterr().out
    assert "compliance 'r3' raised exception: bad" in out
    assert "'r1': PASS (severity=critical)" in out
    statuses = [e["status"] for e in engine._compliance_log]
    assert statuses == ["PASS", "FAIL", "FAIL"]
    summary = engine.get_summary()
    assert summary["compliance_pass"] == 1
    assert summary["compliance_fail"] == 2


def test_export_metrics_writes_payload(tmp_path):
    engine = _engine(tmp_path)
    engine.collect_metric("a", "m", 1)
    engine.check_compliance("ok", lambda: True)
    engine.check_compliance("no", lambda: False)
    path = engine.export_metrics("out.json")
    assert path == engine.workspace / "out.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["start_time"] == engine._start_time
    expected = dict(
        total_metrics=1,
        total_compliance_checks=2,
        compliance_pass=1,
        compliance_fail=1,
    )
    assert payload["summary"] == expected
    assert payload["metrics"][0]["metric_name"] == "m"


def test_export_metrics_default_name(tmp_path):
    path = _engine(tmp_path).export_metrics()
    assert path.name == "gbogeb_metrics.json"
    assert path.is_file()
