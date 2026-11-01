"""Lane A wave 13: ci/w76_zero_coverage.py measurement and CLI."""

import copy
import hashlib
import json
import sys

import pytest

from tests.coverage_waves.lane_a._load import load

HEAD = "a" * 40
BLOB = "b" * 40
LOG = b"test_x (m.T.test_x) ... ok\n\nRan 3 tests in 0.010s\n\nOK (skipped=1)\n"


@pytest.fixture(scope="module")
def w76():
    saved_path = list(sys.path)
    name = "l1_w13_w76_zero_coverage"
    try:
        mod = load("ci/w76_zero_coverage.py", name=name)
    finally:
        sys.path[:] = saved_path
        sys.modules.pop(name, None)
    return mod


def _baseline(paths=("pkg/a.py", "pkg/b.py")):
    return {
        "schema": "codepurple.zero-asset.baseline.v1",
        "source_repository": "GBOGEB/ABACUS",
        "observed_pr_head_sha": HEAD,
        "event_merge_sha": "e" * 40,
        "checkout_sha": "c" * 40,
        "coverage_artifact_id": 77,
        "coverage_tool_version": "7.6.1",
        "acceptance": {
            "authority_transfer": False,
            "merge_authorized": False,
            "qps_owner_accepted": False,
        },
        "baseline_population": {"executable_zero_covered_files": 12},
        "files": [
            {
                "path": p,
                "source_blob_sha": BLOB,
                "eligible_statements": 10,
                "eligible_branches": 4,
                "baseline_covered_statements": 0,
                "baseline_covered_branches": 0,
            }
            for p in paths
        ],
    }


def _summary(cs=5, cb=2, ns=10, nb=4):
    return {
        "summary": {
            "covered_lines": cs,
            "covered_branches": cb,
            "num_statements": ns,
            "num_branches": nb,
        }
    }


def _coverage(files):
    return {"meta": {"branch_coverage": True, "version": "7.6.1"}, "files": files}


def _tests():
    return dict(executed=3, passed=2, failed=0, skipped=1)


def _blob(name):
    return BLOB


def test_ensure_count_and_verify_path(w76):
    assert w76.ensure_count(0, "x") == 0
    for bad in (-1, True, 1.0):
        with pytest.raises(ValueError, match="invalid count: lbl"):
            w76.ensure_count(bad, "lbl")
    assert w76.verify_path("a/b.py") == "a/b.py"
    for bad in (None, "single", "a/../b", ".git/x", "a//b", "a/./b"):
        with pytest.raises(ValueError, match="unsafe"):
            w76.verify_path(bad)


def test_parse_terminal_ok_and_failures(w76):
    assert w76.parse_terminal(LOG) == _tests()
    plain = b"Ran 2 tests in 1s\nOK\n"
    assert w76.parse_terminal(plain)["skipped"] == 0
    with pytest.raises(ValueError, match="bytes"):
        w76.parse_terminal("text")
    with pytest.raises(ValueError, match="ambiguous"):
        w76.parse_terminal(b"Ran 2 tests in 1s\nFAILED\n")
    with pytest.raises(ValueError, match="no positive"):
        w76.parse_terminal(b"Ran 1 tests in 1s\nOK (skipped=1)\n")


def test_measure_mixed_statuses(w76):
    files = {
        "pkg\\a.py": _summary(),
        "pkg/b.py": _summary(cs=0, cb=0),
        "pkg/c.py": _summary(ns=11),
        42: {},
    }
    base = _baseline(("pkg/a.py", "pkg/b.py", "pkg/c.py", "pkg/d.py"))
    out = w76.measure(base, _coverage(files), HEAD, _blob, _tests())
    status = {row["path"]: row["status"] for row in out["files"]}
    assert status == {
        "pkg/a.py": "RECOVERED",
        "pkg/b.py": "ZERO_COVERED",
        "pkg/c.py": "INCOMPARABLE_DENOMINATOR",
        "pkg/d.py": "UNKNOWN_MISSING_COVERAGE",
    }
    assert out["recovered_zero_covered_assets"] == 1
    assert out["still_zero_covered_assets"] == 1
    assert out["unknown_or_incomparable_assets"] == 2
    assert out["matched_statement_coverage"] == {
        "baseline_covered": 0,
        "candidate_covered": 5,
        "eligible": 20,
    }
    assert out["zero_covered_global_baseline"] == 12
    assert out["historical_artifact_id"] == 77


def _expect(w76, match, base=None, cov=None, sha=HEAD, blob=_blob, tests=None):
    base = _baseline() if base is None else base
    cov = _coverage({"pkg/a.py": _summary()}) if cov is None else cov
    tests = _tests() if tests is None else tests
    with pytest.raises(ValueError, match=match):
        w76.measure(base, cov, sha, blob, tests)


def test_measure_identity_and_authority_guards(w76):
    _expect(w76, "baseline identity", base=[])
    bad = _baseline()
    bad["source_repository"] = "x/y"
    _expect(w76, "source identity", base=bad)
    _expect(w76, "source identity", sha="short")
    bad = _baseline()
    bad["acceptance"]["merge_authorized"] = True
    _expect(w76, "admission authority", base=bad)


def test_measure_coverage_and_test_guards(w76):
    _expect(w76, "version drift", cov=["x"])
    _expect(w76, "census", cov={"meta": {"branch_coverage": True, "version": "7.6.1"}})
    bad = _baseline()
    bad["files"] = []
    _expect(w76, "roster", base=bad)
    _expect(w76, "terminal passing", tests={"failed": 1})
    unreconciled = dict(executed=4, failed=0, skipped=1, passed=2)
    _expect(w76, "unreconciled", tests=unreconciled)


def test_measure_member_guards(w76):
    bad = _baseline()
    bad["files"] = ["x"]
    _expect(w76, "baseline member", base=bad)
    _expect(w76, "duplicate baseline", base=_baseline(("pkg/a.py", "pkg/a.py")))
    bad = _baseline()
    bad["files"][0]["source_blob_sha"] = "nope"
    _expect(w76, "blob identity", base=bad)
    _expect(w76, "bytes changed", blob=lambda name: "0" * 40)
    bad = _baseline()
    bad["files"][0]["baseline_covered_statements"] = 1
    _expect(w76, "zero-covered", base=bad)


def test_measure_coverage_record_guards(w76):
    alias = _coverage({"pkg/a.py": _summary(), "pkg\\a.py": _summary()})
    _expect(w76, "duplicate normalized", cov=alias)
    _expect(w76, "instrumented", cov=_coverage({"pkg/a.py": {"summary": 1}}))
    _expect(w76, "exceeds", cov=_coverage({"pkg/a.py": _summary(cs=11)}))


def test_exact_checkout_sha(w76, tmp_path):
    with pytest.raises(ValueError, match="unavailable"):
        w76.exact_checkout_sha(tmp_path)
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "HEAD").write_text("ref: refs/heads/main\n")
    with pytest.raises(ValueError, match="detached"):
        w76.exact_checkout_sha(tmp_path)
    (tmp_path / ".git" / "HEAD").write_text(HEAD + "\n")
    assert w76.exact_checkout_sha(tmp_path) == HEAD


def test_source_blob_sha(w76, tmp_path):
    (tmp_path / "pkg").mkdir()
    data = b"print(1)\n"
    (tmp_path / "pkg" / "a.py").write_bytes(data)
    expected = hashlib.sha1(b"blob 9\0" + data, usedforsecurity=False).hexdigest()
    assert w76.source_blob_sha(tmp_path, "pkg/a.py") == expected
    with pytest.raises(ValueError, match="missing production source"):
        w76.source_blob_sha(tmp_path, "pkg/none.py")


def _cli_inputs(tmp_path, w76, recovered=True):
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    (repo / ".git" / "HEAD").write_text(HEAD + "\n")
    (repo / "pkg").mkdir()
    (repo / "pkg" / "a.py").write_bytes(b"x = 1\n")
    base = _baseline(("pkg/a.py",))
    base["files"][0]["source_blob_sha"] = w76.source_blob_sha(repo, "pkg/a.py")
    cov = _coverage({"pkg/a.py": _summary(cs=5 if recovered else 0, cb=0)})
    paths = {}
    for key, raw in (
        ("baseline", json.dumps(base).encode()),
        ("coverage", json.dumps(cov).encode()),
        ("log", LOG),
    ):
        paths[key] = tmp_path / (key + ".in")
        paths[key].write_bytes(raw)
    return repo, paths


def _argv(repo, paths, out, head=HEAD):
    return [
        "w76",
        "--baseline",
        str(paths["baseline"]),
        "--coverage-json",
        str(paths["coverage"]),
        "--unittest-log",
        str(paths["log"]),
        "--expected-head",
        head,
        "--repository-root",
        str(repo),
        "--out",
        str(out),
    ]


def test_main_success_writes_receipt_and_manifest(w76, tmp_path, monkeypatch, capsys):
    repo, paths = _cli_inputs(tmp_path, w76)
    out = tmp_path / "out"
    monkeypatch.setattr(sys, "argv", _argv(repo, paths, out))
    w76.main()
    receipt = json.loads((out / "zero_asset_pulse.json").read_bytes())
    assert receipt["recovered_zero_covered_assets"] == 1
    assert receipt["unittest_log_sha256"] == hashlib.sha256(LOG).hexdigest()
    manifest = json.loads((out / "evidence_manifest.json").read_text())
    assert set(manifest["sha256"]) == {
        "zero_asset_pulse.json",
        "coverage.json",
        "unittest.log",
        "baseline.json",
    }
    assert json.loads(capsys.readouterr().out)["merge_authorized"] is False


def test_main_head_mismatch_and_incomplete(w76, tmp_path, monkeypatch, capsys):
    repo, paths = _cli_inputs(tmp_path, w76, recovered=False)
    out = tmp_path / "out"
    monkeypatch.setattr(sys, "argv", _argv(repo, paths, out, head="f" * 40))
    with pytest.raises(SystemExit, match="EXACT_HEAD_SOURCE_MISMATCH"):
        w76.main()
    monkeypatch.setattr(sys, "argv", _argv(repo, paths, out))
    with pytest.raises(SystemExit, match="INCOMPLETE_HOLD"):
        w76.main()


def test_receipt_is_deterministic_copy_safe(w76):
    base = _baseline()
    snapshot = copy.deepcopy(base)
    cov = _coverage({"pkg/a.py": _summary(), "pkg/b.py": _summary()})
    w76.measure(base, cov, HEAD, _blob, _tests())
    assert base == snapshot
