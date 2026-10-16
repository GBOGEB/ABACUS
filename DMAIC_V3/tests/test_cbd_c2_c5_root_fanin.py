"""Wave 5: source-owned C2/C4/C5 root-cause integration regressions.

These cases verify source semantics, not permission to merge or close roots.
"""

import json

import DMAIC_V3.pipeline_control as pipeline_module
from DMAIC_V3.convergence.change_detector import ChangeDetector
from DMAIC_V3.core.utils import copy_file_with_backup
from DMAIC_V3.pipeline_control import PipelineController


def test_c2_preserves_old_destination_not_incoming_source(tmp_path):
    original = tmp_path / "original.txt"
    destination = tmp_path / "destination.txt"
    original.write_text("new", encoding="utf-8")
    destination.write_text("old", encoding="utf-8")

    assert copy_file_with_backup(original, destination)
    assert destination.read_text(encoding="utf-8") == "new"
    assert (tmp_path / "destination.txt.bak").read_text(encoding="utf-8") == "old"


def test_c4_legacy_single_backslash_path_reuses_snapshot_identity(tmp_path):
    workspace = tmp_path / "workspace"
    target = workspace / "pkg" / "same.py"
    target.parent.mkdir(parents=True)
    target.write_text("constant", encoding="utf-8")
    detector = ChangeDetector(workspace, tmp_path / "state")
    detector.snapshot_file.write_text(
        json.dumps(
            {
                r"pkg\same.py": {
                    "size": target.stat().st_size,
                    "mtime": target.stat().st_mtime,
                }
            }
        ),
        encoding="utf-8",
    )

    assert list(detector.load_previous_snapshot()) == ["pkg/same.py"]
    assert detector.detect_changes([target]) == []


def _controller_without_signal_side_effects(monkeypatch):
    monkeypatch.setattr(pipeline_module.signal, "signal", lambda *args: None)
    return PipelineController()


def test_c5_caught_crash_still_observes_inter_iteration_pause(monkeypatch):
    controller = _controller_without_signal_side_effects(monkeypatch)
    sleeps = []

    class FakeOrchestrator:
        def __init__(self, **kwargs):
            pass

        def execute_full_pipeline(self, iteration):
            if iteration == 1:
                raise RuntimeError("expected failure")
            return True

    monkeypatch.setattr(pipeline_module, "FullPipelineOrchestrator", FakeOrchestrator)
    monkeypatch.setattr(pipeline_module.time, "sleep", sleeps.append)
    monkeypatch.setattr(pipeline_module.time, "time", lambda: 100.0)

    results = controller.run_n_iterations_with_stops(1, 2)
    assert [row["success"] for row in results] == [False, True]
    assert results[0]["error"] == "expected failure"
    assert sleeps == [3]


def test_c5_stop_requested_after_failure_never_pauses(monkeypatch):
    controller = _controller_without_signal_side_effects(monkeypatch)
    sleeps = []

    class FakeOrchestrator:
        def __init__(self, **kwargs):
            pass

        def execute_full_pipeline(self, iteration):
            controller.stop_requested = True
            raise RuntimeError("stop requested")

    monkeypatch.setattr(pipeline_module, "FullPipelineOrchestrator", FakeOrchestrator)
    monkeypatch.setattr(pipeline_module.time, "sleep", sleeps.append)
    monkeypatch.setattr(pipeline_module.time, "time", lambda: 100.0)

    result = controller.run_n_iterations_with_stops(1, 3)
    assert len(result) == 1
    assert result[0]["iteration"] == 1
    assert result[0]["success"] is False
    assert sleeps == []
