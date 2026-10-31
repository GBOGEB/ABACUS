"""Wave 13 lane A behaviour tests for DMAIC_V3/phases/phase1_define.py."""

import importlib
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


def _import_restoring_sys_path():
    saved = list(sys.path)
    try:
        return importlib.import_module("DMAIC_V3.phases.phase1_define")
    finally:
        sys.path[:] = saved


p1 = _import_restoring_sys_path()


@pytest.fixture
def cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _phase(tmp_path):
    ws = tmp_path / "ws"
    ws.mkdir(exist_ok=True)
    cfg = SimpleNamespace(
        paths=SimpleNamespace(workspace_root=ws, output_root=tmp_path / "out")
    )
    return p1.Phase1Define(cfg, None)


def _files(root, names):
    for name in names:
        p = root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"x\n")


def _walk_order(root):
    order = []
    for r, dirs, files in os.walk(root):
        dirs.sort()
        for f in files:
            order.append(str(Path(r) / f))
    return order


def test_get_file_type(tmp_path):
    ph = _phase(tmp_path)
    assert ph.get_file_type(Path("a.PY")) == "code"
    assert ph.get_file_type(Path("a.ipynb")) == "notebooks"
    assert ph.get_file_type(Path("a.yml")) == "data"
    assert ph.get_file_type(Path("a.bin")) == "unknown"


def test_normalize_execute_results(tmp_path):
    ph = _phase(tmp_path)
    res = ph._normalize_execute_results({"categorized": {"code": 3, "docs": 2}})
    assert (res["code_files"], res["documentation_files"]) == (3, 2)
    res = ph._normalize_execute_results((True, {"categorized": "bad", "code_files": 9}))
    assert (res["code_files"], res["documentation_files"]) == (9, 0)
    with pytest.raises(TypeError, match="Unexpected execute results type: list"):
        ph._normalize_execute_results([1])
    with pytest.raises(TypeError):
        ph._normalize_execute_results(("yes", {}))


def test_scan_progress_roundtrip(tmp_path):
    ph = _phase(tmp_path)
    assert ph.load_scan_progress() is None
    ph.clear_scan_progress()
    ph.save_scan_progress(2, "last", {"k": 1})
    loaded = ph.load_scan_progress()
    assert loaded["chunk_num"] == 2
    assert loaded["accumulated_data"] == {"k": 1}
    ph.clear_scan_progress()
    assert not ph.scan_progress_file.exists()


def test_scan_files_categorises_and_skips(tmp_path):
    ph = _phase(tmp_path)
    ws = ph.workspace_root
    _files(
        ws,
        [
            "README.md",
            "notes.txt",
            "pkg/mod.py",
            "pkg/app.js",
            "nb/run.ipynb",
            "data.json",
            "blob.bin",
            ".git/config.py",
            "node_modules/x.js",
        ],
    )
    all_files, paths, cat, folders, md, py, nb = ph.scan_files_chunked()
    assert len(all_files) == 7
    assert len(paths) == 7
    assert cat == {"docs": 2, "code": 2, "notebooks": 1, "data": 1, "unknown": 1}
    assert md == ["README.md"]
    assert py == [str(Path("pkg") / "mod.py")]
    assert nb == [str(Path("nb") / "run.ipynb")]
    assert set(folders) == {".", "pkg", "nb"}


def test_scan_chunk_boundary_saves_progress(tmp_path, monkeypatch):
    ph = _phase(tmp_path)
    _files(ph.workspace_root, [f"f{i}.py" for i in range(5)])
    ph.max_files_per_chunk = 2
    saved = []
    real_save = ph.save_scan_progress

    def spy(chunk_num, last_path, data):
        saved.append(chunk_num)
        real_save(chunk_num, last_path, data)

    monkeypatch.setattr(ph, "save_scan_progress", spy)
    all_files = ph.scan_files_chunked()[0]
    assert len(all_files) == 5
    assert saved == [1, 2]
    assert not ph.scan_progress_file.exists()


def test_scan_progress_message_every_thousand(tmp_path, capsys):
    ph = _phase(tmp_path)
    ws = ph.workspace_root
    for i in range(1000):
        (ws / f"f{i}.txt").write_bytes(b"")
    assert len(ph.scan_files_chunked()[0]) == 1000
    assert "Scanned 1000/" in capsys.readouterr().out


def test_scan_total_limit_stops_outer_loop(tmp_path, capsys):
    ph = _phase(tmp_path)
    _files(ph.workspace_root, ["a1.py", "a2.py", "a3.py", "sub/b1.py", "sub/b2.py"])
    ph.max_total_files = 2
    all_files = ph.scan_files_chunked()[0]
    assert len(all_files) == 1
    assert "Reached total file limit (2)" in capsys.readouterr().out


def test_scan_resumes_from_saved_progress(tmp_path, capsys):
    ph = _phase(tmp_path)
    ws = ph.workspace_root
    _files(ws, ["a.py", "b.py", "c.py"])
    order = _walk_order(ws)
    ph.save_scan_progress(
        4,
        order[0],
        {
            "all_files": ["earlier.md"],
            "all_file_paths": [str(ws / "earlier.md")],
            "categorized": {"docs": 1},
            "folder_structure": {".": ["earlier.md"]},
            "markdown_files": ["earlier.md"],
            "python_files": [],
            "notebook_files": [],
        },
    )
    all_files, paths, cat, folders, md, py, nb = ph.scan_files_chunked()
    out = capsys.readouterr().out
    assert "Resuming from chunk 4" in out
    assert "Resumed at:" in out
    assert all_files[0] == "earlier.md"
    assert len(all_files) == 3
    assert (cat["docs"], cat["code"], cat["data"]) == (1, 2, 0)
    assert md == ["earlier.md"]
    assert "Total chunks: 5" in out
    assert not ph.scan_progress_file.exists()


def test_calculate_artifact_ranking(tmp_path, capsys):
    ph = _phase(tmp_path)
    assert ph.calculate_artifact_ranking(1) is None
    rf = tmp_path / "out" / "artifact_rankings.json"
    rf.parent.mkdir(parents=True, exist_ok=True)
    rf.write_text(json.dumps({"total_ranked": 2}), encoding="utf-8")
    assert ph.calculate_artifact_ranking(1) == {"total_ranked": 2}
    rf.write_text("{bad", encoding="utf-8")
    assert ph.calculate_artifact_ranking(1) is None
    assert "Error calculating rankings" in capsys.readouterr().out


def test_load_previous_feedback(cwd, capsys):
    ph = _phase(cwd)
    assert ph._load_previous_feedback(1) is None
    assert ph._load_previous_feedback(3) is None
    fb = (
        cwd
        / "DMAIC_V3_OUTPUT"
        / "iteration_2"
        / "phase7_action_tracking"
        / "feedback_for_next_iteration.json"
    )
    fb.parent.mkdir(parents=True)
    fb.write_text(json.dumps({"source_iteration": 2}), encoding="utf-8")
    assert ph._load_previous_feedback(3) == {"source_iteration": 2}
    fb.write_text("{bad", encoding="utf-8")
    assert ph._load_previous_feedback(3) is None
    assert "Failed to load feedback" in capsys.readouterr().out


def test_run_end_to_end_with_feedback_and_rankings(cwd, capsys):
    ph = _phase(cwd)
    _files(
        ph.workspace_root,
        ["pkg/parser.md", "pkg/parser.py", "pkg/other.py", "pkg/parser.ipynb"],
    )
    fb = (
        cwd
        / "DMAIC_V3_OUTPUT"
        / "iteration_1"
        / "phase7_action_tracking"
        / "feedback_for_next_iteration.json"
    )
    fb.parent.mkdir(parents=True)
    fb.write_text(
        json.dumps({"source_iteration": 1, "pending_actions": [1, 2]}),
        encoding="utf-8",
    )
    rf = cwd / "out" / "artifact_rankings.json"
    rf.parent.mkdir(parents=True, exist_ok=True)
    rf.write_text(json.dumps({"total_ranked": 2}), encoding="utf-8")

    ok, res = ph.execute(2)
    assert ok is True
    assert res["total_files"] == 4
    assert res["code_files"] == 2
    assert res["documentation_files"] == 1
    assert res["folders_scanned"] == 1
    kinds = sorted(
        "code" if "code" in r else "notebook" for r in res["file_relationships"]
    )
    assert kinds == ["code", "notebook"]
    assert res["artifact_rankings"] == {"total_ranked": 2}
    out = capsys.readouterr().out
    assert "Pending actions: 2" in out
    assert "Artifacts ranked: 2" in out

    out_dir = cwd / "out" / "iteration_2" / "phase1_define"
    saved = json.loads((out_dir / "phase1_define.json").read_text(encoding="utf-8"))
    assert saved["total_files"] == 4
    book = (out_dir / "DEFINE_BOOK_iteration_2.md").read_text(encoding="utf-8")
    assert "## Artifact Rankings" in book
    assert "Total artifacts ranked: 2" in book
    yaml_text = (out_dir / "ranking_iteration_2.yaml").read_text(encoding="utf-8")
    assert yaml_text.count("artifact: placeholder_") == 4
    report = (out_dir / "analysis_report_iteration_2.md").read_text(encoding="utf-8")
    assert "- **code:** 2 (50.0%)" in report


def test_report_generators_without_rankings(tmp_path):
    ph = _phase(tmp_path)
    tmp_out = tmp_path / "gen"
    tmp_out.mkdir()
    results = {
        "total_files": 0,
        "folders_scanned": 0,
        "categorized": {"code": 0},
        "changes": {"added": 1, "modified": 2, "deleted": 3, "total": 6},
        "artifact_rankings": None,
    }
    book = ph._generate_define_book(results, tmp_out, 1).read_text(encoding="utf-8")
    assert "## Change Detection" in book
    assert "**Total Changes:** 6" in book
    assert "Artifact Rankings" not in book
    yml = ph._generate_ranking_yaml(results, tmp_out, 1).read_text(encoding="utf-8")
    assert "top_30: []" in yml
    rep = ph._generate_analysis_report(results, tmp_out, 1).read_text(encoding="utf-8")
    assert "- **code:** 0 (0.0%)" in rep


def _fake_scan(md, py, nb):
    def scan():
        files = md + py + nb
        return files, [], {"docs": len(md)}, {}, md, py, nb

    return scan


def test_run_relationship_limit_with_code(tmp_path, monkeypatch, capsys):
    ph = _phase(tmp_path)
    py = [f"a/x{i}.py" for i in range(1001)]
    monkeypatch.setattr(
        ph, "scan_files_chunked", _fake_scan(["a/x.md", "a/y.md"], py, [])
    )
    ok, res = ph.run(1)
    assert ok is True
    assert len(res["file_relationships"]) == 1000
    assert "Reached relationship limit (1000)" in capsys.readouterr().out


def test_run_relationship_limit_with_notebooks(tmp_path, monkeypatch):
    ph = _phase(tmp_path)
    nb = [f"b/n{i}.ipynb" for i in range(1001)]
    monkeypatch.setattr(ph, "scan_files_chunked", _fake_scan(["b/n.md"], [], nb))
    ok, res = ph.run(1)
    assert ok is True
    assert len(res["file_relationships"]) == 1000
    assert all("notebook" in r for r in res["file_relationships"])


def test_run_failure_returns_error_payload(tmp_path, monkeypatch):
    ph = _phase(tmp_path)

    def boom():
        raise RuntimeError("walk failed")

    monkeypatch.setattr(ph, "scan_files_chunked", boom)
    ok, res = ph.run(1)
    assert ok is False
    assert res["error"] == "walk failed"
    assert res["total_files"] == 0


def check_production_defect_define_book_reads_capitalised_categories(tmp_path):
    # Pins a production_defect: the DEFINE book looks up 'Code'/'Documentation'
    # while categorized uses 'code'/'docs', so it always reports 0. This check
    # will fail once the lookup keys are fixed.
    ph = _phase(tmp_path)
    tmp_out = tmp_path / "gen"
    tmp_out.mkdir()
    results = {
        "total_files": 5,
        "folders_scanned": 1,
        "categorized": {"code": 3, "docs": 2},
    }
    book = ph._generate_define_book(results, tmp_out, 1).read_text(encoding="utf-8")
    assert "**Code Files:** 0" in book
    assert "**Documentation Files:** 0" in book
