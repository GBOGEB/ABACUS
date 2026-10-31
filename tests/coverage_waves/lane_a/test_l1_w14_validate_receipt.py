"""Lane A wave 14: mip-repo-self-index validate_receipt producer/consumer checks."""

import json
import sys

import pytest

from tests.coverage_waves.lane_a._load import load

REL = ".codex/skills/mip-repo-self-index/scripts/validate_receipt.py"
SHA = "d" * 40


def _import():
    saved_path = list(sys.path)
    saved_mods = set(sys.modules)
    try:
        return load(REL, name="l1_w14_validate_receipt")
    finally:
        sys.path[:] = saved_path
        for key in set(sys.modules) - saved_mods:
            del sys.modules[key]


vr = _import()


def _producer(**over):
    data = {
        "schema_version": "0.1",
        "program": "MIP",
        "verification": "PASS",
        "repository": "GBOGEB/ABACUS",
        "head_sha": SHA,
        "raw_receipt_retention": "transient_runner_only",
        "root_self_index": {"runs": 2, "normalized_equal": True},
    }
    data.update(over)
    return data


def _consumer(**over):
    data = {
        "schema_version": "0.1",
        "program": "MIP",
        "consumer_verification": "PASS",
        "repository": "GBOGEB/ABACUS",
        "head_sha": SHA,
        "producer_artifact": "mip-self-index",
        "checks": ["a"],
        "raw_receipt_retention": "transient_runner_only",
    }
    data.update(over)
    return data


def _write(path, value):
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def test_load_object_and_non_object(tmp_path):
    assert vr.load(_write(tmp_path / "a.json", {"k": 1})) == {"k": 1}
    with pytest.raises(TypeError, match="expected a JSON object"):
        vr.load(_write(tmp_path / "b.json", [1]))


def test_require_lists_failed_sorted():
    vr.require({"a": True})
    with pytest.raises(SystemExit, match="failed: b, c"):
        vr.require({"c": False, "a": True, "b": False})


def test_producer_with_all_optional_sections():
    data = _producer(
        nested_surface={"path": "sub", "runs": 3, "normalized_equal": True},
        nested_diagnostic={
            "verification": "PASS",
            "parent_sha": SHA,
            "source_contract": "c",
            "raw_receipt_retention": "transient_runner_only",
        },
        debug_diagnostic={
            "verification": "FAIL",
            "exact_sha": SHA,
            "raw_receipt_retention": "transient_runner_only",
        },
    )
    assert vr.validate_producer(data, SHA) == SHA
    assert vr.validate_producer(data, None) == SHA


@pytest.mark.parametrize(
    "over,expected,names",
    [
        ({}, "e" * 40, ["expected_sha"]),
        ({"head_sha": ""}, None, ["head_sha"]),
        ({"root_self_index": None}, None, ["root_repeatability", "root_runs"]),
        ({"root_self_index": ["x"]}, None, ["root_repeatability", "root_runs"]),
        ({"root_self_index": {"runs": 1}}, None, ["root_repeatability", "root_runs"]),
        ({"program": "X", "verification": "FAIL"}, None, ["program", "verification"]),
        (
            {"nested_surface": "flat"},
            None,
            ["nested_object", "nested_path", "nested_repeatability", "nested_runs"],
        ),
        ({"nested_surface": {"path": "", "runs": 2}}, None, ["nested_path"]),
        (
            {"nested_diagnostic": 1},
            None,
            ["diagnostic_contract", "diagnostic_object", "diagnostic_pass"],
        ),
        (
            {"nested_diagnostic": {"verification": "PASS", "parent_sha": "x"}},
            None,
            ["diagnostic_contract", "diagnostic_retention", "diagnostic_sha"],
        ),
        ({"debug_diagnostic": "d"}, None, ["debug_object", "debug_retention"]),
        ({"debug_diagnostic": {"verification": "MAYBE"}}, None, ["debug_retention"]),
    ],
)
def test_producer_failures(over, expected, names):
    with pytest.raises(SystemExit) as exc:
        vr.validate_producer(_producer(**over), expected)
    message = str(exc.value)
    for name in names:
        assert name in message


def test_consumer_pass_and_fail():
    vr.validate_consumer(_consumer(), SHA, "GBOGEB/ABACUS")
    with pytest.raises(SystemExit) as exc:
        vr.validate_consumer(_consumer(checks=[]), "f" * 40, "other/repo")
    message = str(exc.value)
    for name in ("consumer_checks", "consumer_head_sha", "consumer_repository"):
        assert name in message


def test_main_producer_only(tmp_path, monkeypatch, capsys):
    prod = _write(tmp_path / "p.json", _producer())
    monkeypatch.setattr(sys, "argv", ["vr", str(prod), "--expected-sha", SHA])
    assert vr.main() == 0
    out = json.loads(capsys.readouterr().out)
    assert out == {"consumer_checked": False, "head_sha": SHA, "verification": "PASS"}


def test_main_with_consumer(tmp_path, monkeypatch, capsys):
    prod = _write(tmp_path / "p.json", _producer())
    cons = _write(tmp_path / "c.json", _consumer())
    monkeypatch.setattr(sys, "argv", ["vr", str(prod), "--consumer", str(cons)])
    assert vr.main() == 0
    assert json.loads(capsys.readouterr().out)["consumer_checked"] is True


def check_production_defect_non_numeric_runs_crashes():
    # Pins a production_defect: a malformed "runs" value raises a raw
    # TypeError/ValueError instead of a "receipt validation failed" verdict.
    # This check will fail once the validator handles it.
    with pytest.raises(TypeError):
        vr.validate_producer(_producer(root_self_index={"runs": None}), None)
    with pytest.raises(ValueError):
        vr.validate_producer(_producer(root_self_index={"runs": "two"}), None)
