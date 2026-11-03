"""Gap tests for scripts/validate_federation_identity.py (validate errors, main)."""

import copy
import sys

import pytest
import yaml

from tests.coverage_waves.lane_b._l2_loader import load

mod = load(
    "scripts/validate_federation_identity.py",
    name="abn_w7_validate_federation_identity",
)

MANIFEST = {
    "federation": {
        "moniker": "DELTA_1",
        "member_repos": [
            {"name": "GBOGEB/ABACUS", "status": "active", "plane": "hub"},
            {
                "name": "gbogeb/codespaces_jyperter",
                "status": "active",
                "plane": "notebook",
            },
        ],
        "planes": {"notebook": {"repository": "GBOGEB/CODESPACES_jyperter"}},
    }
}
RUNTIME = {
    "federation": {"notebook_plane": {"repository": "GBOGEB/codespaces_JYPERTER"}}
}
CONTRACT = {
    "contract": {
        "consumer": "GBOGEB/CODESPACES_jyperter",
        "provider": "gbogeb/abacus",
        "federation_moniker": "DELTA_1",
    }
}


def _docs():
    return copy.deepcopy(MANIFEST), copy.deepcopy(RUNTIME), copy.deepcopy(CONTRACT)


def test_valid_documents_pass_case_insensitively():
    assert mod.validate(*_docs()) is None


def test_unexpected_moniker_rejected():
    manifest, runtime, contract = _docs()
    manifest["federation"]["moniker"] = "DELTA_2"
    with pytest.raises(ValueError, match="unexpected federation moniker"):
        mod.validate(manifest, runtime, contract)


def test_unexpected_provider_rejected():
    manifest, runtime, contract = _docs()
    contract["contract"]["provider"] = "GBOGEB/CODEX"
    with pytest.raises(ValueError, match="unexpected contract provider"):
        mod.validate(manifest, runtime, contract)


def test_contract_federation_mismatch_rejected():
    manifest, runtime, contract = _docs()
    contract["contract"]["federation_moniker"] = "GAMMA"
    with pytest.raises(ValueError, match="contract federation mismatch"):
        mod.validate(manifest, runtime, contract)


def _write_tree(root, docs):
    paths = (
        "federation/manifest.yaml",
        "runtime/federation/codex-abacus-federation.yaml",
        "integration/codespace_jyperter/abacus_contract.yaml",
    )
    for rel, doc in zip(paths, docs):
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(yaml.safe_dump(doc), encoding="utf-8")


def test_main_pass(monkeypatch, tmp_path, capsys):
    _write_tree(tmp_path, _docs())
    monkeypatch.setattr(sys, "argv", ["vfi", "--root", str(tmp_path)])
    assert mod.main() == 0
    assert "identity PASS" in capsys.readouterr().out


def test_main_fails_on_missing_files(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(sys, "argv", ["vfi", "--root", str(tmp_path)])
    assert mod.main() == 1
    assert "identity FAIL" in capsys.readouterr().out


def test_main_fails_on_validation_error(monkeypatch, tmp_path, capsys):
    manifest, runtime, contract = _docs()
    runtime["federation"]["notebook_plane"]["repository"] = "GBOGEB/OTHER"
    _write_tree(tmp_path, (manifest, runtime, contract))
    monkeypatch.setattr(sys, "argv", ["vfi", "--root", str(tmp_path)])
    assert mod.main() == 1
    assert "identity mismatch" in capsys.readouterr().out
