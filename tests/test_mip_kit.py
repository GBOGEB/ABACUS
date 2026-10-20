"""Tests for the shareable MIP kit: manifest, drift check, surface config."""

from __future__ import annotations

import datetime
import importlib.util
import json
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str, relpath: str):
    # ABACUS adaptation: the canonical kit emitter imports ``datetime.UTC``
    # (Python 3.11+), but ABACUS's full CI matrix also collects tests on 3.10.
    # Alias it only while the module executes so the logic under test runs
    # there too; the N2 workflow itself runs the kit on Python 3.12.
    shim = not hasattr(datetime, "UTC")
    if shim:
        datetime.UTC = datetime.timezone.utc  # noqa: UP017 (3.10 has no UTC)
    try:
        spec = importlib.util.spec_from_file_location(name, ROOT / relpath)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    finally:
        if shim:
            del datetime.UTC
    return module


kit = _load("mip_kit_manifest", "scripts/mip_kit_manifest.py")
emitter = _load("mip_repo_self_index", "scripts/mip_repo_self_index.py")
verifier = _load("mip_verify_self_index", "scripts/mip_verify_self_index.py")


@pytest.fixture
def kit_copy(tmp_path: Path) -> Path:
    """A consumer-like copy of the kit files plus a manifest built from them."""
    for rel in kit.KIT_FILES:
        target = tmp_path / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / rel, target)
    manifest = tmp_path / "MIP" / "kit" / "KIT_MANIFEST.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps(kit.build_manifest(tmp_path)), encoding="utf-8")
    return tmp_path


def _manifest(root: Path) -> Path:
    return root / "MIP" / "kit" / "KIT_MANIFEST.json"


# --- manifest / drift check -------------------------------------------------


def test_tracked_manifest_matches_kit_files_in_this_repo():
    result = kit.check()
    assert result["verification"] == "PASS", result
    assert result["file_count"] == len(kit.KIT_FILES)


def test_tracked_manifest_is_what_write_would_produce():
    tracked = json.loads(kit.MANIFEST.read_text(encoding="utf-8"))
    assert tracked == kit.build_manifest()


def test_manifest_excludes_repo_local_surface_config():
    paths = {row["path"] for row in kit.build_manifest()["files"]}
    assert "MIP/mip_surface.json" not in paths
    assert "MIP/kit/KIT_MANIFEST.json" not in paths
    assert set(kit.REPO_LOCAL_FILES).isdisjoint(paths)


def test_clean_copy_passes_and_matches_canonical(kit_copy: Path):
    result = kit.check(kit_copy, _manifest(kit_copy), canonical_path=kit.MANIFEST)
    assert result["verification"] == "PASS", result
    assert result["matches_canonical"] is True
    assert result["diverged_from_canonical"] == []


def test_edited_kit_file_is_reported_as_changed(kit_copy: Path):
    target = kit_copy / "scripts" / "mip_verify_self_index.py"
    target.write_text(
        target.read_text(encoding="utf-8") + "\n# local edit\n", encoding="utf-8"
    )
    result = kit.check(kit_copy, _manifest(kit_copy))
    assert result["verification"] == "FAIL"
    assert result["changed_files"] == ["scripts/mip_verify_self_index.py"]
    assert result["missing_files"] == []


def test_missing_kit_file_is_reported(kit_copy: Path):
    (kit_copy / ".codex/skills/mip-repo-self-index/agents/openai.yaml").unlink()
    result = kit.check(kit_copy, _manifest(kit_copy))
    assert result["verification"] == "FAIL"
    assert result["missing_files"] == [
        ".codex/skills/mip-repo-self-index/agents/openai.yaml"
    ]


def test_crlf_checkout_is_not_drift(kit_copy: Path):
    target = kit_copy / ".codex/skills/mip-repo-self-index/SKILL.md"
    target.write_bytes(target.read_bytes().replace(b"\n", b"\r\n"))
    assert kit.check(kit_copy, _manifest(kit_copy))["verification"] == "PASS"


def test_tampered_manifest_digest_fails(kit_copy: Path):
    manifest = json.loads(_manifest(kit_copy).read_text(encoding="utf-8"))
    manifest["kit_digest_sha256"] = "0" * 64
    _manifest(kit_copy).write_text(json.dumps(manifest), encoding="utf-8")
    result = kit.check(kit_copy, _manifest(kit_copy))
    assert result["verification"] == "FAIL"
    assert result["manifest_digest_consistent"] is False


def test_consumer_out_of_date_with_canonical_fails(kit_copy: Path):
    # The consumer edited a file AND regenerated its own manifest: the local
    # check passes, but the canonical comparison must still fail.
    target = kit_copy / "scripts" / "mip_repo_self_index.py"
    target.write_text(
        target.read_text(encoding="utf-8") + "\n# fork\n", encoding="utf-8"
    )
    _manifest(kit_copy).write_text(
        json.dumps(kit.build_manifest(kit_copy)), encoding="utf-8"
    )
    result = kit.check(kit_copy, _manifest(kit_copy), canonical_path=kit.MANIFEST)
    assert result["missing_files"] == [] and result["changed_files"] == []
    assert result["matches_canonical"] is False
    assert result["diverged_from_canonical"] == ["scripts/mip_repo_self_index.py"]
    assert result["verification"] == "FAIL"


def test_check_cli_exit_codes_and_summary(tmp_path_factory):
    summary = tmp_path_factory.mktemp("out") / "nested" / "kit.json"
    assert kit.main(["check", "--summary", str(summary)]) == 0
    assert json.loads(summary.read_text(encoding="utf-8"))["verification"] == "PASS"

    bad = tmp_path_factory.mktemp("bad") / "manifest.json"
    manifest = json.loads(kit.MANIFEST.read_text(encoding="utf-8"))
    manifest["files"][0]["sha256"] = "0" * 64
    bad.write_text(json.dumps(manifest), encoding="utf-8")
    assert kit.main(["check", "--canonical", str(bad)]) == 1


def test_unreadable_manifest_is_a_clear_error(tmp_path: Path):
    with pytest.raises(SystemExit, match="cannot read kit manifest"):
        kit.check(tmp_path, tmp_path / "absent.json")
    broken = tmp_path / "broken.json"
    broken.write_text("{", encoding="utf-8")
    with pytest.raises(SystemExit, match="not valid JSON"):
        kit.check(tmp_path, broken)


def test_kit_files_do_not_reference_abacus_only_paths():
    for rel in kit.KIT_FILES:
        text = (ROOT / rel).read_text(encoding="utf-8")
        assert "codespace_jyperter" not in text, rel


# --- surface config resolution ---------------------------------------------


def test_abacus_surface_config_declares_existing_health_probe():
    # ABACUS adaptation: CODEX declares no probe; ABACUS points at its own.
    config = emitter.load_surface_config()
    assert config["program"] == "MIP"
    assert config["health_probe"] == "scripts/mip_health_selfheal_probe.py"
    probe = emitter.resolve_health_probe(config)
    assert probe == (ROOT / config["health_probe"]).resolve()
    assert probe.is_file()


def test_health_probe_absent_key_uses_default(tmp_path: Path):
    assert (
        emitter.resolve_health_probe({}, tmp_path)
        == tmp_path / emitter.DEFAULT_HEALTH_PROBE
    )


@pytest.mark.parametrize("value", [None, ""])
def test_health_probe_null_means_no_probe(tmp_path: Path, value):
    assert emitter.resolve_health_probe({"health_probe": value}, tmp_path) is None


def test_health_probe_relative_path_resolves_under_root(tmp_path: Path):
    resolved = emitter.resolve_health_probe(
        {"health_probe": "tools/probe.py"}, tmp_path
    )
    assert resolved == (tmp_path / "tools" / "probe.py").resolve()


@pytest.mark.parametrize("value", ["../outside.py", "/etc/probe.py", 7])
def test_health_probe_outside_repo_or_wrong_type_is_rejected(tmp_path: Path, value):
    with pytest.raises(SystemExit):
        emitter.resolve_health_probe({"health_probe": value}, tmp_path)


def test_missing_or_broken_surface_config_reads_as_empty(tmp_path: Path):
    assert emitter.load_surface_config(tmp_path / "absent.json") == {}
    broken = tmp_path / "broken.json"
    broken.write_text("[1, 2]", encoding="utf-8")
    assert emitter.load_surface_config(broken) == {}


def test_no_probe_leaves_health_unexecuted():
    assert emitter.run_health_selfheal_probe(None) is None


def test_verifier_tolerates_missing_surface_config(tmp_path: Path):
    surface = verifier.load_surface(tmp_path / "absent.json")
    assert surface == {"program": "MIP"}
    assert surface.get("nested_surfaces", []) == []


def test_verifier_loads_repo_surface_config():
    surface = verifier.load_surface()
    assert surface["shareable_skill"] == ".codex/skills/mip-repo-self-index"
    assert (ROOT / surface["shareable_skill"] / "SKILL.md").is_file()
    assert set(surface["required_green"]) <= set(verifier.LANES)


@pytest.mark.parametrize(
    ("config", "message"),
    [
        ({"program": "OTHER"}, "program=MIP"),
        (
            {"program": "MIP", "required_green": ["not_a_lane"]},
            "unknown required_green",
        ),
        ({"program": "MIP", "required_green": "repo_self_produce"}, "must be a list"),
        ({"program": "MIP", "nested_surfaces": [{"path": "x"}]}, "path and emitter"),
    ],
)
def test_verifier_rejects_invalid_surface_config(tmp_path: Path, config, message):
    path = tmp_path / "mip_surface.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    with pytest.raises(SystemExit, match=message):
        verifier.load_surface(path)


def test_skill_validator_accepts_minimal_producer_summary(tmp_path: Path):
    validator = _load(
        "mip_validate_receipt",
        ".codex/skills/mip-repo-self-index/scripts/validate_receipt.py",
    )
    producer = {
        "schema_version": "0.1",
        "program": "MIP",
        "verification": "PASS",
        "repository": "GBOGEB/CODEX",
        "head_sha": "a" * 40,
        "raw_receipt_retention": "transient_runner_only",
        "root_self_index": {"runs": 2, "normalized_equal": True},
    }
    assert validator.validate_producer(producer, "a" * 40) == "a" * 40
    with pytest.raises(SystemExit, match="expected_sha"):
        validator.validate_producer(producer, "b" * 40)
