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
    assert (
        receipt["coverage_report_sha256"]
        == hashlib.sha256(path.read_bytes()).hexdigest()
    )


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


# W9: disjoint fail-closed, mutation-sensitive branch penetration.
# All inputs are synthetic; no security, approval, or merge authority changes.
import sys

import scripts.bridge_coverage_receipt as bridge_receipt


@pytest.mark.parametrize("origin", ["module", "global"])
@pytest.mark.parametrize(
    "field",
    ["num_statements", "covered_lines", "num_branches", "covered_branches"],
)
@pytest.mark.parametrize("bad", [None, -1, False, "5"])
def test_malformed_measurement_counts_are_rejected(measured, origin, field, bad):
    path, source, report = measured
    summary = (
        report["files"][source.as_posix()]["summary"]
        if origin == "module"
        else report["totals"]
    )
    summary[field] = bad
    path.write_text(json.dumps(report), encoding="utf-8")
    with pytest.raises(ValueError, match="coverage count"):
        build_receipt(path, source, HEAD_SHA)


@pytest.mark.parametrize("origin", ["module", "global"])
@pytest.mark.parametrize(
    "field", ["num_statements", "covered_lines", "num_branches", "covered_branches"]
)
def test_missing_required_count_rejected(measured, origin, field):
    path, source, report = measured
    summary = (
        report["files"][source.as_posix()]["summary"]
        if origin == "module"
        else report["totals"]
    )
    del summary[field]
    path.write_text(json.dumps(report), encoding="utf-8")
    with pytest.raises(ValueError, match="coverage count"):
        build_receipt(path, source, HEAD_SHA)


@pytest.mark.parametrize(
    "broken",
    [
        [],
        {"files": []},
        {"files": {}},
        {"files": {"x.py": {"summary": {}}}},
        {"files": {"x.py": {"summary": {}}}, "totals": []},
    ],
)
def test_invalid_report_shape_rejected(measured, broken):
    path, source, _report = measured
    path.write_text(json.dumps(broken), encoding="utf-8")
    with pytest.raises(ValueError):
        build_receipt(path, source, HEAD_SHA)


@pytest.mark.parametrize("record", [None, [], {}, {"summary": []}])
def test_source_record_or_summary_missing_rejected(measured, record):
    path, source, report = measured
    report["files"][source.as_posix()] = record
    path.write_text(json.dumps(report), encoding="utf-8")
    with pytest.raises(ValueError, match="source module summary"):
        build_receipt(path, source, HEAD_SHA)


@pytest.mark.parametrize(
    "metric, total, covered, missing",
    [
        ("statements", 9, 6, 3),
        ("statements", 10, 5, 5),
        ("branches", 5, 3, 2),
        ("branches", 6, 2, 4),
    ],
)
def test_module_must_fit_within_global_measurement(
    measured, metric, total, covered, missing
):
    path, source, report = measured
    if metric == "statements":
        report["totals"].update(
            num_statements=total, covered_lines=covered, missing_lines=missing
        )
    else:
        report["totals"].update(
            num_branches=total, covered_branches=covered, missing_branches=missing
        )
    # Two files suppress the stricter one-file equality check.
    report["files"]["other.py"] = {"summary": report["totals"].copy()}
    path.write_text(json.dumps(report), encoding="utf-8")
    with pytest.raises(ValueError, match="module (denominator|numerator)"):
        build_receipt(path, source, HEAD_SHA)


def test_multiple_modules_do_not_inflate_single_module_receipt(measured):
    path, source, report = measured
    report["files"]["other.py"] = {
        "summary": {
            "num_statements": 5,
            "covered_lines": 4,
            "missing_lines": 1,
            "num_branches": 2,
            "covered_branches": 1,
            "missing_branches": 1,
        }
    }
    report["totals"].update(
        num_statements=15,
        covered_lines=10,
        missing_lines=5,
        num_branches=8,
        covered_branches=4,
        missing_branches=4,
    )
    path.write_text(json.dumps(report), encoding="utf-8")
    receipt = build_receipt(path, source, HEAD_SHA)
    assert receipt["scope"] == "one_python_module"
    assert receipt["statements"]["covered"] == 6
    assert receipt["statements"]["total"] == 10
    assert receipt["branches"]["covered"] == 3
    assert receipt["branches"]["total"] == 6


def test_bytes_change_hash_without_inventing_coverage_delta(measured):
    path, source, _report = measured
    baseline = build_receipt(path, source, HEAD_SHA)
    source.write_bytes(source.read_bytes() + b"# source byte change\n")
    changed = build_receipt(path, source, HEAD_SHA)
    assert changed["source_sha256"] != baseline["source_sha256"]
    assert changed["coverage_report_sha256"] == baseline["coverage_report_sha256"]
    assert changed["statements"] == baseline["statements"]
    assert changed["branches"] == baseline["branches"]


def test_coverage_json_bytes_change_hash_without_inventing_counts(measured):
    path, source, _report = measured
    baseline = build_receipt(path, source, HEAD_SHA)
    path.write_bytes(path.read_bytes() + b" \n")
    changed = build_receipt(path, source, HEAD_SHA)
    assert changed["coverage_report_sha256"] != baseline["coverage_report_sha256"]
    assert changed["source_sha256"] == baseline["source_sha256"]
    assert changed["statements"] == baseline["statements"]


def test_cli_writes_structured_source_bound_receipt(
    measured, tmp_path, monkeypatch, capsys
):
    path, source, _report = measured
    output = tmp_path / "receipt.json"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "bridge_coverage_receipt.py",
            "--coverage",
            str(path),
            "--source",
            str(source),
            "--head",
            HEAD_SHA,
            "--output",
            str(output),
        ],
    )
    bridge_receipt.main()
    receipt = json.loads(output.read_text(encoding="utf-8"))
    printed = json.loads(capsys.readouterr().out)
    assert receipt == printed
    assert receipt["head_sha"] == HEAD_SHA
    assert receipt["source_path"] == source.as_posix()


def test_cli_failure_is_nonzero_and_does_not_publish(
    measured, tmp_path, monkeypatch, capsys
):
    path, source, _report = measured
    output = tmp_path / "must-not-exist.json"
    path.write_text("not json", encoding="utf-8")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "bridge_coverage_receipt.py",
            "--coverage",
            str(path),
            "--source",
            str(source),
            "--head",
            HEAD_SHA,
            "--output",
            str(output),
        ],
    )
    with pytest.raises(SystemExit) as exc:
        bridge_receipt.main()
    assert exc.value.code == 2
    assert not output.exists()
    assert "bridge coverage proof failed" in capsys.readouterr().err
