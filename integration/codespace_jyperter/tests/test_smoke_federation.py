"""
Smoke tests for the codespace_jyperter federation assimilation hook.

These tests verify that:
  1. The codespace_jyperter integration manifest stub exists and is valid YAML.
  2. The authoritative DELTA_1 spec file exists (runtime plane check).
  3. integration/codespace_jyperter/src/federation.assimilate() returns status == "ok".
  4. The global ABACUS federation manifest lists GBOGEB/codespace_jyperter as a member.

Marked @pytest.mark.smoke so they run in the fast pre-merge gate
(pytest -m smoke) as well as the full suite.
"""

from pathlib import Path

import pytest

# Repo root is four levels up from this file:
# integration/codespace_jyperter/tests/test_smoke_federation.py
#   -> tests -> codespace_jyperter -> integration -> root
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent

_INTEGRATION_MANIFEST = (
    _REPO_ROOT / "integration" / "codespace_jyperter" / "federation" / "manifest.yaml"
)
_FEDERATION_SPEC = _REPO_ROOT / "runtime" / "federation" / "codex-abacus-federation.yaml"
_GLOBAL_MANIFEST = _REPO_ROOT / "federation" / "manifest.yaml"


@pytest.mark.smoke
def test_integration_manifest_exists():
    """integration/codespace_jyperter/federation/manifest.yaml must be present."""
    assert _INTEGRATION_MANIFEST.is_file(), (
        f"Missing codespace_jyperter integration manifest: {_INTEGRATION_MANIFEST}"
    )


@pytest.mark.smoke
def test_federation_spec_exists():
    """runtime/federation/codex-abacus-federation.yaml must be present."""
    assert _FEDERATION_SPEC.is_file(), (
        f"Missing DELTA_1 federation spec: {_FEDERATION_SPEC}"
    )


@pytest.mark.smoke
def test_integration_manifest_is_yaml():
    """integration manifest must be valid YAML with a 'federation' key."""
    try:
        import yaml
    except ImportError:
        pytest.skip("PyYAML not installed")

    content = _INTEGRATION_MANIFEST.read_text(encoding="utf-8")
    data = yaml.safe_load(content)
    assert isinstance(data, dict), "integration manifest must parse to a dict"
    assert "federation" in data, "integration manifest must have a 'federation' key"


@pytest.mark.smoke
def test_integration_manifest_lists_self():
    """integration manifest must identify codespace_jyperter as the auxiliary member."""
    try:
        import yaml
    except ImportError:
        pytest.skip("PyYAML not installed")

    data = yaml.safe_load(_INTEGRATION_MANIFEST.read_text(encoding="utf-8"))
    member_self = data["federation"].get("member_self", {})
    assert member_self.get("name") == "GBOGEB/codespace_jyperter", (
        "member_self.name must be 'GBOGEB/codespace_jyperter'"
    )
    assert member_self.get("plane") == "auxiliary"


@pytest.mark.smoke
def test_global_manifest_includes_codespace_jyperter():
    """The global federation/manifest.yaml must list GBOGEB/codespace_jyperter."""
    try:
        import yaml
    except ImportError:
        pytest.skip("PyYAML not installed")

    data = yaml.safe_load(_GLOBAL_MANIFEST.read_text(encoding="utf-8"))
    member_names = [m.get("name") for m in data["federation"].get("member_repos", [])]
    assert "GBOGEB/codespace_jyperter" in member_names, (
        "federation/manifest.yaml must list GBOGEB/codespace_jyperter in member_repos"
    )


@pytest.mark.smoke
def test_assimilate_returns_ok():
    """integration/codespace_jyperter/src/federation.assimilate() must return status == 'ok'."""
    from integration.codespace_jyperter.src.federation import assimilate

    result = assimilate(context={"session": "smoke-test"})
    assert isinstance(result, dict), "assimilate() must return a dict"
    assert result.get("repo") == "GBOGEB/codespace_jyperter"
    assert result.get("plane") == "auxiliary"
    assert result.get("status") == "ok", (
        f"Expected status 'ok', got '{result.get('status')}'. "
        f"Details: {result.get('details')}"
    )
