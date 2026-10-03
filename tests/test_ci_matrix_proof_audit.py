from scripts.ci_matrix_proof_audit import audit


def write_manifest(path, version, checks):
    import json

    path.write_text(
        json.dumps(
            {
                "python_version": version,
                "proof_role": "full-matrix",
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
    assert audit(tmp_path, "full", "3.10")["status"] == "PASS"


def test_missing_summary_is_proof_debt(tmp_path):
    result = audit(tmp_path, "full", "3.10")
    assert result["status"] == "FAIL"
    assert "3.10:MISSING_SUMMARY" in result["errors"]
