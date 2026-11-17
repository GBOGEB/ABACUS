"""Behaviour tests for scripts/mip_health_selfheal_probe.py.

``git`` is answered by a fake ``subprocess.check_output`` and the transient
fixture directory is redirected into ``tmp_path``. The real
``DMAIC_V3.quick_error_fix.QuickFixer`` performs the repair.
"""

import contextlib
import json
import sys
from types import SimpleNamespace

import pytest

from tests.coverage_waves.lane_b._l2_loader import load

_saved_path = list(sys.path)
mod = load("scripts/mip_health_selfheal_probe.py", name="abn_mip_health_selfheal")
sys.path[:] = _saved_path

SHA = "a" * 40


class _Git:
    def __init__(self, statuses):
        self.statuses = list(statuses)
        self.calls = []

    def __call__(self, cmd, **kwargs):
        self.calls.append((cmd, kwargs))
        if cmd[3:] == ["rev-parse", "HEAD"]:
            return SHA + "\n"
        return self.statuses.pop(0) if len(self.statuses) > 1 else self.statuses[0]


@pytest.fixture
def fixture_dir(tmp_path, monkeypatch):
    target = tmp_path / "fixture_dir"
    target.mkdir()

    @contextlib.contextmanager
    def temp_dir(prefix=""):
        yield str(target)

    monkeypatch.setattr(mod, "tempfile", SimpleNamespace(TemporaryDirectory=temp_dir))
    return target


def _use_git(monkeypatch, *statuses):
    fake = _Git(statuses or ("",))
    monkeypatch.setattr(mod.subprocess, "check_output", fake)
    return fake


def test_git_invokes_git_dash_c_root_and_strips(monkeypatch):
    fake = _use_git(monkeypatch, "  M file.py \n")
    assert mod.git("status", "--porcelain") == "M file.py"
    cmd, kwargs = fake.calls[0]
    assert cmd == ["git", "-C", str(mod.ROOT), "status", "--porcelain"]
    assert kwargs["text"] is True


def test_sha256_text_and_compile_ok():
    expected = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    assert mod.sha256_text("") == expected
    assert mod.compile_ok(mod.BEFORE) is True
    assert mod.compile_ok("def broken(:\n") is False


def test_recompute_verification_pass_and_fail():
    receipt = {"checks": {"b": True, "a": True}}
    mod._recompute_verification(receipt)
    assert receipt["verification"] == "PASS"
    assert receipt["return_state"] == "IMPROVED"
    assert receipt["failed_checks"] == []
    receipt["checks"].update(z=False, c=False)
    mod._recompute_verification(receipt)
    assert receipt["verification"] == "FAIL"
    assert receipt["return_state"] == "REGRESSED"
    assert receipt["failed_checks"] == ["c", "z"]


def test_build_receipt_pass_on_clean_checkout(monkeypatch, fixture_dir):
    _use_git(monkeypatch, "")
    receipt = mod.build_receipt()
    assert receipt["verification"] == "PASS"
    assert receipt["return_state"] == "IMPROVED"
    assert receipt["exact_sha"] == SHA
    assert (receipt["before_metric"], receipt["after_metric"]) == (1, 0)
    assert receipt["delta"] == -1
    assert receipt["fixture_before_sha256"] == mod.sha256_text(mod.BEFORE)
    assert receipt["fixture_after_sha256"] == mod.sha256_text(mod.AFTER)
    assert all(receipt["checks"].values())
    assert receipt["promotion_authority"] is False
    fixture = fixture_dir / "fixture.py"
    assert fixture.read_text(encoding="utf-8") == mod.AFTER


def test_build_receipt_fails_when_checkout_dirty(monkeypatch, fixture_dir):
    _use_git(monkeypatch, " M x.py", " M x.py")
    receipt = mod.build_receipt()
    assert receipt["verification"] == "FAIL"
    assert receipt["return_state"] == "REGRESSED"
    assert receipt["source_checkout_unchanged"] is False
    assert receipt["failed_checks"] == [
        "source_checkout_clean_after_repair",
        "source_checkout_clean_before",
        "source_checkout_unchanged",
    ]


def test_build_receipt_fails_when_fixer_does_nothing(monkeypatch, fixture_dir):
    class NoopFixer:
        def __init__(self):
            self.fixes_applied = []

        def fix_type_hints(self, path):
            return False

    _use_git(monkeypatch, "")
    monkeypatch.setattr(mod, "QuickFixer", NoopFixer)
    receipt = mod.build_receipt()
    assert receipt["verification"] == "FAIL"
    assert receipt["delta"] == 0
    assert receipt["failed_checks"] == [
        "after_fixture_exact",
        "after_metric_closed",
        "improvement_delta",
        "repair_applied",
        "repair_recorded",
        "repair_status_success",
    ]


def test_main_with_output_pass(monkeypatch, fixture_dir, tmp_path, capsys):
    _use_git(monkeypatch, "")
    out = tmp_path / "out" / "receipt.json"
    monkeypatch.setattr(sys, "argv", ["prog", "--output", str(out)])
    assert mod.main() == 0
    written = json.loads(out.read_text(encoding="utf-8"))
    assert written["checks"]["source_checkout_clean_after_output"] is True
    assert written["verification"] == "PASS"
    assert json.loads(capsys.readouterr().out) == written


def test_main_without_output_fails_on_late_dirty_checkout(
    monkeypatch, fixture_dir, capsys
):
    _use_git(monkeypatch, "", "", "?? receipt.json")
    monkeypatch.setattr(sys, "argv", ["prog"])
    assert mod.main() == 1
    printed = json.loads(capsys.readouterr().out)
    assert printed["checks"]["source_checkout_clean_after_output"] is False
    assert printed["source_checkout_unchanged"] is False
    assert printed["checks"]["source_checkout_unchanged"] is False
    assert printed["failed_checks"] == [
        "source_checkout_clean_after_output",
        "source_checkout_unchanged",
    ]
