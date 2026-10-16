"""Deterministic file-state and shutdown coverage for background change detection."""

import json
import os

from DMAIC_V3.convergence import background_change_detector as detector_module

BackgroundChangeDetector = detector_module.BackgroundChangeDetector


def test_added_modified_deleted_files_keep_distinct_receipts(tmp_path):
    workspace = tmp_path / "workspace"
    tracked = workspace / "DMAIC_V3"
    tracked.mkdir(parents=True)
    output = workspace / "DMAIC_V3_OUTPUT"
    output.mkdir()
    state = tmp_path / "state"
    target = tracked / "source.py"
    target.write_text("first", encoding="utf-8")
    ignored = output / "cached.pyc"
    ignored.write_bytes(b"not a source file")
    detector = BackgroundChangeDetector(workspace, state)

    assert detector.get_summary() == {"total": 0, "added": 0, "modified": 0, "deleted": 0}
    detector._take_snapshot()
    summary = detector.get_summary()
    assert (summary["total"], summary["added"], summary["modified"], summary["deleted"]) == (
        1, 1, 0, 0
    )
    assert json.loads(detector.changes_file.read_text())["changes"] == [
        {"path": "DMAIC_V3/source.py", "type": "added"}
    ]
    original_mtime = target.stat().st_mtime
    os.utime(target, (original_mtime + 3, original_mtime + 3))
    detector._take_snapshot()
    summary = detector.get_summary()
    assert (summary["total"], summary["added"], summary["modified"], summary["deleted"]) == (
        1, 0, 1, 0
    )
    target.unlink()
    detector._take_snapshot()
    summary = detector.get_summary()
    assert (summary["total"], summary["added"], summary["modified"], summary["deleted"]) == (
        1, 0, 0, 1
    )


def test_missing_scan_directories_do_not_fabricate_changes(tmp_path):
    checker = BackgroundChangeDetector(tmp_path / "empty", tmp_path / "state")
    checker._take_snapshot()
    assert json.loads(checker.snapshot_file.read_text()) == {}
    assert checker.get_summary() == {"total": 0, "added": 0, "modified": 0, "deleted": 0}


def test_corrupt_state_snapshot_and_summary_fail_closed(tmp_path):
    workspace = tmp_path / "repo"
    directory = workspace / "DMAIC_V3"
    directory.mkdir(parents=True)
    (directory / "new.txt").write_text("new", encoding="utf-8")
    checker = BackgroundChangeDetector(workspace, tmp_path / "state")
    checker.snapshot_file.write_text("invalid json", encoding="utf-8")
    checker._take_snapshot()
    assert checker.get_summary()["added"] == 1
    checker.changes_file.write_text("bad json", encoding="utf-8")
    assert checker.get_summary() == {"total": 0, "added": 0, "modified": 0, "deleted": 0}
    checker.changes_file.write_text(
        json.dumps({"changes": [{"unknown_key": "missing type"}]}),
        encoding="utf-8",
    )
    assert checker.get_summary() == {"total": 0, "added": 0, "modified": 0, "deleted": 0}


def test_summary_reports_each_change_family_and_optional_timestamp(tmp_path):
    checker = BackgroundChangeDetector(tmp_path, tmp_path / "state")
    checker.changes_file.write_text(
        json.dumps(
            {
                "timestamp": "2026-10-16T09:30:00",
                "changes": [
                    {"type": "added"},
                    {"type": "modified"},
                    {"type": "deleted"},
                    {"type": "added"},
                ],
            }
        ),
        encoding="utf-8",
    )
    assert checker.get_summary() == {
        "total": 4, "added": 2, "modified": 1, "deleted": 1,
        "timestamp": "2026-10-16T09:30:00",
    }


def test_detection_loop_catches_errors_and_stops_without_busy_wait(tmp_path, monkeypatch):
    checker = BackgroundChangeDetector(tmp_path, tmp_path / "state")
    checker.running = True
    checker.snapshot_interval = 2
    calls = []

    def failing_snapshot():
        calls.append("snapshot")
        checker.running = False
        raise OSError("test scan failure")

    monkeypatch.setattr(checker, "_take_snapshot", failing_snapshot)
    checker._detection_loop()
    assert calls == ["snapshot"]


def test_start_is_idempotent_and_stop_joins_worker(tmp_path, monkeypatch):
    created = []

    class FakeThread:
        def __init__(self, target, daemon):
            assert daemon is True
            assert callable(target)
            self.started = False
            self.joined = False
            created.append(self)

        def start(self):
            self.started = True

        def join(self, timeout):
            assert timeout == 5
            self.joined = True

    monkeypatch.setattr(detector_module.threading, "Thread", FakeThread)
    checker = BackgroundChangeDetector(tmp_path, tmp_path / "state")
    checker.start()
    checker.start()
    assert len(created) == 1
    assert checker.running and created[0].started
    checker.stop()
    assert not checker.running and created[0].joined
