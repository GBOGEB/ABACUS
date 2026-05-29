"""
Smoke tests for the DELTA_1 federation assimilation hook.

These tests verify that:
  1. The global federation manifest exists and is loadable.
  2. The authoritative DELTA_1 spec file exists.
  3. src/dmaic/federation.assimilate() returns status == "ok".
  4. GBOGEB/codespace_jyperter is registered as an auxiliary federation member.

Marked @pytest.mark.smoke so they run in the fast pre-merge gate
(pytest -m smoke) as well as the full suite.
"""

import pytest
from pathlib import Path

# Repo root is three levels up from this file:
# DMAIC_V3/tests/test_smoke_federation.py -> DMAIC_V3/tests -> DMAIC_V3 -> root
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent

FEDERATION_MANIFEST = _REPO_ROOT / "federation" / "manifest.yaml"
FEDERATION_SPEC = _REPO_ROOT / "runtime" / "federation" / "codex-abacus-federation.yaml"
_INTEGRATION_MANIFEST = (
    _REPO_ROOT / "integration" / "codespace_jyperter" / "federation" / "manifest.yaml"
)


@pytest.mark.smoke
def test_federation_manifest_exists():
    """federation/manifest.yaml must be present."""
    assert FEDERATION_MANIFEST.is_file(), (
        f"Missing global federation manifest: {FEDERATION_MANIFEST}"
    )


@pytest.mark.smoke
def test_federation_spec_exists():
    """runtime/federation/codex-abacus-federation.yaml must be present."""
    assert FEDERATION_SPEC.is_file(), (
        f"Missing DELTA_1 federation spec: {FEDERATION_SPEC}"
    )


@pytest.mark.smoke
def test_federation_manifest_is_yaml():
    """federation/manifest.yaml must be valid YAML with a 'federation' key."""
    try:
        import yaml
    except ImportError:
        pytest.skip("PyYAML not installed")

    content = FEDERATION_MANIFEST.read_text(encoding="utf-8")
    data = yaml.safe_load(content)
    assert isinstance(data, dict), "federation/manifest.yaml must parse to a dict"
    assert "federation" in data, "federation/manifest.yaml must have a 'federation' key"


@pytest.mark.smoke
def test_codespace_jyperter_registered_in_manifest():
    """federation/manifest.yaml must list GBOGEB/codespace_jyperter as auxiliary member."""
    try:
        import yaml
    except ImportError:
        pytest.skip("PyYAML not installed")

    data = yaml.safe_load(FEDERATION_MANIFEST.read_text(encoding="utf-8"))
    member_names = [m.get("name") for m in data["federation"].get("member_repos", [])]
    assert "GBOGEB/codespace_jyperter" in member_names, (
        f"GBOGEB/codespace_jyperter missing from member_repos. Found: {member_names}"
    )


@pytest.mark.smoke
def test_codespace_jyperter_in_runtime_spec():
    """runtime federation spec must list codespace_jyperter as an auxiliary plane."""
    try:
        import yaml
    except ImportError:
        pytest.skip("PyYAML not installed")

    data = yaml.safe_load(FEDERATION_SPEC.read_text(encoding="utf-8"))
    planes = data["federation"].get("auxiliary_planes", [])
    repos = [p.get("repository") for p in planes]
    assert "GBOGEB/codespace_jyperter" in repos, (
        f"GBOGEB/codespace_jyperter missing from auxiliary_planes. Found: {repos}"
    )


@pytest.mark.smoke
def test_codespace_jyperter_integration_manifest_exists():
    """integration/codespace_jyperter/federation/manifest.yaml must be present."""
    assert _INTEGRATION_MANIFEST.is_file(), (
        f"Missing codespace_jyperter integration manifest: {_INTEGRATION_MANIFEST}"
    )


@pytest.mark.smoke
def test_assimilate_returns_ok():
    """src/dmaic/federation.assimilate() must return status == 'ok'."""
    from src.dmaic.federation import assimilate

    result = assimilate(context={"session": "smoke-test"})
    assert isinstance(result, dict), "assimilate() must return a dict"
    assert result.get("status") == "ok", (
        f"Federation assimilation status is '{result.get('status')}'; "
        f"details: {result.get('details')}"
    )
    assert result["manifest_found"] is True
    assert result["spec_found"] is True


@pytest.mark.smoke
def test_assimilate_context_passthrough():
    """assimilate() must echo the caller context in the returned dict."""
    from src.dmaic.federation import assimilate

    ctx = {"iteration": 42, "session_id": "test-abc"}
    result = assimilate(context=ctx)
    assert result["context"] == ctx
