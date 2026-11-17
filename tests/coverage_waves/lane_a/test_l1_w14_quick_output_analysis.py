"""Lane A wave 14: DMAIC_V3.quick_output_analysis on synthetic output trees."""

import importlib
import json
import sys


def _import_restoring_sys_path():
    saved = list(sys.path)
    try:
        return importlib.import_module("DMAIC_V3.quick_output_analysis")
    finally:
        sys.path[:] = saved


qoa = _import_restoring_sys_path()


def _iteration(root, name="iteration_1", nfiles=5):
    it = root / "DMAIC_V3_OUTPUT" / name
    p = it / "phase1_define"
    (p / "nested").mkdir(parents=True)
    for i in range(nfiles):
        (p / f"f{i}.json").write_bytes(b"{}")
    (p / "nested" / "deep.txt").write_bytes(b"12345")
    (it / "phase2_measure").mkdir()
    (it / "loose.txt").write_bytes(b"x")
    return it


def test_analyze_missing_dir(tmp_path):
    res = qoa.analyze_iteration(tmp_path / "iteration_9")
    assert res["error"] == "Directory not found"
    assert res["total_files"] == 0


def test_analyze_iteration_counts(tmp_path):
    it = _iteration(tmp_path)
    res = qoa.analyze_iteration(it)
    assert res["iteration"] == "iteration_1"
    assert res["total_files"] == 6
    assert res["total_size_bytes"] == 15
    assert set(res["phases"]) == {"phase1_define", "phase2_measure"}
    assert res["phases"]["phase2_measure"]["file_count"] == 0
    paths = {
        f["path"].replace("\\", "/") for f in res["phases"]["phase1_define"]["files"]
    }
    assert "phase1_define/nested/deep.txt" in paths


def test_analyze_records_skipped_files(tmp_path, monkeypatch):
    it = _iteration(tmp_path, nfiles=1)
    original = qoa.Path.relative_to

    def flaky(self, *other, **kw):
        if self.name == "deep.txt":
            raise ValueError("not relative")
        return original(self, *other, **kw)

    monkeypatch.setattr(qoa.Path, "relative_to", flaky)
    res = qoa.analyze_iteration(it)
    phase = res["phases"]["phase1_define"]
    assert [s["name"] for s in phase["skipped_files"]] == ["deep.txt"]
    assert phase["skipped_files"][0]["error"] == "not relative"
    assert res["total_size_bytes"] == 2


def test_load_json_file(tmp_path):
    good = tmp_path / "g.json"
    good.write_text('{"a": 1}', encoding="utf-8")
    assert qoa.load_json_file(good) == {"a": 1}
    assert "error" in qoa.load_json_file(tmp_path / "missing.json")


def test_main_without_output(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert qoa.main() == 1
    assert "not found" in capsys.readouterr().out


def test_main_full_report(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    it1 = _iteration(tmp_path)
    _iteration(tmp_path, name="iteration_2", nfiles=1)
    (tmp_path / "DMAIC_V3_OUTPUT" / "notes").mkdir()
    registry = {
        "version": "9",
        "agents": {
            "a1": {"category": "core", "name": "Alpha"},
            "a2": {"category": "core"},
            "a3": {},
        },
    }
    (tmp_path / "DMAIC_V3_OUTPUT" / "agent_registry.json").write_text(
        json.dumps(registry), encoding="utf-8"
    )
    stats = {"orchestration": {"total_phases": 9, "total_duration_seconds": 1.5}}
    (it1 / "orchestration_statistics.json").write_text(
        json.dumps(stats), encoding="utf-8"
    )
    assert qoa.main() == 0
    out = capsys.readouterr().out
    assert "Found 2 iterations" in out
    assert "... and 3 more" in out
    assert "Total Agents: 3" in out
    assert "CORE: Alpha, a2" in out
    assert "UNKNOWN: a3" in out
    assert "Total Phases: 9" in out
    assert "Duration: 1.50s" in out


def test_main_registry_without_agents(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    it = _iteration(tmp_path, nfiles=1)
    out_root = tmp_path / "DMAIC_V3_OUTPUT"
    (out_root / "agent_registry.json").write_text("{}", encoding="utf-8")
    (it / "orchestration_statistics.json").write_text("{}", encoding="utf-8")
    assert qoa.main() == 0
    out = capsys.readouterr().out
    assert "AGENT REGISTRY" in out
    assert "Total Agents" not in out
    assert "Total Phases" not in out


def test_main_includes_any_iteration_prefix(tmp_path, monkeypatch, capsys):
    name = "iteration_x"
    monkeypatch.chdir(tmp_path)
    _iteration(tmp_path, name=name, nfiles=0)
    assert qoa.main() == 0
    assert name.upper() in capsys.readouterr().out
