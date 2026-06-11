"""
Smoke tests for the notebook (CODESPACES_jyperter) federation plane.

These tests verify that:
  1. The global federation manifest registers GBOGEB/CODESPACES_jyperter.
  2. The manifest defines a 'notebook' plane entry.
  3. The DELTA_1 spec defines a 'notebook_plane' section.
  4. src/dmaic/federation.assimilate() still returns status == "ok" with the
     notebook plane registered.

Marked @pytest.mark.smoke so they run in the fast pre-merge gate
(pytest -m smoke) as well as the full suite.
"""

import pytest
from pathlib import Path

# Repo root is three levels up from this file:
# DMAIC_V3/tests/test_smoke_federation_jupyter.py -> DMAIC_V3/tests -> DMAIC_V3 -> root
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent

FEDERATION_MANIFEST = _REPO_ROOT / "federation" / "manifest.yaml"
FEDERATION_SPEC = _REPO_ROOT / "runtime" / "federation" / "codex-abacus-federation.yaml"

_NOTEBOOK_REPO = "GBOGEB/CODESPACES_jyperter"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_yaml(path: Path):
    try:
        import yaml
    except ImportError:
        pytest.skip("PyYAML not installed")
    return yaml.safe_load(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.smoke
def test_manifest_registers_notebook_member():
    """federation/manifest.yaml must list GBOGEB/CODESPACES_jyperter as a member."""
    data = _load_yaml(FEDERATION_MANIFEST)
    members = data.get("federation", {}).get("member_repos", [])
    names = [m.get("name") for m in members]
    assert _NOTEBOOK_REPO in names, (
        f"{_NOTEBOOK_REPO} not found in federation member_repos; got: {names}"
    )


@pytest.mark.smoke
def test_manifest_notebook_plane_active():
    """The CODESPACES_jyperter member entry must have plane='notebook' and status='active'."""
    data = _load_yaml(FEDERATION_MANIFEST)
    members = data.get("federation", {}).get("member_repos", [])
    entry = next((m for m in members if m.get("name") == _NOTEBOOK_REPO), None)
    assert entry is not None, f"{_NOTEBOOK_REPO} missing from member_repos"
    assert entry.get("plane") == "notebook", (
        f"Expected plane='notebook', got '{entry.get('plane')}'"
    )
    assert entry.get("status") == "active", (
        f"Expected status='active', got '{entry.get('status')}'"
    )


@pytest.mark.smoke
def test_manifest_planes_has_notebook():
    """federation/manifest.yaml planes section must include a 'notebook' entry."""
    data = _load_yaml(FEDERATION_MANIFEST)
    planes = data.get("federation", {}).get("planes", {})
    assert "notebook" in planes, (
        f"'notebook' plane not defined in federation.planes; got: {list(planes.keys())}"
    )
    notebook_plane = planes["notebook"]
    assert notebook_plane.get("repository") == _NOTEBOOK_REPO, (
        f"notebook plane repository mismatch: {notebook_plane.get('repository')}"
    )


@pytest.mark.smoke
def test_spec_defines_notebook_plane():
    """codex-abacus-federation.yaml must define a 'notebook_plane' section."""
    data = _load_yaml(FEDERATION_SPEC)
    fed = data.get("federation", {})
    assert "notebook_plane" in fed, (
        "Missing 'notebook_plane' in runtime/federation/codex-abacus-federation.yaml"
    )
    nb = fed["notebook_plane"]
    assert nb.get("repository") == _NOTEBOOK_REPO, (
        f"notebook_plane repository mismatch: {nb.get('repository')}"
    )
    responsibilities = nb.get("responsibilities", nb.get("responsibility", []))
    assert "notebook_execution" in responsibilities, (
        "'notebook_execution' not listed in notebook_plane responsibilities"
    )


@pytest.mark.smoke
def test_assimilate_still_ok_with_notebook_plane():
    """assimilate() must still return status == 'ok' after notebook plane is added."""
    from src.dmaic.federation import assimilate

    result = assimilate(context={"session": "smoke-test-jupyter"})
    assert isinstance(result, dict), "assimilate() must return a dict"
    assert result.get("status") == "ok", (
        f"Federation assimilation status is '{result.get('status')}'; "
        f"details: {result.get('details')}"
    )
    assert result["manifest_found"] is True
    assert result["spec_found"] is True
