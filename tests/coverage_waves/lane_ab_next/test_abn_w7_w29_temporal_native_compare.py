"""Gap tests for tools/recovery/w29_temporal_native_compare.py (main)."""

import hashlib
import json
import types

import pytest

from tests.coverage_waves.lane_b._l2_loader import load

temporal = load(
    "scripts/cbd_coverage_temporal_gate.py",
    name="abn_w7_cbd_coverage_temporal_gate",
)
_SCRIPTS = types.ModuleType("scripts")
_SCRIPTS.cbd_coverage_temporal_gate = temporal
mod = load(
    "tools/recovery/w29_temporal_native_compare.py",
    name="abn_w7_w29_temporal_native_compare",
    deps={"scripts": _SCRIPTS, "scripts.cbd_coverage_temporal_gate": temporal},
)


def _argv(tmp_path):
    return [
        "--before-cov",
        str(tmp_path / "b.json"),
        "--after-cov",
        str(tmp_path / "a.json"),
        "--before-junit",
        str(tmp_path / "b.xml"),
        "--after-junit",
        str(tmp_path / "a.xml"),
        "--exact-head",
        "f" * 40,
        "--out",
        str(tmp_path / "out" / "receipt.json"),
    ]


@pytest.fixture
def wired(monkeypatch, tmp_path):
    calls = {}
    monkeypatch.setattr(mod, "coverage_from", lambda path: ("cov", path.name))
    monkeypatch.setattr(mod, "junit_from", lambda path: ("junit", path.name))

    def fake_compare(old, new, old_cases, new_cases, exact_head):
        calls["args"] = (old, new, old_cases, new_cases, exact_head)
        return {"delta": {"covered_statements": 3}, "merge_admission": "HOLD"}

    monkeypatch.setattr(mod, "compare", fake_compare)
    monkeypatch.chdir(tmp_path)
    (tmp_path / "scripts").mkdir()
    return calls


def test_main_writes_receipt_with_source_hash(wired, tmp_path, capsys):
    source = b"print(1)\n"
    (tmp_path / "scripts" / "cbd_coverage_temporal_gate.py").write_bytes(source)
    assert mod.main(_argv(tmp_path)) == 0
    assert wired["args"] == (
        ("cov", "b.json"),
        ("cov", "a.json"),
        ("junit", "b.xml"),
        ("junit", "a.xml"),
        "f" * 40,
    )
    receipt = json.loads(
        (tmp_path / "out" / "receipt.json").read_text(encoding="utf-8")
    )
    assert receipt["source_sha256"] == hashlib.sha256(source).hexdigest()
    printed = json.loads(capsys.readouterr().out)
    assert printed == {
        "admission": "HOLD",
        "delta": {"covered_statements": 3},
        "head": "f" * 40,
    }


def test_main_rejects_empty_source_module(wired, tmp_path):
    (tmp_path / "scripts" / "cbd_coverage_temporal_gate.py").write_bytes(b"")
    with pytest.raises(ValueError, match="missing exact physical module"):
        mod.main(_argv(tmp_path))
    assert not (tmp_path / "out").exists()
