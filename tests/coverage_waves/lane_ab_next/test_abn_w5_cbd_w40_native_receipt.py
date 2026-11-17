"""Behaviour tests for scripts/cbd_w40_native_receipt.py.

Fixtures for ``artifacts/w40`` (coverage JSON and JUnit XML) are built under
``tmp_path`` and the workflow environment is supplied with ``monkeypatch``.
"""

import hashlib
import json

import pytest

from tests.coverage_waves.lane_b._l2_loader import load

mod = load("scripts/cbd_w40_native_receipt.py", name="abn_cbd_w40_native_receipt")

SHA = "a" * 40
BACKSLASH = chr(92)
KEY = BACKSLASH.join(["C:", "repo", "tools", "qps_binary_bridge.py"])


def _cov(lines, branches, stmts=100, nbranch=40, key=KEY):
    summary = dict(
        num_statements=stmts,
        num_branches=nbranch,
        covered_lines=lines,
        covered_branches=branches,
    )
    files = {key: dict(summary=summary), "other/module.py": dict(summary={})}
    return json.dumps(dict(files=files)).encode("utf-8")


def _case(classname, name, child=""):
    return (
        '<testcase classname="'
        + classname
        + '" name="'
        + name
        + '">'
        + child
        + "</testcase>"
    )


def _junit(cases):
    return ("<testsuite>" + "".join(cases) + "</testsuite>").encode("utf-8")


def _baseline_cases(n=3):
    return [_case("tests.test_base", "test_" + str(i)) for i in range(n)]


def _new_cases(w40=42, w41=12):
    cases = [
        _case("tests.test_qps_binary_bridge_w40_penetration", "t" + str(i))
        for i in range(w40)
    ]
    cases += [
        _case("tests.x", "test_qps_binary_bridge_w41_frontier_" + str(i))
        for i in range(w41)
    ]
    return cases


def _setup(tmp_path, monkeypatch, after=None, before=None, junit=None, base=None):
    monkeypatch.chdir(tmp_path)
    out = tmp_path / "artifacts" / "w40"
    out.mkdir(parents=True)
    (out / "coverage.json").write_bytes(after or _cov(80, 30))
    (out / "baseline-coverage.json").write_bytes(before or _cov(70, 25))
    baseline = base if base is not None else _baseline_cases()
    (out / "baseline-junit.xml").write_bytes(_junit(baseline))
    current = junit if junit is not None else baseline + _new_cases()
    (out / "junit.xml").write_bytes(_junit(current))
    monkeypatch.setenv("EXACT_HEAD", SHA)
    monkeypatch.setenv("RUN_ID", "123")
    monkeypatch.setenv("RUN_ATTEMPT", "2")
    monkeypatch.setenv("GITHUB_JOB_NAME", "cell-a")
    return out


def test_source_summary_matches_suffix_across_separators(tmp_path):
    path = tmp_path / "c.json"
    path.write_bytes(_cov(1, 2))
    key, summary = mod.source_summary(path)
    assert key == KEY
    assert summary["covered_branches"] == 2


def test_source_summary_rejects_missing_or_ambiguous(tmp_path):
    path = tmp_path / "c.json"
    path.write_bytes(json.dumps(dict(files={"x.py": {}})).encode())
    with pytest.raises(AssertionError, match="missing/ambiguous"):
        mod.source_summary(path)
    two = dict(files={"a/tools/qps_binary_bridge.py": {}, KEY: {}})
    path.write_bytes(json.dumps(two).encode())
    with pytest.raises(AssertionError, match="missing/ambiguous"):
        mod.source_summary(path)


@pytest.mark.parametrize("child", ["<failure/>", "<error/>", "<skipped/>"])
def test_clean_cases_rejects_bad_outcomes(tmp_path, child):
    path = tmp_path / "j.xml"
    path.write_bytes(_junit([_case("c", "ok"), _case("c", "bad", child)]))
    with pytest.raises(AssertionError, match="native test failure or skip"):
        mod.clean_cases(path)


def test_clean_cases_returns_all_testcases(tmp_path):
    path = tmp_path / "j.xml"
    path.write_bytes(_junit(_baseline_cases(4)))
    assert len(mod.clean_cases(path)) == 4


def test_main_emits_receipt_and_hashes(tmp_path, monkeypatch, capsys):
    out = _setup(tmp_path, monkeypatch)
    mod.main()
    receipt = json.loads((out / "receipt.json").read_text(encoding="utf-8"))
    assert receipt == json.loads(capsys.readouterr().out)
    assert receipt["source_sha"] == SHA
    assert receipt["run_id"] == 123 and receipt["attempt"] == 2
    assert receipt["cell"] == "cell-a"
    assert receipt["total_junit_cases"] == 57
    assert receipt["baseline_junit_cases"] == 3
    assert receipt["new_case_total"] == 54
    assert receipt["delta_statement_covered"] == 10
    assert receipt["delta_branch_covered"] == 5
    assert receipt["matched_eligible_opportunities"] == 140
    assert receipt["matched_before_covered"] == 95
    assert receipt["matched_after_covered"] == 110
    assert receipt["source_file_key"] == KEY
    assert receipt["admission"] == "HOLD"
    hashes = json.loads((out / "SHA256.json").read_text(encoding="utf-8"))
    assert "SHA256.json" not in hashes
    assert sorted(hashes) == [
        "baseline-coverage.json",
        "baseline-junit.xml",
        "coverage.json",
        "junit.xml",
        "receipt.json",
    ]
    digest = hashlib.sha256((out / "receipt.json").read_bytes()).hexdigest()
    assert hashes["receipt.json"] == digest


@pytest.mark.parametrize(
    "kwargs,message",
    [
        (dict(after=_cov(80, 30, stmts=101)), "changed eligible module denominator"),
        (dict(after=_cov(60, 30)), "coverage regression"),
        (dict(after=_cov(80, 20)), "coverage regression"),
        (dict(base=[], junit=_new_cases()), "baseline suite must be green"),
        (dict(junit=_baseline_cases() + _new_cases(w40=41)), "W40 denominator"),
        (dict(junit=_baseline_cases() + _new_cases(w41=11)), "W41 denominator"),
        (
            dict(junit=_baseline_cases(2) + _new_cases()),
            "unmatched test populations",
        ),
    ],
)
def test_main_assertion_gates(tmp_path, monkeypatch, kwargs, message):
    out = _setup(tmp_path, monkeypatch, **kwargs)
    with pytest.raises(AssertionError, match=message):
        mod.main()
    assert not (out / "receipt.json").exists()


@pytest.mark.parametrize("sha", ["a" * 39, "A" * 40, "g" * 40])
def test_main_rejects_malformed_exact_head(tmp_path, monkeypatch, sha):
    out = _setup(tmp_path, monkeypatch)
    monkeypatch.setenv("EXACT_HEAD", sha)
    with pytest.raises(AssertionError):
        mod.main()
    assert not (out / "receipt.json").exists()


def test_main_requires_run_environment(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    monkeypatch.delenv("RUN_ID")
    with pytest.raises(KeyError):
        mod.main()
