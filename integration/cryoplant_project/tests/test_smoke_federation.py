"""
Smoke tests for the cryoplant-project federation assimilation hook.

Modeled directly on
integration/codespace_jyperter/tests/test_smoke_federation.py. These tests
verify that:
  1. The cryoplant-project integration manifest stub exists and is valid YAML.
  2. The authoritative DELTA_1 spec file exists (runtime plane check).
  3. integration/cryoplant_project/src/federation.assimilate() returns status == "ok".
  4. The global ABACUS federation manifest lists GBOGEB/cryoplant-project as a member.

Marked @pytest.mark.smoke so they run in the fast pre-merge gate
(pytest -m smoke) as well as the full suite.
"""

import json
from pathlib import Path

import pytest

# Repo root is four levels up from this file:
# integration/cryoplant_project/tests/test_smoke_federation.py
#   -> tests -> cryoplant_project -> integration -> root
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent

_INTEGRATION_MANIFEST = (
    _REPO_ROOT / "integration" / "cryoplant_project" / "federation" / "manifest.yaml"
)
_FEDERATION_SPEC = (
    _REPO_ROOT / "runtime" / "federation" / "codex-abacus-federation.yaml"
)
_GLOBAL_MANIFEST = _REPO_ROOT / "federation" / "manifest.yaml"


@pytest.mark.smoke
def test_integration_manifest_exists():
    """integration/cryoplant_project/federation/manifest.yaml must be present."""
    assert (
        _INTEGRATION_MANIFEST.is_file()
    ), f"Missing cryoplant-project integration manifest: {_INTEGRATION_MANIFEST}"


@pytest.mark.smoke
def test_federation_spec_exists():
    """runtime/federation/codex-abacus-federation.yaml must be present."""
    assert (
        _FEDERATION_SPEC.is_file()
    ), f"Missing DELTA_1 federation spec: {_FEDERATION_SPEC}"


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
    """integration manifest must identify cryoplant-project as the auxiliary member."""
    try:
        import yaml
    except ImportError:
        pytest.skip("PyYAML not installed")

    data = yaml.safe_load(_INTEGRATION_MANIFEST.read_text(encoding="utf-8"))
    member_self = data["federation"].get("member_self", {})
    assert (
        member_self.get("name") == "GBOGEB/cryoplant-project"
    ), "member_self.name must be 'GBOGEB/cryoplant-project'"
    assert member_self.get("plane") == "auxiliary"


@pytest.mark.smoke
def test_global_manifest_includes_cryoplant_project():
    """The global federation/manifest.yaml must list GBOGEB/cryoplant-project."""
    try:
        import yaml
    except ImportError:
        pytest.skip("PyYAML not installed")

    data = yaml.safe_load(_GLOBAL_MANIFEST.read_text(encoding="utf-8"))
    member_names = [m.get("name") for m in data["federation"].get("member_repos", [])]
    assert (
        "GBOGEB/cryoplant-project" in member_names
    ), "federation/manifest.yaml must list GBOGEB/cryoplant-project in member_repos"


@pytest.mark.smoke
def test_assimilate_returns_ok():
    """integration/cryoplant_project/src/federation.assimilate() must return status == 'ok'."""
    from integration.cryoplant_project.src.federation import assimilate

    result = assimilate(context={"session": "smoke-test"})
    assert isinstance(result, dict), "assimilate() must return a dict"
    assert result.get("repo") == "GBOGEB/cryoplant-project"
    assert result.get("plane") == "auxiliary"
    assert result.get("status") == "ok", (
        f"Expected status 'ok', got '{result.get('status')}'. "
        f"Details: {result.get('details')}"
    )


_RECIPROCAL_EVIDENCE = (
    _REPO_ROOT
    / "integration"
    / "cryoplant_project"
    / "federation"
    / "reciprocal_smoke.json"
)


@pytest.mark.smoke
def test_active_membership_has_reciprocal_evidence():
    """An active cryoplant member needs a passing ABACUS-to-cryoplant run.

    The tests above only read this repository. Activation also requires
    scripts/reciprocal_smoke.py to have contacted cryoplant-project itself;
    its recorded result must be ok in that direction.
    """
    import yaml

    data = yaml.safe_load(_GLOBAL_MANIFEST.read_text(encoding="utf-8"))
    entry = next(
        m
        for m in data["federation"]["member_repos"]
        if m.get("name") == "GBOGEB/cryoplant-project"
    )
    if entry.get("status") != "active":
        return
    evidence = json.loads(_RECIPROCAL_EVIDENCE.read_text(encoding="utf-8"))
    assert evidence["direction"] == ("GBOGEB/ABACUS -> GBOGEB/cryoplant-project")
    assert evidence["status"] == "ok"
    assert evidence["checks"] and all(evidence["checks"].values())
    assert len(evidence["member_main_sha"]) == 40


@pytest.mark.smoke
def test_reciprocal_checks_reject_inactive_or_foreign_member():
    from integration.cryoplant_project.scripts.reciprocal_smoke import checks_for

    good = {
        "federation": {
            "moniker": "DELTA_1",
            "status": "active",
            "self": {
                "repository": "GBOGEB/cryoplant-project",
                "plane": "auxiliary",
            },
            "hub": {"runtime_plane": {"repository": "GBOGEB/ABACUS"}},
        }
    }
    assert all(checks_for(good).values())
    proposed = json.loads(json.dumps(good))
    proposed["federation"]["status"] = "proposed"
    assert not checks_for(proposed)["member_status_active"]
    foreign = json.loads(json.dumps(good))
    foreign["federation"]["hub"]["runtime_plane"]["repository"] = "x/y"
    assert not checks_for(foreign)["runtime_hub_is_abacus"]
    assert not any(checks_for({}).values())
