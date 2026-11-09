"""Behaviour tests for refactoring_executor.py (lane AB next, wave 1)."""

import json
import os
import sys
from pathlib import Path

import pytest

from tests.coverage_waves.lane_b._l2_loader import load

_PREV_ENC = os.environ.get("PYTHONIOENCODING")
mod = load("refactoring_executor.py", name="abn_w1_refactoring_executor")
if _PREV_ENC is None:
    os.environ.pop("PYTHONIOENCODING", None)
else:
    os.environ["PYTHONIOENCODING"] = _PREV_ENC

HEADER_MARK = "# Version:"


def _write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-8"))
    return path


def _metrics(tmp_path, data):
    path = tmp_path / "metrics.json"
    path.write_bytes(json.dumps(data).encode("utf-8"))
    return path


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    sleeps = []
    monkeypatch.setattr(mod.time, "sleep", lambda s: sleeps.append(s))
    return sleeps


def _make(tmp_path, data, **kwargs):
    return mod.RefactoringExecutor(_metrics(tmp_path, data), **kwargs)


def test_init_loads_metrics_and_creates_backup_dir(tmp_path, env):
    ex = _make(tmp_path, {"files": {}}, dry_run=True, batch_size=7)
    assert ex.metrics == {"files": {}}
    assert ex.dry_run is True
    assert ex.batch_size == 7
    assert ex.backup_dir.is_dir()
    assert ex.backup_dir.name == "refactoring_" + ex.execution_id
    assert ex.stats["duplicates_removed"] == 0
    assert ex.stats["errors"] == []


def test_backup_file_live_copies_and_dry_run_skips(tmp_path, env, capsys):
    src = _write(Path("pkg") / "a.py", "x = 1\n")
    live = _make(tmp_path, {})
    live.backup_file(src)
    copied = live.backup_dir / src
    assert copied.read_bytes() == b"x = 1\n"
    assert "[BACKUP]" in capsys.readouterr().out

    other = _write(Path("pkg") / "b.py", "y = 2\n")
    dry = _make(tmp_path, {}, dry_run=True)
    dry.backup_file(other)
    assert not (dry.backup_dir / other).exists()
    assert "[BACKUP]" not in capsys.readouterr().out


def test_remove_duplicates_prefers_version_header_live(tmp_path, env, capsys):
    a = _write(Path("a.py"), "print(1)\n")
    b = _write(Path("b.py"), HEADER_MARK + " 1.0\nprint(1)\n")
    c = _write(Path("c.py"), "print(1)\n")
    data = dict(duplicates={"h1": [str(a), str(b), str(c)], "solo": [str(a)]})
    ex = _make(tmp_path, data)
    removed = ex.remove_duplicates()
    out = capsys.readouterr().out
    assert removed == 2
    assert b.exists()
    assert not a.exists() and not c.exists()
    assert (ex.backup_dir / "a.py").exists()
    assert "[PRESERVE] b.py" in out
    assert ex.stats["batches_processed"] == 1
    assert env == []


def test_remove_duplicates_prefers_core_systems_and_skips_unreadable(
    tmp_path, env, capsys
):
    folder = Path("adir")
    folder.mkdir()
    core = _write(Path("13_CORE_SYSTEMS") / "m.py", "y = 2\n")
    other = _write(Path("other.py"), "y = 2\n")
    missing = "does_not_exist.py"
    data = dict(duplicates={"h": [missing, str(folder), str(other), str(core)]})
    ex = _make(tmp_path, data, dry_run=True)
    removed = ex.remove_duplicates()
    out = capsys.readouterr().out
    # missing file is listed for removal but skipped since it is absent;
    # folder and other.py are counted (dry run keeps them on disk).
    assert removed == 2
    assert core.exists() and other.exists() and folder.exists()
    assert "duplicate of " + str(core) in out
    assert "[REMOVE] " + missing not in out


def test_remove_duplicates_falls_back_to_first_and_batches_with_sleep(
    tmp_path, env, capsys
):
    files = [_write(Path("d%d.py" % i), "z = 3\n") for i in range(4)]
    data = dict(duplicates={"h": [str(p) for p in files]})
    ex = _make(tmp_path, data, batch_size=2)
    removed = ex.remove_duplicates()
    out = capsys.readouterr().out
    assert removed == 3
    assert files[0].exists()
    assert not any(p.exists() for p in files[1:])
    assert ex.stats["batches_processed"] == 2
    assert "[BATCH 2/2]" in out
    assert env == [0.5]


def test_remove_duplicates_records_errors(tmp_path, env, capsys):
    a = _write(Path("a.py"), "q = 1\n")
    b = _write(Path("b.py"), "q = 1\n")
    ex = _make(tmp_path, dict(duplicates={"h": [str(a), str(b)]}))

    def boom(path):
        raise OSError("disk full")

    ex.backup_file = boom
    assert ex.remove_duplicates() == 0
    assert b.exists()
    assert ex.stats["errors"] == ["Error removing b.py: disk full"]
    assert "[ERROR]" in capsys.readouterr().out


def test_fix_import_paths_live_dry_and_errors(tmp_path, env, capsys):
    rel = _write(Path("rel.py"), "from ...pkg import a\nfrom ..mod import b\n")
    clean = _write(Path("clean.py"), "import os\n")
    folder = Path("folder")
    folder.mkdir()
    issues = [str(rel), str(clean), str(folder), "nope.py"]
    ex = _make(tmp_path, dict(import_issues=issues))
    assert ex.fix_import_paths() == 1
    out = capsys.readouterr().out
    text = rel.read_bytes().decode("utf-8")
    assert "from 13_CORE_SYSTEMS.pkg import a" in text
    assert "from 13_CORE_SYSTEMS.mod import b" in text
    assert (ex.backup_dir / "rel.py").exists()
    assert "[FIX] rel.py" in out
    assert "[ERROR] Failed to fix folder" in out
    assert "Fixed 1 import paths" in out

    dry_src = _write(Path("dry.py"), "from ..x import y\n")
    dry = _make(tmp_path, dict(import_issues=[str(dry_src)]), dry_run=True)
    assert dry.fix_import_paths() == 1
    assert dry_src.read_bytes() == b"from ..x import y\n"


def test_production_defect_imports_fixed_stat_never_updated(tmp_path, env):
    """production_defect: imports_fixed stat never incremented by fix_import_paths; this test fails once fixed"""  # noqa: E501
    rel = _write(Path("rel.py"), "from ..mod import b\n")
    ex = _make(tmp_path, dict(import_issues=[str(rel)]))
    assert ex.fix_import_paths() == 1
    assert ex.stats["imports_fixed"] == 0


def test_add_version_headers_live_inserts_after_shebang(tmp_path, env, capsys):
    shebang = _write(
        Path("s.py"), "#!/usr/bin/env python\n# -*- coding: utf-8 -*-\nx=1\n"
    )
    plain = _write(Path("p.py"), "y = 2\n")
    has = _write(Path("h.py"), "__version__ = '1'\n")
    folder = Path("fold")
    folder.mkdir()
    files = {str(shebang): {}, str(plain): {}, str(has): {}, str(folder): {}}
    files["ghost.py"] = {}
    ex = _make(tmp_path, dict(files=files))
    assert ex.add_version_headers() == 2
    lines = shebang.read_text(encoding="utf-8").splitlines()
    assert lines[0].startswith("#!")
    assert "coding" in lines[1]
    assert lines[2] == '"""'
    assert lines[3] == "# Version: 1.0.0"
    assert plain.read_text(encoding="utf-8").startswith('"""\n# Version: 1.0.0')
    assert has.read_bytes() == b"__version__ = '1'\n"
    out = capsys.readouterr().out
    assert "Total files to update: 2" in out
    assert "Added 2 version headers in 1 batches" in out


def test_add_version_headers_max_files_batches_and_dry_run(tmp_path, env, capsys):
    paths = [_write(Path("f%d.py" % i), "a = %d\n" % i) for i in range(5)]
    files = {str(p): {} for p in paths}
    dry = _make(tmp_path, dict(files=files), dry_run=True, batch_size=2)
    assert dry.add_version_headers(max_files=3) == 3
    assert all(HEADER_MARK not in p.read_bytes().decode("utf-8") for p in paths)
    assert dry.stats["batches_processed"] == 2
    assert env == []

    live = _make(tmp_path, dict(files=files), batch_size=2)
    assert live.add_version_headers(max_files=3) == 3
    assert env == [0.5]
    assert "[BATCH 2/2]" in capsys.readouterr().out


def test_add_version_headers_write_and_processing_errors(
    tmp_path, env, monkeypatch, capsys
):
    p = _write(Path("e.py"), "v = 1\n")
    ex = _make(tmp_path, dict(files={str(p): {}}))

    def boom(path):
        raise OSError("ro")

    ex.backup_file = boom
    assert ex.add_version_headers() == 0
    assert ex.stats["errors"] == ["Error adding header to e.py: ro"]

    class BrokenDatetime:
        @staticmethod
        def now():
            raise RuntimeError("clock")

    ex2 = _make(tmp_path, dict(files={str(p): {}}))
    monkeypatch.setattr(mod, "datetime", BrokenDatetime)
    assert ex2.add_version_headers() == 0
    assert ex2.stats["errors"] == ["Error processing e.py: clock"]
    assert p.read_bytes() == b"v = 1\n"
    assert "[ERROR]" in capsys.readouterr().out


def test_execute_refactoring_default_actions_writes_results(tmp_path, env, capsys):
    p = _write(Path("x.py"), "from ..a import b\n")
    data = dict(files={str(p): {}}, duplicates={}, import_issues=[str(p)])
    ex = _make(tmp_path, data, dry_run=True)
    results = ex.execute_refactoring()
    out = capsys.readouterr().out
    assert results["actions_executed"] == ["headers", "duplicates", "imports"]
    assert results["dry_run"] is True
    assert results["stats"]["headers_added"] == 1
    saved = Path("DMAIC_INTEGRATION_OUTPUT/cicd_github") / (
        "refactoring_" + ex.execution_id + ".json"
    )
    on_disk = json.loads(saved.read_bytes().decode("utf-8"))
    assert on_disk["execution_id"] == ex.execution_id
    assert on_disk["metrics_file"] == str(ex.metrics_file)
    assert "Mode: DRY RUN" in out
    assert "REFACTORING COMPLETE" in out


def test_execute_refactoring_subset_live(tmp_path, env, capsys):
    p = _write(Path("x.py"), "from ..a import b\n")
    data = dict(files={str(p): {}}, import_issues=[str(p)])
    ex = _make(tmp_path, data)
    results = ex.execute_refactoring(actions=["imports"])
    out = capsys.readouterr().out
    assert results["actions_executed"] == ["imports"]
    assert results["stats"]["headers_added"] == 0
    assert "Mode: LIVE" in out
    assert "Adding version headers" not in out
    assert HEADER_MARK not in p.read_bytes().decode("utf-8")
    assert "13_CORE_SYSTEMS" in p.read_bytes().decode("utf-8")


def test_main_parses_cli_and_runs(tmp_path, env, monkeypatch, capsys):
    p = _write(Path("x.py"), "k = 1\n")
    metrics = _metrics(tmp_path, dict(files={str(p): {}}))
    argv = [
        "refactoring_executor.py",
        "--metrics",
        str(metrics),
        "--dry-run",
        "--batch-size",
        "5",
        "--actions",
        "headers",
        "--max-headers",
        "1",
    ]
    monkeypatch.setattr(sys, "argv", argv)
    mod.main()
    out = capsys.readouterr().out
    assert "Batch Size: 5" in out
    assert "Headers added: 1" in out
    assert p.read_bytes() == b"k = 1\n"
