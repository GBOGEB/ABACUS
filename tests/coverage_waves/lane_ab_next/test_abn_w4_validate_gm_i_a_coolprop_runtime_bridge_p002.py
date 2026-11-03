"""Behaviour tests for scripts/validate_gm_i_a_coolprop_runtime_bridge_p002.py.

Network access is replaced by a fake ``urlopen`` returning in-memory bytes.
"""

import hashlib
import io
import json
import runpy
import sys

import pytest

from tests.coverage_waves.lane_b._l2_loader import REPO_ROOT, load

REL = "scripts/validate_gm_i_a_coolprop_runtime_bridge_p002.py"
mod = load(REL, name="abn_w4_validate_gm_i_a_coolprop_runtime_bridge_p002")

PULSE = "GM-I-A-MCLOCK-P002"
HEAVY = "sha256:" + "a" * 64
FAST = "sha256:" + "b" * 64


class _Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False


def _attestation():
    return {
        "pulse_id": PULSE,
        "source_head_sha": "h" * 40,
        "source_merge_sha": "m" * 40,
        "workflow": {"run_id": 99, "conclusion": "success"},
        "heavy": {"conclusion": "success", "artifact": {"digest": HEAVY}},
        "fast": {
            "conclusion": "success",
            "artifact": {"digest": FAST},
            "build_invoked": False,
            "source_checkout_performed": False,
        },
        "authority": {"authority_transfer": False},
        "runtime_economics": {"fast_seconds": 2},
    }


def _manifest(raw):
    return {
        "schema": "abacus.gm_i_a.coolprop_runtime_bridge.v1",
        "pulse_id": PULSE,
        "authority_transfer": False,
        "provider": {
            "source_head_sha": "h" * 40,
            "source_merge_sha": "m" * 40,
            "attestation_commit_sha": "c" * 40,
            "attestation_path": "qps/p002.json",
            "attestation_sha256": hashlib.sha256(raw).hexdigest(),
            "workflow_run_id": 99,
            "heavy_artifact_digest": HEAVY,
            "fast_artifact_digest": FAST,
        },
    }


def _setup(tmp_path, monkeypatch, manifest, raw, seen=None):
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    receipt = tmp_path / "receipt.json"

    def fake(url, timeout):
        if seen is not None:
            seen.append((url, timeout))
        return _Resp(raw)

    monkeypatch.setattr(mod, "MANIFEST", path)
    monkeypatch.setattr(mod.urllib.request, "urlopen", fake)
    monkeypatch.setattr(sys, "argv", ["prog", "--receipt", str(receipt)])
    return receipt


def test_canonical_bytes_sorted_with_trailing_newline():
    assert mod.canonical_bytes({"z": 1, "a": [1]}) == (
        b'{\n  "a": [\n    1\n  ],\n  "z": 1\n}\n'
    )


def test_manifest_points_at_repo_triage():
    assert mod.MANIFEST == REPO_ROOT / "triage" / mod.MANIFEST.name
    assert json.loads(mod.MANIFEST.read_text(encoding="utf-8"))["pulse_id"] == PULSE


def test_main_writes_receipt_from_pinned_attestation(tmp_path, monkeypatch):
    raw = json.dumps(_attestation()).encode("utf-8")
    seen = []
    receipt = _setup(tmp_path, monkeypatch, _manifest(raw), raw, seen)
    mod.main()
    assert seen == [
        (
            "https://raw.githubusercontent.com/GBOGEB/CoolProp/"
            + "c" * 40
            + "/qps/p002.json",
            30,
        )
    ]
    data = receipt.read_bytes()
    value = json.loads(data)
    assert data == mod.canonical_bytes(value)
    assert value["pulse_id"] == PULSE
    assert value["status"] == "PASS"
    assert value["provider_attestation_sha256"] == hashlib.sha256(raw).hexdigest()
    assert value["provider_workflow_run_id"] == 99
    assert value["provider_source_head_sha"] == "h" * 40
    assert value["runtime_economics"] == {"fast_seconds": 2}
    assert value["engineering_promotion_forbidden"] is True


def test_main_rejects_digest_mismatch(tmp_path, monkeypatch):
    raw = json.dumps(_attestation()).encode("utf-8")
    receipt = _setup(tmp_path, monkeypatch, _manifest(raw), raw + b"\n")
    with pytest.raises(AssertionError):
        mod.main()
    assert not receipt.exists()


def test_main_rejects_wrong_manifest_pulse(tmp_path, monkeypatch):
    raw = json.dumps(_attestation()).encode("utf-8")
    manifest = _manifest(raw)
    manifest["pulse_id"] = "GM-I-A-MCLOCK-P001"
    _setup(tmp_path, monkeypatch, manifest, raw)
    with pytest.raises(AssertionError):
        mod.main()


@pytest.mark.parametrize(
    "section,key,value",
    [
        (None, "source_merge_sha", "x" * 40),
        ("workflow", "conclusion", "cancelled"),
        ("fast", "source_checkout_performed", True),
        ("authority", "authority_transfer", True),
    ],
)
def test_main_rejects_attestation_guard_breach(
    tmp_path, monkeypatch, section, key, value
):
    att = _attestation()
    target = att if section is None else att[section]
    target[key] = value
    raw = json.dumps(att).encode("utf-8")
    receipt = _setup(tmp_path, monkeypatch, _manifest(raw), raw)
    with pytest.raises(AssertionError):
        mod.main()
    assert not receipt.exists()


def test_main_requires_receipt_argument(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["prog"])
    with pytest.raises(SystemExit) as exc:
        mod.main()
    assert exc.value.code == 2


def test_dunder_main_fails_closed_on_unpinned_bytes(tmp_path, monkeypatch):
    monkeypatch.setattr("urllib.request.urlopen", lambda url, timeout: _Resp(b"{}"))
    receipt = tmp_path / "r.json"
    monkeypatch.setattr(sys, "argv", ["prog", "--receipt", str(receipt)])
    with pytest.raises(AssertionError):
        runpy.run_path(str(REPO_ROOT / REL), run_name="__main__")
    assert not receipt.exists()
