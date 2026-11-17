"""Lane A wave 6: handover verifier, G3CS snapshot builder, MIP surface self-index."""

import hashlib
import json
import runpy
import sys
import zipfile

import pytest

from tests.coverage_waves.lane_a._load import REPO, load

vh = load("handover/mc2/everred_20261014/verify_handover.py")
ms = load("integration/codespace_jyperter/scripts/mip_surface_self_index.py")
SNAPSHOT = REPO / "MIP" / "G3CS_CONVERGENCE_V2" / "source" / "build_snapshot.py"


def test_blob_sha_matches_git():
    assert vh.blob_sha(b"") == "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391"
    assert vh.blob_sha(b"hello\n") == "ce013625030ba8dba906f756967f9e9ca394464a"


def test_verify_handover_on_committed_package(capsys):
    vh.main()
    assert "PASS: Git handover blob hashes" in capsys.readouterr().out


def _handover(tmp_path, content=b"payload", size=None, sha=None, **state_over):
    (tmp_path / "f.txt").write_bytes(content)
    manifest = {
        "schema": "code-purple.lossless-manifest.v1",
        "files": {
            "f.txt": {
                "bytes": len(content) if size is None else size,
                "git_blob_sha1": vh.blob_sha(content) if sha is None else sha,
            }
        },
    }
    state = {
        "schema": "code-purple.lossless-handover.v1",
        "role": "HISTORICAL_RECEIVER_NOT_MERGE_AUTHORITY",
        "cut": {"main_sha": "a" * 40},
        "invariants": {
            "security_waiver": False,
            "authority_transfer": False,
            "engineering_credit_delta": 0,
        },
        "tasks": [{"id": 1}, {"id": 2}],
        "unarchived": [{"status": "NOT_ARCHIVED"}],
    }
    state.update(state_over)
    (tmp_path / "manifest.json").write_bytes(json.dumps(manifest).encode())
    (tmp_path / "state.json").write_bytes(json.dumps(state).encode())


def test_verify_handover_synthetic_pass(tmp_path, monkeypatch, capsys):
    _handover(tmp_path)
    monkeypatch.setattr(vh, "DIR", tmp_path)
    vh.main()
    assert "PASS" in capsys.readouterr().out


@pytest.mark.parametrize(
    "kwargs",
    [
        {"size": 1},
        {"sha": "0" * 40},
        {"role": "MERGE_AUTHORITY"},
        {"tasks": [{"id": 1}, {"id": 1}]},
        {"unarchived": [{"status": "ARCHIVED"}]},
        {"cut": {"main_sha": "short"}},
    ],
)
def test_verify_handover_fails_closed(tmp_path, monkeypatch, kwargs):
    _handover(tmp_path, **kwargs)
    monkeypatch.setattr(vh, "DIR", tmp_path)
    with pytest.raises(AssertionError):
        vh.main()


SHAS = {
    1: "6e23c38b2ee6504216887210769d119b4e6a709a",
    2: "38277a30cd5638a82f5dd5447d511d253d5846c0",
    3: "0f98f4f091b433c0984c361826ca7c2e9b3630c9",
}


def _zip(path, member, payload):
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr(member, json.dumps(payload))


def _artifacts(directory, bad_sha_wave=None):
    directory.mkdir()
    for i, sha in SHAS.items():
        w70 = {
            "source_sha": sha,
            "run_id": 100 + i,
            "run_attempt": 1,
            "coverage": {
                "source_sha256": "c" * 64,
                "test_selection": "sel",
                "tool_version": "7",
                "line": {"covered": 1},
                "branch": {"covered": 2},
            },
            "lanes": 3,
            "debt": {
                "closed_manifestations_sum": 4,
                "open_manifestations_sum": 5,
                "unique_confirmed_roots": 6,
            },
            "coverage_delta": 0.5,
        }
        dab = {
            "exact_sha": "f" * 40 if i == bad_sha_wave else sha,
            "command": "flake8",
            "total": 9,
            "all_families": {"E225": 1},
        }
        _zip(directory / ("dmaic-g3cs-w" + str(i) + "w70.zip"), "W70_METRICS.json", w70)
        _zip(
            directory / ("dmaic-g3cs-w" + str(i) + "dab.zip"),
            "dab_flake8_census.json",
            dab,
        )


def _build(monkeypatch, *argv):
    monkeypatch.setattr(sys, "argv", ["build_snapshot.py", *argv])
    return runpy.run_path(str(SNAPSHOT))


def test_build_snapshot_writes_bound_observation(tmp_path, monkeypatch, capsys):
    art = tmp_path / "art"
    _artifacts(art)
    out = tmp_path / "o" / "snap.json"
    _build(monkeypatch, "--artifact-dir", str(art), "--out", str(out))
    snap = json.loads(out.read_text(encoding="utf-8"))
    assert [w["wave"] for w in snap["waves"]] == ["S1", "S2", "S3"]
    assert snap["waves"][0]["source_sha"] == SHAS[1]
    assert snap["waves"][0]["proofs"] == {
        "handover_native_tests": 14,
        "native_smoke": "success",
    }
    assert snap["waves"][1]["proofs"] == {}
    assert snap["waves"][2]["proofs"] == {"pytest_validation_workflow": "success"}
    assert snap["waves"][1]["dab"]["families"] == {"E225": 1, "W292": None}
    assert snap["waves"][2]["w70"]["closed_manifestations"] == 4
    assert len(snap["evidence_files"]) == 6
    first = snap["evidence_files"][0]
    raw = zipfile.ZipFile(art / "dmaic-g3cs-w1w70.zip").read("W70_METRICS.json")
    assert first["sha256"] == hashlib.sha256(raw).hexdigest()
    assert first["locator"] == "dmaic-g3cs-w1w70.zip#W70_METRICS.json"
    assert "evidence_objects 6" in capsys.readouterr().out


def test_build_snapshot_requires_artifacts(tmp_path, monkeypatch):
    (tmp_path / "empty").mkdir()
    with pytest.raises(FileNotFoundError, match="Native artifact required"):
        _build(monkeypatch, "--artifact-dir", str(tmp_path / "empty"), "--out", "x")


def test_build_snapshot_rejects_sha_mismatch(tmp_path, monkeypatch):
    _artifacts(tmp_path / "art", bad_sha_wave=2)
    with pytest.raises(AssertionError):
        _build(
            monkeypatch,
            "--artifact-dir",
            str(tmp_path / "art"),
            "--out",
            str(tmp_path / "s.json"),
        )


@pytest.fixture
def surface(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    root = repo / "integration" / "cj"
    for rel, text in {
        "src/notebook_parser.py": "# TODO tidy\n",
        "tests/test_smoke.py": "def test(): pass\n",
        "contract.yaml": "a: 1\n",
        "federation_manifest.json": "{}\n",
        "debug/trace_log.md": "notes\n",
        "selfheal/repair.sh": "echo ok\n",
        "data.bin": "\x00",
        ".git/config": "x",
        "__pycache__/x.pyc": "x",
    }.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.encode())
    monkeypatch.setattr(ms, "SURFACE_ROOT", root)
    monkeypatch.setattr(ms, "REPO_ROOT", repo)
    return root


def test_iter_files_and_helpers(surface):
    files = ms.iter_files()
    names = [p.as_posix() for p in files]
    assert ".git/config" not in names and "__pycache__/x.pyc" not in names
    assert names == sorted(names)
    assert ms.contains_any(files[0], ("contract",)) is (names[0] == "contract.yaml")
    assert ms.grep_count(files, ("todo",)) == 1
    assert ms.sample(files, limit=2) == names[:2]


def test_grep_count_skips_unreadable(surface):
    from pathlib import Path

    assert ms.grep_count([Path("missing.md"), Path("data.bin")], ("x",)) == 0


def test_classify_signals(surface):
    result = ms.classify(ms.iter_files())
    assert result["repo_self_assess_debug_ldab"]["status"] == "green"
    assert result["repo_self_assess_runners_mcp"]["status"] == "green"
    assert result["repo_self_assess_codz_health_selfheal"]["status"] == "amber"
    assert result["repo_self_produce"]["status"] == "amber"


def test_classify_empty_surface():
    result = ms.classify([])
    assert result["repo_self_assess_debug_ldab"]["status"] == "red"
    assert "Add a tiny" in result["repo_self_assess_debug_ldab"]["next_action"]
    assert result["repo_self_assess_runners_mcp"]["status"] == "amber"
    assert result["repo_self_assess_codz_health_selfheal"]["status"] == "green"
    assert result["repo_self_produce"]["status"] == "red"


def test_run_git_success_and_failure(monkeypatch):
    def ok(cmd, stderr, text):
        assert cmd[:2] == ["git", "-C"]
        return " value \n"

    monkeypatch.setattr("subprocess.check_output", ok)
    assert ms.run_git(["rev-parse", "HEAD"]) == "value"

    def fail(cmd, stderr, text):
        raise OSError("no git")

    monkeypatch.setattr("subprocess.check_output", fail)
    assert ms.run_git(["x"]) is None


def test_main_writes_receipt(surface, tmp_path, monkeypatch, capsys):
    answers = {
        "status": " M src/notebook_parser.py\n?? new.md",
        "remote": "https://example.invalid/repo.git",
        "branch": "",
        "rev-parse": "d" * 40,
    }

    def fake_git(args):
        if args[0] == "rev-parse" and args[1] == "--abbrev-ref":
            return "detached"
        return answers.get(args[0]) or None

    monkeypatch.setattr(ms, "run_git", fake_git)
    out = surface.parent.parent / "out" / "receipt.json"
    monkeypatch.setattr(sys, "argv", ["self_index", "--output", str(out)])
    assert ms.main() == 0
    receipt = json.loads(out.read_text(encoding="utf-8"))
    assert receipt["surface"]["path"].replace("\\", "/") == "integration/cj"
    assert receipt["surface"]["parent_branch"] == "detached"
    assert receipt["surface"]["dirty_file_count"] == 2
    assert receipt["census"]["file_count"] == 7
    assert receipt["census"]["top_directory_counts"]["<root>"] == 3
    printed = capsys.readouterr().out
    assert "Wrote out" in printed.replace("\\", "/")

    outside = tmp_path / "elsewhere.json"
    monkeypatch.setattr(sys, "argv", ["self_index", "--output", str(outside)])
    assert ms.main() == 0
    assert str(outside) in capsys.readouterr().out
