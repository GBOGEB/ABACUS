"""Gap tests for scripts/cbd_b0_scope_comparison.py (fail paths, main)."""

import json

import pytest

from tests.coverage_waves.lane_b._l2_loader import load

mod = load("scripts/cbd_b0_scope_comparison.py", name="abn_w7_cbd_b0_scope")

IDENTITY = dict(
    head_sha="a" * 40,
    run_id=7,
    attempt=1,
    canonical_job_id=12,
    report_job_id=13,
    canonical_artifact_id=21,
    report_artifact_id=22,
)


def _cov(covered=(5, 4), timestamp="2026-10-17T10:10:51Z", meta_ok=True):
    files = {}
    for index, path in enumerate(mod.TARGETS):
        files[path] = {
            "summary": {
                "covered_lines": covered[index],
                "num_statements": 10,
                "covered_branches": 1,
                "num_branches": 4,
            }
        }
    return {
        "meta": {"timestamp": timestamp, "branch_coverage": meta_ok},
        "files": files,
    }


def _junit(tests="2", stamp="2026-10-17T10:10:49"):
    return (
        '<testsuite tests="' + tests + '" time="1" timestamp="' + stamp + '">'
        "<testcase/><testcase/></testsuite>"
    )


@pytest.mark.parametrize("value", [None, "   ", 5])
def test_timestamp_unavailable(value):
    with pytest.raises(ValueError, match="timestamp unavailable"):
        mod.timestamp(value)


def test_timestamp_naive_is_utc():
    assert mod.timestamp("2026-01-01T00:00:00").utcoffset().total_seconds() == 0


def test_suite_summary_single_testsuite_root():
    summary = mod.suite_summary(_junit())
    assert summary["declared_tests"] == 2
    assert summary["count_difference"] == 0


def test_suite_summary_without_suites():
    with pytest.raises(ValueError, match="JUnit suite unavailable"):
        mod.suite_summary("<testsuites></testsuites>")


@pytest.mark.parametrize("tests", ["x", "-1"])
def test_suite_summary_invalid_declared_tests(tests):
    with pytest.raises(ValueError, match="invalid JUnit declared tests"):
        mod.suite_summary(_junit(tests=tests))


def test_suite_summary_missing_tests_attribute():
    with pytest.raises(ValueError, match="invalid JUnit declared tests"):
        mod.suite_summary("<testsuites><testsuite/></testsuites>")


def test_stats_requires_branch_coverage():
    with pytest.raises(ValueError, match="branch coverage evidence"):
        mod.stats(_cov(meta_ok=False))
    with pytest.raises(ValueError, match="branch coverage evidence"):
        mod.stats([])


def test_stats_requires_file_inventory():
    doc = _cov()
    doc["files"] = None
    with pytest.raises(ValueError, match="file inventory unavailable"):
        mod.stats(doc)


def test_compare_requires_identity_dict():
    with pytest.raises(ValueError, match="identity required"):
        mod.compare(_cov(), _cov(), _junit(), None)


@pytest.mark.parametrize("sha", ["A" * 40, "a" * 39, 12])
def test_compare_rejects_invalid_sha(sha):
    identity = dict(IDENTITY, head_sha=sha)
    with pytest.raises(ValueError, match="invalid exact source SHA"):
        mod.compare(_cov(), _cov(), _junit(), identity)


def _write_inputs(tmp_path, canonical):
    paths = {}
    payloads = {
        "canonical": json.dumps(canonical),
        "report-only": json.dumps(_cov((0, 0), "2026-10-17T10:06:20Z")),
        "junit": _junit(),
        "identity": json.dumps(IDENTITY),
    }
    argv = []
    for name, text in payloads.items():
        path = tmp_path / (name + ".in")
        path.write_text(text, encoding="utf-8")
        paths[name] = path
        argv += ["--" + name, str(path)]
    out = tmp_path / "receipt.json"
    return argv + ["--out", str(out)], out


def test_main_after_suite_returns_zero(tmp_path, capsys):
    argv, out = _write_inputs(tmp_path, _cov())
    assert mod.main(argv) == 0
    receipt = json.loads(out.read_text(encoding="utf-8"))
    assert receipt["measurement_state"] == "SCOPED_CANONICAL_AFTER_TEST"
    assert receipt["cross_scope_statement_contrast"] == 9
    printed = json.loads(capsys.readouterr().out)
    assert printed == {"canonical_combined": [11, 28], "junit_count_integrity": "PASS"}


def test_main_stale_canonical_returns_two(tmp_path, capsys):
    argv, out = _write_inputs(tmp_path, _cov(timestamp="2026-10-17T10:00:00Z"))
    assert mod.main(argv) == 2
    receipt = json.loads(out.read_text(encoding="utf-8"))
    assert receipt["measurement_state"] == "HOLD_CANONICAL_EVIDENCE_STALE"
    assert "canonical_combined" in capsys.readouterr().out
