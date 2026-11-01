from scripts.ci_matrix_proof_audit import audit

EXPECTED_SHA = "a" * 40


def write_manifest(
    path,
    version,
    checks,
    exact_sha=EXPECTED_SHA,
    proof_role="full-matrix",
):
    import json

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


def test_full_matrix_accepts_classified_role_skips(tmp_path):
    base = {
        "3.11": {
            "canonical_coverage": "CLASSIFIED_ROLE_SKIP",
            "functional_compatibility": "EXECUTED_PASS",
            "phase0": "CLASSIFIED_ROLE_SKIP",
            "qps_w08": "CLASSIFIED_ROLE_SKIP",
            "recursive_build": "EXECUTED_PASS",
            "artifact_upload": "OPTIONAL_NO_PAYLOAD",
        },
        "3.12": {
            "canonical_coverage": "EXECUTED_PASS",
            "functional_compatibility": "CLASSIFIED_ROLE_SKIP",
            "phase0": "EXECUTED_PASS",
            "qps_w08": "EXECUTED_PASS",
            "recursive_build": "EXECUTED_PASS",
            "artifact_upload": "OPTIONAL_NO_PAYLOAD",
        },
    }
    for version, checks in base.items():
        write_manifest(tmp_path / f"python-{version}-proof.json", version, checks)
    assert audit(tmp_path, "full", "3.11", EXPECTED_SHA)["status"] == "PASS"


def test_missing_summary_is_proof_debt(tmp_path):
    result = audit(tmp_path, "full", "3.11", EXPECTED_SHA)
    assert result["status"] == "FAIL"
    assert "3.11:MISSING_SUMMARY" in result["errors"]
    assert "3.12:MISSING_SUMMARY" in result["errors"]
    assert not any(e.startswith("3.10:") for e in result["errors"])


def test_manifest_identity_and_role_must_match_expected_matrix(tmp_path):
    checks = {
        "canonical_coverage": "CLASSIFIED_ROLE_SKIP",
        "functional_compatibility": "EXECUTED_PASS",
        "phase0": "CLASSIFIED_ROLE_SKIP",
        "qps_w08": "CLASSIFIED_ROLE_SKIP",
        "recursive_build": "EXECUTED_PASS",
        "artifact_upload": "OPTIONAL_NO_PAYLOAD",
    }
    write_manifest(
        tmp_path / "python-3.11-proof.json",
        "3.12",
        checks,
        exact_sha="b" * 40,
        proof_role="sentinel",
    )
    result = audit(tmp_path, "sampled", "3.11", EXPECTED_SHA)
    assert "3.11:exact_sha" in result["errors"]
    assert "3.11:python_version" in result["errors"]
    assert "3.11:proof_role" in result["errors"]


def test_invalid_manifest_payload_is_fail_closed(tmp_path):
    import json

    import pytest

    from scripts.ci_matrix_proof_audit import expected_versions

    assert expected_versions("full", "3.11") == ["3.11", "3.12"]
    assert expected_versions("sampled", "3.11") == ["3.11", "3.12"]
    for bad in ("3.10", "3.12", "3.9", "", "3.10,3.11"):
        with pytest.raises(ValueError):
            expected_versions("sampled", bad)

    for label, payload in (
        ("nonobject", "[]"),
        ("broken_json", "{"),
        ("null_checks", json.dumps({"checks": None})),
        ("array_checks", json.dumps({"checks": []})),
        ("false_checks", json.dumps({"checks": False})),
    ):
        (tmp_path / "python-3.12-proof.json").write_text(payload, encoding="utf-8")
        receipt = audit(tmp_path, "sentinel", "3.11", EXPECTED_SHA)
        assert receipt["status"] == "FAIL", label
        assert receipt["errors"], label


def test_invalid_source_hash_type_is_fail_closed(tmp_path):
    for bad in (None, 123, True, [], {}):
        result = audit(tmp_path, "sentinel", "3.11", bad)
        assert result["status"] == "FAIL"
        assert "EXPECTED_SHA_INVALID" in result["errors"]
