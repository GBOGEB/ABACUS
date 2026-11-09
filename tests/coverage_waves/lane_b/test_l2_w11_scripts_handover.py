"""Lane-B wave 11: handover / knowledge-package generator scripts."""

import json
import sys
import types
import zipfile
from datetime import datetime as real_datetime

import pytest
import yaml

from ._l2_loader import load

hg = load("scripts/handover_generator.py")
kp = load("scripts/initialize_knowledge_packages.py")
gy = load("scripts/build_handover_from_glob_yaml.py")
tm = load("src/dmaic/tuple_metadata.py")

_saved_path = list(sys.path)
try:
    ft = load(
        "scripts/build_final_handover_tracker.py",
        deps={
            "dmaic": types.ModuleType("dmaic"),
            "dmaic.tuple_metadata": tm,
        },
    )
finally:
    sys.path[:] = _saved_path

FIXED = real_datetime(2026, 1, 2, 3, 4, 5)


class _FrozenDatetime(real_datetime):
    @classmethod
    def now(cls, tz=None):
        return FIXED


# --------------------------------------------------------------------------
# handover_generator
# --------------------------------------------------------------------------


def test_handover_summary_contains_sections_and_timestamps(monkeypatch):
    monkeypatch.setattr(hg, "datetime", _FrozenDatetime)
    text = hg.generate_handover_summary()
    assert text.startswith("# DMAIC V3.3 - Enhanced Handover Package")
    assert text.count(FIXED.isoformat()) == 2
    assert "results.get('statistics', {})" in text
    assert "## ✅ SUCCESS CRITERIA" in text


def test_handover_checklist_structure(monkeypatch):
    monkeypatch.setattr(hg, "datetime", _FrozenDatetime)
    data = hg.generate_handover_checklist()["handover_checklist"]
    assert data["version"] == "3.3.0-enhanced"
    assert data["generated_at"] == FIXED.isoformat()
    names = [s["section"] for s in data["sections"]]
    assert names == [
        "Code Deliverables",
        "Documentation",
        "Testing & Validation",
        "Deployment",
    ]
    statuses = {i["status"] for s in data["sections"] for i in s["items"]}
    assert statuses == {"COMPLETE", "PENDING"}


def test_handover_main_writes_all_artifacts(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "scripts").mkdir()
    hg.main()
    out = capsys.readouterr().out
    assert "HANDOVER PACKAGE GENERATED" in out
    md = tmp_path / "artifacts" / "markdown" / "HANDOVER_PACKAGE.md"
    assert md.read_text(encoding="utf-8").startswith("# DMAIC V3.3")
    js = json.loads(
        (tmp_path / "artifacts" / "json" / "handover_checklist.json").read_text(
            encoding="utf-8"
        )
    )
    ym = yaml.safe_load(
        (tmp_path / "artifacts" / "yaml" / "handover_checklist.yaml").read_text(
            encoding="utf-8"
        )
    )
    assert js == ym
    assert len(js["handover_checklist"]["sections"]) == 4
    sh = (tmp_path / "scripts" / "execute_phase4_enhanced.sh").read_text(
        encoding="utf-8"
    )
    assert sh.startswith("#!/bin/bash")


def test_handover_main_requires_existing_scripts_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(FileNotFoundError):
        hg.main()
    assert (tmp_path / "artifacts" / "yaml" / "handover_checklist.yaml").exists()


# --------------------------------------------------------------------------
# initialize_knowledge_packages
# --------------------------------------------------------------------------


def test_write_if_changed_created_skipped_updated(tmp_path):
    target = tmp_path / "deep" / "file.txt"
    assert kp._write_if_changed(target, "a") == "created"
    assert kp._write_if_changed(target, "a") == "skipped"
    assert kp._write_if_changed(target, "b") == "updated"
    assert target.read_text(encoding="utf-8") == "b"


def test_knowledge_package_contents(tmp_path):
    init = kp.KnowledgePackageInitializer(tmp_path)
    assert init.knowledge_dir == tmp_path / "knowledge_packages"
    assert init.knowledge_dir.is_dir()
    pkg = init.create_dmaic_knowledge_package()
    assert pkg["version"] == kp.VERSION
    assert [p["id"] for p in pkg["process_overview"]["phases"]] == [
        "phase" + str(i) for i in range(7)
    ]
    ctx = init.create_agent_context()
    assert ctx["agent_role"] == "DMAIC Process Assistant"
    assert set(ctx["guidelines"]) == {
        "code_analysis",
        "metrics_interpretation",
        "recommendations",
    }


def test_initialize_all_packages_is_idempotent(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(kp, "datetime", _FrozenDatetime)
    init = kp.KnowledgePackageInitializer(tmp_path)
    init.initialize_all_packages()
    first = capsys.readouterr().out
    assert first.count("Created:") == 5
    assert "5 files present" in first

    kdir = tmp_path / "knowledge_packages"
    loaded = json.loads((kdir / "dmaic_core_knowledge.json").read_text("utf-8"))
    assert loaded["created"] == FIXED.isoformat()
    readme = (kdir / "README.md").read_text(encoding="utf-8")
    assert "**Generated:** 2026-01-02 03:04:05" in readme

    (kdir / "agent_context.yaml").write_text("stale", encoding="utf-8")
    init.initialize_all_packages()
    second = capsys.readouterr().out
    assert second.count("Skipped:") == 4
    assert second.count("Updated:") == 1
    assert yaml.safe_load((kdir / "agent_context.yaml").read_text("utf-8"))[
        "version"
    ] == (kp.VERSION)


# --------------------------------------------------------------------------
# build_handover_from_glob_yaml
# --------------------------------------------------------------------------


def _glob_env(tmp_path, monkeypatch, spec=None):
    root = tmp_path / "repo"
    out = root / "handover"
    out.mkdir(parents=True)
    spec_path = out / "GLOOB.yaml"
    if spec is not None:
        spec_path.write_text(yaml.safe_dump(spec), encoding="utf-8")
    monkeypatch.setattr(gy, "ROOT", root)
    monkeypatch.setattr(gy, "SPEC", spec_path)
    monkeypatch.setattr(gy, "OUT_DIR", out)
    return root, out


def test_sha256sum_matches_hashlib(tmp_path):
    p = tmp_path / "blob.bin"
    p.write_bytes(b"x" * 20000)
    assert gy.sha256sum(p) == gy.hashlib.sha256(b"x" * 20000).hexdigest()


def test_glob_spec_missing_returns_2(tmp_path, monkeypatch, capsys):
    _glob_env(tmp_path, monkeypatch)
    assert gy.main() == 2
    assert "Spec not found" in capsys.readouterr().out


def test_glob_no_matches_returns_1_with_default_bundle(tmp_path, monkeypatch, capsys):
    _, out = _glob_env(tmp_path, monkeypatch, spec={"other": 1})
    assert gy.main() == 1
    assert "No files matched" in capsys.readouterr().out
    assert not list(out.glob("*.zip"))


def test_glob_builds_zip_and_checksums(tmp_path, monkeypatch, capsys):
    spec = {
        "bundle": {
            "name": "BUNDLE",
            "include": ["docs/**", "notes.txt"],
            "exclude": ["docs/skip.md"],
        }
    }
    root, out = _glob_env(tmp_path, monkeypatch, spec=spec)
    (root / "docs" / "sub").mkdir(parents=True)
    (root / "docs" / "keep.md").write_text("keep", encoding="utf-8")
    (root / "docs" / "skip.md").write_text("skip", encoding="utf-8")
    (root / "docs" / "sub" / "deep.md").write_text("deep", encoding="utf-8")
    (root / "notes.txt").write_text("n", encoding="utf-8")

    assert gy.main() == 0
    assert "with 3 files" in capsys.readouterr().out
    with zipfile.ZipFile(out / "BUNDLE.zip") as zf:
        names = sorted(n.replace("\\", "/") for n in zf.namelist())
    assert names == ["docs/keep.md", "docs/sub/deep.md", "notes.txt"]
    sums = json.loads((out / "BUNDLE.sha256.json").read_text(encoding="utf-8"))
    norm = {k.replace("\\", "/"): v for k, v in sums.items()}
    assert norm["notes.txt"] == gy.hashlib.sha256(b"n").hexdigest()
    assert len(norm) == 3


# --------------------------------------------------------------------------
# build_final_handover_tracker
# --------------------------------------------------------------------------

_ENV_KEYS = (
    "GITHUB_JOB_STATUS",
    "GITHUB_REF_NAME",
    "BRANCH_NAME",
    "ABACUS_REVIEWED_BRANCHES",
    "GITHUB_REPOSITORY",
    "GITHUB_RUN_ID",
    "GITHUB_WORKFLOW",
    "GITHUB_RUN_NUMBER",
    "GITHUB_EVENT_NAME",
    "GITHUB_SHA",
)


@pytest.fixture
def tracker_env(tmp_path, monkeypatch):
    for key in _ENV_KEYS:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(ft, "ROOT_DIR", tmp_path)
    return tmp_path


def _write_manifest(root, payload):
    path = root / "docs" / "api" / "phase2_reconstruction_manifest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_phase2_manifest_missing(tracker_env):
    assert ft._load_phase2_manifest() == {
        "manifest_version": "missing",
        "component_count": 0,
    }


def test_phase2_manifest_present(tracker_env):
    _write_manifest(tracker_env, {"component_map": [1, 2], "artifacts": [1]})
    assert ft._load_phase2_manifest() == {
        "manifest_version": "unknown",
        "component_count": 2,
        "artifact_count": 1,
    }


@pytest.mark.parametrize(
    "raw,expected",
    [
        (" SUCCESS ", "validated"),
        ("failure", "blocked"),
        ("cancelled", "blocked"),
        ("", "in_progress"),
    ],
)
def test_ci_status_mapping(tracker_env, monkeypatch, raw, expected):
    monkeypatch.setenv("GITHUB_JOB_STATUS", raw)
    assert ft._ci_status() == expected


def test_current_branch_precedence(tracker_env, monkeypatch):
    assert ft._current_branch() == "local"
    monkeypatch.setenv("BRANCH_NAME", "b-env")
    assert ft._current_branch() == "b-env"
    monkeypatch.setenv("GITHUB_REF_NAME", "ref")
    assert ft._current_branch() == "ref"


def test_reviewed_branches(tracker_env, monkeypatch):
    assert ft._reviewed_branches("main") == ["develop", "main"]
    assert ft._reviewed_branches("feat") == ["develop", "feat", "main"]
    monkeypatch.setenv("ABACUS_REVIEWED_BRANCHES", " x , ,x,y")
    assert ft._reviewed_branches("y") == ["x", "y"]


def test_build_payload_defaults_valid(tracker_env):
    payload = ft.build_payload()
    assert tm.validate_tracker_payload(payload) == []
    assert payload["ci_pipeline"]["status"] == "in_progress"
    assert payload["ci_pipeline"]["run_url"].endswith("GBOGEB/ABACUS/actions/runs/0")
    assert payload["branches"] == [
        {"name": "develop", "reviewed": True, "status": "validated"},
        {"name": "local", "reviewed": False, "status": "in_progress"},
        {"name": "main", "reviewed": True, "status": "validated"},
    ]
    phase2_mod = payload["modules"][3]
    assert phase2_mod["status"] == "in_progress"
    by_id = {t["tuple_id"]: t for t in payload["tuple_metadata"]}
    assert by_id["tuple-artifact-export"]["status"] == "in_progress"
    assert by_id["tuple-reconstruction-manifest"]["status"] == "in_progress"


def test_build_payload_success_with_manifest(tracker_env, monkeypatch):
    _write_manifest(tracker_env, {"manifest_version": "2", "component_map": [1]})
    monkeypatch.setenv("GITHUB_JOB_STATUS", "success")
    monkeypatch.setenv("GITHUB_REPOSITORY", "o/r")
    monkeypatch.setenv("GITHUB_RUN_ID", "77")
    payload = ft.build_payload()
    assert payload["ci_pipeline"]["run_url"] == (
        "https://github.com/o/r/actions/runs/77"
    )
    assert payload["modules"][3]["status"] == "validated"
    statuses = {t["tuple_id"]: t["status"] for t in payload["tuple_metadata"]}
    assert set(statuses.values()) == {"validated"}
    assert payload["tuple_metadata"][2]["validation_log"] == "phase2 components: 1"


def test_main_writes_relative_output(tracker_env, monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["prog"])
    assert ft.main() == 0
    out = tracker_env / "docs" / "api" / "final_handover_tracker.json"
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["status_schema"] == list(tm.default_status_schema())
    assert "[OK] Wrote tracker metadata" in capsys.readouterr().out


def test_main_writes_absolute_output(tracker_env, tmp_path, monkeypatch):
    target = tmp_path / "abs" / "t.json"
    monkeypatch.setattr(sys, "argv", ["prog", "--output", str(target)])
    assert ft.main() == 0
    assert json.loads(target.read_text(encoding="utf-8"))["branches"]


def test_main_reports_validation_errors(tracker_env, monkeypatch, capsys):
    monkeypatch.setattr(ft, "validate_tracker_payload", lambda p: ["bad1", "bad2"])
    monkeypatch.setattr(sys, "argv", ["prog"])
    assert ft.main() == 1
    out = capsys.readouterr().out
    assert "ERROR: bad1" in out and "ERROR: bad2" in out
    assert not (tracker_env / "docs").exists()
