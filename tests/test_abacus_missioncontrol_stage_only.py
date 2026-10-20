"""ABACUS native stage-only fail-closed contract tests."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

MODULE = Path(__file__).resolve().parents[1] / "scripts" / "abacus_missioncontrol_stage_only.py"
spec = importlib.util.spec_from_file_location("abacus_missioncontrol_stage_only", MODULE)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
HEAD = "a" * 40


def runtime() -> dict[str, str]:
    return {
        "GITHUB_REPOSITORY": "GBOGEB/ABACUS", "GITHUB_ACTOR": "GBOGEB",
        "GITHUB_SHA": HEAD, "GITHUB_REF": "refs/heads/main",
        "GITHUB_EVENT_NAME": "workflow_dispatch",
        "GITHUB_RUN_ID": "123", "GITHUB_RUN_ATTEMPT": "1",
    }


def test_stage_receipt_has_no_mutation_credit() -> None:
    result = module.validate(runtime(), HEAD)
    assert result["state"] == "STAGED_ONLY_NO_WORKER_DISPATCH"
    assert result["worker_launch_id"] is None
    assert result["native_worker_job_id"] is None
    assert result["accepted_rex_receipt"] is None
    assert result["merge_admission"] == "HOLD"
    assert result["coverage_delta"] is None and result["bd_root_closures"] is None
    assert result["mutation_enabled"] is False
    assert result["request"]["head_sha"] == HEAD
    assert len(result["request_sha256"]) == 64


@pytest.mark.parametrize(("key", "bad"), [
    ("GITHUB_REPOSITORY", "GBOGEB/CODEX"),
    ("GITHUB_ACTOR", "untrusted-runner"),
    ("GITHUB_EVENT_NAME", "pull_request"),
    ("GITHUB_EVENT_NAME", "issue_comment"),
    ("GITHUB_REF", "refs/heads/feature"),
    ("GITHUB_SHA", "b" * 40),
    ("GITHUB_SHA", "not-a-sha"),
    ("GITHUB_RUN_ID", "0"),
    ("GITHUB_RUN_ID", "not-an-int"),
    ("GITHUB_RUN_ATTEMPT", "0"),
    ("GITHUB_RUN_ATTEMPT", "not-an-int"),
])
def test_rejects_invalid_native_context(key: str, bad: str) -> None:
    data = runtime()
    data[key] = bad
    with pytest.raises(module.StageRejected):
        module.validate(data, HEAD)


@pytest.mark.parametrize("expected", ["b" * 40, "short", "", "../main"])
def test_rejects_invalid_head_or_stale_request(expected: str) -> None:
    with pytest.raises(module.StageRejected):
        module.validate(runtime(), expected)


def test_stable_stage_digest_and_no_launch() -> None:
    a = module.validate(runtime(), HEAD)
    b = module.validate(runtime(), HEAD)
    assert a == b
    assert a["worker_launch_id"] is None
