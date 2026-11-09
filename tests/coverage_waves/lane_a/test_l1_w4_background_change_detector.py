"""Lane A wave 4: DMAIC_V3.convergence.background_change_detector."""

import json
import os
import types

import pytest

from DMAIC_V3.convergence import background_change_detector as bcd


@pytest.fixture
def ws(tmp_path):
    root = tmp_path / "ws"
    src = root / "DMAIC_V3" / "pkg"
    src.mkdir(parents=True)
    (src / "a.py").write_bytes(b"a = 1\n")
    (src / "skip.pyc").write_bytes(b"\x00")
    out = root / "DMAIC_V3_OUTPUT"
    out.mkdir()
    (out / "r.json").write_bytes(b"{}")
    (root / "outside.txt").write_bytes(b"ignored")
    return root


@pytest.fixture
def det(ws, tmp_path):
    return bcd.BackgroundChangeDetector(ws, tmp_path / "state" / "deep")


def _snapshot(det):
    return json.loads(det.snapshot_file.read_bytes())


def _changes(det):
    data = json.loads(det.changes_file.read_bytes())
    return {(c["path"], c["type"]) for c in data["changes"]}


def test_init_creates_state_dir(det, tmp_path):
    assert (tmp_path / "state" / "deep").is_dir()
    assert det.running is False and det.thread is None
    assert det.snapshot_interval == 30


def test_first_snapshot_reports_added_and_skips_binaries(det):
    det._take_snapshot()
    snap = _snapshot(det)
    assert set(snap) == {"DMAIC_V3/pkg/a.py", "DMAIC_V3_OUTPUT/r.json"}
    assert _changes(det) == {
        ("DMAIC_V3/pkg/a.py", "added"),
        ("DMAIC_V3_OUTPUT/r.json", "added"),
    }
    summary = det.get_summary()
    assert summary["total"] == 2 and summary["added"] == 2
    assert summary["timestamp"]


def test_modified_deleted_and_legacy_keys(det, ws):
    a_py = ws / "DMAIC_V3" / "pkg" / "a.py"
    r_json = ws / "DMAIC_V3_OUTPUT" / "r.json"
    legacy = {
        "DMAIC_V3\\pkg\\a.py": a_py.stat().st_mtime - 100,
        "DMAIC_V3_OUTPUT\\r.json": r_json.stat().st_mtime,
        "DMAIC_V3\\gone.py": 1.0,
    }
    det.snapshot_file.write_bytes(json.dumps(legacy).encode())
    det._take_snapshot()
    assert _changes(det) == {
        ("DMAIC_V3/pkg/a.py", "modified"),
        ("DMAIC_V3/gone.py", "deleted"),
    }
    assert det.get_summary() == {
        "total": 2,
        "added": 0,
        "modified": 1,
        "deleted": 1,
        "timestamp": json.loads(det.changes_file.read_bytes())["timestamp"],
    }


def test_no_changes_keeps_previous_changes_file(det):
    det._take_snapshot()
    before = det.changes_file.read_bytes()
    os.utime(det.changes_file, (1, 1))
    det._take_snapshot()
    assert det.changes_file.read_bytes() == before
    assert det.changes_file.stat().st_mtime == 1


@pytest.mark.parametrize("payload", [b"[1, 2]", b"{not json"])
def test_unusable_previous_snapshot_treated_as_empty(det, payload):
    det.snapshot_file.write_bytes(payload)
    det._take_snapshot()
    assert {t for _, t in _changes(det)} == {"added"}


def test_missing_scan_dirs_produce_empty_snapshot(tmp_path):
    det = bcd.BackgroundChangeDetector(tmp_path / "empty", tmp_path / "st")
    det._take_snapshot()
    assert _snapshot(det) == {}
    assert not det.changes_file.exists()


def test_save_failure_is_swallowed(ws, tmp_path):
    det = bcd.BackgroundChangeDetector(ws, tmp_path / "st")
    det.snapshot_file.mkdir()
    det._take_snapshot()
    assert not det.changes_file.exists()


def test_summary_defaults_and_errors(det):
    empty = {"total": 0, "added": 0, "modified": 0, "deleted": 0}
    assert det.get_summary() == empty
    det.changes_file.write_bytes(b"{broken")
    assert det.get_summary() == empty
    det.changes_file.write_bytes(b'{"changes": [{"path": "x"}]}')
    assert det.get_summary() == empty
    det.changes_file.write_bytes(b"{}")
    assert det.get_summary() == {
        "total": 0,
        "added": 0,
        "modified": 0,
        "deleted": 0,
        "timestamp": "",
    }


def test_detection_loop_logs_errors_and_exits(det, capsys, monkeypatch):
    det.snapshot_interval = 0
    det.running = True

    def failing_snapshot():
        det.running = False
        raise RuntimeError("scan broke")

    monkeypatch.setattr(det, "_take_snapshot", failing_snapshot)
    det._detection_loop()
    assert "Error: scan broke" in capsys.readouterr().out


def test_detection_loop_sleeps_in_steps_and_stops(det, monkeypatch):
    sleeps = []
    snaps = []
    det.snapshot_interval = 3
    det.running = True

    def fake_sleep(seconds):
        sleeps.append(seconds)
        if len(sleeps) == 4:
            det.running = False

    monkeypatch.setattr(bcd, "time", types.SimpleNamespace(sleep=fake_sleep))
    monkeypatch.setattr(det, "_take_snapshot", lambda: snaps.append(1))
    det._detection_loop()
    # first round: 3 full sleeps; second round: stop after the first sleep
    assert sleeps == [1, 1, 1, 1]
    assert len(snaps) == 2


def test_start_stop_thread_lifecycle(det, monkeypatch, capsys):
    monkeypatch.setattr(bcd, "time", types.SimpleNamespace(sleep=lambda s: None))
    det.snapshot_interval = 1
    det.start()
    first_thread = det.thread
    det.start()  # already running: no new thread
    assert det.thread is first_thread
    det.stop()
    first_thread.join(timeout=2)
    assert not first_thread.is_alive()
    assert det.running is False
    out = capsys.readouterr().out
    assert "Started (snapshot every 1s)" in out and "Stopped" in out


def test_stop_without_start(det, capsys):
    det.stop()
    assert "Stopped" in capsys.readouterr().out
