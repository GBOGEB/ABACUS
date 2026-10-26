"""N+6 high-leverage zero-coverage and counter integrity test family."""
from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path

import pytest

from tools.recovery import w46_gap_census as census

SHA = "b" * 40


def row(statement=5, covered=0, branches=4, covered_branches=0):
    return {"summary": {
        "num_statements": statement,
        "covered_lines": covered,
        "missing_lines": statement - covered,
        "num_branches": branches,
        "covered_branches": covered_branches,
        "missing_branches": branches - covered_branches,
    }}


def source():
    return {
        "meta": {"branch_coverage": True},
        "files": {
            "DMAIC_V3/a.py": row(5, 0, 4, 0),
            "DMAIC_V3/b.py": row(50, 48, 10, 9),
            "models/b.py": row(10, 0, 5, 0),
            "scripts/c.py": row(12, 11, 4, 4),
            "tools/d.py": row(7, 0, 5, 0),
        },
    }


def test_zero_paths_rank_explicitly_and_keep_denominators():
    result = census.rollup(source(), head_sha=SHA)
    assert result["zero_coverage_file_count"] == 3
    assert result["zero_covered_source_paths"] == [
        "models/b.py", "tools/d.py", "DMAIC_V3/a.py"
    ]
    assert [p["path"] for p in result["zero_first_disjoint_recovery_candidates"]] == [
        "models/b.py", "tools/d.py", "DMAIC_V3/a.py"
    ]
    assert result["measured_zero_coverage_reduction"] is None
    assert result["merge_admission"] == "HOLD"
    assert result["eligible"] == 112
    assert result["covered"] == 72


def test_zero_first_not_falsely_promoted_over_real_source_evidence():
    result = census.rollup(source(), head_sha=SHA)
    assert result["top_paths"][0]["path"] == "models/b.py"
    assert result["predicted_gain"] is None
    assert result["native_workflow_dispatches"] == 0
    assert result["broad_main_coverage_uplift"] is None


@pytest.mark.parametrize("path", [
    "/tmp/x.py", "C:/private/x.py", "a/../b.py", "a/./b.py",
    "a//b.py", "a\\b.py", "a/", "../x.py", ".",
])
def test_unsafe_or_ambiguous_paths_fail_closed(path):
    data = source()
    data["files"][path] = data["files"].pop("models/b.py")
    with pytest.raises(ValueError, match="unsafe or foreign"):
        census.rollup(data, head_sha=SHA)


def test_zero_statement_file_not_misclassified_as_zero_coverage():
    data = source()
    data["files"]["tools/empty.py"] = row(0, 0, 0, 0)
    result = census.rollup(data, head_sha=SHA)
    assert result["zero_coverage_file_count"] == 3
    assert "tools/empty.py" not in result["zero_covered_source_paths"]
    assert result["file_count"] == 6


def test_zero_cap_selects_distinct_owners():
    result = census.rollup(source(), head_sha=SHA, max_lanes=2)
    assert len(result["zero_first_disjoint_recovery_candidates"]) == 2
    assert len(result["proposed_source_disjoint_lanes"]) == 2
    assert len(set(p["owner_candidate"] for p in
                   result["zero_first_disjoint_recovery_candidates"])) == 2


def test_only_one_zero_candidate_per_owner():
    data = source()
    data["files"]["DMAIC_V3/another.py"] = row(100)
    result = census.rollup(data, head_sha=SHA)
    assert len([p for p in result["zero_first_disjoint_recovery_candidates"]
                if p["owner_candidate"] == "DMAIC_V3"]) == 1
    assert "DMAIC_V3/another.py" in result["zero_covered_source_paths"]


def test_all_covered_means_zero_zero_coverage_files():
    data = {"meta": {"branch_coverage": True}, "files": {"a.py": row(2, 2, 1, 1)}}
    r = census.rollup(data, head_sha=SHA)
    assert r["zero_coverage_file_count"] == 0
    assert r["zero_first_disjoint_recovery_candidates"] == []
    assert r["combined_percent"] == 100.0
    assert r["merge_admission"] == "HOLD"


def test_wrong_source_totals_fail_even_if_scored_higher():
    data = source()
    baseline = census.rollup(data, head_sha=SHA)
    counters = {
        "num_statements": baseline["statement"]["eligible"],
        "covered_lines": baseline["statement"]["covered"],
        "missing_lines": baseline["statement"]["eligible"] - baseline["statement"]["covered"],
        "num_branches": baseline["branch"]["eligible"],
        "covered_branches": baseline["branch"]["covered"],
        "missing_branches": baseline["branch"]["eligible"] - baseline["branch"]["covered"],
    }
    assert census.rollup(data, head_sha=SHA, expected_totals=counters)["covered"] == 72
    counters["missing_lines"] += 1
    with pytest.raises(ValueError, match="denominator mismatch"):
        census.rollup(data, head_sha=SHA, expected_totals=counters)


def test_none_not_false_for_unverified_reduction():
    assert census.rollup(source(), head_sha=SHA)["measured_zero_coverage_reduction"] is None


def test_equal_missing_sorted_by_source_path():
    data = {"meta": {"branch_coverage": True}, "files": {
        "tools/z.py": row(2), "tools/a.py": row(2)
    }}
    result = census.rollup(data, head_sha=SHA)
    assert result["zero_covered_source_paths"] == ["tools/a.py", "tools/z.py"]


def test_source_file_count_not_synthetic_test_count():
    data = source()
    assert census.rollup(data, head_sha=SHA)["file_count"] == len(data["files"])


def test_cli_generates_read_only_source_bound_receipt(tmp_path, monkeypatch):
    data = source()
    expected = census.rollup(data, head_sha=SHA)
    counters = dict(num_statements=expected["statement"]["eligible"],
                    covered_lines=expected["statement"]["covered"],
                    missing_lines=expected["statement"]["eligible"] -
                    expected["statement"]["covered"],
                    num_branches=expected["branch"]["eligible"],
                    covered_branches=expected["branch"]["covered"],
                    missing_branches=expected["branch"]["eligible"] -
                    expected["branch"]["covered"])
    archive = tmp_path / "source.zip"
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr("coverage-contexts.json", json.dumps(data))
        z.writestr("coverage-dab.json",
                   json.dumps({"full_measurement": counters}))
    receipt = tmp_path / "out.json"
    monkeypatch.setattr(sys, "argv", [
        "w46_gap_census", "--zip", str(archive), "--head", SHA, "--out", str(receipt)
    ])
    assert census.main() == 0
    loaded = json.loads(receipt.read_text(encoding="utf-8"))
    assert loaded["exact_head"] == SHA
    assert loaded["zero_coverage_file_count"] == 3
    assert loaded["native_workflow_dispatches"] == 0
