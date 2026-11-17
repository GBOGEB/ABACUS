"""Behaviour tests for scripts/validate_gm_i_a_coolprop_runtime_bridge.py.

Network access is replaced by a fake ``urlopen`` returning in-memory bytes.
"""

import copy
import hashlib
import io
import json
import runpy
import sys

import pytest

from tests.coverage_waves.lane_b._l2_loader import REPO_ROOT, load

REL = "scripts/validate_gm_i_a_coolprop_runtime_bridge.py"
mod = load(REL, name="abn_w4_validate_gm_i_a_coolprop_runtime_bridge")

HEAVY = "sha256:" + "a" * 64
FAST = "sha256:" + "b" * 64


class _Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False


def _attestation(head="h" * 40, run_id=42):
    return {
        "schema": "qps.gm_i_a.fast_heavy.federation_attestation.v1",
        "provider_repo": "GBOGEB/CoolProp",
        "source_head_sha": head,
        "workflow": {"run_id": run_id, "conclusion": "success"},
        "heavy": {"conclusion": "success", "artifact": {"digest": HEAVY}},
        "fast": {
            "conclusion": "success",
            "artifact": {"digest": FAST},
            "build_invoked": False,
            "source_checkout_performed": False,
            "calculations_passed": 17,
        },
        "authority": {
            "authority_transfer": False,
            "engineering_promotion": "WITHHELD",
        },
        "runtime_economics": {"fast_seconds": 1.5, "heavy_seconds": 900},
    }


def _manifest(raw, head="h" * 40, run_id=42):
    return {
        "schema": "abacus.gm_i_a.coolprop_runtime_bridge.v1",
        "consumer_repo": "GBOGEB/ABACUS",
        "authority_transfer": False,
        "engineering_promotion_forbidden": True,
        "provider": {
            "repo": "GBOGEB/CoolProp",
            "source_head_sha": head,
            "attestation_commit_sha": "c" * 40,
            "attestation_path": "qps/att.json",
            "attestation_sha256": hashlib.sha256(raw).hexdigest(),
            "workflow_run_id": run_id,
            "heavy_artifact_digest": HEAVY,
            "fast_artifact_digest": FAST,
        },
    }


def _fake_urlopen(raw, seen):
    def fake(url, timeout):
        seen.append((url, timeout))
        return _Resp(raw)

    return fake


def test_canonical_bytes_sorted_indented_newline():
    out = mod.canonical_bytes({"b": 1, "a": "é"})
    assert out == b'{\n  "a": "\\u00e9",\n  "b": 1\n}\n'


def test_sha256_bytes_matches_hashlib():
    assert mod.sha256_bytes(b"abc") == hashlib.sha256(b"abc").hexdigest()


def test_load_manifest_accepts_repo_manifest():
    value = mod.load_manifest()
    assert value["provider"]["repo"] == "GBOGEB/CoolProp"
    assert mod.MANIFEST == REPO_ROOT / "triage" / mod.MANIFEST.name


def test_load_manifest_rejects_authority_transfer(tmp_path, monkeypatch):
    bad = _manifest(b"x")
    bad["authority_transfer"] = True
    path = tmp_path / "m.json"
    path.write_text(json.dumps(bad), encoding="utf-8")
    monkeypatch.setattr(mod, "MANIFEST", path)
    with pytest.raises(AssertionError):
        mod.load_manifest()


def test_load_manifest_rejects_short_commit_sha(tmp_path, monkeypatch):
    bad = _manifest(b"x")
    bad["provider"]["attestation_commit_sha"] = "abc"
    path = tmp_path / "m.json"
    path.write_text(json.dumps(bad), encoding="utf-8")
    monkeypatch.setattr(mod, "MANIFEST", path)
    with pytest.raises(AssertionError):
        mod.load_manifest()


def test_fetch_provider_builds_pinned_url_and_returns_digest(monkeypatch):
    raw = json.dumps(_attestation()).encode("utf-8")
    manifest = _manifest(raw)
    seen = []
    monkeypatch.setattr(mod.urllib.request, "urlopen", _fake_urlopen(raw, seen))
    value, digest = mod.fetch_provider(manifest)
    assert value == _attestation()
    assert digest == hashlib.sha256(raw).hexdigest()
    assert seen == [
        (
            "https://raw.githubusercontent.com/GBOGEB/CoolProp/"
            + "c" * 40
            + "/qps/att.json",
            30,
        )
    ]


def test_fetch_provider_rejects_tampered_bytes(monkeypatch):
    raw = json.dumps(_attestation()).encode("utf-8")
    manifest = _manifest(raw)
    monkeypatch.setattr(mod.urllib.request, "urlopen", _fake_urlopen(raw + b" ", []))
    with pytest.raises(ValueError, match="digest mismatch"):
        mod.fetch_provider(manifest)


def test_validate_provider_accepts_matching_attestation():
    manifest = _manifest(b"x")
    assert mod.validate_provider(manifest, _attestation()) is None


@pytest.mark.parametrize(
    "path,value",
    [
        (("schema",), "other"),
        (("source_head_sha",), "z" * 40),
        (("workflow", "run_id"), 7),
        (("workflow", "conclusion"), "failure"),
        (("heavy", "artifact", "digest"), "sha256:" + "0" * 64),
        (("fast", "build_invoked"), True),
        (("authority", "engineering_promotion"), "GRANTED"),
    ],
)
def test_validate_provider_rejects_each_guard(path, value):
    att = copy.deepcopy(_attestation())
    node = att
    for key in path[:-1]:
        node = node[key]
    node[path[-1]] = value
    with pytest.raises(AssertionError):
        mod.validate_provider(_manifest(b"x"), att)


def test_main_writes_canonical_receipt(tmp_path, monkeypatch):
    raw = json.dumps(_attestation()).encode("utf-8")
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(_manifest(raw)), encoding="utf-8")
    receipt = tmp_path / "receipt.json"
    monkeypatch.setattr(mod, "MANIFEST", manifest_path)
    monkeypatch.setattr(mod.urllib.request, "urlopen", _fake_urlopen(raw, []))
    monkeypatch.setattr(sys, "argv", ["prog", "--receipt", str(receipt)])
    mod.main()
    data = receipt.read_bytes()
    value = json.loads(data)
    assert data == mod.canonical_bytes(value)
    assert value["status"] == "PASS"
    assert value["provider_attestation_sha256"] == hashlib.sha256(raw).hexdigest()
    assert value["provider_attestation_commit_sha"] == "c" * 40
    assert value["provider_workflow_run_id"] == 42
    assert value["fast_calculation_count"] == 17
    assert value["heavy_artifact_digest"] == HEAVY
    assert value["runtime_economics"] == {"fast_seconds": 1.5, "heavy_seconds": 900}
    assert value["authority_transfer"] is False


def test_main_requires_receipt_argument(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["prog"])
    with pytest.raises(SystemExit) as exc:
        mod.main()
    assert exc.value.code == 2


def test_dunder_main_fails_closed_on_unpinned_bytes(tmp_path, monkeypatch):
    monkeypatch.setattr("urllib.request.urlopen", _fake_urlopen(b"{}", []))
    receipt = tmp_path / "r.json"
    monkeypatch.setattr(sys, "argv", ["prog", "--receipt", str(receipt)])
    with pytest.raises(ValueError, match="digest mismatch"):
        runpy.run_path(str(REPO_ROOT / REL), run_name="__main__")
    assert not receipt.exists()
