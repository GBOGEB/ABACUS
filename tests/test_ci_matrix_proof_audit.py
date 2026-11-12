"""Proof-audit contract. Interpreter versions come from ssot/python_versions.lanes.json,
so these tests keep their meaning across Python bumps without literal edits."""

import json

import pytest

from scripts.ci_matrix_proof_audit import (
    COMPATIBILITY_CHECKS,
    SENTINEL_CHECKS,
    audit,
    expected_versions,
    load_lane,
)

EXPECTED_SHA = "a" * 40
LANE = load_lane()
SENTINEL = LANE["pin"]
SECONDARY = LANE["oldest"]


def write_manifest(
    path,
    version,
    checks,
    exact_sha=EXPECTED_SHA,
    proof_role="full-matrix",
):
    path.write_text(
        json.dumps(
            {
                "exact_sha": exact_sha,
                "python_version": version,
                "proof_role": proof_role,
                "checks": checks,
            }
        ),
        encoding="utf-8",
    )


def passing_checks(version):
    base = SENTINEL_CHECKS if version == SENTINEL else COMPATIBILITY_CHECKS
    return {**base, "artifact_upload": "OPTIONAL_NO_PAYLOAD"}


def test_lane_view_shape_is_consistent():
    assert SENTINEL in LANE["versions"]
    assert SECONDARY == LANE["versions"][0]
    assert (
        SENTINEL != SECONDARY
    ), "sentinel and compatibility sample must be distinct cells"


def test_full_matrix_accepts_classified_role_skips(tmp_path):
    for version in LANE["versions"]:
        write_manifest(
            tmp_path / f"python-{version}-proof.json", version, passing_checks(version)
        )
    assert audit(tmp_path, "full", SECONDARY, EXPECTED_SHA)["status"] == "PASS"


def test_full_matrix_requires_every_lane_version(tmp_path):
    for version in LANE["versions"][:-1]:
        write_manifest(
            tmp_path / f"python-{version}-proof.json", version, passing_checks(version)
        )
    result = audit(tmp_path, "full", SECONDARY, EXPECTED_SHA)
    assert result["status"] == "FAIL"
    assert f"{LANE['versions'][-1]}:MISSING_SUMMARY" in result["errors"]


def test_missing_summary_is_proof_debt(tmp_path):
    result = audit(tmp_path, "full", SECONDARY, EXPECTED_SHA)
    assert result["status"] == "FAIL"
    for version in LANE["versions"]:
        assert f"{version}:MISSING_SUMMARY" in result["errors"]
    assert not any(e.startswith(("3.9:", "3.10:")) for e in result["errors"])


def test_manifest_identity_and_role_must_match_expected_matrix(tmp_path):
    write_manifest(
        tmp_path / f"python-{SECONDARY}-proof.json",
        SENTINEL,
        passing_checks(SECONDARY),
        exact_sha="b" * 40,
        proof_role="sentinel",
    )
    result = audit(tmp_path, "sampled", SECONDARY, EXPECTED_SHA)
    assert f"{SECONDARY}:exact_sha" in result["errors"]
    assert f"{SECONDARY}:python_version" in result["errors"]
    assert f"{SECONDARY}:proof_role" in result["errors"]


def test_sentinel_duties_follow_the_lane_pin(tmp_path):
    # A non-sentinel cell that ran sentinel-only checks is proof debt.
    write_manifest(
        tmp_path / f"python-{SECONDARY}-proof.json",
        SECONDARY,
        {**SENTINEL_CHECKS, "artifact_upload": "OPTIONAL_NO_PAYLOAD"},
        proof_role="compatibility-sample",
    )
    write_manifest(
        tmp_path / f"python-{SENTINEL}-proof.json",
        SENTINEL,
        passing_checks(SENTINEL),
        proof_role="sentinel",
    )
    result = audit(tmp_path, "sampled", SECONDARY, EXPECTED_SHA)
    assert result["status"] == "FAIL"
    assert f"{SECONDARY}:canonical_coverage:EXECUTED_PASS" in result["errors"]


def test_invalid_manifest_payload_is_fail_closed(tmp_path):
    assert expected_versions("full", SECONDARY) == LANE["versions"]
    assert expected_versions("sampled", SECONDARY) == [SECONDARY, SENTINEL]
    assert expected_versions("sentinel", SECONDARY) == [SENTINEL]
    for bad in ("3.10", SENTINEL, "3.9", "", f"3.10,{SECONDARY}"):
        with pytest.raises(ValueError):
            expected_versions("sampled", bad)
    with pytest.raises(ValueError):
        expected_versions("full", SECONDARY, lane="no-such-lane")

    for label, payload in (
        ("nonobject", "[]"),
        ("broken_json", "{"),
        ("null_checks", json.dumps({"checks": None})),
        ("array_checks", json.dumps({"checks": []})),
        ("false_checks", json.dumps({"checks": False})),
    ):
        (tmp_path / f"python-{SENTINEL}-proof.json").write_text(
            payload, encoding="utf-8"
        )
        receipt = audit(tmp_path, "sentinel", SECONDARY, EXPECTED_SHA)
        assert receipt["status"] == "FAIL", label
        assert receipt["errors"], label


def test_invalid_source_hash_type_is_fail_closed(tmp_path):
    for bad in (None, 123, True, [], {}):
        result = audit(tmp_path, "sentinel", SECONDARY, bad)
        assert result["status"] == "FAIL"
        assert "EXPECTED_SHA_INVALID" in result["errors"]
