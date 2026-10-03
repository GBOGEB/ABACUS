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
        "3.10": {
            "canonical_coverage": "CLASSIFIED_ROLE_SKIP",
            "functional_compatibility": "EXECUTED_PASS",
            "phase0": "CLASSIFIED_ROLE_SKIP",
            "qps_w08": "CLASSIFIED_ROLE_SKIP",
            "recursive_build": "EXECUTED_PASS",
            "artifact_upload": "OPTIONAL_NO_PAYLOAD",
        },
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
    assert audit(tmp_path, "full", "3.10", EXPECTED_SHA)["status"] == "PASS"


def test_missing_summary_is_proof_debt(tmp_path):
    result = audit(tmp_path, "full", "3.10", EXPECTED_SHA)
    assert result["status"] == "FAIL"
    assert "3.10:MISSING_SUMMARY" in result["errors"]


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
        tmp_path / "python-3.10-proof.json",
        "3.11",
        checks,
        exact_sha="b" * 40,
        proof_role="sentinel",
    )
    result = audit(tmp_path, "sampled", "3.10", EXPECTED_SHA)
    assert "3.10:exact_sha" in result["errors"]
    assert "3.10:python_version" in result["errors"]
    assert "3.10:proof_role" in result["errors"]
