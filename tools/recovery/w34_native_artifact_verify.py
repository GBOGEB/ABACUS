"""W34 read-only native ZIP verifier: bytes, JUnit, scope and exact identity.

A caller-supplied expected tuple is a trust boundary requiring separate GitHub
API readback. Successful verification establishes byte equality only; it does
not authenticate a principal, approve a human review or admit a merge.
"""
from __future__ import annotations

import hashlib
import io
import json
import re
import zipfile
from xml.etree import ElementTree

_SHA = re.compile(r"^[0-9a-f]{40}$")
_HASH = re.compile(r"^[0-9a-f]{64}$")
_MEMBERS = frozenset({"junit.xml", "coverage.json", "receipt.json"})
_MAX_BUNDLE = 5_000_000
_MAX_MEMBER = 3_000_000
_MAX_RATIO = 120


def _need(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _positive(value: object) -> bool:
    return type(value) is int and value > 0


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _parse_json(raw: bytes, label: str) -> dict:
    try:
        value = json.loads(raw)
    except (ValueError, UnicodeError) as exc:
        raise ValueError("invalid " + label) from exc
    _need(isinstance(value, dict), "invalid " + label)
    return value


def _read_zip(blob: bytes) -> dict[str, bytes]:
    _need(type(blob) is bytes and 0 < len(blob) <= _MAX_BUNDLE,
          "missing or oversized artifact bytes")
    try:
        with zipfile.ZipFile(io.BytesIO(blob), "r") as archive:
            infos = archive.infolist()
            names = [x.filename for x in infos]
            _need(len(names) == len(_MEMBERS) and set(names) == _MEMBERS,
                  "missing, duplicate or foreign ZIP member")
            for x in infos:
                _need(x.file_size > 0 and x.file_size <= _MAX_MEMBER,
                      "empty or oversized archive member")
                _need(x.file_size <= _MAX_RATIO * max(1, x.compress_size),
                      "excessive archive expansion ratio")
                _need(x.filename in _MEMBERS and not x.is_dir(),
                      "unsafe archive member")
                mode = (x.external_attr >> 16) & 0o170000
                _need(mode != 0o120000, "symlink archive member")
            return {name: archive.read(name) for name in names}
    except (zipfile.BadZipFile, RuntimeError) as exc:
        raise ValueError("invalid ZIP bytes") from exc


def _junit(data: bytes) -> int:
    _need(b"<!DOCTYPE" not in data.upper() and b"<!ENTITY" not in data.upper(),
          "unsafe JUnit declaration")
    try:
        root = ElementTree.fromstring(data)
    except ElementTree.ParseError as exc:
        raise ValueError("invalid JUnit XML") from exc
    _need(root.tag in {"testsuites", "testsuite"}, "invalid JUnit root")
    suites = [root] if root.tag == "testsuite" else root.findall("testsuite")
    _need(len(suites) > 0, "missing JUnit suites")
    cases = []
    for suite in suites:
        cases.extend(suite.findall("testcase"))
    _need(len(cases) > 0, "no executed native testcases")
    for attr, actual in (
        ("tests", len(cases)),
        ("failures", sum(c.find("failure") is not None for c in cases)),
        ("errors", sum(c.find("error") is not None for c in cases)),
        ("skipped", sum(c.find("skipped") is not None for c in cases)),
    ):
        try:
            declared = sum(int(s.attrib[attr]) for s in suites)
        except (ValueError, KeyError, TypeError) as exc:
            raise ValueError("missing or invalid JUnit header") from exc
        _need(declared == actual, "JUnit header / element disagreement: " + attr)
    _need(not any(c.find(k) is not None for c in cases
                  for k in ("failure", "error", "skipped")),
          "non-green native JUnit result")
    identities = [(c.attrib.get("classname"), c.attrib.get("name")) for c in cases]
    _need(all(isinstance(a, str) and a and isinstance(b, str) and b
              for a, b in identities), "missing JUnit case identity")
    _need(len(identities) == len(set(identities)), "duplicate JUnit testcase identity")
    return len(cases)


def _coverage(data: bytes, scope: list[str]) -> tuple[int, int]:
    report = _parse_json(data, "coverage JSON")
    _need(report.get("meta", {}).get("branch_coverage") is True,
          "branch coverage not measured")
    rows = report.get("files")
    _need(isinstance(rows, dict), "missing coverage file population")
    _need(len(scope) == len(set(scope)) and len(scope) > 0,
          "invalid coverage scope")
    _need(all(isinstance(p, str) and p and ".." not in p and "\\" not in p
              for p in scope), "unsafe coverage source path")
    covered = eligible = 0
    for name in scope:
        _need(name in rows, "missing exact coverage source: " + name)
        stats = rows[name].get("summary")
        _need(isinstance(stats, dict), "missing scope counters")
        values = [stats.get(k) for k in (
            "num_statements", "covered_lines", "num_branches", "covered_branches")]
        _need(all(type(x) is int and x >= 0 for x in values),
              "invalid statement/branch counters")
        s, c, b, d = values
        _need(c <= s and d <= b, "impossible covered opportunities")
        eligible += s + b
        covered += c + d
    _need(eligible > 0, "empty eligible coverage denominator")
    return covered, eligible


def verify(archive_bytes: bytes, *, expected: dict) -> dict:
    """Fail closed; expected metadata must be separately verified by caller."""
    _need(isinstance(expected, dict), "missing external expected identity")
    head, expected_digest = expected.get("head_sha"), expected.get("zip_sha256")
    _need(isinstance(head, str) and bool(_SHA.fullmatch(head)), "invalid exact SHA")
    _need(isinstance(expected_digest, str) and bool(_HASH.fullmatch(expected_digest)),
          "missing external ZIP hash")
    for key in ("run_id", "run_attempt", "job_id"):
        _need(_positive(expected.get(key)), "invalid external " + key)
    _need(type(archive_bytes) is bytes and _digest(archive_bytes) == expected_digest,
          "archive SHA256 mismatch")
    files = _read_zip(archive_bytes)
    receipt = _parse_json(files["receipt.json"], "receipt JSON")
    _need(receipt.get("schema") == "abacus.w34.native.v1", "foreign receipt schema")
    for src, dst in (("head_sha", "head_sha"), ("run_id", "run_id"),
                     ("run_attempt", "run_attempt"), ("job_id", "job_id")):
        _need(type(receipt.get(src)) is type(expected[dst])
              and receipt[src] == expected[dst], "foreign exact native identity: " + src)
    for name in ("junit.xml", "coverage.json"):
        value = receipt.get("member_sha256", {}).get(name)
        _need(isinstance(value, str) and bool(_HASH.fullmatch(value))
              and value == _digest(files[name]), "member SHA256 mismatch: " + name)
    scope = expected.get("scope_paths")
    _need(isinstance(scope, list) and scope == receipt.get("scope_paths"),
          "source scope / receipt mismatch")
    cases = _junit(files["junit.xml"])
    covered, eligible = _coverage(files["coverage.json"], scope)
    threshold = expected.get("coverage_floor_pct")
    _need(type(threshold) in (int, float) and 0 <= threshold <= 100,
          "invalid coverage threshold")
    _need(covered * 100 >= threshold * eligible, "coverage below required floor")
    return {
        "schema": "abacus.w34.byte-verification.v1",
        "head_sha": head, "run_id": expected["run_id"],
        "run_attempt": expected["run_attempt"], "job_id": expected["job_id"],
        "archive_sha256": expected_digest,
        "executed_cases": cases, "covered_opportunities": covered,
        "eligible_opportunities": eligible,
        "scoped_coverage_pct": round(100 * covered / eligible, 6),
        "byte_integrity": "LOCAL_BYTE_MATCHED",
        "github_provider_authentication": None,
        "independent_human_review": None,
        "admission": "HOLD", "security_waiver": False,
        "formal_root_closed": None,
    }
