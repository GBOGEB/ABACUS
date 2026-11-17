"""Behaviour tests for clone_based_validator.py (lane ab-next, wave 1)."""

import hashlib
import json
import os
import runpy
import sys
from pathlib import Path

import pytest

from tests.coverage_waves.lane_b._l2_loader import REPO_ROOT, load


class _StdoutProbe:
    """Stand-in stdout so the import-time reconfigure touches nothing real."""

    def __init__(self):
        self.calls = []

    def reconfigure(self, **kwargs):
        self.calls.append(kwargs)

    def write(self, text):
        return len(text)

    def flush(self):
        return None


_PROBE = _StdoutProbe()
_ENV_KEY = "PYTHONIOENCODING"
_ENV_BEFORE = os.environ.get(_ENV_KEY)
_STDOUT_BEFORE = sys.stdout
sys.stdout = _PROBE
try:
    cbv = load("clone_based_validator.py", name="abn_clone_based_validator")
    _ENV_AT_IMPORT = os.environ.get(_ENV_KEY)
finally:
    sys.stdout = _STDOUT_BEFORE
    if _ENV_BEFORE is None:
        os.environ.pop(_ENV_KEY, None)
    else:
        os.environ[_ENV_KEY] = _ENV_BEFORE


def _validator(monkeypatch, tmp_path, branch="main"):
    monkeypatch.chdir(tmp_path)
    return cbv.CloneBasedValidator("https://example.invalid/repo.git", branch)


def _tree(root, files):
    root.mkdir(parents=True, exist_ok=True)
    for name, body in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)
    return root


def _short(data):
    return hashlib.sha256(data).hexdigest()[:16]


def test_import_sets_utf8_io():
    assert _ENV_AT_IMPORT == "utf-8"
    assert _PROBE.calls == [dict(encoding="utf-8")]


def test_init_creates_output_dir(monkeypatch, tmp_path):
    validator = _validator(monkeypatch, tmp_path, branch="dev")
    assert validator.branch == "dev"
    assert validator.clone_dir is None
    assert len(validator.execution_id) == 15
    assert (tmp_path / "DMAIC_INTEGRATION_OUTPUT" / "clone_validation").is_dir()


def test_calculate_file_checksum_truncated_sha256(monkeypatch, tmp_path):
    validator = _validator(monkeypatch, tmp_path)
    path = tmp_path / "f.bin"
    payload = bytes(i % 251 for i in range(20000))
    path.write_bytes(payload)
    assert validator.calculate_file_checksum(path) == _short(payload)


def test_calculate_file_checksum_error(monkeypatch, tmp_path):
    validator = _validator(monkeypatch, tmp_path)
    result = validator.calculate_file_checksum(tmp_path / "missing.py")
    assert result.startswith("ERROR:")
    assert len(result) <= len("ERROR:") + 20


def test_extract_imports(monkeypatch, tmp_path):
    validator = _validator(monkeypatch, tmp_path)
    path = tmp_path / "m.py"
    path.write_bytes(
        b"import os\n    from a.b import c\nx = 1  # import y\nfromage = 2\n"
    )
    assert validator.extract_imports(path) == ["import os", "from a.b import c"]


def test_extract_imports_missing_file_is_empty(monkeypatch, tmp_path):
    validator = _validator(monkeypatch, tmp_path)
    assert validator.extract_imports(tmp_path / "nope.py") == []


def test_build_dependency_graph(monkeypatch, tmp_path, capsys):
    validator = _validator(monkeypatch, tmp_path)
    root = _tree(tmp_path / "src", {"a.py": b"from b import x\n", "b.py": b"y = 1\n"})
    (root / "notes.txt").write_bytes(b"ignored")
    graph = validator.build_dependency_graph(root)
    assert sorted(graph) == ["a.py", "b.py"]
    node = graph["a.py"]
    assert node.imports == ["from b import x"]
    assert node.imported_by == []
    assert node.size_bytes == len(b"from b import x\n")
    assert node.checksum == _short(b"from b import x\n")
    assert node.last_modified != "unknown"
    assert "Found 2 Python files" in capsys.readouterr().out


def test_build_dependency_graph_reports_progress(monkeypatch, tmp_path, capsys):
    """500 virtual (absent) files: progress line plus unreadable-file defaults."""
    validator = _validator(monkeypatch, tmp_path)

    class _VirtualRoot(type(tmp_path)):
        def rglob(self, pattern):
            return [self / ("m%03d.py" % idx) for idx in range(500)]

    graph = validator.build_dependency_graph(_VirtualRoot(tmp_path / "many"))
    assert len(graph) == 500
    node = graph["m499.py"]
    assert node.imports == []
    assert node.checksum.startswith("ERROR:")
    assert node.size_bytes == 0
    assert node.last_modified == "unknown"
    assert "Progress: 500/500 files..." in capsys.readouterr().out


def test_build_dependency_graph_stat_failure_defaults(monkeypatch, tmp_path, capsys):
    validator = _validator(monkeypatch, tmp_path)
    root = _tree(tmp_path / "src", {"a.py": b"x = 1\n"})

    class _BrokenDatetime:
        @staticmethod
        def fromtimestamp(value):
            raise OSError("bad stat")

    monkeypatch.setattr(cbv, "datetime", _BrokenDatetime)
    node = validator.build_dependency_graph(root)["a.py"]
    assert node.size_bytes == 0
    assert node.last_modified == "unknown"


def _node(path, imports):
    return cbv.DependencyNode(
        file_path=path,
        imports=imports,
        imported_by=[],
        checksum="c",
        size_bytes=0,
        last_modified="t",
    )


def test_detect_circular_ignores_non_matching(monkeypatch, tmp_path, capsys):
    validator = _validator(monkeypatch, tmp_path)
    graph = {
        "a.py": _node("a.py", ["import b", "from", "from zzz import q"]),
        "b.py": _node("b.py", []),
    }
    assert validator.detect_circular_dependencies(graph) == []
    assert "Found 0 circular dependencies" in capsys.readouterr().out


def test_production_defect_circular_dependencies_never_detected(
    monkeypatch, tmp_path, capsys
):
    """production_defect: detect_circular_dependencies compares a file path against raw import statements so a real cycle is never reported; this test fails once fixed"""
    validator = _validator(monkeypatch, tmp_path)
    graph = {
        "a.py": _node("a.py", ["from b import x"]),
        "b.py": _node("b.py", ["from a import y"]),
    }
    assert validator.detect_circular_dependencies(graph) == []


def test_find_orphaned_files(monkeypatch, tmp_path, capsys):
    validator = _validator(monkeypatch, tmp_path)
    root = _tree(
        tmp_path / "clone",
        {
            "a.py": b"from b import x\nif __name__ == '__main__':\n    pass\n",
            "b.py": b"y = 1\n",
            "c.py": b"import b\n",
        },
    )
    validator.clone_dir = root
    graph = validator.build_dependency_graph(root)
    orphaned = validator.find_orphaned_files(graph)
    assert sorted(orphaned) == ["a.py", "c.py"]
    assert "Found 2 orphaned files (1 entry points)" in capsys.readouterr().out


def test_calculate_code_checksum(monkeypatch, tmp_path, capsys):
    validator = _validator(monkeypatch, tmp_path)
    root = _tree(
        tmp_path / "clone",
        {
            "main.py": b"from lib import f\nif __name__ == '__main__':\n    f()\n",
            "lib.py": b"def f():\n    return 1\n",
            "tool.py": b"x = 2\n",
        },
    )
    validator.clone_dir = root
    result = validator.calculate_code_checksum(root)
    assert result.total_files == 3
    assert result.total_checksums["lib.py"] == _short(b"def f():\n    return 1\n")
    assert sorted(result.orphaned_files) == ["main.py", "tool.py"]
    assert result.entry_points == ["main.py"]
    assert result.circular_dependencies == []
    assert set(result.dependency_graph) == {"main.py", "lib.py", "tool.py"}


def test_compare_with_workspace(monkeypatch, tmp_path, capsys):
    validator = _validator(monkeypatch, tmp_path)
    ws = _tree(
        tmp_path / "ws",
        {"same.py": b"s\n", "changed.py": b"new\n", "local.py": b"l\n"},
    )
    validator.dependency_graph = {
        "same.py": cbv.DependencyNode("same.py", [], [], _short(b"s\n"), 2, "t"),
        "changed.py": cbv.DependencyNode(
            "changed.py", [], [], _short(b"old\n"), 4, "t"
        ),
        "remote.py": cbv.DependencyNode("remote.py", [], [], "abc", 1, "t"),
    }
    comparison = validator.compare_with_workspace(ws)
    assert comparison == {
        "matching_files": 1,
        "different_files": 1,
        "clone_only": ["remote.py"],
        "workspace_only": ["local.py"],
        "total_clone_files": 3,
        "total_workspace_files": 3,
    }
    out = capsys.readouterr().out
    assert "Matching: 1" in out
    assert "Workspace only: 1" in out


def test_save_results_writes_json(monkeypatch, tmp_path, capsys):
    validator = _validator(monkeypatch, tmp_path, branch="rel")
    checksum = cbv.CodeChecksum(
        total_files=1,
        total_checksums={"a.py": "h"},
        dependency_graph={},
        circular_dependencies=[("a.py", "b.py")],
        orphaned_files=["a.py"],
        entry_points=[],
    )
    validator.save_results(checksum, dict(matching_files=1))
    out_file = validator.output_dir / (
        "clone_validation_%s.json" % validator.execution_id
    )
    data = json.loads(out_file.read_text(encoding="utf-8"))
    assert data["branch"] == "rel"
    assert data["repo_url"] == "https://example.invalid/repo.git"
    assert data["checksum"]["circular_dependencies"] == [["a.py", "b.py"]]
    assert data["checksum"]["total_checksums"] == {"a.py": "h"}
    assert data["comparison"] == {"matching_files": 1}
    assert "[SAVE] Results saved to" in capsys.readouterr().out


def test_cleanup(monkeypatch, tmp_path, capsys):
    validator = _validator(monkeypatch, tmp_path)
    validator.cleanup()
    assert capsys.readouterr().out == ""
    validator.clone_dir = tmp_path / "gone"
    validator.cleanup()
    assert capsys.readouterr().out == ""
    target = _tree(tmp_path / "clone", {"x.py": b""})
    validator.clone_dir = target
    validator.cleanup()
    assert not target.exists()
    assert "Cleanup complete" in capsys.readouterr().out


def _patch_mkdtemp(monkeypatch, tmp_path):
    clone = tmp_path / "clone"

    def fake_mkdtemp(prefix=""):
        clone.mkdir()
        return str(clone)

    monkeypatch.setattr(cbv.tempfile, "mkdtemp", fake_mkdtemp)
    return clone


def test_clone_repository_invokes_git(monkeypatch, tmp_path, capsys):
    validator = _validator(monkeypatch, tmp_path, branch="dev")
    clone = _patch_mkdtemp(monkeypatch, tmp_path)
    seen = {}

    def fake_run(cmd, **kwargs):
        seen["cmd"] = cmd
        seen.update(kwargs)

    monkeypatch.setattr(cbv.subprocess, "run", fake_run)
    assert validator.clone_repository() == clone
    assert validator.clone_dir == clone
    assert seen["cmd"] == [
        "git",
        "clone",
        "--branch",
        "dev",
        "--depth",
        "1",
        "https://example.invalid/repo.git",
        str(clone),
    ]
    assert seen["check"] is True
    assert seen["timeout"] == 300


def test_clone_repository_called_process_error(monkeypatch, tmp_path, capsys):
    validator = _validator(monkeypatch, tmp_path)
    _patch_mkdtemp(monkeypatch, tmp_path)

    def fake_run(cmd, **kwargs):
        raise cbv.subprocess.CalledProcessError(128, cmd, stderr=b"fatal: nope")

    monkeypatch.setattr(cbv.subprocess, "run", fake_run)
    with pytest.raises(cbv.subprocess.CalledProcessError):
        validator.clone_repository()
    assert "[ERROR] Clone failed: fatal: nope" in capsys.readouterr().out


def test_execute_validation_timeout_cleans_up(monkeypatch, tmp_path, capsys):
    validator = _validator(monkeypatch, tmp_path)
    clone = _patch_mkdtemp(monkeypatch, tmp_path)

    def fake_run(cmd, **kwargs):
        raise cbv.subprocess.TimeoutExpired(cmd, 300)

    monkeypatch.setattr(cbv.subprocess, "run", fake_run)
    with pytest.raises(cbv.subprocess.TimeoutExpired):
        validator.execute_validation(tmp_path)
    out = capsys.readouterr().out
    assert "[ERROR] Clone timeout after 300 seconds" in out
    assert "[ERROR] Validation failed" in out
    assert not clone.exists()


def _fake_clone(files):
    def fake_run(cmd, **kwargs):
        _tree(Path(cmd[-1]), files)

    return fake_run


def test_execute_validation_end_to_end(monkeypatch, tmp_path, capsys):
    validator = _validator(monkeypatch, tmp_path)
    clone = _patch_mkdtemp(monkeypatch, tmp_path)
    files = {
        "app.py": b"from util import h\nif __name__ == '__main__':\n    h()\n",
        "util.py": b"def h():\n    return 0\n",
    }
    monkeypatch.setattr(cbv.subprocess, "run", _fake_clone(files))
    ws = _tree(tmp_path / "ws", {"app.py": files["app.py"], "util.py": b"changed\n"})
    validator.execute_validation(ws)
    out = capsys.readouterr().out
    assert "VALIDATION COMPLETE" in out
    assert not clone.exists()
    saved = list(validator.output_dir.glob("clone_validation_*.json"))
    assert len(saved) == 1
    data = json.loads(saved[0].read_text(encoding="utf-8"))
    assert data["checksum"]["total_files"] == 2
    assert data["checksum"]["entry_points"] == ["app.py"]
    assert data["comparison"]["matching_files"] == 1
    assert data["comparison"]["different_files"] == 1


def test_main_parses_args(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    seen = {}

    def fake_execute(self, workspace):
        seen["url"] = self.repo_url
        seen["branch"] = self.branch
        seen["workspace"] = workspace

    monkeypatch.setattr(cbv.CloneBasedValidator, "execute_validation", fake_execute)
    monkeypatch.setattr(
        sys, "argv", ["prog", "--repo-url", "u", "--branch", "b", "--workspace", "w"]
    )
    cbv.main()
    assert seen == dict(url="u", branch="b", workspace=Path("w"))


def test_main_requires_repo_url(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["prog"])
    with pytest.raises(SystemExit) as info:
        cbv.main()
    assert info.value.code == 2
    assert "--repo-url" in capsys.readouterr().err


def test_main_guard_end_to_end(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv(_ENV_KEY, "utf-8")
    _patch_mkdtemp(monkeypatch, tmp_path)
    monkeypatch.setattr("subprocess.run", _fake_clone({"only.py": b"z = 1\n"}))
    ws = _tree(tmp_path / "ws", {"other.py": b"o\n"})
    monkeypatch.setattr(
        sys, "argv", ["prog", "--repo-url", "u", "--workspace", str(ws)]
    )
    runpy.run_path(str(REPO_ROOT / "clone_based_validator.py"), run_name="__main__")
    out = capsys.readouterr().out
    assert "Clone only: 1" in out
    assert "Workspace only: 1" in out
