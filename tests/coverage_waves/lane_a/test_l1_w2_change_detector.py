"""Lane A wave 2: DMAIC_V3.convergence.change_detector."""

import hashlib
import json
import os

import pytest

from DMAIC_V3.convergence import change_detector as cd


@pytest.fixture
def ws(tmp_path):
    root = tmp_path / "ws"
    root.mkdir()
    (root / "a.py").write_bytes("print(1)\n".encode())
    (root / "b.md").write_bytes("# b\n".encode())
    return root


@pytest.fixture
def det(ws, tmp_path):
    return cd.ChangeDetector(ws, tmp_path / "state" / "nested")


def test_file_change_timestamp_defaults_and_keeps_explicit():
    assert cd.FileChange("x", "added").timestamp
    assert cd.FileChange("x", "added", timestamp="T").timestamp == "T"


def test_init_creates_state_dir(det):
    assert det.state_dir.is_dir()
    assert det.snapshot_file.name == "file_snapshot.json"


def test_compute_file_hash(det, ws):
    expected = hashlib.sha256(b"# b\n").hexdigest()
    assert det.compute_file_hash(ws / "b.md") == expected
    assert det.compute_file_hash(ws / "missing") == ""
    assert det.compute_file_hash(ws) == ""


def test_compute_file_hash_unexpected_error(det, ws, monkeypatch):
    def boom():
        raise ValueError("no hasher")

    monkeypatch.setattr(cd.hashlib, "sha256", boom)
    assert det.compute_file_hash(ws / "a.py") == ""


def test_create_snapshot_skips_missing_and_outside(det, ws, tmp_path, capsys):
    outside = tmp_path / "outside.txt"
    outside.write_bytes("x".encode())
    snap = det.create_snapshot([ws / "a.py", ws / "nope.py", outside])
    assert list(snap) == ["a.py"]
    assert snap["a.py"]["size"] == (ws / "a.py").stat().st_size
    assert len(snap["a.py"]["hash"]) == 64
    assert "Completed: 2/3" in capsys.readouterr().out


def test_create_snapshot_reports_progress(det, ws, capsys, monkeypatch):
    monkeypatch.setattr(det, "compute_file_hash", lambda path: "h")
    snap = det.create_snapshot([ws / "a.py"] * 5000)
    assert list(snap) == ["a.py"]
    assert "Progress: 5000/5000" in capsys.readouterr().out


def test_load_previous_snapshot_variants(det, capsys):
    assert det.load_previous_snapshot() == {}
    det.snapshot_file.write_bytes(json.dumps({"d\\e.py": {"size": 1}}).encode())
    assert det.load_previous_snapshot() == {"d/e.py": {"size": 1}}
    det.snapshot_file.write_bytes("[1, 2]".encode())
    assert det.load_previous_snapshot() == {}
    det.snapshot_file.write_bytes("{not json".encode())
    assert det.load_previous_snapshot() == {}
    assert "Error loading previous snapshot" in capsys.readouterr().out


def test_save_snapshot_error_is_reported(det, capsys):
    det.snapshot_file.mkdir()
    det.save_snapshot({"a": {}})
    assert "Error saving snapshot" in capsys.readouterr().out


def test_detect_changes_lifecycle(det, ws, tmp_path):
    files = [ws / "a.py", ws / "b.md"]
    first = det.detect_changes(files)
    assert sorted((c.path, c.change_type) for c in first) == [
        ("a.py", "added"),
        ("b.md", "added"),
    ]
    assert det.has_changes() is True
    assert det.get_change_summary()["added"] == 2

    unchanged = det.detect_changes(files)
    assert unchanged == []
    assert det.has_changes() is False

    (ws / "a.py").write_bytes("print('longer content')\n".encode())
    st = (ws / "b.md").stat()
    os.utime(ws / "b.md", (st.st_atime, st.st_mtime + 100))
    (ws / "c.txt").write_bytes("c".encode())
    outside = tmp_path / "outside.txt"
    outside.write_bytes("o".encode())
    changes = det.detect_changes([ws / "a.py", ws / "b.md", ws / "c.txt", outside])
    kinds = {c.path: c.change_type for c in changes}
    assert kinds == {"a.py": "modified", "b.md": "modified", "c.txt": "added"}
    modified = next(c for c in changes if c.path == "a.py")
    assert modified.old_size == len("print(1)\n".encode())

    gone = det.detect_changes([ws / "a.py", ws / "nope"])
    kinds = {c.path: c.change_type for c in gone}
    assert kinds == {"b.md": "deleted", "c.txt": "deleted"}
    summary = det.get_change_summary()
    assert summary["deleted"] == 2 and summary["total"] == 2
    assert summary["timestamp"]


def test_save_changes_error_is_reported(det, capsys):
    det.changes_file.mkdir()
    det._save_changes([cd.FileChange("x", "added")])
    assert "Error saving changes" in capsys.readouterr().out


def test_get_change_summary_missing_and_corrupt(det):
    empty = {"total": 0, "added": 0, "modified": 0, "deleted": 0}
    assert det.get_change_summary() == empty
    det.changes_file.write_bytes(json.dumps({"changes": [{"path": "x"}]}).encode())
    assert det.get_change_summary() == empty


def test_get_changed_files_filters(det, capsys):
    assert det.get_changed_files() == []
    data = {
        "changes": [
            {"path": "a.py", "change_type": "added"},
            {"path": "b.md", "change_type": "modified"},
            {"path": "c.py", "change_type": "deleted"},
        ]
    }
    det.changes_file.write_bytes(json.dumps(data).encode())
    assert det.get_changed_files() == ["a.py", "b.md"]
    assert det.get_changed_files({".py"}) == ["a.py"]
    det.changes_file.write_bytes("{bad".encode())
    assert det.get_changed_files() == []
    assert "Error loading changes" in capsys.readouterr().out


def test_has_changes_corrupt_file_means_changed(det):
    det.changes_file.write_bytes("{bad".encode())
    assert det.has_changes() is True
