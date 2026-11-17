import pytest

from scripts import coverage_dab_census as dab
from tools.triage.floating_evidence_join import reconcile


def sample():
    coverage = {
        "meta": {"branch_coverage": True},
        "files": {
            "src/work.py": {
                "summary": {
                    "num_statements": 10,
                    "covered_lines": 3,
                    "percent_covered": 30,
                    "num_branches": 6,
                    "covered_branches": 2,
                }
            },
            "src/isolated.py": {
                "summary": {
                    "num_statements": 7,
                    "covered_lines": 0,
                    "percent_covered": 0,
                }
            },
        },
    }
    return dab.build_census(coverage, exact_sha="a" * 40)


def test_denominators_are_measured_or_unknown():
    d = sample()
    rows = {r["path"]: r for r in d["rows"]}
    assert rows["src/work.py"]["missed_branches"] == 4
    assert rows["src/isolated.py"]["eligible_branches"] is None
    assert d["active_source"]["branches_complete"] is False
    assert d["active_source"]["eligible_branches"] is None


def test_join_retains_unknown_and_is_deterministic():
    f = {"floating_buckets": {"x": {"paths": ["src/isolated.py", "src/absent.py"]}}}
    a = reconcile(sample(), f, source_sha="a" * 40, floating_sha="a" * 40)
    b = reconcile(sample(), f, source_sha="a" * 40, floating_sha="a" * 40)
    assert a == b
    assert a["candidate_paths"] == 2
    assert a["candidate_measured_overlap"] == 1
    assert a["candidate_unmeasured"] == 1
    assert (
        next(r for r in a["rows"] if r["path"] == "src/absent.py")["statements_covered"]
        is None
    )
    assert all(
        r["runtime_reachability"] == "UNKNOWN"
        and r["orphan"] is None
        and not r["prune_authorized"]
        for r in a["rows"]
    )


def test_refuses_unmatched_source_sha():
    with pytest.raises(ValueError, match="DAB source SHA"):
        reconcile(sample(), {}, source_sha="b" * 40, floating_sha="b" * 40)
    with pytest.raises(ValueError, match="floating source SHA"):
        reconcile(sample(), {}, source_sha="a" * 40, floating_sha="b" * 40)


def test_branch_coverage_disabled_cannot_claim_branches():
    c = {
        "meta": {"branch_coverage": False},
        "files": {
            "src/f.py": {
                "summary": {
                    "num_statements": 2,
                    "covered_lines": 2,
                    "num_branches": 2,
                    "covered_branches": 2,
                }
            }
        },
    }
    row = dab.build_census(c, exact_sha="c" * 40)["rows"][0]
    assert row["eligible_branches"] is None
