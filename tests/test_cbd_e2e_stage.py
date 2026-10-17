"""Adversarial stage, clock, clean-clone, source and coverage-scope tests."""
import copy
import json
import subprocess
import sys
from pathlib import Path
from unittest import mock

import pytest

from scripts import cbd_e2e_stage as e2e


def receipt(stage="checkout", sha="a" * 40, tests=55):
    return {
        "schema": "abacus.cbd.e2e.stage.v1",
        "stage": stage,
        "status": "PASS",
        "source": {"head_sha": sha, "head_tree_sha": "b" * 40},
        "checks": [{"name": name, "status": "PASS"}
                   for name in ("compile", "black", "isort", "pytest")],
        "tests_executed": tests,
        "clock": {"elapsed_process_ms": 1200},
    }


def test_identical_exact_source_parity_passes_not_merge():
    result = e2e.compare(receipt(), receipt("replay"))
    assert result["status"] == "PASS"
    assert result["merge_admission"] == "HOLD"
    assert result["developer_pre_push_vs_ci"] is None
    assert result["cross_host_elapsed_delta_ms"] is None


def test_different_source_sha_cannot_pass():
    other = receipt("replay", sha="c" * 40)
    result = e2e.compare(receipt(), other)
    assert result["status"] == "HOLD"
    assert "source mismatch: head_sha" in result["differences"]


def test_different_tree_sha_cannot_pass():
    other = receipt("replay")
    other["source"]["head_tree_sha"] = "d" * 40
    assert "source mismatch: head_tree_sha" in e2e.compare(receipt(), other)["differences"]


def test_different_executed_denominators_hold():
    other = receipt("replay", tests=54)
    result = e2e.compare(receipt(), other)
    assert result["status"] == "HOLD"
    assert "test denominator mismatch" in result["differences"]


@pytest.mark.parametrize("value", [None, 0, "55"])
def test_unverified_test_denominator_holds(value):
    other = receipt("replay", tests=value)
    result = e2e.compare(receipt(), other)
    assert result["status"] == "HOLD"


def test_failed_stage_cannot_be_promoted_to_parity():
    other = receipt("replay")
    other["status"] = "FAIL"
    assert e2e.compare(receipt(), other)["status"] == "HOLD"


def test_missing_required_linter_holds():
    other = receipt("replay")
    other["checks"] = [x for x in other["checks"] if x["name"] != "black"]
    assert "unverified check: black" in e2e.compare(receipt(), other)["differences"]


def test_output_hashes_instead_of_raw_secret(tmp_path):
    result = e2e.command(
        [sys.executable, "-c", "print('SECRET_TOKEN_SHOULD_NOT_APPEAR')"], tmp_path
    )
    evidence = e2e.project_check(result, "other")
    assert evidence["status"] == "PASS"
    assert "SECRET_TOKEN_SHOULD_NOT_APPEAR" not in json.dumps(evidence)
    assert len(evidence["stdout_sha256"]) == 64


def test_nonzero_command_fails_closed(tmp_path):
    value = e2e.command([sys.executable, "-c", "raise SystemExit(3)"], tmp_path)
    assert value["status"] == "FAIL"
    assert value["returncode"] == 3


def test_false_green_on_unparseable_pytest_denominator_rejected():
    value = {"status": "PASS", "output": "OK: Ran 0 tests", "returncode": 0}
    result = e2e.project_check(value, "pytest")
    assert result["tests_passed"] is None
    assert result["status"] == "UNKNOWN"


def test_no_required_files_is_not_success(tmp_path):
    result = e2e.run_stage(tmp_path, "pre-commit")
    assert result["status"] == "FAIL"
    assert result["tests_executed"] is None
    assert result["local_developer_hook_verified"] is None


def test_expected_git_sha_mismatch_is_hard_failure(tmp_path):
    with mock.patch.object(e2e, "fingerprint", return_value={
        "head_sha": "a" * 40,
        "head_tree_sha": "b" * 40,
        "tracked_changes_present": False,
    }), mock.patch.object(e2e, "tools_for_stage", return_value=[
        ("pytest", [sys.executable, "-c", "print('4 passed')"])
    ]):
        result = e2e.run_stage(tmp_path, "checkout", "c" * 40)
    assert result["status"] == "FAIL"
    assert result["source_exact"] is False


def test_dirty_tracked_prepush_is_rejected(tmp_path):
    with mock.patch.object(e2e, "fingerprint", return_value={
        "head_sha": "a" * 40,
        "head_tree_sha": "b" * 40,
        "tracked_changes_present": True,
    }), mock.patch.object(e2e, "tools_for_stage", return_value=[
        ("pytest", [sys.executable, "-c", "print('3 passed')"])
    ]):
        result = e2e.run_stage(tmp_path, "pre-push")
    assert result["status"] == "FAIL"
    assert result["clean_tracked"] is False


def test_receipt_is_deterministic_file_shape(tmp_path):
    path = tmp_path / "receipt.json"
    original = e2e.compare(receipt(), receipt("replay"))
    assert e2e.write_receipt(path, original) == path
    parsed = json.loads(path.read_text())
    assert parsed["schema"] == "abacus.cbd.e2e.diff.v1"
    assert parsed["merge_admission"] == "HOLD"


def test_local_git_replay_checks_exact_checkout_without_network(tmp_path):
    origin = tmp_path / "origin"
    origin.mkdir()
    subprocess.run(["git", "init", "-q", str(origin)], check=True)
    (origin / "README.md").write_text("source-bound")
    subprocess.run(["git", "-C", str(origin), "add", "README.md"], check=True)
    subprocess.run([
        "git", "-C", str(origin), "-c", "user.name=Test",
        "-c", "user.email=tests@example.invalid", "commit", "-qm", "fixture"
    ], check=True)
    sha = e2e.git_value(origin, "rev-parse", "HEAD")
    tree = e2e.git_value(origin, "rev-parse", "HEAD^{tree}")
    asserted = []

    def verify_fresh_clone(repo, stage, expected):
        assert stage == "checkout"
        assert repo != origin
        assert e2e.git_value(repo, "rev-parse", "HEAD") == sha == expected
        assert e2e.git_value(repo, "rev-parse", "HEAD^{tree}") == tree
        asserted.append(True)
        data = receipt(stage, sha)
        return data

    with mock.patch.object(e2e, "run_stage", side_effect=verify_fresh_clone):
        result = e2e.replay(origin, sha)
    assert asserted == [True]
    assert result["status"] == "PASS"
    assert result["remote_github_fresh_clone_proven"] is False
    assert [x["status"] for x in result["clone_steps"]] == ["PASS"] * 3


def test_unfetchable_head_fails_not_claim_success(tmp_path):
    origin = tmp_path / "origin"
    origin.mkdir()
    subprocess.run(["git", "init", "-q", str(origin)], check=True)
    result = e2e.replay(origin, "e" * 40)
    assert result["status"] == "FAIL"
    assert result["remote_github_fresh_clone_proven"] is False
