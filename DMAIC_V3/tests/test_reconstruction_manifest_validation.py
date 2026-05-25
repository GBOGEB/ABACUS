import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT_DIR / "src"))

from dmaic.reconstruction_manifest import validate_reconstruction_manifest  # noqa: E402


def test_reconstruction_manifest_in_repo_is_valid():
    payload = json.loads((ROOT_DIR / "docs/api/phase2_reconstruction_manifest.json").read_text(encoding="utf-8"))
    errors = validate_reconstruction_manifest(payload, ROOT_DIR)
    assert errors == []


def test_reconstruction_manifest_requires_all_components():
    payload = json.loads((ROOT_DIR / "docs/api/phase2_reconstruction_manifest.json").read_text(encoding="utf-8"))
    payload["component_map"] = [c for c in payload["component_map"] if c["name"] != "branch DAG"]
    errors = validate_reconstruction_manifest(payload, ROOT_DIR)
    assert "component_map missing required component: branch DAG" in errors
