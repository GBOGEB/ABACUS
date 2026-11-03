"""Behaviour tests for tools/everred_v3/scripts/build_top21_rollout.py.

``top21_rollout.rollout_census`` is replaced by a recording stub so the tests
exercise the script's argument handling, optional inputs, render and
fail-closed --check mode. All files live under tmp_path.
"""

import importlib.util
import json
import sys
import types

import pytest

from tests.coverage_waves.lane_b._l2_loader import REPO_ROOT, load

REL = "tools/everred_v3/scripts/build_top21_rollout.py"
SCRIPT = REPO_ROOT / REL
CALLS = []


def _rollout_census(contract, receipts=None, ranking=None):
    CALLS.append((contract, receipts, ranking))
    return {
        "schema": "abacus.everred.top21.rollout.v1",
        "contract": contract,
        "receipts": receipts,
        "ranking": ranking,
    }


def _stub():
    stub = types.ModuleType("top21_rollout")
    stub.rollout_census = _rollout_census
    return stub


DEPS = {"top21_rollout": _stub()}
_saved_path = list(sys.path)
mod = load(REL, name="abn_w4_build_top21_rollout", deps=DEPS)
sys.path[:] = _saved_path


@pytest.fixture(autouse=True)
def _reset_calls():
    CALLS.clear()
    yield
    CALLS.clear()


def _write(path, obj):
    path.write_bytes(json.dumps(obj).encode("utf-8"))
    return path


def _expected(contract, receipts=None, ranking=None):
    result = _rollout_census(contract, receipts, ranking)
    CALLS.pop()
    return json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n"


def test_main_writes_report_with_contract_only(tmp_path):
    contract = _write(tmp_path / "c.json", {"schema_version": 1})
    out = tmp_path / "nested" / "report.json"
    rc = mod.main(["--contract", str(contract), "--output", str(out)])
    assert rc == 0
    assert CALLS == [({"schema_version": 1}, None, None)]
    assert out.read_text(encoding="utf-8") == _expected({"schema_version": 1})


def test_main_reads_optional_ranking_and_receipts(tmp_path):
    contract = _write(tmp_path / "c.json", {"schema_version": 2})
    receipts = _write(tmp_path / "r.json", {"rows": [1]})
    ranking = _write(tmp_path / "k.json", {"ranks": ["a/b"]})
    out = tmp_path / "report.json"
    args = [
        "--contract",
        str(contract),
        "--output",
        str(out),
        "--ranking",
        str(ranking),
        "--receipts",
        str(receipts),
    ]
    assert mod.main(args) == 0
    assert CALLS == [({"schema_version": 2}, {"rows": [1]}, {"ranks": ["a/b"]})]
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["ranking"] == {"ranks": ["a/b"]}
    assert report["receipts"] == {"rows": [1]}


def test_check_passes_on_fresh_report(tmp_path):
    contract = _write(tmp_path / "c.json", {"schema_version": 1})
    out = tmp_path / "report.json"
    args = ["--contract", str(contract), "--output", str(out)]
    assert mod.main(args) == 0
    before = out.read_bytes()
    assert mod.main(args + ["--check"]) == 0
    assert out.read_bytes() == before


def test_check_fails_when_report_missing(tmp_path, capsys):
    contract = _write(tmp_path / "c.json", {"schema_version": 1})
    out = tmp_path / "absent.json"
    rc = mod.main(["--contract", str(contract), "--output", str(out), "--check"])
    assert rc == 1
    assert "TOP21 report absent or stale" in capsys.readouterr().err
    assert not out.exists()


def test_check_fails_when_report_stale(tmp_path, capsys):
    contract = _write(tmp_path / "c.json", {"schema_version": 1})
    out = tmp_path / "report.json"
    out.write_text("{}\n", encoding="utf-8")
    rc = mod.main(["--contract", str(contract), "--output", str(out), "--check"])
    assert rc == 1
    assert "absent or stale" in capsys.readouterr().err
    assert out.read_text(encoding="utf-8") == "{}\n"


def test_contract_and_output_are_required(capsys):
    with pytest.raises(SystemExit) as exc:
        mod.main(["--contract", "c.json"])
    assert exc.value.code == 2
    assert "--output" in capsys.readouterr().err


def test_script_entry_point_exits_with_main_status(tmp_path, monkeypatch):
    contract = _write(tmp_path / "c.json", {"schema_version": 3})
    out = tmp_path / "entry.json"
    argv = [str(SCRIPT), "--contract", str(contract), "--output", str(out)]
    monkeypatch.setattr(sys, "argv", argv)
    spec = importlib.util.spec_from_file_location("__main__", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    saved_path = list(sys.path)
    saved = sys.modules.get("top21_rollout")
    sys.modules.update(DEPS)
    try:
        with pytest.raises(SystemExit) as exc:
            spec.loader.exec_module(module)
    finally:
        sys.path[:] = saved_path
        if saved is None:
            sys.modules.pop("top21_rollout", None)
        else:
            sys.modules["top21_rollout"] = saved
    assert exc.value.code == 0
    assert json.loads(out.read_text(encoding="utf-8"))["contract"] == {
        "schema_version": 3
    }
