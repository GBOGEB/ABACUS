"""Behaviour tests for scripts/mip_debug_diagnostic.py.

The real kit validator under ``.codex`` is exercised for the PASS path; fake
validators written into ``tmp_path`` drive each fail-closed branch.
"""

import json
import sys
from types import SimpleNamespace

import pytest

from tests.coverage_waves.lane_b._l2_loader import load

mod = load("scripts/mip_debug_diagnostic.py", name="abn_mip_debug_diagnostic")


def _validator(tmp_path, body):
    path = tmp_path / "validate_receipt.py"
    path.write_text(body, encoding="utf-8")
    return path


def test_probe_target_raises_lookup_error_on_target_line():
    with pytest.raises(LookupError, match="mip debug diagnostic"):
        mod.mip_debug_probe_target()
    code = mod.mip_debug_probe_target.__code__
    assert mod.TARGET_LINE == code.co_firstlineno + 1


def test_traceback_localizes_true_for_real_target():
    assert mod.traceback_localizes() is True


def test_traceback_localizes_false_when_target_does_not_raise(monkeypatch):
    monkeypatch.setattr(mod, "mip_debug_probe_target", lambda: None)
    assert mod.traceback_localizes() is False


def test_traceback_localizes_false_when_frame_is_elsewhere(monkeypatch):
    def other():
        raise LookupError("mip debug diagnostic")

    monkeypatch.setattr(mod, "mip_debug_probe_target", other)
    assert mod.traceback_localizes() is False


def test_validator_fails_closed_true_with_real_kit_validator():
    assert mod.VALIDATOR.is_file()
    assert mod.validator_fails_closed() is True


def test_validator_missing_is_false(monkeypatch, tmp_path):
    monkeypatch.setattr(mod, "VALIDATOR", tmp_path / "absent.py")
    assert mod.validator_fails_closed() is False


def test_validator_without_spec_is_false(monkeypatch, tmp_path):
    monkeypatch.setattr(mod, "VALIDATOR", _validator(tmp_path, "x = 1\n"))
    fake_util = SimpleNamespace(spec_from_file_location=lambda *a: None)
    monkeypatch.setattr(mod, "importlib", SimpleNamespace(util=fake_util))
    assert mod.validator_fails_closed() is False


def test_validator_that_accepts_fail_receipt_is_false(monkeypatch, tmp_path):
    body = "def validate_producer(data, sha):\n    return 'ok'\n"
    monkeypatch.setattr(mod, "VALIDATOR", _validator(tmp_path, body))
    assert mod.validator_fails_closed() is False


def test_validator_raising_other_error_is_false(monkeypatch, tmp_path):
    body = "def validate_producer(data, sha):\n    raise ValueError('bad')\n"
    monkeypatch.setattr(mod, "VALIDATOR", _validator(tmp_path, body))
    assert mod.validator_fails_closed() is False


def test_validator_exit_without_expected_message_is_false(monkeypatch, tmp_path):
    body = "def validate_producer(data, sha):\n    raise SystemExit('nope')\n"
    monkeypatch.setattr(mod, "VALIDATOR", _validator(tmp_path, body))
    assert mod.validator_fails_closed() is False


def test_validator_receives_a_copy_of_failing_receipt(monkeypatch, tmp_path):
    body = (
        "seen = []\n"
        "def validate_producer(data, sha):\n"
        "    data['mutated'] = True\n"
        "    raise SystemExit('receipt validation failed: verification')\n"
    )
    monkeypatch.setattr(mod, "VALIDATOR", _validator(tmp_path, body))
    assert mod.validator_fails_closed() is True
    assert "mutated" not in mod.FAILING_RECEIPT


def test_build_receipt_pass_shape():
    receipt = mod.build_receipt()
    assert receipt["verification"] == "PASS"
    assert receipt["failed_checks"] == []
    assert receipt["diagnostic"] == mod.DIAGNOSTIC_NAME
    assert set(receipt["checks"]) == {"traceback_localizes", "validator_fails_closed"}


def test_build_receipt_fail_lists_sorted_failures(monkeypatch):
    monkeypatch.setattr(mod, "traceback_localizes", lambda: False)
    monkeypatch.setattr(mod, "validator_fails_closed", lambda: False)
    receipt = mod.build_receipt()
    assert receipt["verification"] == "FAIL"
    assert receipt["failed_checks"] == ["traceback_localizes", "validator_fails_closed"]


def test_main_pass_writes_receipt_and_returns_0(monkeypatch, tmp_path, capsys):
    out = tmp_path / "nested" / "receipt.json"
    monkeypatch.setattr(sys, "argv", ["prog", "--output", str(out)])
    assert mod.main() == 0
    written = json.loads(out.read_text(encoding="utf-8"))
    assert written["verification"] == "PASS"
    assert json.loads(capsys.readouterr().out) == written


def test_main_fail_returns_1(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(mod, "VALIDATOR", tmp_path / "absent.py")
    out = tmp_path / "r.json"
    monkeypatch.setattr(sys, "argv", ["prog", "--output", str(out)])
    assert mod.main() == 1
    printed = json.loads(capsys.readouterr().out)
    assert printed["failed_checks"] == ["validator_fails_closed"]
