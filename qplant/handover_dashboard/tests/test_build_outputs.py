import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_manifest_has_hashes():
    manifest_path = ROOT / "docs" / "manifest.json"
    assert manifest_path.exists()

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert "files" in manifest
    assert isinstance(manifest["files"], dict)
    assert len(manifest["files"]) > 0

    sample = list(manifest["files"].values())[:10]
    for entry in sample:
        assert len(entry["sha256"]) == 64
        assert entry["size"] >= 0


def test_required_release_files_present():
    required = [
        ROOT / "README.md",
        ROOT / "CONTRIBUTING.md",
        ROOT / "VERSION",
        ROOT / "requirements.txt",
        ROOT / "setup.sh",
        ROOT / "build.sh",
        ROOT / "validate.sh",
        ROOT / "package.sh",
        ROOT / ".github" / "workflows" / "build.yml",
    ]
    for path in required:
        assert path.exists(), f"Missing required file: {path}"
