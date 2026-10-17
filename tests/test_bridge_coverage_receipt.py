"""Positive and negative controls for source-bound DMAIC bridge coverage."""

import hashlib
import json

import pytest

from scripts.bridge_coverage_receipt import build_receipt

HEAD_SHA = "a" * 40


@pytest.fixture
def measured(tmp_path):
    source = tmp_path / "DMAIC_V3" / "core" / "test_system_bridge.py"
    source.parent.mkdir(parents=True)
    source.write_text("def live(value):\n    return bool(value)\n", encoding="utf-8")
    summary = {
        "num_statements": 10,
        "covered_lines": 6,
        "missing_lines": 4,
        "num_branches": 6,
        "covered_branches": 3,
        "missing_branches": 3,
    }
    report = {
        "files": {source.as_posix(): {"summary": summary.copy()}},
        "totals": summary.copy(),
    }
    path = tmp_path / "coverage.json"
    path.write_text(json.dumps(report), encoding="utf-8")
    return path, source, report


def test_receipt_binds_exact_source_and_coverage_bytes(measured):
    path, source, _ = measured
    receipt = build_receipt(path, source, HEAD_SHA)
    assert receipt["head_sha"] == HEAD_SHA
    assert receipt["scope"] == "one_python_module"
    assert receipt["statements"] == {"covered": 6, "total": 10, "percent": 60.0}
    assert receipt["branches"] == {"covered": 3, "total": 6, "percent": 50.0}
    assert receipt["source_sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()
    assert receipt["coverage_report_sha256"] == hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


@pytest.mark.parametrize(
    "metric, invalid",
    [
        ("num_statements", 0),
        ("num_branches", 0),
        ("covered_lines", 11),
        ("covered_branches", 7),
        ("covered_branches", True),
        ("num_branches", "6"),
        ("missing_lines", 0),
        ("missing_branches", 2),
    ],
)
def test_invalid_denominators_and_numerators_fail_closed(measured, metric, invalid):
    path, source, report = measured
    report["files"][source.as_posix()]["summary"][metric] = invalid
    path.write_text(json.dumps(report), encoding="utf-8")
    with pytest.raises(ValueError):
        build_receipt(path, source, HEAD_SHA)


@pytest.mark.parametrize("head", ["", "abc", "G" * 40, "a" * 39])
def test_incomplete_or_invalid_sha_fails_closed(measured, head):
    path, source, _ = measured
    with pytest.raises(ValueError, match="head SHA"):
        build_receipt(path, source, head)


def test_missing_source_coverage_fails_closed(measured):
    path, source, report = measured
    report["files"] = {"different_file.py": {"summary": report["totals"]}}
    path.write_text(json.dumps(report), encoding="utf-8")
    with pytest.raises(ValueError, match="missing or ambiguous"):
        build_receipt(path, source, HEAD_SHA)


def test_ambiguous_source_coverage_fails_closed(measured):
    path, source, report = measured
    report["files"]["another/" + source.as_posix().lstrip("/")] = {
        "summary": report["totals"]
    }
    path.write_text(json.dumps(report), encoding="utf-8")
    with pytest.raises(ValueError, match="ambiguous"):
        build_receipt(path, source, HEAD_SHA)


def test_global_and_source_mismatch_fails_closed(measured):
    path, source, report = measured
    report["totals"]["covered_lines"] = 7
    report["totals"]["missing_lines"] = 3
    path.write_text(json.dumps(report), encoding="utf-8")
    with pytest.raises(ValueError, match="differ"):
        build_receipt(path, source, HEAD_SHA)


def test_invalid_json_fails_closed(measured):
    path, source, _ = measured
    path.write_text("{", encoding="utf-8")
    with pytest.raises(ValueError):
        build_receipt(path, source, HEAD_SHA)


def test_missing_physical_source_fails_closed(measured):
    path, source, _ = measured
    source.unlink()
    with pytest.raises(OSError):
        build_receipt(path, source, HEAD_SHA)
