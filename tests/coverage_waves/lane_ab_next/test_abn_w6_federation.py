"""Behaviour tests for src/dmaic/federation.py."""

import pytest

from src.dmaic import federation as mod


def _point_at(monkeypatch, root, manifest, spec):
    m = root / "federation" / "manifest.yaml"
    s = root / "runtime" / "federation" / "codex-abacus-federation.yaml"
    for flag, path in ((manifest, m), (spec, s)):
        if flag:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"x: 1\n")
    monkeypatch.setattr(mod, "_REPO_ROOT", root)
    monkeypatch.setattr(mod, "FEDERATION_MANIFEST", m)
    monkeypatch.setattr(mod, "FEDERATION_SPEC", s)


@pytest.mark.parametrize(
    "manifest,spec,status",
    [
        (True, True, "ok"),
        (True, False, "degraded"),
        (False, True, "degraded"),
        (False, False, "error"),
    ],
)
def test_assimilate_status_matrix(tmp_path, monkeypatch, manifest, spec, status):
    _point_at(monkeypatch, tmp_path, manifest, spec)
    out = mod.assimilate({"session_id": "s1"})
    assert out["status"] == status
    assert out["manifest_found"] is manifest
    assert out["spec_found"] is spec
    assert out["context"] == {"session_id": "s1"}
    first = "manifest OK" if manifest else "manifest MISSING"
    second = "spec OK" if spec else "spec MISSING"
    assert out["details"][0].startswith(first)
    assert out["details"][1].startswith(second)
    assert "manifest.yaml" in out["details"][0]


def test_assimilate_none_context(tmp_path, monkeypatch):
    _point_at(monkeypatch, tmp_path, True, True)
    assert mod.assimilate()["context"] == {}


def test_paths_resolve_under_repo_root():
    rel = mod.FEDERATION_MANIFEST.relative_to(mod._REPO_ROOT)
    assert rel.parts == ("federation", "manifest.yaml")
    assert mod.FEDERATION_SPEC.name == "codex-abacus-federation.yaml"
