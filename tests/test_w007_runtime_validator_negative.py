"""Fail-closed W007 runtime evidence and validator branch regressions.

Synthetic fixtures exercise negative paths without mutating repository evidence,
claiming a Pages publication, or granting engineering authority.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sys

import pytest

from scripts.validate_runtime_foundation import (
    REQUIRED_CAPABILITIES,
    validate_runtime_foundation,
)
import scripts.write_runtime_governance_status as runtime_status


@pytest.fixture
def runtime_tree(tmp_path: Path) -> Path:
    """A minimal contract-valid W007 repository with no published status JSON."""
    docs = tmp_path / "docs"
    (docs / "api").mkdir(parents=True)
    (docs / "evidence.txt").write_text("verified fixture\n", encoding="utf-8")
    (docs / "runtime.html").write_text(
        "W007 Runtime Foundation | SSOT Dashboard | Traceability | "
        "runtime-artifact-manifest.json | Visualization Layer",
        encoding="utf-8",
    )
    entries = []
    for capability in sorted(REQUIRED_CAPABILITIES):
        if capability == "runtime_governance_status":
            producer = tmp_path / "scripts" / "runtime_generator.py"
            producer.parent.mkdir(parents=True, exist_ok=True)
            producer.write_text("# fixture producer\n", encoding="utf-8")
            entries.append(
                {
                    "capability": capability,
                    "path": "reports/runtime_status.json",
                    "status": "runtime_generated",
                    "producer": "scripts/runtime_generator.py",
                }
            )
        else:
            path = f"docs/capabilities/{capability}.txt"
            artifact = tmp_path / path
            artifact.parent.mkdir(parents=True, exist_ok=True)
            artifact.write_text("present\n", encoding="utf-8")
            entries.append({"capability": capability, "path": path, "status": "active"})
    (docs / "runtime-artifact-manifest.json").write_text(
        json.dumps({"wave": "W007", "artifacts": entries}), encoding="utf-8"
    )
    (docs / "api" / "rtm_trace_matrix.json").write_text(
        json.dumps(
            {"rows": [{"requirement_id": "R1", "evidence_id": "E1",
                       "evidence_artifact": "docs/evidence.txt", "available": True}]}
        ),
        encoding="utf-8",
    )
    return tmp_path


def _manifest(root: Path) -> tuple[Path, dict]:
    path = root / "docs" / "runtime-artifact-manifest.json"
    return path, json.loads(path.read_text(encoding="utf-8"))


def _matrix(root: Path) -> tuple[Path, dict]:
    path = root / "docs" / "api" / "rtm_trace_matrix.json"
    return path, json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data), encoding="utf-8")


def _errors(root: Path) -> str:
    return "\n".join(validate_runtime_foundation(root))


def test_minimal_valid_runtime_and_unpublished_generated_artifact(runtime_tree: Path) -> None:
    assert validate_runtime_foundation(runtime_tree) == []
    # A run-generated artifact must not be forced into the published source tree.
    assert not (runtime_tree / "reports/runtime_status.json").exists()


@pytest.mark.parametrize(
    ("case", "expected"),
    [
        ("wrong_wave", "runtime manifest wave must be W007"),
        ("empty_artifacts", "runtime manifest must define non-empty artifacts list"),
        ("non_object_entry", "runtime manifest artifact #1 must be an object"),
        ("missing_capability", "runtime manifest artifact #1 missing capability"),
        ("missing_path", "runtime manifest artifact #1 missing path"),
        ("unsupported_status", "runtime manifest artifact has unsupported status"),
        ("missing_active_file", "manifest artifact path does not exist"),
        ("missing_producer", "runtime-generated artifact missing producer"),
        ("missing_producer_file", "runtime-generated artifact producer does not exist"),
        ("missing_required_capability", "runtime manifest missing capability"),
    ],
)
def test_manifest_rejects_invalid_evidence(
    runtime_tree: Path, case: str, expected: str
) -> None:
    path, doc = _manifest(runtime_tree)
    entries = doc["artifacts"]
    generated = next(x for x in entries if x["status"] == "runtime_generated")
    active = next(x for x in entries if x["status"] == "active")
    if case == "wrong_wave":
        doc["wave"] = "W008"
    elif case == "empty_artifacts":
        doc["artifacts"] = []
    elif case == "non_object_entry":
        entries.insert(0, 42)
    elif case == "missing_capability":
        entries[0].pop("capability")
    elif case == "missing_path":
        entries[0].pop("path")
    elif case == "unsupported_status":
        active["status"] = "published_without_receipt"
    elif case == "missing_active_file":
        active["path"] = "docs/not-released.html"
    elif case == "missing_producer":
        generated.pop("producer")
    elif case == "missing_producer_file":
        generated["producer"] = "scripts/not-authorized.py"
    elif case == "missing_required_capability":
        entries.remove(active)
    _write(path, doc)
    assert expected in _errors(runtime_tree)


@pytest.mark.parametrize(
    ("case", "expected"),
    [
        ("empty_rows", "RTM trace matrix must contain traceability rows"),
        ("non_object_row", "RTM trace row #1 must be an object"),
        ("missing_fields", "RTM trace row #1 missing fields"),
        ("unavailable", "RTM trace matrix has unavailable or missing evidence: E1"),
        ("not_boolean_true", "RTM trace matrix has unavailable or missing evidence: E1"),
        ("missing_file", "RTM trace matrix has unavailable or missing evidence: E1"),
        ("blank_path", "evidence_artifact must be a non-empty string"),
    ],
)
def test_rtm_rejects_false_or_missing_evidence(
    runtime_tree: Path, case: str, expected: str
) -> None:
    path, doc = _matrix(runtime_tree)
    row = doc["rows"][0]
    if case == "empty_rows":
        doc["rows"] = []
    elif case == "non_object_row":
        doc["rows"][0] = "not an object"
    elif case == "missing_fields":
        row.pop("requirement_id")
    elif case == "unavailable":
        row["available"] = False
    elif case == "not_boolean_true":
        row["available"] = "true"
    elif case == "missing_file":
        row["evidence_artifact"] = "docs/never-published.html"
    elif case == "blank_path":
        row["evidence_artifact"] = ""
    _write(path, doc)
    assert expected in _errors(runtime_tree)


@pytest.mark.parametrize("kind", ["manifest", "matrix"])
@pytest.mark.parametrize(
    ("failure", "expected"),
    [
        ("missing", "missing JSON artifact:"),
        ("invalid", "invalid JSON in"),
        ("non_object", "JSON artifact must be an object:"),
    ],
)
def test_missing_or_malformed_json_is_not_accepted(
    runtime_tree: Path, kind: str, failure: str, expected: str
) -> None:
    path = (_manifest(runtime_tree) if kind == "manifest" else _matrix(runtime_tree))[0]
    if failure == "missing":
        path.unlink()
    elif failure == "invalid":
        path.write_text("{broken", encoding="utf-8")
    elif failure == "non_object":
        path.write_text("[]", encoding="utf-8")
    assert expected in _errors(runtime_tree)


@pytest.mark.parametrize(
    ("case", "expected"),
    [
        ("missing", "missing runtime portal: docs/runtime.html"),
        ("hidden_section", "runtime portal missing visible section: Traceability"),
    ],
)
def test_runtime_portal_cannot_disappear_silently(
    runtime_tree: Path, case: str, expected: str
) -> None:
    path = runtime_tree / "docs/runtime.html"
    if case == "missing":
        path.unlink()
    else:
        path.write_text("W007 Runtime Foundation | SSOT Dashboard | "
                        "runtime-artifact-manifest.json | Visualization Layer", encoding="utf-8")
    assert expected in _errors(runtime_tree)


def test_status_success_binds_native_identity_without_authority(
    runtime_tree: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    values = {
        "GITHUB_REPOSITORY": "GBOGEB/ABACUS",
        "GITHUB_SHA": "a" * 40,
        "GITHUB_RUN_ID": "39100000111",
        "GITHUB_RUN_ATTEMPT": "2",
        "GITHUB_WORKFLOW": "W007 Runtime Validator Negative Matrix",
    }
    for key, value in values.items():
        monkeypatch.setenv(key, value)
    status = runtime_status.build_status(runtime_tree)
    assert status["runtime_status"] == "validated"
    assert status["validation_passed"] is True
    assert status["validation_errors"] == []
    assert status["head_sha"] == "a" * 40
    assert status["run_id"] == "39100000111"
    assert status["run_attempt"] == "2"
    assert status["workflow"] == values["GITHUB_WORKFLOW"]
    assert status["authority"] == "RUNTIME_EVIDENCE_ONLY_ZERO_ENGINEERING_AUTHORITY"
    assert datetime.fromisoformat(status["generated_at_utc"]).tzinfo == timezone.utc


def test_status_failure_never_calls_itself_validated(runtime_tree: Path) -> None:
    (runtime_tree / "docs" / "api" / "rtm_trace_matrix.json").unlink()
    status = runtime_status.build_status(runtime_tree)
    assert status["runtime_status"] == "validation_failed"
    assert status["validation_passed"] is False
    assert "missing JSON artifact:" in "\n".join(status["validation_errors"])
    assert status["authority"] == "RUNTIME_EVIDENCE_ONLY_ZERO_ENGINEERING_AUTHORITY"


@pytest.mark.parametrize("is_valid,expected_exit", [(True, 0), (False, 1)])
def test_cli_preserves_status_json_and_exit_code(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str], is_valid: bool, expected_exit: int
) -> None:
    destination = tmp_path / "nested" / "run-bound.json"
    status = {"validation_passed": is_valid, "runtime_status":
              "validated" if is_valid else "validation_failed",
              "authority": "RUNTIME_EVIDENCE_ONLY_ZERO_ENGINEERING_AUTHORITY"}
    monkeypatch.setattr(runtime_status, "build_status", lambda: status)
    monkeypatch.setattr(sys, "argv", ["status", "--output", str(destination)])
    assert runtime_status.main() == expected_exit
    assert json.loads(destination.read_text(encoding="utf-8")) == status
    assert json.loads(capsys.readouterr().out) == status


# W007 next-slice negative contract: every structural assumption is evidence,
# including an existing but empty JSON object (not the same as missing bytes).
@pytest.mark.parametrize(
    ("kind", "expected"),
    [
        ("manifest", "runtime manifest wave must be W007"),
        ("matrix", "RTM trace matrix must contain traceability rows"),
    ],
)
def test_empty_object_json_must_fail_closed(
    runtime_tree: Path, kind: str, expected: str
) -> None:
    path = (_manifest(runtime_tree) if kind == "manifest" else _matrix(runtime_tree))[0]
    path.write_text("{}\n", encoding="utf-8")
    assert expected in _errors(runtime_tree)


@pytest.mark.parametrize("capability", sorted(REQUIRED_CAPABILITIES))
def test_each_required_runtime_capability_is_nonoptional(
    runtime_tree: Path, capability: str
) -> None:
    path, manifest = _manifest(runtime_tree)
    manifest["artifacts"] = [
        item for item in manifest["artifacts"]
        if item["capability"] != capability
    ]
    _write(path, manifest)
    assert f"runtime manifest missing capability: {capability}" in _errors(runtime_tree)


@pytest.mark.parametrize(
    ("kind", "expected"),
    [
        ("non_string_active_path", "runtime manifest artifact #1 missing path"),
        ("blank_active_path", "runtime manifest artifact #1 missing path"),
        ("non_string_generated_producer", "runtime-generated artifact missing producer"),
        ("blank_generated_producer", "runtime-generated artifact missing producer"),
    ],
)
def test_nonpath_or_blank_artifact_identity_is_not_accepted(
    runtime_tree: Path, kind: str, expected: str
) -> None:
    path, manifest = _manifest(runtime_tree)
    active = next(item for item in manifest["artifacts"] if item["status"] == "active")
    generated = next(
        item for item in manifest["artifacts"]
        if item["status"] == "runtime_generated"
    )
    if kind == "non_string_active_path":
        active["path"] = 123
    elif kind == "blank_active_path":
        active["path"] = ""
    elif kind == "non_string_generated_producer":
        generated["producer"] = 7
    else:
        generated["producer"] = ""
    index = manifest["artifacts"].index(active) + 1
    _write(path, manifest)
    message = expected.replace("#1", f"#{index}")
    assert message in _errors(runtime_tree)


@pytest.mark.parametrize(
    "section",
    [
        "W007 Runtime Foundation",
        "SSOT Dashboard",
        "Traceability",
        "runtime-artifact-manifest.json",
        "Visualization Layer",
    ],
)
def test_each_runtime_portal_section_is_contractual(
    runtime_tree: Path, section: str
) -> None:
    portal = runtime_tree / "docs" / "runtime.html"
    portal.write_text(
        portal.read_text(encoding="utf-8").replace(section, "WITHHELD"),
        encoding="utf-8",
    )
    assert f"runtime portal missing visible section: {section}" in _errors(runtime_tree)


@pytest.mark.parametrize("value", [None, 0, 1, "false", [], {}])
def test_rtm_available_must_be_literal_json_true(
    runtime_tree: Path, value: object
) -> None:
    path, matrix = _matrix(runtime_tree)
    matrix["rows"][0]["available"] = value
    _write(path, matrix)
    assert "RTM trace matrix has unavailable or missing evidence: E1" in _errors(
        runtime_tree
    )


@pytest.mark.parametrize("evidence_path", [None, 0, False, []])
def test_rtm_nonpath_evidence_must_fail_closed(
    runtime_tree: Path, evidence_path: object
) -> None:
    path, matrix = _matrix(runtime_tree)
    matrix["rows"][0]["evidence_artifact"] = evidence_path
    _write(path, matrix)
    failures = _errors(runtime_tree)
    assert "RTM trace row #1 evidence_artifact must be a non-empty string" in failures
    assert "RTM trace matrix has unavailable or missing evidence: E1" in failures
