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
import os
from datetime import datetime, timezone
from pathlib import Path

import pytest

# datetime.UTC needs Python 3.11; the Unit Tests matrix still runs 3.10.
UTC = timezone.utc  # noqa: UP017

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
    # The Reciprocal Probe CI job rewrites the receipt from the member's
    # current main just before this runs and sets a maximum age, so a stale
    # committed receipt cannot stand in for a live check there.
    max_age = os.environ.get("RECIPROCAL_RECEIPT_MAX_AGE_SECONDS")
    if max_age:
        checked_at = datetime.strptime(
            evidence["checked_at"], "%Y-%m-%dT%H:%M:%SZ"
        ).replace(tzinfo=UTC)
        age = (datetime.now(UTC) - checked_at).total_seconds()
        assert 0 <= age <= int(max_age), f"reciprocal receipt is {age:.0f}s old"


@pytest.mark.smoke
def test_stale_receipt_fails_when_a_maximum_age_is_set(monkeypatch, tmp_path):
    # Self-contained: an active entry and an otherwise passing receipt, so
    # only its age can fail, whatever the committed status and receipt are.
    manifest = tmp_path / "manifest.yaml"
    manifest.write_text(
        "federation:\n"
        "  member_repos:\n"
        "    - name: GBOGEB/cryoplant-project\n"
        "      status: active\n",
        encoding="utf-8",
    )
    stale = {
        "direction": "GBOGEB/ABACUS -> GBOGEB/cryoplant-project",
        "checked_at": "2020-01-01T00:00:00Z",
        "member_main_sha": "0" * 40,
        "checks": {"member_status_active": True},
        "status": "ok",
    }
    receipt = tmp_path / "reciprocal_smoke.json"
    receipt.write_text(json.dumps(stale), encoding="utf-8")
    monkeypatch.setitem(globals(), "_GLOBAL_MANIFEST", manifest)
    monkeypatch.setitem(globals(), "_RECIPROCAL_EVIDENCE", receipt)
    monkeypatch.setenv("RECIPROCAL_RECEIPT_MAX_AGE_SECONDS", "900")
    with pytest.raises(AssertionError, match="reciprocal receipt is"):
        test_active_membership_has_reciprocal_evidence()


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
