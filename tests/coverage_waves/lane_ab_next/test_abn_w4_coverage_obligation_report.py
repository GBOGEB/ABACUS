"""Behaviour tests for tools/everred_v3/scripts/coverage_obligation_report.py.

``obligation_lineage`` is replaced by a recording stub so the CLI wiring
(argument parsing, file reads, output writing, receipt printing) is tested in
isolation from the lineage algebra.
"""

import json
import runpy
import sys
import types

import pytest

from tests.coverage_waves.lane_b._l2_loader import REPO_ROOT, load

REL = "tools/everred_v3/scripts/coverage_obligation_report.py"
SCRIPT = REPO_ROOT / REL


def _make_stub():
    stub = types.ModuleType("obligation_lineage")
    stub.calls = []

    def parse_artifact(raw, manifest):
        stub.calls.append((raw, manifest))
        return dict(raw=raw.decode("utf-8"), sha=manifest["sha"])

    def compare(before, after):
        return dict(
            before_sha=before["sha"],
            after_sha=after["sha"],
            status="NO_REGRESSION",
            merge_admission="HOLD",
            detail=[before["raw"], after["raw"]],
        )

    stub.parse_artifact = parse_artifact
    stub.compare = compare
    return stub


STUB = _make_stub()
_saved_path = list(sys.path)
mod = load(
    REL, name="abn_coverage_obligation_report", deps={"obligation_lineage": STUB}
)
sys.path[:] = _saved_path


def _inputs(tmp_path):
    files = {}
    for label, sha in (("before", "1" * 40), ("after", "2" * 40)):
        js = tmp_path / (label + ".json")
        js.write_bytes(("{" + label + "}").encode("utf-8"))
        man = tmp_path / (label + "_manifest.json")
        man.write_bytes(json.dumps(dict(sha=sha)).encode("utf-8"))
        files[label] = (js, man)
    return files


def _argv(files, out):
    argv = []
    for label in ("before", "after"):
        js, man = files[label]
        argv += ["--" + label + "-json", str(js), "--" + label + "-manifest", str(man)]
    return argv + ["--out", str(out)]


def test_main_writes_report_and_prints_receipt(tmp_path, capsys, monkeypatch):
    files = _inputs(tmp_path)
    out = tmp_path / "deep" / "report.json"
    STUB.calls.clear()
    monkeypatch.setattr(sys, "argv", ["prog"] + _argv(files, out))
    mod.main()
    printed = json.loads(capsys.readouterr().out)
    assert printed == dict(
        before_sha="1" * 40,
        after_sha="2" * 40,
        status="NO_REGRESSION",
        merge_admission="HOLD",
    )
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["detail"] == ["{before}", "{after}"]
    assert [c[0] for c in STUB.calls] == [b"{before}", b"{after}"]
    assert out.read_text(encoding="utf-8").endswith("}\n")


def test_main_requires_all_arguments(tmp_path, monkeypatch, capsys):
    files = _inputs(tmp_path)
    argv = _argv(files, tmp_path / "o.json")
    monkeypatch.setattr(sys, "argv", ["prog"] + argv[:-2])
    with pytest.raises(SystemExit):
        mod.main()
    assert "--out" in capsys.readouterr().err


def test_main_missing_input_file(tmp_path, monkeypatch):
    files = _inputs(tmp_path)
    files["after"][0].unlink()
    monkeypatch.setattr(sys, "argv", ["prog"] + _argv(files, tmp_path / "o.json"))
    with pytest.raises(FileNotFoundError):
        mod.main()
    assert not (tmp_path / "o.json").exists()


def test_run_as_script(tmp_path, capsys, monkeypatch):
    files = _inputs(tmp_path)
    out = tmp_path / "r.json"
    monkeypatch.setattr(sys, "path", list(sys.path))
    monkeypatch.setitem(sys.modules, "obligation_lineage", _make_stub())
    monkeypatch.setattr(sys, "argv", [str(SCRIPT)] + _argv(files, out))
    runpy.run_path(str(SCRIPT), run_name="__main__")
    assert json.loads(capsys.readouterr().out)["status"] == "NO_REGRESSION"
    assert out.is_file()
