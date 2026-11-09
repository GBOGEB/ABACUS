"""Tests for deploy.py, the package builder that ci-cd.yml's deploy jobs run."""

import json
from pathlib import Path

import pytest

import deploy

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci-cd.yml"


@pytest.fixture
def source_root(tmp_path):
    root = tmp_path / "src"
    root.mkdir()
    for name in deploy.PACKAGE_FILES:
        (root / name).write_bytes(f"# {name}\r\nbody\n".encode())
    return root


def _build(source_root, output_root, stamp="20261023T000000Z", env="production"):
    return deploy.build_package(
        env=env,
        source_root=source_root,
        output_root=output_root,
        stamp=stamp,
        commit="abc123",
        version="2026.10.23-0000",
    )


def test_package_contains_every_file_and_a_manifest(source_root, tmp_path):
    package = _build(source_root, tmp_path / "out")

    assert package.name == "deployment_production_20261023T000000Z"
    names = sorted(p.name for p in package.iterdir())
    assert names == sorted([*deploy.PACKAGE_FILES, deploy.MANIFEST_NAME])
    manifest = json.loads((package / deploy.MANIFEST_NAME).read_text("utf-8"))
    assert manifest["environment"] == "production"
    assert manifest["commit"] == "abc123"
    assert manifest["version"] == "2026.10.23-0000"
    assert manifest["stamp"] == "20261023T000000Z"


def test_manifest_hashes_match_the_packaged_bytes(source_root, tmp_path):
    package = _build(source_root, tmp_path / "out")

    manifest = json.loads((package / deploy.MANIFEST_NAME).read_text("utf-8"))
    assert set(manifest["files"]) == set(deploy.PACKAGE_FILES)
    for name, digest in manifest["files"].items():
        assert (package / name).read_bytes() == (source_root / name).read_bytes()
        assert deploy.sha256_file(package / name) == digest


def test_two_runs_give_the_same_file_set_and_hashes(source_root, tmp_path):
    first = _build(source_root, tmp_path / "out", stamp="A")
    second = _build(source_root, tmp_path / "out", stamp="B")

    first_manifest = json.loads((first / deploy.MANIFEST_NAME).read_text("utf-8"))
    second_manifest = json.loads((second / deploy.MANIFEST_NAME).read_text("utf-8"))
    assert first_manifest["files"] == second_manifest["files"]


def test_unknown_environment_is_rejected(source_root, tmp_path):
    with pytest.raises(ValueError, match="unknown environment"):
        _build(source_root, tmp_path / "out", env="qa")
    with pytest.raises(SystemExit) as exit_info:
        deploy.main(["--env", "qa", "--source-root", str(source_root)])
    assert exit_info.value.code == 2


def test_missing_source_file_fails_without_a_package(source_root, tmp_path, capsys):
    (source_root / "dow_phase3_reporting.py").unlink()
    out = tmp_path / "out"

    code = deploy.main(
        [
            "--env",
            "staging",
            "--source-root",
            str(source_root),
            "--output-root",
            str(out),
        ]
    )

    assert code == 1
    assert "dow_phase3_reporting.py" in capsys.readouterr().err
    assert not out.exists()


def test_existing_package_directory_is_not_overwritten(source_root, tmp_path):
    out = tmp_path / "out"
    args = [
        "--env",
        "staging",
        "--source-root",
        str(source_root),
        "--output-root",
        str(out),
        "--stamp",
        "S",
    ]

    assert deploy.main(args) == 0
    assert deploy.main(args) == 1


def test_main_defaults_stamp_commit_and_version(source_root, tmp_path, monkeypatch):
    monkeypatch.setenv("GITHUB_SHA", "deadbeef")
    out = tmp_path / "out"

    code = deploy.main(
        [
            "--env",
            "staging",
            "--source-root",
            str(source_root),
            "--output-root",
            str(out),
        ]
    )

    assert code == 0
    [package] = list(out.iterdir())
    manifest = json.loads((package / deploy.MANIFEST_NAME).read_text("utf-8"))
    assert package.name == f"deployment_staging_{manifest['stamp']}"
    assert manifest["version"] == manifest["stamp"]
    assert manifest["stamp"].endswith("Z")


def test_repository_has_every_packaged_file(tmp_path):
    package = deploy.build_package(
        env="production",
        source_root=REPO_ROOT,
        output_root=tmp_path,
        stamp="repo",
        commit="HEAD",
        version="repo",
    )

    assert (package / deploy.MANIFEST_NAME).is_file()


def test_workflow_retests_the_deploy_script_when_it_changes():
    source = WORKFLOW.read_text(encoding="utf-8")

    assert source.count("      - 'deploy.py'") == 2
    assert source.count("      - 'tests/test_deploy.py'") == 2
    assert "python deploy.py --env production" in source
    assert "python deploy.py --env staging" in source
