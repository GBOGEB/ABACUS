"""Lane 2 coverage: B0 report-only admission census evidence integrity.

``scripts/test_admission_census.py`` is a CI script (despite its ``test_`` name)
that discovers excluded suites, runs pytest per file, reads the JUnit XML each
run emits and classifies every file into a governed ``TEST_*`` state.  The key
property exercised here: missing, forged or contradictory evidence must never
classify as ``TEST_GREEN``.

Hermetic: the module is loaded by file path (a site-packages ``scripts``
package can shadow the repo namespace dir), its ``ROOT``/``DEFAULT_ROOTS``
constants are pointed at ``tmp_path`` and ``subprocess`` is replaced at the
module import site by a scripted fake, so no real pytest/coverage/git runs.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "scripts" / "test_admission_census.py"
MODULE_NAME = "_lane2_admission_census"


def _load():
    if MODULE_NAME in sys.modules:
        return sys.modules[MODULE_NAME]
    spec = importlib.util.spec_from_file_location(MODULE_NAME, MODULE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[MODULE_NAME] = module
    spec.loader.exec_module(module)
    return module


census = _load()

# The census module's own subprocess and ElementTree, bound before any test
# swaps them out. Importing them here only adds Bandit B404/B405 noise to a
# test file that never launches a process or parses untrusted XML (594189ef).
subprocess = census.subprocess
ET = census.ET

ZERO = {"pass": 0, "fail": 0, "error": 0, "skip": 0}


def _junit(path: Path, cases: str) -> Path:
    path.write_text(
        '<?xml version="1.0" encoding="utf-8"?>'
        f'<testsuites><testsuite name="s">{cases}</testsuite></testsuites>',
        encoding="utf-8",
    )
    return path


def _skip(state: str | None = None, message: str = "skipped", text: str = "") -> str:
    props = (
        f'<properties><property name="test_state" value="{state}"/></properties>'
        if state
        else ""
    )
    return f'<testcase name="t">{props}<skipped message="{message}">{text}</skipped></testcase>'


# --------------------------------------------------------------------------
# junit_counts_and_states
# --------------------------------------------------------------------------


def test_missing_junit_yields_zero_counts_not_green(tmp_path):
    counts, states = census.junit_counts_and_states(tmp_path / "absent.xml")
    assert counts == ZERO
    assert states == {}
    # Absent evidence with a clean exit code is never promoted to green.
    assert (
        census.classify_report_only_state(counts, states, 0)
        == "TEST_EXISTS_UNCOLLECTED"
    )
    assert (
        census.classify_report_only_state(counts, states, 5)
        == "TEST_EXISTS_UNCOLLECTED"
    )


def test_error_and_failure_cases_counted_before_skip(tmp_path):
    xml = _junit(
        tmp_path / "mixed.xml",
        '<testcase name="e"><error message="boom"/></testcase>'
        # error takes precedence even if the case also carries <skipped>
        '<testcase name="e2"><error/><skipped/></testcase>'
        '<testcase name="f"><failure message="x"/></testcase>'
        '<testcase name="f2"><failure/><skipped/></testcase>'
        '<testcase name="p"/>',
    )
    counts, states = census.junit_counts_and_states(xml)
    assert counts == {"pass": 1, "fail": 2, "error": 2, "skip": 0}
    assert states == {}
    assert census.classify_report_only_state(counts, states, 1) == "TEST_FAILING"


def test_property_other_than_test_state_falls_back_to_skip_text(tmp_path):
    xml = _junit(
        tmp_path / "props.xml",
        '<testcase name="a"><properties>'
        '<property name="owner" value="TEST_BLOCKED_CONFIG"/>'
        '</properties><skipped message="">TEST_BLOCKED_DEPENDENCY: numpy</skipped></testcase>',
    )
    counts, states = census.junit_counts_and_states(xml)
    assert counts["skip"] == 1
    # The unrelated property is ignored; the skip body text is the evidence.
    assert states == {"TEST_BLOCKED_DEPENDENCY": 1}


def test_explicit_property_wins_over_skip_message(tmp_path):
    xml = _junit(
        tmp_path / "explicit.xml",
        _skip("TEST_NOT_IMPLEMENTED", message="TEST_BLOCKED_CONFIG mentioned"),
    )
    _, states = census.junit_counts_and_states(xml)
    assert states == {"TEST_NOT_IMPLEMENTED": 1}


def test_properties_without_test_state_and_plain_skip_records_no_state(tmp_path):
    xml = _junit(
        tmp_path / "plain.xml",
        '<testcase name="a"><properties><property name="x" value="y"/></properties>'
        "<skipped/></testcase>",
    )
    counts, states = census.junit_counts_and_states(xml)
    assert counts == {"pass": 0, "fail": 0, "error": 0, "skip": 1}
    assert states == {}


def test_malformed_junit_fails_closed_with_parse_error(tmp_path):
    bad = tmp_path / "bad.xml"
    bad.write_text("<testsuites><testcase name='x'>", encoding="utf-8")
    with pytest.raises(ET.ParseError):
        census.junit_counts_and_states(bad)


def test_empty_suite_is_uncollected(tmp_path):
    xml = _junit(tmp_path / "empty.xml", "")
    counts, states = census.junit_counts_and_states(xml)
    assert counts == ZERO
    assert (
        census.classify_report_only_state(counts, states, 5)
        == "TEST_EXISTS_UNCOLLECTED"
    )


# --------------------------------------------------------------------------
# classify_report_only_state: adversarial / forged evidence
# --------------------------------------------------------------------------


@pytest.mark.parametrize("returncode", [1, 2, 3, 4, -9, 137])
def test_passes_with_bad_returncode_are_failing(returncode):
    counts = {"pass": 10, "fail": 0, "error": 0, "skip": 0}
    assert census.classify_report_only_state(counts, {}, returncode) == "TEST_FAILING"


def test_forged_green_state_property_never_classifies_green(tmp_path):
    xml = _junit(tmp_path / "forged.xml", _skip("TEST_GREEN") + _skip("TEST_GREEN"))
    counts, states = census.junit_counts_and_states(xml)
    assert states == {"TEST_GREEN": 2}
    assert (
        census.classify_report_only_state(counts, states, 0)
        == "TEST_EXISTS_UNCOLLECTED"
    )


def test_mixed_blocking_states_are_not_collapsed():
    counts = {"pass": 0, "fail": 0, "error": 0, "skip": 2}
    states = {"TEST_BLOCKED_CONFIG": 1, "TEST_BLOCKED_DEPENDENCY": 1}
    assert (
        census.classify_report_only_state(counts, states, 0)
        == "TEST_EXISTS_UNCOLLECTED"
    )


def test_partially_governed_skips_are_uncollected():
    counts = {"pass": 0, "fail": 0, "error": 0, "skip": 3}
    states = {"TEST_BLOCKED_CONFIG": 2}
    assert (
        census.classify_report_only_state(counts, states, 0)
        == "TEST_EXISTS_UNCOLLECTED"
    )


def test_overcounted_state_does_not_match_skip_total():
    counts = {"pass": 0, "fail": 0, "error": 0, "skip": 1}
    states = {"TEST_BLOCKED_CONFIG": 2}
    assert (
        census.classify_report_only_state(counts, states, 0)
        == "TEST_EXISTS_UNCOLLECTED"
    )


def test_unknown_state_alongside_blocking_state_is_ignored_for_match():
    counts = {"pass": 0, "fail": 0, "error": 0, "skip": 2}
    states = {"TEST_BLOCKED_SOURCE_MISSING": 2, "TEST_GREEN": 5}
    assert (
        census.classify_report_only_state(counts, states, 0)
        == "TEST_BLOCKED_SOURCE_MISSING"
    )


def test_skips_with_failing_returncode_are_failing():
    counts = {"pass": 0, "fail": 0, "error": 0, "skip": 1}
    assert (
        census.classify_report_only_state(counts, {"TEST_BLOCKED_CONFIG": 1}, 2)
        == "TEST_FAILING"
    )


# --------------------------------------------------------------------------
# discover_tests / run_command / helpers
# --------------------------------------------------------------------------


def _touch(path: Path, text: str = "") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_discover_tests_layouts_missing_roots_and_dedup(tmp_path):
    dmaic = tmp_path / "DMAIC_V3" / "tests"
    integ = tmp_path / "integration"
    a = _touch(dmaic / "test_alpha.py")
    _touch(dmaic / "helper.py")
    (dmaic / "test_dir.py").mkdir()  # directory matching the glob is ignored
    b = _touch(integ / "pkg" / "tests" / "test_beta.py")
    _touch(integ / "test_top_level_ignored.py")  # integration root needs */tests/
    found = census.discover_tests([dmaic, integ, tmp_path / "missing", dmaic])
    assert found == sorted([a.resolve(), b.resolve()])


def test_discover_tests_all_roots_missing_is_empty(tmp_path):
    assert census.discover_tests([tmp_path / "nope", tmp_path / "integration"]) == []


def test_run_command_uses_root_cwd_and_merges_stderr(monkeypatch, tmp_path):
    seen = {}

    def fake_run(args, **kwargs):
        seen["args"] = args
        seen.update(kwargs)
        return subprocess.CompletedProcess(args, 3, stdout="out")

    monkeypatch.setattr(census, "ROOT", tmp_path)
    monkeypatch.setattr(
        census, "subprocess", SimpleNamespace(run=fake_run, PIPE=-1, STDOUT=-2)
    )
    result = census.run_command(["x", "y"])
    assert result.returncode == 3
    assert seen["args"] == ["x", "y"]
    assert seen["cwd"] == tmp_path
    assert seen["text"] is True and seen["check"] is False
    assert seen["stdout"] == -1 and seen["stderr"] == -2


def test_estimated_candidates_excludes_tests_and_self(monkeypatch, tmp_path):
    monkeypatch.setattr(census, "ROOT", tmp_path)
    _touch(tmp_path / "pkg" / "widget.py")
    _touch(tmp_path / "lib" / "deep" / "widget.py")
    _touch(tmp_path / "tests" / "widget.py")
    _touch(tmp_path / "pkg" / "tests" / "widget.py")
    test_file = _touch(tmp_path / "DMAIC_V3" / "tests" / "test_widget.py").resolve()
    assert census._estimated_candidates(test_file) == [
        "lib/deep/widget.py",
        "pkg/widget.py",
    ]
    # A file whose stem matches itself (no test_ prefix) is skipped as its own candidate.
    own = _touch(tmp_path / "solo" / "lonely.py").resolve()
    assert census._estimated_candidates(own) == []


def test_context_mapping_missing_and_measured(monkeypatch, tmp_path):
    monkeypatch.setattr(census, "ROOT", tmp_path)
    t1 = _touch(tmp_path / "DMAIC_V3" / "tests" / "test_one.py").resolve()
    t2 = _touch(tmp_path / "integration" / "p" / "tests" / "test_two.py").resolve()
    cov = tmp_path / "cov.json"
    empty = census._context_mapping(cov, [t1, t2])
    assert empty == {
        "DMAIC_V3/tests/test_one.py": [],
        "integration/p/tests/test_two.py": [],
    }
    cov.write_text(
        json.dumps(
            {
                "files": {
                    "src\\a.py": {"contexts": {"1": ["test_one|run"], "2": [""]}},
                    "src/b.py": {
                        "contexts": {
                            "1": ["integration.p.tests.test_two.TestX.test_y|run"],
                            "2": "not-a-list",
                        }
                    },
                    "src/c.py": {"contexts": {"3": ["unrelated|run"]}},
                    "src/d.py": {},
                    "src/a2.py": {
                        "contexts": {"1": ["test_one|run"], "4": ["test_one|run"]}
                    },
                }
            }
        ),
        encoding="utf-8",
    )
    mapping = census._context_mapping(cov, [t1, t2])
    assert mapping == {
        "DMAIC_V3/tests/test_one.py": ["src/a.py", "src/a2.py"],
        "integration/p/tests/test_two.py": ["src/b.py"],
    }


def test_context_mapping_tampered_json_raises(monkeypatch, tmp_path):
    monkeypatch.setattr(census, "ROOT", tmp_path)
    t1 = _touch(tmp_path / "DMAIC_V3" / "tests" / "test_one.py").resolve()
    cov = tmp_path / "cov.json"
    cov.write_text("{not json", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        census._context_mapping(cov, [t1])


# --------------------------------------------------------------------------
# main(): end-to-end with a scripted subprocess
# --------------------------------------------------------------------------


class FakeProcs:
    """Scripted stand-in for ``subprocess`` at the census import site.

    ``plans`` maps a test file stem to a dict with optional keys:
    ``collect_rc``, ``run_rc``, ``junit`` (XML cases or None = do not write).
    """

    PIPE = subprocess.PIPE
    STDOUT = subprocess.STDOUT

    def __init__(self, plans, coverage_payload=None, coverage_rc=0):
        self.plans = plans
        self.coverage_payload = coverage_payload
        self.coverage_rc = coverage_rc
        self.calls = []

    def _plan(self, args):
        rel = args[-1]
        return self.plans[Path(rel).stem]

    def run(self, args, **kwargs):
        self.calls.append(list(args))
        assert kwargs["cwd"] == census.ROOT
        if args[1:3] == ["-m", "coverage"]:
            if args[3] == "erase":
                return subprocess.CompletedProcess(args, 0, stdout="")
            out = Path(args[args.index("-o") + 1])
            if self.coverage_payload is not None:
                out.write_text(json.dumps(self.coverage_payload), encoding="utf-8")
            return subprocess.CompletedProcess(args, self.coverage_rc, stdout="")
        plan = self._plan(args)
        if "--collect-only" in args:
            rc = plan.get("collect_rc", 0)
            return subprocess.CompletedProcess(
                args, rc, stdout="C" * 5000 if rc else "collected"
            )
        junit_arg = next(a for a in args if a.startswith("--junitxml="))
        junit = Path(junit_arg.split("=", 1)[1])
        if plan.get("junit") is not None:
            _junit(junit, plan["junit"])
        return subprocess.CompletedProcess(
            args, plan.get("run_rc", 0), stdout="R" * 4100
        )


@pytest.fixture
def tree(monkeypatch, tmp_path):
    root = tmp_path / "repo"
    dmaic = root / "DMAIC_V3" / "tests"
    integ = root / "integration"
    monkeypatch.setattr(census, "ROOT", root)
    monkeypatch.setattr(census, "DEFAULT_ROOTS", (dmaic, integ))
    monkeypatch.delenv("GITHUB_SHA", raising=False)
    return SimpleNamespace(root=root, dmaic=dmaic, integ=integ, out=tmp_path / "out")


def _install(monkeypatch, fake):
    monkeypatch.setattr(census, "subprocess", fake)


def _argv(tree, *extra):
    return [
        "--out",
        str(tree.out / "report" / "census.json"),
        "--coverage-out",
        str(tree.out / "cov" / "coverage.json"),
        "--junit-dir",
        str(tree.out / "junit"),
        *extra,
    ]


def _read_report(tree):
    return json.loads((tree.out / "report" / "census.json").read_text(encoding="utf-8"))


def test_main_full_census_classifies_every_evidence_shape(monkeypatch, tree, capsys):
    files = {
        "test_green": tree.dmaic / "test_green.py",
        "test_broken": tree.dmaic / "test_broken.py",
        "test_noxml": tree.dmaic / "test_noxml.py",
        "test_blocked": tree.integ / "pkg" / "tests" / "test_blocked.py",
        "test_redrc": tree.integ / "pkg" / "tests" / "test_redrc.py",
    }
    for path in files.values():
        _touch(path)
    _touch(tree.root / "src" / "noxml.py")
    plans = {
        "test_green": {"junit": '<testcase name="ok"/>'},
        "test_broken": {"collect_rc": 2},
        "test_noxml": {"junit": None, "run_rc": 0},
        "test_blocked": {"junit": _skip("TEST_BLOCKED_CONFIG"), "run_rc": 0},
        "test_redrc": {"junit": '<testcase name="ok"/>', "run_rc": 1},
    }
    coverage = {"files": {"src/green.py": {"contexts": {"1": ["test_green|run"]}}}}
    fake = FakeProcs(plans, coverage_payload=coverage, coverage_rc=0)
    _install(monkeypatch, fake)

    assert census.main(_argv(tree, "--exact-sha", "a" * 40)) == 0
    report = _read_report(tree)
    printed = json.loads(capsys.readouterr().out)
    assert printed == report

    rows = {Path(r["path"]).stem: r for r in report["rows"]}
    assert rows["test_green"]["test_state"] == "TEST_GREEN"
    assert rows["test_green"]["measured_source_paths"] == ["src/green.py"]
    assert (
        rows["test_green"]["existing_test_surface_evidence"]
        == "DYNAMIC_CONTEXT (MEASURED)"
    )
    assert rows["test_green"]["estimated_source_candidates"] == []
    assert len(rows["test_green"]["run_output"]) == 4000

    broken = rows["test_broken"]
    assert broken["collection_status"] == "ERROR"
    assert broken["test_state"] == "TEST_FAILING"
    assert broken["outcomes"] == {"pass": 0, "fail": 0, "error": 1, "skip": 0}
    assert len(broken["collection_output"]) == 4000
    assert "run_returncode" not in broken
    # Rows with no measured path fall back to name-match estimates even after
    # a collection error.
    assert broken["existing_test_surface_evidence"] == "NAME_MATCH (ESTIMATED)"

    # Missing JUnit evidence with exit 0 must not be green.
    assert rows["test_noxml"]["test_state"] == "TEST_EXISTS_UNCOLLECTED"
    assert rows["test_noxml"]["outcomes"] == ZERO
    assert rows["test_noxml"]["estimated_source_candidates"] == ["src/noxml.py"]

    assert rows["test_blocked"]["test_state"] == "TEST_BLOCKED_CONFIG"
    assert rows["test_blocked"]["governed_state_counts"] == {"TEST_BLOCKED_CONFIG": 1}
    assert rows["test_redrc"]["test_state"] == "TEST_FAILING"

    assert report["schema"] == "abacus-test-admission-census/1.0.0"
    assert report["exact_sha"] == "a" * 40
    assert report["report_only"] is True
    assert report["authority_transfer"] is False
    assert report["baseline_test_count_credit"] == 0
    assert report["formal_credit_delta"] == report["engineering_credit_delta"] == 0
    assert report["test_file_count"] == 5
    assert report["collection_error_count"] == 1
    assert report["test_failing_file_count"] == 2
    assert report["coverage_export_returncode"] == 0

    # Command protocol: erase first, coverage json last, broken file never run.
    assert fake.calls[0][-1] == "erase"
    assert fake.calls[-1][3:5] == ["json", "--show-contexts"]
    run_targets = [
        c[-1] for c in fake.calls if any(a.startswith("--junitxml=") for a in c)
    ]
    assert all("test_broken" not in t for t in run_targets)
    assert len(run_targets) == 4
    junit_names = sorted(p.name for p in (tree.out / "junit").iterdir())
    # Index follows sorted discovery order (DMAIC_V3/... before integration/...);
    # the collection-error file (index 0) and the no-XML file (index 2) leave gaps.
    assert junit_names == [
        "001-test_green.xml",
        "003-test_blocked.xml",
        "004-test_redrc.xml",
    ]


def test_main_without_sha_records_withheld_and_github_sha_is_used(monkeypatch, tree):
    _touch(tree.dmaic / "test_a.py")
    _install(monkeypatch, FakeProcs({"test_a": {"junit": '<testcase name="x"/>'}}))
    census.main(_argv(tree))
    assert _read_report(tree)["exact_sha"] == "WITHHELD"

    monkeypatch.setenv("GITHUB_SHA", "b" * 40)
    census.main(_argv(tree))
    assert _read_report(tree)["exact_sha"] == "b" * 40


def test_main_explicit_roots_and_empty_population(monkeypatch, tree, tmp_path):
    fake = FakeProcs({}, coverage_payload=None, coverage_rc=1)
    _install(monkeypatch, fake)
    census.main(_argv(tree, "--roots", str(tmp_path / "no_such_root")))
    report = _read_report(tree)
    assert report["rows"] == []
    assert report["test_file_count"] == 0
    assert report["coverage_export_returncode"] == 1
    # only erase + json export were executed
    assert [c[3] for c in fake.calls] == ["erase", "json"]


def test_main_is_idempotent_on_repeat(monkeypatch, tree):
    _touch(tree.dmaic / "test_a.py")
    _touch(tree.dmaic / "test_b.py")
    plans = {"test_a": {"junit": '<testcase name="x"/>'}, "test_b": {"junit": _skip()}}
    _install(monkeypatch, FakeProcs(plans))
    census.main(_argv(tree, "--exact-sha", "c" * 40))
    first = (tree.out / "report" / "census.json").read_bytes()
    census.main(_argv(tree, "--exact-sha", "c" * 40))
    second = (tree.out / "report" / "census.json").read_bytes()
    assert first == second
    rows = json.loads(first)["rows"]
    assert [r["test_state"] for r in rows] == ["TEST_GREEN", "TEST_EXISTS_UNCOLLECTED"]


def test_main_malformed_junit_aborts_without_report(monkeypatch, tree):
    _touch(tree.dmaic / "test_a.py")

    class Corrupting(FakeProcs):
        def run(self, args, **kwargs):
            result = super().run(args, **kwargs)
            for a in args:
                if a.startswith("--junitxml="):
                    Path(a.split("=", 1)[1]).write_text(
                        "<testsuites><broken", encoding="utf-8"
                    )
            return result

    _install(monkeypatch, Corrupting({"test_a": {"junit": None}}))
    with pytest.raises(ET.ParseError):
        census.main(_argv(tree))
    assert not (tree.out / "report" / "census.json").exists()


# Finding F3 (a stale JUnit left in --junit-dir was trusted as current evidence)
# is fixed in PR #2391.  Its stale-evidence assertions live there
# (tests/test_f3_census_stale_junit.py), so this wave pins neither behaviour
# and merges in either order.


def test_main_requires_mandatory_arguments(capsys):
    with pytest.raises(SystemExit) as exc:
        census.main(["--out", "x.json"])
    assert exc.value.code == 2
    assert "required" in capsys.readouterr().err
