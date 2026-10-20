"""Synthetic adversarial corpus for byte-verifier; no real GitHub admission."""
import hashlib
import io
import json
import zipfile
from xml.etree import ElementTree as ET

import pytest
from tools.recovery import w34_native_artifact_verify as v

HEAD = "a" * 40
SCOPE = ["tools/recovery/w32_runner_telemetry.py"]


def make_bundle(*, cases=2, header=None, fail=False, skip=False,
                branch=True, covered=9, eligible=10, override=None,
                other_members=None):
    suite = ET.Element("testsuite", {
        "tests": str(cases if header is None else header),
        "failures": str(int(fail)), "errors": "0", "skipped": str(int(skip)),
    })
    for i in range(cases):
        case = ET.SubElement(suite, "testcase", classname="suite", name=f"test_{i}")
        if i == 0 and fail:
            ET.SubElement(case, "failure")
        if i == 0 and skip:
            ET.SubElement(case, "skipped")
    junit = ET.tostring(suite)
    coverage = json.dumps({"meta": {"branch_coverage": branch},
      "files": {SCOPE[0]: {"summary": {
          "num_statements": eligible - 2, "covered_lines": covered - 2,
          "num_branches": 2, "covered_branches": 2}}}}).encode()
    receipt = {"schema": "abacus.w34.native.v1", "head_sha": HEAD,
               "run_id": 39123456789, "run_attempt": 1, "job_id": 117123456789,
               "scope_paths": SCOPE,
               "member_sha256": {"junit.xml": hashlib.sha256(junit).hexdigest(),
                                 "coverage.json": hashlib.sha256(coverage).hexdigest()}}
    if override:
        receipt.update(override)
    content = {"junit.xml": junit, "coverage.json": coverage,
               "receipt.json": json.dumps(receipt).encode()}
    if other_members:
        content.update(other_members)
    f = io.BytesIO()
    with zipfile.ZipFile(f, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for k, data in content.items():
            z.writestr(k, data)
    blob = f.getvalue()
    expected = {"head_sha": HEAD, "run_id": 39123456789, "run_attempt": 1,
                "job_id": 117123456789, "scope_paths": SCOPE,
                "zip_sha256": hashlib.sha256(blob).hexdigest(),
                "coverage_floor_pct": 80}
    return blob, expected


def test_valid_synthetic_integrity_is_not_native_admission():
    zipdata, expected = make_bundle()
    r = v.verify(zipdata, expected=expected)
    assert r["executed_cases"] == 2
    assert r["eligible_opportunities"] == 10
    assert r["covered_opportunities"] == 9
    assert r["admission"] == "HOLD"
    assert r["github_provider_authentication"] is None


@pytest.mark.parametrize("field,bad,match", [
    ("head_sha", "b" * 40, "foreign exact"),
    ("run_id", 2, "foreign exact"),
    ("run_attempt", 3, "foreign exact"),
    ("job_id", 999, "foreign exact"),
    ("scope_paths", ["wrong.py"], "scope / receipt"),
])
def test_wrong_external_identity_denied(field, bad, match):
    z, meta = make_bundle()
    meta[field] = bad
    with pytest.raises(ValueError, match=match):
        v.verify(z, expected=meta)


def test_tampered_archive_rejected_even_if_receipt_claims_green():
    z, meta = make_bundle()
    meta["zip_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="archive SHA256 mismatch"):
        v.verify(z, expected=meta)


def test_failed_test_rejected():
    z, meta = make_bundle(fail=True)
    with pytest.raises(ValueError, match="non-green"):
        v.verify(z, expected=meta)


def test_skip_rejected():
    z, meta = make_bundle(skip=True)
    with pytest.raises(ValueError, match="non-green"):
        v.verify(z, expected=meta)


def test_inflated_header_rejected():
    z, meta = make_bundle(header=3)
    with pytest.raises(ValueError, match="header / element"):
        v.verify(z, expected=meta)


def test_missing_branch_mode_rejected():
    z, meta = make_bundle(branch=False)
    with pytest.raises(ValueError, match="branch coverage"):
        v.verify(z, expected=meta)


def test_coverage_floor_rejected():
    z, meta = make_bundle(covered=6)
    with pytest.raises(ValueError, match="coverage below"):
        v.verify(z, expected=meta)


def test_foreign_member_rejected():
    z, meta = make_bundle(other_members={"../secret": b"bad"})
    with pytest.raises(ValueError, match="ZIP member"):
        v.verify(z, expected=meta)


def test_no_external_digest_does_not_pass():
    z, meta = make_bundle()
    meta.pop("zip_sha256")
    with pytest.raises(ValueError, match="missing external ZIP hash"):
        v.verify(z, expected=meta)


def test_zero_cases_rejected():
    z, meta = make_bundle(cases=0)
    with pytest.raises(ValueError, match="no executed"):
        v.verify(z, expected=meta)


def test_receipt_self_claim_false_can_never_authorize_merge():
    z, meta = make_bundle(override={"merged": True, "human_approved": True,
                                    "security_waiver": True})
    r = v.verify(z, expected=meta)
    assert r["admission"] == "HOLD"
    assert r["independent_human_review"] is None
    assert r["security_waiver"] is False


def test_bad_expected_sha_rejected():
    z, meta = make_bundle()
    meta["head_sha"] = "BAD"
    with pytest.raises(ValueError, match="invalid exact SHA"):
        v.verify(z, expected=meta)


def test_false_type_attempt_rejected():
    z, meta = make_bundle()
    meta["run_attempt"] = True
    with pytest.raises(ValueError, match="invalid external run_attempt"):
        v.verify(z, expected=meta)
