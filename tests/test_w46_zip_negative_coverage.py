"""W46 local high-yield archive failure paths, source W34 unchanged.

These tests validate local synthetic bytes only: no authenticated GitHub
artifact, reviewer, or merge-admission authority is introduced.
"""
from __future__ import annotations

import hashlib
import io
import json
import struct
import zipfile
from xml.etree import ElementTree as ET

import pytest

from test_w34_native_artifact_verify import make_bundle
from tools.recovery import w34_native_artifact_verify as verifier


def rebuild(blob, changes=None, *, sync_receipt=True, compression=zipfile.ZIP_DEFLATED):
    changes = changes or {}
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        rows = {n: z.read(n) for n in z.namelist()}
    rows.update(changes)
    if sync_receipt and rows.get("receipt.json"):
        receipt = json.loads(rows["receipt.json"])
        for name in ("junit.xml", "coverage.json"):
            receipt["member_sha256"][name] = hashlib.sha256(rows[name]).hexdigest()
        rows["receipt.json"] = json.dumps(receipt).encode()
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", compression=compression) as z:
        for name, raw in rows.items():
            z.writestr(name, raw)
    return out.getvalue()


def expected_for(blob, old):
    return {**old, "zip_sha256": hashlib.sha256(blob).hexdigest()}


def assert_rejected(blob, old, message):
    with pytest.raises(ValueError, match=message):
        verifier.verify(blob, expected=expected_for(blob, old))


@pytest.mark.parametrize("malformed", [b"{", b"[]", b"null", b"invalid", b"\xff"])
def test_receipt_json_parser_rejects_invalid_or_foreign_type(malformed):
    blob, old = make_bundle()
    changed = rebuild(blob, {"receipt.json": malformed}, sync_receipt=False)
    assert_rejected(changed, old, "invalid receipt JSON")


@pytest.mark.parametrize("malformed", [b"{", b"[]", b"null", b"garbage", b"\xfe"])
def test_coverage_json_parser_rejects_invalid_or_foreign_type(malformed):
    blob, old = make_bundle()
    changed = rebuild(blob, {"coverage.json": malformed})
    assert_rejected(changed, old, "invalid coverage JSON")


@pytest.mark.parametrize("invalid_xml", [b"<testsuite", b"<testsuite><testcase>", b"<testsuite><no></testsuite>"])
def test_malformed_xml_rejected_after_verified_sha(invalid_xml):
    blob, old = make_bundle()
    changed = rebuild(blob, {"junit.xml": invalid_xml})
    assert_rejected(changed, old, "invalid JUnit XML")


@pytest.mark.parametrize("attribute", ["tests", "failures", "errors", "skipped"])
def test_missing_junit_header_is_fail_closed(attribute):
    blob, old = make_bundle()
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        root = ET.fromstring(z.read("junit.xml"))
    root.attrib.pop(attribute)
    changed = rebuild(blob, {"junit.xml": ET.tostring(root)})
    assert_rejected(changed, old, "missing or invalid JUnit header")


@pytest.mark.parametrize("attribute", ["tests", "failures", "errors", "skipped"])
def test_invalid_junit_header_is_fail_closed(attribute):
    blob, old = make_bundle()
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        root = ET.fromstring(z.read("junit.xml"))
    root.set(attribute, "not-an-integer")
    changed = rebuild(blob, {"junit.xml": ET.tostring(root)})
    assert_rejected(changed, old, "missing or invalid JUnit header")


def test_stored_member_corruption_hits_crc_guard():
    blob, old = make_bundle()
    stored = rebuild(blob, compression=zipfile.ZIP_STORED)
    arr = bytearray(stored)
    with zipfile.ZipFile(io.BytesIO(stored)) as z:
        info = z.getinfo("junit.xml")
        assert info.compress_type == zipfile.ZIP_STORED
        i = info.header_offset
        assert arr[i:i+4] == b"PK\x03\x04"
        filename_len, extra_len = struct.unpack_from("<HH", arr, i + 26)
        off = i + 30 + filename_len + extra_len
        arr[off] ^= 1
    assert_rejected(bytes(arr), old, "invalid ZIP bytes")


def test_duplicate_case_identity_is_not_reported_as_two_independent_tests():
    blob, old = make_bundle()
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        root = ET.fromstring(z.read("junit.xml"))
    rows = root.findall("testcase")
    rows[1].set("name", rows[0].get("name"))
    changed = rebuild(blob, {"junit.xml": ET.tostring(root)})
    assert_rejected(changed, old, "duplicate JUnit testcase identity")


@pytest.mark.parametrize("new_name", ["", "../outside.py", "folder\\file.py"])
def test_unsafe_or_empty_coverage_scope_is_denied(new_name):
    blob, old = make_bundle()
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        receipt = json.loads(z.read("receipt.json"))
    receipt["scope_paths"] = [new_name]
    changed = rebuild(blob, {"receipt.json": json.dumps(receipt).encode()})
    meta = {**expected_for(changed, old), "scope_paths": [new_name]}
    with pytest.raises(ValueError, match="unsafe coverage source path"):
        verifier.verify(changed, expected=meta)


def test_signed_receipt_cannot_claim_human_approval_or_merge():
    blob, old = make_bundle(override={"approvals": 18, "merge_admission": "PASS"})
    result = verifier.verify(blob, expected=old)
    assert result["independent_human_review"] is None
    assert result["admission"] == "HOLD"
    assert result["github_provider_authentication"] is None
