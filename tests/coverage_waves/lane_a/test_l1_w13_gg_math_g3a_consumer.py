"""Lane A wave 13: MIP.statistics.gg_math_g3a_consumer paths not in the base suite."""

import copy
import json
import sys
import types

import pytest

from MIP.statistics import gg_math_g3a_consumer as gg

SAMPLE = {
    "schema": "code-purple.mip.g3a.statistical-control.v1",
    "lineage": {
        "n13_sha": "b16ba5c6ff3d4106db9ac5cfb3d3164b3206cb52",
        "n13_run": 39040416656,
        "n14_sha": "1446d78a6e93a455d9bed71f070a6b460dc6e86d",
        "n14_run": 39046868554,
        "coverage_version": "7.16.2",
        "source_bytes_frozen": True,
        "exact_arcs_rejoined": True,
    },
    "aggregate": {
        "eligible": 446,
        "n13_covered": 115,
        "n14_covered": 200,
        "six_sigma": "NOT_ASSESSED_FROM_BRANCH_COVERAGE",
    },
    "controls": {"merge_admission": "HOLD"},
    "modules": [
        {
            "path": "DMAIC_V3/debug_pipeline.py",
            "eligible": 116,
            "n13": 17,
            "n14": 94,
            "gained": 77,
            "lost": 0,
        },
        {
            "path": "DMAIC_V3/phases/phase4_improve.py",
            "eligible": 134,
            "n13": 45,
            "n14": 53,
            "gained": 8,
            "lost": 0,
        },
        {
            "path": "DMAIC_V3/phases/phase8_todo_management.py",
            "eligible": 118,
            "n13": 30,
            "n14": 30,
            "gained": 0,
            "lost": 0,
        },
        {
            "path": "cicd_github_orchestrator.py",
            "eligible": 78,
            "n13": 23,
            "n14": 23,
            "gained": 0,
            "lost": 0,
        },
    ],
}


def _snap():
    return copy.deepcopy(SAMPLE)


def test_wrong_schema_rejected():
    snap = _snap()
    snap["schema"] = "other"
    with pytest.raises(ValueError, match="schema"):
        gg.transform(snap)


def test_module_numerator_mismatch_rejected():
    snap = _snap()
    snap["modules"][0]["n13"] = 18
    snap["modules"][0]["gained"] = 76
    with pytest.raises(ValueError, match="numerator mismatch"):
        gg.transform(snap)


def test_non_exact_sha_rejected():
    snap = _snap()
    snap["lineage"]["n13_sha"] = "ABC"
    with pytest.raises(ValueError, match="non-exact SHA"):
        gg.transform(snap)


def test_bool_run_rejected():
    snap = _snap()
    snap["lineage"]["n13_run"] = True
    with pytest.raises(ValueError, match="run ID"):
        gg.transform(snap)


def test_transform_rows():
    rows = gg.transform(_snap())["observations"]
    got = [(r["n"], r["k"], r["d"]) for r in rows]
    assert got == [(13, 115, 446), (14, 200, 446)]


def test_provider_checkout_missing(tmp_path):
    with pytest.raises(ValueError, match="checkout missing"):
        gg.run_pinned_provider({}, tmp_path)


def _provider_root(tmp_path):
    (tmp_path / "kernels").mkdir()
    (tmp_path / "kernels" / "convergence_control.py").write_text("", encoding="utf-8")
    return tmp_path


def _fixed_output(value):
    def fake(*args, **kwargs):
        return value

    return fake


def test_provider_sha_drift(tmp_path, monkeypatch):
    root = _provider_root(tmp_path)
    monkeypatch.setattr("subprocess.check_output", _fixed_output("0" * 40 + "\n"))
    with pytest.raises(ValueError, match="SHA drift"):
        gg.run_pinned_provider({}, root)


def _fake_kernel(monkeypatch, report):
    pkg = types.ModuleType("kernels")
    pkg.__path__ = []
    mod = types.ModuleType("kernels.convergence_control")

    def assess_convergence(payload):
        return dict(report, seen=payload)

    mod.assess_convergence = assess_convergence
    monkeypatch.setitem(sys.modules, "kernels", pkg)
    monkeypatch.setitem(sys.modules, "kernels.convergence_control", mod)


def test_provider_executes_and_restores_sys_path(tmp_path, monkeypatch):
    root = _provider_root(tmp_path)
    monkeypatch.setattr("subprocess.check_output", _fixed_output(gg.GG_MATH_SHA + "\n"))
    good = {
        "schema": "gg_math.convergence_receipt.v1",
        "merge_admission": "HOLD",
        "authority_transfer": False,
    }
    _fake_kernel(monkeypatch, good)
    before = list(sys.path)
    out = gg.run_pinned_provider({"p": 1}, root)
    assert sys.path == before
    assert out["status"] == "PINNED_LOCAL_PROVIDER_EXECUTED"
    assert out["result"]["seen"] == {"p": 1}


def test_provider_invalid_guards(tmp_path, monkeypatch):
    root = _provider_root(tmp_path)
    monkeypatch.setattr("subprocess.check_output", _fixed_output(gg.GG_MATH_SHA + "\n"))
    _fake_kernel(monkeypatch, {"schema": "x"})
    with pytest.raises(ValueError, match="authority guards"):
        gg.run_pinned_provider({}, root)


def test_main_source_only(tmp_path, capsys):
    snap = tmp_path / "snap.json"
    snap.write_text(json.dumps(SAMPLE), encoding="utf-8")
    out = tmp_path / "o" / "receipt.json"
    assert gg.main(["--snapshot", str(snap), "--out", str(out)]) == 0
    receipt = json.loads(out.read_text(encoding="utf-8"))
    assert receipt["provider"]["status"] == "PROVIDER_NOT_EXECUTED_SOURCE_ONLY"
    assert json.loads(capsys.readouterr().out)["merge_admission"] == "HOLD"


def test_main_with_provider_root(tmp_path, monkeypatch, capsys):
    snap = tmp_path / "snap.json"
    snap.write_text(json.dumps(SAMPLE), encoding="utf-8")
    out = tmp_path / "receipt.json"
    calls = []

    def fake_run(payload, root):
        calls.append(root)
        return {"status": "PINNED_LOCAL_PROVIDER_EXECUTED"}

    monkeypatch.setattr(gg, "run_pinned_provider", fake_run)
    args = ["--snapshot", str(snap), "--out", str(out), "--provider-root", "pr"]
    assert gg.main(args) == 0
    assert calls and calls[0].name == "pr"
    assert "PINNED_LOCAL" in capsys.readouterr().out


def _mutate(path, value):
    snap = _snap()
    target = snap
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    return snap


@pytest.mark.parametrize(
    "path,value,match",
    [
        (("aggregate", "n13_covered"), 116, "denominator drift"),
        (("lineage", "coverage_version"), "7.0", "arc evidence"),
        (("lineage", "exact_arcs_rejoined"), False, "arc evidence"),
        (("modules",), [], "scope drift"),
        (("modules", 1, "lost"), 1, "arc gain/loss"),
        (("aggregate", "six_sigma"), "YES", "Six Sigma"),
        (("controls",), {}, "admission control"),
    ],
)
def test_transform_hold_guards(path, value, match):
    with pytest.raises(ValueError, match=match):
        gg.transform(_mutate(path, value))
