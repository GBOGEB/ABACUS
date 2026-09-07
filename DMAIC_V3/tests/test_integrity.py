import json
import subprocess

import pytest

from DMAIC_V3.core.integrity import (
    assert_expected_sha,
    canonical_json_bytes,
    git_identity,
    payload_receipt,
    sha256_json,
)


def test_json_digest_is_order_independent():
    left = {"b": 2, "a": [3, 1]}
    right = {"a": [3, 1], "b": 2}
    assert canonical_json_bytes(left) == canonical_json_bytes(right)
    assert sha256_json(left) == sha256_json(right)


def test_json_digest_rejects_non_finite_numbers():
    with pytest.raises(ValueError):
        sha256_json({"bad": float("nan")})


def test_git_identity_binds_head_and_tree(tmp_path):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "ABACUS Test"], cwd=tmp_path, check=True)
    (tmp_path / "payload.json").write_text("{}\n", encoding="utf-8")
    subprocess.run(["git", "add", "payload.json"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "fixture"], cwd=tmp_path, check=True)

    identity = git_identity(tmp_path)
    assert identity.commit_sha == subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=tmp_path, text=True).strip()
    assert identity.tree_sha == subprocess.check_output(["git", "rev-parse", "HEAD^{tree}"], cwd=tmp_path, text=True).strip()


def test_receipt_is_deterministic_for_same_payload(tmp_path):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "ABACUS Test"], cwd=tmp_path, check=True)
    (tmp_path / "seed").write_text("seed", encoding="utf-8")
    subprocess.run(["git", "add", "seed"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "fixture"], cwd=tmp_path, check=True)

    first = payload_receipt(tmp_path, {"x": 1})
    second = payload_receipt(tmp_path, {"x": 1})
    assert first == second
    assert first.receipt_sha256 == second.receipt_sha256
    json.dumps(first.to_dict())


def test_expected_sha_fails_closed():
    with pytest.raises(ValueError, match="mismatch"):
        assert_expected_sha("actual", "expected")
