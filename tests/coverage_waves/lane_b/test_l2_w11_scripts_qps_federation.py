"""Lane-B wave 11: QPS / federation scripts (DOW coverage flight, W285, W84)."""

import contextlib
import hashlib
import json
import sys
import types

import pytest

from ._l2_loader import REPO_ROOT, load

flight = load("scripts/qps_math_dow_coverage_flight.py")
# A10 F3 phase B moved scripts/qps_w111_power_utility_analysis.py and its
# payloads to the private cryoplant-project; its tests moved out with it (see
# git history of this file at origin/main for the removed W111 cases).
w285 = load("scripts/w285_recompute_federation_depth.py")
w84 = load("scripts/w84_validate_lldb_dap_federation.py")

SHA = "a" * 40
SHA2 = "b" * 40


# ---------------------------------------------------------------------------
# qps_math_dow_coverage_flight: source_head
# ---------------------------------------------------------------------------


def _git(tmp_path, head, *, as_file=None):
    git_dir = tmp_path / "realgit"
    git_dir.mkdir()
    (git_dir / "HEAD").write_text(head + "\n", encoding="utf-8")
    if as_file is None:
        git_dir.rename(tmp_path / ".git")
        return tmp_path / ".git"
    (tmp_path / ".git").write_text(as_file, encoding="utf-8")
    return git_dir


def test_digest_is_sha256():
    assert flight.digest(b"x") == hashlib.sha256(b"x").hexdigest()


def test_source_head_detached_sha(tmp_path, monkeypatch):
    monkeypatch.setattr(flight, "ROOT", tmp_path)
    _git(tmp_path, SHA)
    assert flight.source_head() == SHA


def test_source_head_gitdir_relative_and_loose_ref(tmp_path, monkeypatch):
    monkeypatch.setattr(flight, "ROOT", tmp_path)
    git_dir = _git(tmp_path, "ref: refs/heads/main", as_file="gitdir: realgit\n")
    (git_dir / "refs" / "heads").mkdir(parents=True)
    (git_dir / "refs" / "heads" / "main").write_text(SHA2 + "\n", encoding="utf-8")
    assert flight.source_head() == SHA2


def test_source_head_gitdir_absolute_and_packed_ref(tmp_path, monkeypatch):
    monkeypatch.setattr(flight, "ROOT", tmp_path)
    git_dir = tmp_path / "realgit"
    _git(tmp_path, "ref: refs/heads/main", as_file="gitdir: " + str(git_dir))
    (git_dir / "packed-refs").write_text(
        "# pack-refs\n" + SHA + " refs/heads/other\n" + SHA2 + " refs/heads/main\n",
        encoding="utf-8",
    )
    assert flight.source_head() == SHA2


@pytest.mark.parametrize(
    "head, marker, packed, match",
    [
        (SHA, "nonsense", None, "invalid gitdir link"),
        ("ref: heads/main", None, None, "invalid Git HEAD ref"),
        ("ref: refs/../x", None, None, "invalid Git HEAD ref"),
        ("ref: refs/heads/main", None, None, "missing exact git SHA"),
        ("ref: refs/heads/main", None, "", "missing or ambiguous"),
        (
            "ref: refs/heads/main",
            None,
            SHA + " refs/heads/main\n" + SHA2 + " refs/heads/main\n",
            "missing or ambiguous",
        ),
        ("not-a-sha", None, None, "missing exact git SHA"),
    ],
)
def test_source_head_rejections(tmp_path, monkeypatch, head, marker, packed, match):
    monkeypatch.setattr(flight, "ROOT", tmp_path)
    git_dir = _git(tmp_path, head, as_file=marker)
    if packed is not None:
        (git_dir / "packed-refs").write_text(packed, encoding="utf-8")
    with pytest.raises(ValueError, match=match):
        flight.source_head()


# ---------------------------------------------------------------------------
# qps_math_dow_coverage_flight: parse_coverage
# ---------------------------------------------------------------------------


def _report(name=None, **summary):
    values = {
        "covered_lines": 8,
        "missing_lines": 2,
        "num_branches": 4,
        "covered_branches": 2,
    }
    values.update(summary)
    return {
        "meta": {"branch_coverage": True, "version": flight.TOOL_VERSION},
        "files": {name or flight.TARGET: {"summary": values}},
    }


def test_parse_coverage_valid_relative_and_absolute(tmp_path, monkeypatch):
    monkeypatch.setattr(flight, "ROOT", tmp_path)
    out = flight.parse_coverage(_report(), tests=3)
    assert out == {
        "source": flight.TARGET,
        "tests_executed": 3,
        "lines_covered": 8,
        "lines_eligible": 10,
        "branches_covered": 2,
        "branches_eligible": 4,
        "combined_percent": round(100 * 10 / 14, 4),
    }
    absolute = str(tmp_path / flight.TARGET)
    assert flight.parse_coverage(_report(absolute), tests=1)["tests_executed"] == 1


def _mutate(fn):
    obj = _report()
    fn(obj)
    return obj


@pytest.mark.parametrize(
    "obj, tests, match",
    [
        ([], 1, "missing coverage report"),
        ({"meta": []}, 1, "branch mode missing"),
        ({"meta": {"branch_coverage": False}}, 1, "branch mode missing"),
        (
            _mutate(lambda o: o["meta"].update(version="0")),
            1,
            "tool version drift",
        ),
        (_mutate(lambda o: o.update(files=[])), 1, "exactly one source module"),
        (
            _mutate(lambda o: o["files"].update(other={})),
            1,
            "exactly one source module",
        ),
        (
            _mutate(lambda o: o.update(files={flight.TARGET: []})),
            1,
            "invalid source module entry",
        ),
        (_report("elsewhere.py"), 1, "scope mismatch"),
        (
            _mutate(lambda o: o["files"][flight.TARGET].update(summary=[])),
            1,
            "invalid coverage numerators",
        ),
        (_report(covered_lines=1.0), 1, "invalid coverage numerators"),
        (_report(missing_lines=-1), 1, "invalid coverage numerators"),
        (_report(), 0, "ineligible zero"),
        (_report(covered_lines=0, missing_lines=0), 1, "ineligible zero"),
        (_report(num_branches=0, covered_branches=0), 1, "ineligible zero"),
        (_report(covered_branches=9), 1, "ineligible zero"),
    ],
)
def test_parse_coverage_rejections(tmp_path, monkeypatch, obj, tests, match):
    monkeypatch.setattr(flight, "ROOT", tmp_path)
    with pytest.raises(ValueError, match=match):
        flight.parse_coverage(obj, tests=tests)


# ---------------------------------------------------------------------------
# qps_math_dow_coverage_flight: run_suite (coverage + unittest faked)
# ---------------------------------------------------------------------------


class _FakeCoverage:
    calls = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        _FakeCoverage.calls.append(("init", kwargs["include"]))

    def erase(self):
        _FakeCoverage.calls.append(("erase",))

    def start(self):
        _FakeCoverage.calls.append(("start",))

    def stop(self):
        _FakeCoverage.calls.append(("stop",))

    def save(self):
        _FakeCoverage.calls.append(("save",))

    def json_report(self, morfs, outfile, ignore_errors):
        _FakeCoverage.calls.append(("json", morfs, ignore_errors))
        with open(outfile, "w", encoding="utf-8") as handle:
            json.dump(_report(), handle)


def _fake_tempfile(tmp_path):
    work = tmp_path / "cov-tmp"

    def temporary_directory(prefix):
        assert prefix == "qps-dow-coverage-"
        work.mkdir(exist_ok=True)
        return contextlib.nullcontext(str(work))

    return types.SimpleNamespace(TemporaryDirectory=temporary_directory)


def _fake_unittest(success=True, runs=2, boom=False):
    seen = {}

    class Loader:
        def discover(self, start_dir, pattern):
            seen["discover"] = (start_dir, pattern)
            return "SUITE"

    class Runner:
        def __init__(self, stream, verbosity):
            seen["verbosity"] = verbosity

        def run(self, suite):
            seen["suite"] = suite
            if boom:
                raise RuntimeError("runner exploded")
            return types.SimpleNamespace(wasSuccessful=lambda: success, testsRun=runs)

    return types.SimpleNamespace(TestLoader=Loader, TextTestRunner=Runner), seen


def test_run_suite_success(tmp_path, monkeypatch):
    monkeypatch.setattr(flight, "ROOT", tmp_path)
    fake, seen = _fake_unittest()
    monkeypatch.setattr(flight, "unittest", fake)
    monkeypatch.setattr(flight, "Coverage", _FakeCoverage)
    monkeypatch.setattr(flight, "tempfile", _fake_tempfile(tmp_path))
    _FakeCoverage.calls.clear()
    out = tmp_path / "cov.json"
    result = flight.run_suite("test_x*.py", out)
    assert seen["discover"] == (str(tmp_path / "tests"), "test_x*.py")
    assert seen["suite"] == "SUITE" and seen["verbosity"] == 2
    assert result["tests_executed"] == 2 and result["lines_covered"] == 8
    assert result["coverage_sha256"] == flight.digest(out.read_bytes())
    names = [c[0] for c in _FakeCoverage.calls]
    assert names == ["init", "erase", "start", "stop", "save", "json"]


@pytest.mark.parametrize(
    "kwargs, err, match",
    [
        ({"success": False}, RuntimeError, "suite failed"),
        ({"runs": 0}, ValueError, "missing executed test denominator"),
        ({"boom": True}, RuntimeError, "runner exploded"),
    ],
)
def test_run_suite_failures(tmp_path, monkeypatch, kwargs, err, match):
    monkeypatch.setattr(flight, "ROOT", tmp_path)
    fake, _ = _fake_unittest(**kwargs)
    monkeypatch.setattr(flight, "unittest", fake)
    monkeypatch.setattr(flight, "Coverage", _FakeCoverage)
    monkeypatch.setattr(flight, "tempfile", _fake_tempfile(tmp_path))
    _FakeCoverage.calls.clear()
    with pytest.raises(err, match=match):
        flight.run_suite("p", tmp_path / "cov.json")
    assert ("stop",) in _FakeCoverage.calls
    assert not (tmp_path / "cov.json").exists()


# ---------------------------------------------------------------------------
# qps_math_dow_coverage_flight: pulse and main
# ---------------------------------------------------------------------------


def _measure(tests, lines, branches, **over):
    m = {
        "source": flight.TARGET,
        "tests_executed": tests,
        "lines_covered": lines,
        "lines_eligible": 100,
        "branches_covered": branches,
        "branches_eligible": 20,
        "combined_percent": round(100 * (lines + branches) / 120, 4),
        "coverage_sha256": "c" * 64,
    }
    m.update(over)
    return m


def _patch_pulse(monkeypatch, baseline, expanded, sha=SHA):
    monkeypatch.setattr(flight, "source_head", lambda: sha)
    results = {
        "coverage_baseline.json": baseline,
        "coverage_expanded.json": expanded,
    }
    monkeypatch.setattr(flight, "run_suite", lambda pattern, out: results[out.name])


def test_pulse_writes_receipt(tmp_path, monkeypatch):
    monkeypatch.setenv("GITHUB_RUN_ID", "77")
    monkeypatch.delenv("GITHUB_RUN_ATTEMPT", raising=False)
    _patch_pulse(monkeypatch, _measure(3, 50, 5), _measure(5, 60, 9))
    out = tmp_path / "pulse"
    report = flight.pulse(out, expected_head=SHA)
    written = json.loads((out / "coverage_pulse.json").read_text(encoding="utf-8"))
    assert written == report
    assert report["exact_source_sha"] == SHA
    assert report["github_run_id"] == "77" and report["github_run_attempt"] is None
    assert report["additional_tests"] == 2
    assert report["additional_covered_lines"] == 10
    assert report["additional_covered_branches"] == 4
    assert report["combined_delta_percentage_points"] == round(
        _measure(5, 60, 9)["combined_percent"] - _measure(3, 50, 5)["combined_percent"],
        4,
    )
    assert report["merge_authorized"] is False and report["qps_disposition"] == "DEFER"
    body = {k: v for k, v in report.items() if k != "receipt_sha256"}
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    assert report["receipt_sha256"] == flight.digest(canonical)


@pytest.mark.parametrize(
    "baseline, expanded, expected, match",
    [
        (_measure(3, 50, 5), _measure(5, 60, 9), SHA2, "expected PR head"),
        (
            _measure(3, 50, 5),
            _measure(5, 60, 9, source="x"),
            None,
            "not a source-matched",
        ),
        (
            _measure(3, 50, 5),
            _measure(5, 60, 9, lines_eligible=1),
            None,
            "not a source-matched",
        ),
        (
            _measure(3, 50, 5),
            _measure(5, 60, 9, branches_eligible=1),
            None,
            "not a source-matched",
        ),
        (_measure(3, 50, 5), _measure(3, 60, 9), None, "expansion not executed"),
        (_measure(3, 50, 5), _measure(5, 40, 9), None, "lost covered obligations"),
        (_measure(3, 50, 5), _measure(5, 60, 1), None, "lost covered obligations"),
    ],
)
def test_pulse_rejections(tmp_path, monkeypatch, baseline, expanded, expected, match):
    _patch_pulse(monkeypatch, baseline, expanded)
    with pytest.raises(ValueError, match=match):
        flight.pulse(tmp_path / "pulse", expected_head=expected)
    assert not (tmp_path / "pulse" / "coverage_pulse.json").exists()


def test_flight_main(tmp_path, monkeypatch, capsys):
    _patch_pulse(monkeypatch, _measure(3, 50, 5), _measure(4, 50, 5))
    out = tmp_path / "o"
    monkeypatch.setattr(sys, "argv", ["flight", "--out", str(out)])
    assert flight.main() == 0
    printed = json.loads(capsys.readouterr().out)
    assert printed == {
        "sha": SHA,
        "additional_tests": 1,
        "delta_points": 0.0,
        "qps_disposition": "DEFER",
    }
    assert (out / "coverage_pulse.json").is_file()


# ---------------------------------------------------------------------------
# w285_recompute_federation_depth (committed fixtures are the real input)
# ---------------------------------------------------------------------------


def test_w285_recompute_on_committed_fixtures():
    out = w285.recompute()
    assert out["status"] == "PASS_INDEPENDENT_RECOMPUTE"
    assert out["credited_atoms"] == 9 and out["atom_denominator"] == 16
    assert out["B"] == pytest.approx(1 / 3)
    assert out["D_equal_function"] == pytest.approx(0.6)
    assert out["pooled_atom_ratio"] == pytest.approx(9 / 16)
    assert out["PEN"] == pytest.approx(0.2)


def test_w285_git_blob_matches_git_object_format(tmp_path):
    path = tmp_path / "f"
    path.write_bytes(b"hello\n")
    # `git hash-object` of "hello\n"
    assert w285.git_blob(path) == "ce013625030ba8dba906f756967f9e9ca394464a"


def test_w285_recompute_rejects_changed_depth_fixture(tmp_path, monkeypatch):
    depth = tmp_path / "depth.json"
    depth.write_bytes(w285.DEPTH.read_bytes() + b" ")
    monkeypatch.setattr(w285, "DEPTH", depth)
    with pytest.raises(AssertionError):
        w285.recompute()


def test_w285_recompute_rejects_atom_text_drift(tmp_path, monkeypatch):
    data = json.loads(w285.DEPTH.read_text(encoding="utf-8"))
    data["covered_functions"][0]["atoms"][0]["text"] = "drifted"
    depth = tmp_path / "depth.json"
    depth.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr(w285, "DEPTH", depth)
    monkeypatch.setattr(w285, "EXPECTED_DEPTH", w285.git_blob(depth))
    with pytest.raises(AssertionError):
        w285.recompute()


TOPO_TEXT = """repositories:
  - repo: a
    function: ALPHA
    current_use:
      - first use
      - second use
      not a bullet
    evidence_basis:
      - ignored
  other: top level
  - repo: b
    function: NONE
    current_use:
      - dropped
  - repo: c
    function: GAMMA
    state: x
    current_use:
      - only
  - repo: d
    current_use:
      - orphan
"""


def test_w285_current_use_parser():
    assert w285.current_use(TOPO_TEXT) == {
        "ALPHA": ["first use", "second use"],
        "GAMMA": ["only"],
    }


def test_w285_current_use_top_level_line_keeps_state():
    text = "    function: F\n    current_use:\n      - a\nzzz\n      - b\n"
    assert w285.current_use(text) == {"F": ["a", "b"]}


# ---------------------------------------------------------------------------
# w84_validate_lldb_dap_federation
# ---------------------------------------------------------------------------

FED = {
    "target_language": "Python",
    "semantic_owner": "CODEX/KEB",
}
REQ = {"command": "launch", "program": "app.py"}


def _rows(**first_over):
    rows = []
    for name in w84.REQUIRED_EVENTS:
        rows.append(
            {
                "session_id": "s-1",
                "event": {"name": name},
                "adapter": {"name": "lldb-dap"},
                "backbone": {"language": "Swift"},
                "federation": dict(FED),
                "normalized_request": dict(REQ),
                "github": {"repository": "GBOGEB/ABACUS", "commit_sha": SHA},
            }
        )
    rows[0].update(first_over)
    return rows


def _trace(tmp_path, rows):
    path = tmp_path / "trace.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n\n", encoding="utf-8")
    return path


def test_w84_validate_launch(tmp_path):
    out = w84.validate(_trace(tmp_path, _rows()))
    assert out == {
        "status": "PASS",
        "session_id": "s-1",
        "target_language": "Python",
        "mode": "launch",
        "events": 8,
        "repository": "GBOGEB/ABACUS",
        "commit_sha": SHA,
    }


def test_w84_validate_attach(tmp_path):
    req = {"command": "attach", "process_id": 0}
    rows = _rows()
    for row in rows:
        row["normalized_request"] = dict(req)
    assert w84.validate(_trace(tmp_path, rows))["mode"] == "attach"


def _mutated_rows(fn):
    rows = _rows()
    fn(rows)
    return rows


def _first(**over):
    return lambda rows: rows[0].update(over)


W84_CASES = [
    ([], "empty federation trace"),
    (_mutated_rows(lambda r: r[1].update(session_id="s-2")), "exactly one governed"),
    (
        _mutated_rows(lambda r: [row.pop("session_id") for row in r]),
        "exactly one governed",
    ),
    (_mutated_rows(lambda r: r.pop()), "event sequence mismatch"),
    (_mutated_rows(lambda r: r[0].pop("event")), "event sequence mismatch"),
    (_mutated_rows(_first(adapter={"name": "gdb"})), "not lldb-dap"),
    (_mutated_rows(lambda r: r[0].pop("adapter")), "not lldb-dap"),
    (_mutated_rows(lambda r: r[0].pop("backbone")), "backbone is not Swift"),
    (
        _mutated_rows(
            _first(federation={"target_language": "Rust", "semantic_owner": "x"})
        ),
        "unsupported target language",
    ),
    (_mutated_rows(lambda r: r[0].pop("federation")), "unsupported target"),
    (
        _mutated_rows(
            _first(federation={"target_language": "Swift", "semantic_owner": "x"})
        ),
        "semantic owner",
    ),
    (_mutated_rows(_first(normalized_request={"command": "launch"})), "no program"),
    (
        _mutated_rows(_first(normalized_request={"command": "attach"})),
        "no process_id",
    ),
    (
        _mutated_rows(_first(normalized_request={"command": "run"})),
        "unsupported request mode",
    ),
    (_mutated_rows(lambda r: r[0].pop("normalized_request")), "unsupported request"),
    (_mutated_rows(lambda r: r[0].pop("github")), "not bound to repository"),
    (
        _mutated_rows(_first(github={"repository": "x", "commit_sha": ""})),
        "not bound to repository",
    ),
    (
        _mutated_rows(
            lambda r: r[3].update(
                federation={"target_language": "Swift", "semantic_owner": "CODEX/KEB"}
            )
        ),
        "federation profile changed",
    ),
    (
        _mutated_rows(lambda r: r[3].update(normalized_request={"command": "x"})),
        "normalized DAP request changed",
    ),
]


@pytest.mark.parametrize("rows, match", W84_CASES)
def test_w84_validate_rejections(tmp_path, rows, match):
    with pytest.raises(ValueError, match=match):
        w84.validate(_trace(tmp_path, rows))


def test_w84_main_with_and_without_receipt(tmp_path, monkeypatch, capsys):
    trace = _trace(tmp_path, _rows())
    monkeypatch.setattr(sys, "argv", ["w84", str(trace)])
    assert w84.main() == 0
    plain = capsys.readouterr().out
    assert json.loads(plain)["status"] == "PASS"
    receipt = tmp_path / "nested" / "dir" / "receipt.json"
    monkeypatch.setattr(sys, "argv", ["w84", str(trace), "--receipt", str(receipt)])
    assert w84.main() == 0
    assert capsys.readouterr().out == plain
    assert receipt.read_text(encoding="utf-8") == plain


def test_repo_root_is_checkout():
    assert (REPO_ROOT / "scripts" / "w84_validate_lldb_dap_federation.py").is_file()
