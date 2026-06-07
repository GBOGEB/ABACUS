"""
================================================================================
 Module : tests/test_golden_files.py
 Purpose: Golden-file regression gate (W007 CI/CD). Pins the *stable semantic
          invariants* of the make.sh-produced model artifacts against committed
          golden snapshots in tests/golden/, so a structural regression in the
          colour-line model, the as-drawn component catalog, or the W006
          design<->as-drawn cross-map fails CI loudly.
 Current Wave : W007
 Status : ACTIVE
 Convention : STANDALONE RUNNER — this project does NOT use pytest. Run with
          `PYTHONPATH=src python3 tests/test_golden_files.py` (or via the CI
          test loop / coverage wrapper). Each check is an assert-raising
          function; `_run_all()` aggregates them and a `__main__` guard makes
          the file directly executable.
 Inputs  : data/model/line_model.json, data/excel/catalog_register.json,
           reports/W006_crossmap_statistics.json  (all derived/git-ignored —
           build first via ./make.sh). Golden snapshots: tests/golden/*.json.
 Design  : Only invariant fields are compared (counts, ids, names, roles,
           histograms). Volatile geometry/coordinate fields and the known
           ~1-byte XLSX jitter are intentionally NOT part of any golden file,
           so the gate is deterministic across runs.
 Outputs : pass/fail to stdout (exit code 0 on success, 1 on failure).
================================================================================
"""

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOLDEN = os.path.join(ROOT, "tests", "golden")
MODEL = os.path.join(ROOT, "data", "model")
EXCEL = os.path.join(ROOT, "data", "excel")
REPORTS = os.path.join(ROOT, "reports")
sys.path.insert(0, os.path.join(ROOT, "src"))


def _load(path):
    with open(path) as fh:
        return json.load(fh)


def _strip_comment(d):
    """Return a copy of a golden dict without the documentation `_comment` key."""
    return {k: v for k, v in d.items() if k != "_comment"}


# --------------------------------------------------------------------------- #
# Data availability — derived artifacts are git-ignored, so on a fresh clone
# these checks are skipped (CI builds them via ./make.sh before running).
# --------------------------------------------------------------------------- #
REQUIRED = [
    os.path.join(MODEL, "line_model.json"),
    os.path.join(EXCEL, "catalog_register.json"),
    os.path.join(REPORTS, "W006_crossmap_statistics.json"),
]


def _data_available():
    return all(os.path.isfile(p) for p in REQUIRED)


# --------------------------------------------------------------------------- #
# Golden-file presence (pure — always runs; golden snapshots are committed)
# --------------------------------------------------------------------------- #
def test_golden_files_present():
    for name in (
        "expected_line_model_structure.json",
        "expected_component_counts.json",
        "expected_crossmap_stats.json",
    ):
        path = os.path.join(GOLDEN, name)
        assert os.path.isfile(path), f"missing golden snapshot: {path}"
        g = _load(path)
        assert isinstance(g, dict) and len(_strip_comment(g)) > 0, \
            f"golden snapshot is empty: {name}"


# --------------------------------------------------------------------------- #
# Data-dependent golden comparisons
# --------------------------------------------------------------------------- #
def test_line_model_matches_golden():
    golden = _strip_comment(_load(os.path.join(GOLDEN, "expected_line_model_structure.json")))
    actual = _load(os.path.join(MODEL, "line_model.json"))

    assert actual["line_count"] == golden["line_count"], (
        f"line_count drift: golden={golden['line_count']} actual={actual['line_count']}")

    actual_lines = {
        ln["line_id"]: {
            "line_id": ln["line_id"],
            "canonical_name": ln.get("canonical_name"),
            "role": ln.get("role"),
            "process_code": ln.get("process_code"),
        }
        for ln in actual["lines"]
    }
    for exp in golden["lines"]:
        lid = exp["line_id"]
        assert lid in actual_lines, f"golden line {lid} missing from model"
        got = actual_lines[lid]
        assert got == exp, f"line {lid} drift:\n  golden={exp}\n  actual={got}"


def test_component_counts_match_golden():
    golden = _strip_comment(_load(os.path.join(GOLDEN, "expected_component_counts.json")))
    actual = _load(os.path.join(EXCEL, "catalog_register.json"))

    for key in ("scheme", "unique_count", "real_count", "template_count"):
        assert actual[key] == golden[key], (
            f"catalog '{key}' drift: golden={golden[key]} actual={actual[key]}")

    assert sorted(actual["instrument_sheets"]) == golden["instrument_sheets"], (
        "instrument_sheets drift")
    assert actual["real_prefix_histogram"] == golden["real_prefix_histogram"], (
        f"real_prefix_histogram drift:\n  golden={golden['real_prefix_histogram']}"
        f"\n  actual={actual['real_prefix_histogram']}")
    # internal consistency: histogram sums to real_count
    assert sum(actual["real_prefix_histogram"].values()) == actual["real_count"], (
        "real_prefix_histogram does not sum to real_count")


def test_crossmap_stats_match_golden():
    golden = _strip_comment(_load(os.path.join(GOLDEN, "expected_crossmap_stats.json")))
    actual = _load(os.path.join(REPORTS, "W006_crossmap_statistics.json"))

    for key, exp in golden.items():
        assert key in actual, f"crossmap stat '{key}' missing from runtime output"
        assert actual[key] == exp, (
            f"crossmap '{key}' drift: golden={exp} actual={actual[key]}")
    # internal consistency: confidence tiers sum to mapped total
    tiers = actual["high_confidence"] + actual["medium_confidence"] + actual["low_confidence"]
    assert tiers == actual["mapped"], (
        f"confidence tiers ({tiers}) != mapped ({actual['mapped']})")


PURE_TESTS = ["test_golden_files_present"]


def _run_all():
    g = globals()
    pure = [g[n] for n in PURE_TESTS]
    data_fns = [v for k, v in sorted(g.items())
                if k.startswith("test_") and k not in PURE_TESTS]

    passed = 0
    for fn in pure:
        fn()
        print(f"  PASS  {fn.__name__}")
        passed += 1

    if not _data_available():
        print("SKIP  golden data-dependent assertions — derived model artifacts "
              "not built. Run ./make.sh first (data/model/, data/excel/ are "
              "git-ignored).")
        print(f"\n{passed}/{len(pure)} golden presence checks passed "
              f"({len(data_fns)} data comparisons skipped).")
        return passed

    for fn in data_fns:
        fn()
        print(f"  PASS  {fn.__name__}")
        passed += 1
    total = len(pure) + len(data_fns)
    print(f"\n{passed}/{total} golden-file assertions passed.")
    return passed


if __name__ == "__main__":
    try:
        _run_all()
    except AssertionError as exc:
        print(f"\nFAIL  {exc}")
        sys.exit(1)
