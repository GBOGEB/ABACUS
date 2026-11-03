"""Behaviour tests for tools/validate_w286_gloob_pandoc_p1.py.

The validator runs entirely at import time, so each test executes it by path.
The failure path swaps the JSON payload via a monkeypatched ``read_text``.
"""

import json
import pathlib

import pytest

from tests.coverage_waves.lane_b._l2_loader import REPO_ROOT, load

REL = "tools/validate_w286_gloob_pandoc_p1.py"
RECEIPT = "W286_GLOOB_PANDOC_P1_RECEIVER_HOLD_v0.1.json"


def _real_payload():
    path = REPO_ROOT / "architecture" / "w286" / RECEIPT
    return json.loads(path.read_bytes().decode("utf-8"))


def _patch_payload(monkeypatch, payload):
    original = pathlib.Path.read_text

    def fake_read_text(self, *args, **kwargs):
        if self.name == RECEIPT:
            return json.dumps(payload)
        return original(self, *args, **kwargs)

    monkeypatch.setattr(pathlib.Path, "read_text", fake_read_text)


def test_validator_passes_on_committed_receipt(capsys):
    mod = load(REL, name="abn_validate_w286_pass")
    assert "PASS W286 ABACUS independent P1 parity" in capsys.readouterr().out
    assert mod.D["formal_credit_delta"] == 0
    assert mod.P.name == RECEIPT


def test_validator_rejects_authority_transfer(monkeypatch, capsys):
    payload = _real_payload()
    payload["authority_transfer"] = True
    _patch_payload(monkeypatch, payload)
    with pytest.raises(AssertionError):
        load(REL, name="abn_validate_w286_bad_transfer")
    assert "PASS" not in capsys.readouterr().out


def test_validator_rejects_wrong_repo(monkeypatch):
    payload = _real_payload()
    payload["repo"] = "GBOGEB/CODEX"
    _patch_payload(monkeypatch, payload)
    with pytest.raises(AssertionError):
        load(REL, name="abn_validate_w286_bad_repo")
