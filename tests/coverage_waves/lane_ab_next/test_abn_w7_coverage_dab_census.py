"""Gap tests for scripts/coverage_dab_census.py (classes, guards, main)."""

import json

import pytest

from tests.coverage_waves.lane_b._l2_loader import load

mod = load("scripts/coverage_dab_census.py", name="abn_w7_coverage_dab_census")


def _summary(statements, covered, branches=None, covered_branches=None):
    summary = {
        "num_statements": statements,
        "covered_lines": covered,
        "percent_covered": 100.0 * covered / statements if statements else 0.0,
    }
    if branches is not None:
        summary["num_branches"] = branches
        summary["covered_branches"] = covered_branches
    return {"summary": summary}


def test_classify_override_and_fallbacks():
    overrides = {"x/y.py": {"source_class": "FORCED"}}
    assert mod.classify_source("./x/y.py", overrides) == "FORCED"
    assert mod.classify_source("a/pytest-of-u/b.py", {}) == "TEST_SUPPORT"
    assert mod.classify_source("scripts/build/gen.py", {}) == "GENERATED"
    assert mod.classify_source("scripts/BACKUPS/old.py", {}) == "LEGACY_QUARANTINED"
    assert mod.classify_source("lib/x_LEGACY_y.py", {}) == "LEGACY_QUARANTINED"
    assert mod.classify_source("toplevel.py", {}) == "ACTIVE_SOURCE"
    assert mod.classify_source("elsewhere/mod.py", {}) == "UNKNOWN"


def test_outcome_index_ignores_bad_rows():
    assert mod._test_outcome_index({"rows": "nope"}) == {}
    index = mod._test_outcome_index(
        {"rows": ["bad", {"test": "  "}, {"test": "t::a|x", "outcome": "passed"}]}
    )
    assert list(index) == ["t.a"]


def test_measured_contexts_skips_non_list_and_blank():
    data = {"contexts": {"1": ["", "ctx_b", "ctx_a"], "2": "not-a-list"}}
    assert mod.measured_contexts(data) == ["ctx_a", "ctx_b"]


def test_load_json_none_and_non_object(tmp_path):
    assert mod._load_json(None) == {}
    path = tmp_path / "arr.json"
    path.write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError, match="expected JSON object"):
        mod._load_json(path)


def test_invalid_branch_counts_raise():
    coverage = {
        "meta": {"branch_coverage": True},
        "files": {"scripts/a.py": _summary(4, 2, branches=2, covered_branches=5)},
    }
    with pytest.raises(ValueError, match="invalid measured branch counts"):
        mod.build_census(coverage)


def test_failing_state_legacy_and_non_dict_criticality():
    coverage = {
        "meta": {"branch_coverage": True},
        "files": {
            "scripts/a.py": {
                **_summary(4, 2, branches=2, covered_branches=1),
                "contexts": {"1": ["t::a", "t::b"]},
            },
            "scripts/BACKUPS/old.py": _summary(3, 0, branches=0, covered_branches=0),
        },
    }
    evidence = {
        "rows": [
            {"test": "t::a", "outcome": "failed", "test_state": "TEST_FAILING"},
            {"test": "t::b", "outcome": "passed", "test_state": "TEST_GREEN"},
        ]
    }
    census = mod.build_census(
        coverage,
        criticality={"files": ["not", "a", "dict"]},
        test_evidence=evidence,
        exact_sha="abc",
    )
    rows = {row["path"]: row for row in census["rows"]}
    measured = rows["scripts/a.py"]
    assert measured["test_state"] == "TEST_FAILING"
    assert measured["test_state_evidence"] == "JUNIT_CONTEXT_JOIN (MEASURED)"
    legacy = rows["scripts/BACKUPS/old.py"]
    assert legacy["disposition"] == "REVIEW_QUARANTINE"
    assert legacy["test_state"] == "NO_TEST"
    assert census["exact_sha"] == "abc"


def test_main_writes_and_prints(tmp_path, capsys):
    cov = tmp_path / "cov.json"
    cov.write_text(
        json.dumps({"files": {"tools/x.py": _summary(5, 0)}, "totals": {"n": 1}}),
        encoding="utf-8",
    )
    crit = tmp_path / "crit.json"
    crit.write_text(
        json.dumps({"files": {"tools/x.py": {"criticality": "HIGH"}}}),
        encoding="utf-8",
    )
    out = tmp_path / "sub" / "census.json"
    rc = mod.main(
        [
            "--coverage-json",
            str(cov),
            "--criticality",
            str(crit),
            "--out",
            str(out),
            "--exact-sha",
            "deadbeef",
        ]
    )
    assert rc == 0
    written = json.loads(out.read_text(encoding="utf-8"))
    assert written["exact_sha"] == "deadbeef"
    assert written["rows"][0]["disposition"] == "ADMISSION_PENDING"
    assert written["rows"][0]["criticality"] == "HIGH"
    assert written["pressure_order"] == ["tools/x.py"]
    printed = json.loads(capsys.readouterr().out)
    assert printed["schema"] == "abacus-coverage-dab/1.0.0"
