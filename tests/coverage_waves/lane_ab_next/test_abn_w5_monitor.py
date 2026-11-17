"""Behaviour tests for production/monitoring/monitor.py.

The script runs an endless poll loop at import time. Each test loads it inside
``tmp_path`` with ``time.sleep`` replaced by a fake that ends the loop after a
chosen number of cycles, so no real waiting happens.
"""

import json
import sys
import time

import pytest

from tests.coverage_waves.lane_b._l2_loader import load

REL = "production/monitoring/monitor.py"
NAME = "abn_production_monitor"


class _StopLoop(Exception):
    pass


def _run(monkeypatch, tmp_path, cycles):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "production" / "logs").mkdir(parents=True, exist_ok=True)
    sleeps = []

    def fake_sleep(seconds):
        sleeps.append(seconds)
        if len(sleeps) >= cycles:
            raise _StopLoop()

    monkeypatch.setattr(time, "sleep", fake_sleep)
    try:
        with pytest.raises(_StopLoop):
            load(REL, name=NAME)
        module = sys.modules[NAME]
    finally:
        sys.modules.pop(NAME, None)
    log = (tmp_path / "production" / "logs" / "monitoring.log").read_text(
        encoding="utf-8"
    )
    return module, sleeps, log.splitlines()


def test_loop_without_metrics_logs_empty_dict(monkeypatch, tmp_path):
    module, sleeps, lines = _run(monkeypatch, tmp_path, cycles=2)
    assert sleeps == [300, 300]
    assert len(lines) == 2
    assert all(line.endswith(" - Monitoring check: {}") for line in lines)
    assert module.check_metrics() == {}


def test_loop_with_metrics_file_logs_its_json(monkeypatch, tmp_path):
    mon = tmp_path / "production" / "monitoring"
    mon.mkdir(parents=True)
    (mon / "current_metrics.json").write_bytes(json.dumps(dict(cpu=12)).encode())
    module, sleeps, lines = _run(monkeypatch, tmp_path, cycles=1)
    assert sleeps == [300]
    assert lines == [lines[0]]
    assert lines[0].endswith('Monitoring check: {"cpu": 12}')
    assert module.check_metrics() == {"cpu": 12}


def test_log_status_appends_timestamped_line(monkeypatch, tmp_path):
    module, _, _ = _run(monkeypatch, tmp_path, cycles=1)
    module.log_status("hello")
    module.log_status("again")
    log = (tmp_path / "production" / "logs" / "monitoring.log").read_text(
        encoding="utf-8"
    )
    lines = log.splitlines()
    assert lines[-2].endswith(" - hello")
    assert lines[-1].endswith(" - again")
    assert "T" in lines[-1].split(" - ")[0]


def test_missing_log_dir_raises(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(time, "sleep", lambda s: None)
    try:
        with pytest.raises(FileNotFoundError):
            load(REL, name=NAME)
    finally:
        sys.modules.pop(NAME, None)
