"""Lane A wave 13: mission_control_lite.coverage_pulse build/compare/render/CLI."""

import copy
import json
import sys

import pytest

from mission_control_lite import coverage_pulse as cp

SHA = "a" * 40
EVENT = "b" * 40
NAMES = ("core.py", "policy.py", "rex.py", "cli.py", "recovery_triage.py")
FAMILIES = ("positive", "negative", "reverse", "force_trip")


def _summary(cl=5, ns=10, cb=1, nb=2):
    return {
        "covered_lines": cl,
        "num_statements": ns,
        "covered_branches": cb,
        "num_branches": nb,
    }


def _report(extra=None):
    files = {"mission_control_lite/" + n: {"summary": _summary()} for n in NAMES}
    files.update(extra or {})
    totals = {
        k: sum(f["summary"][k] for f in files.values())
        for k in ("covered_lines", "num_statements", "covered_branches", "num_branches")
    }
    return {"meta": {"version": "7.6.1"}, "files": files, "totals": totals}


def _log(ids):
    lines = [method + " (" + qualified + ") ... ok" for method, qualified in ids]
    lines += ["", "Ran " + str(len(ids)) + " tests in 0.01s", "", "OK", ""]
    return "\n".join(lines)


def _family_log():
    ids = []
    for fam in FAMILIES:
        for i in range(4):
            method = "test_" + fam + "_case" + str(i)
            ids.append((method, "pkg.mod.Fam." + method))
    return _log(ids)


def _logs():
    return {
        "core": _log([("test_a", "t.C.test_a"), ("test_b", "t.C.test_b")]),
        "rex": _log([("test_a", "t.C.test_a")]),
    }


def test_counts_validation():
    with pytest.raises(ValueError, match="missing coverage totals"):
        cp._counts(None)
    with pytest.raises(ValueError, match="invalid coverage covered_lines"):
        cp._counts(dict(_summary(), covered_lines=True))
    with pytest.raises(ValueError, match="line denominator"):
        cp._counts(_summary(cl=0, ns=0, cb=0, nb=0))
    with pytest.raises(ValueError, match="empty module branch"):
        cp._counts(_summary(cl=0, ns=0, cb=0, nb=1), allow_empty=True)
    with pytest.raises(ValueError, match="branch denominator"):
        cp._counts(_summary(cb=3))
    assert cp._percent(1, 0) is None
    assert cp._percent(1, 3) == 33.3333


def test_build_input_guards():
    rep = _report()
    with pytest.raises(ValueError, match="executed source SHA"):
        cp.build(rep, _logs(), "x", EVENT, 1)
    with pytest.raises(ValueError, match="event SHA"):
        cp.build(rep, _logs(), SHA, None, 1)
    with pytest.raises(ValueError, match="run ID"):
        cp.build(rep, _logs(), SHA, EVENT, "r1")
    with pytest.raises(ValueError, match="metadata"):
        cp.build({}, _logs(), SHA, EVENT, 1)
    with pytest.raises(ValueError, match="files/version"):
        cp.build({"meta": {"version": ""}, "files": {}}, _logs(), SHA, EVENT, 1)
    bad = _report({"other/x.py": {"summary": _summary()}})
    with pytest.raises(ValueError, match="scope invalid"):
        cp.build(bad, _logs(), SHA, EVENT, 1)
    partial = _report()
    del partial["files"]["mission_control_lite/cli.py"]
    with pytest.raises(ValueError, match="incomplete"):
        cp.build(partial, _logs(), SHA, EVENT, 1)


def test_build_log_guards():
    rep = _report()
    with pytest.raises(ValueError, match="test logs missing"):
        cp.build(rep, {}, SHA, EVENT, 1)
    with pytest.raises(ValueError, match="native passing"):
        cp.build(rep, {"x": "Ran 1 test in 0s\nFAILED\n"}, SHA, EVENT, 1)
    with pytest.raises(ValueError, match="empty test suite"):
        cp.build(rep, {"x": "Ran 0 tests in 0s\nOK\n"}, SHA, EVENT, 1)
    short = "test_a (t.C.test_a) ... ok\nRan 2 tests in 0s\nOK\n"
    with pytest.raises(ValueError, match="case identity count"):
        cp.build(rep, {"x": short}, SHA, EVENT, 1)
    wrong = "test_a (t.C.test_b) ... ok\nRan 1 test in 0s\nOK\n"
    with pytest.raises(ValueError, match="malformed case identity"):
        cp.build(rep, {"x": wrong}, SHA, EVENT, 1)
    forged = _report()
    forged["totals"]["covered_lines"] -= 1
    with pytest.raises(ValueError, match="disagree"):
        cp.build(forged, _logs(), SHA, EVENT, 1)


def test_build_complete_ids_backlog_and_family():
    logs = _logs()
    logs["adversarial_family"] = _family_log()
    extra = {"mission_control_lite/empty.py": {"summary": _summary(0, 0, 0, 0)}}
    pulse = cp.build(_report(extra), logs, SHA, EVENT, 7)
    assert pulse["test_id_status"] == "COMPLETE"
    assert pulse["tests_passed"] == 19
    assert pulse["unique_test_cases"] == 18
    assert pulse["duplicate_case_executions"] == 1
    assert pulse["per_file"]["mission_control_lite/empty.py"]["line_percent"] is None
    assert pulse["coverage_backlog"][-1]["path"] == "mission_control_lite/empty.py"
    assert pulse["adversarial_test_family"]["families_represented"] == 4
    assert pulse["comparison"]["status"] == "UNKNOWN"
    assert "execution_phases" not in pulse


def test_build_summary_only_and_phases():
    logs = {"core": "Ran 3 tests in 0.1s\nOK\n"}
    phases = [
        {"phase": "a", "duration_seconds": 1.5, "exit_code": 0},
        {"phase": "b", "duration_seconds": 1, "exit_code": 0},
    ]
    pulse = cp.build(_report(), logs, SHA, EVENT, "9", phases=phases)
    assert pulse["test_id_status"] == "SUMMARY_ONLY"
    assert pulse["unique_test_cases"] is None
    assert pulse["test_case_id_sha256"] is None
    assert pulse["timed_execution_seconds"] == 2.5
    assert pulse["tests_per_timed_second"] == 1.2
    zero = [{"phase": "z", "duration_seconds": 0, "exit_code": 0}]
    pulse = cp.build(_report(), logs, SHA, EVENT, "9", phases=zero)
    assert pulse["tests_per_timed_second"] is None


@pytest.mark.parametrize(
    "phases,match",
    [
        ([], "missing native phase"),
        ("x", "missing native phase"),
        (["x"], "invalid native phase record"),
        ([{"phase": "", "duration_seconds": 1, "exit_code": 0}], "duplicate or"),
        (
            [
                {"phase": "a", "duration_seconds": 1, "exit_code": 0},
                {"phase": "a", "duration_seconds": 1, "exit_code": 0},
            ],
            "duplicate or",
        ),
        ([{"phase": "a", "duration_seconds": True, "exit_code": 0}], "failed"),
        ([{"phase": "a", "duration_seconds": -1, "exit_code": 0}], "failed"),
        ([{"phase": "a", "duration_seconds": 1, "exit_code": 1}], "failed"),
    ],
)
def test_build_phase_guards(phases, match):
    with pytest.raises(ValueError, match=match):
        cp.build(_report(), _logs(), SHA, EVENT, 1, phases=phases)


def test_compare_paths():
    base = cp.build(_report(), _logs(), SHA, EVENT, 1)
    with pytest.raises(ValueError, match="baseline schema"):
        cp.compare({"schema": "x"}, base)
    other = dict(base, scope_id="different")
    assert cp.compare(other, base)["status"] == "INCOMPARABLE"
    rep = _report()
    rep["files"]["mission_control_lite/core.py"]["summary"]["num_statements"] = 11
    rep["totals"]["num_statements"] += 1
    grown = cp.build(rep, _logs(), "c" * 40, EVENT, 2)
    assert cp.compare(base, grown)["reason"] == "coverage denominator changed"

    rep = _report()
    rep["files"]["mission_control_lite/core.py"]["summary"]["covered_lines"] = 9
    rep["totals"]["covered_lines"] += 4
    logs = _logs()
    logs["rex"] = _log([("test_a", "t.C.test_a"), ("test_n", "t.C.test_n")])
    newer = cp.build(rep, logs, "c" * 40, EVENT, 2, previous=base)
    comp = newer["comparison"]
    assert comp["status"] == "COMPARABLE"
    assert comp["new_unique_case_ids"] == 1
    assert comp["new_covered_lines"] == 4
    assert comp["test_delta"] == 1
    assert comp["line_delta_pp"] > 0

    logs["extra"] = "Ran 1 test in 0s\nOK\n"
    changed = cp.build(rep, logs, "c" * 40, EVENT, 3, previous=base)
    comp = changed["comparison"]
    assert comp["test_census_status"] == "INCOMPARABLE_SUITE_POPULATION"
    assert comp["new_unique_case_ids"] is None
    assert comp["test_delta"] is None


def test_compare_zero_branch_denominator_gives_none_delta():
    files = {
        "mission_control_lite/" + n: {"summary": _summary(nb=0, cb=0)} for n in NAMES
    }
    totals = _summary(cl=25, ns=50, cb=0, nb=0)
    rep = {"meta": {"version": "v"}, "files": files, "totals": totals}
    base = cp.build(rep, _logs(), SHA, EVENT, 1)
    nxt = cp.build(copy.deepcopy(rep), _logs(), SHA, EVENT, 2, previous=base)
    assert nxt["comparison"]["branch_delta_pp"] is None


def test_render_summary_full_and_unknown():
    logs = _logs()
    logs["adversarial_family"] = _family_log()
    phases = [{"phase": "unit", "duration_seconds": 2, "exit_code": 0}]
    pulse = cp.build(_report(), logs, SHA, EVENT, 5, phases=phases)
    text = cp.render_summary(pulse)
    assert "| Adversarial family reach | 4/4 |" in text
    assert "| unit | 2 | 0 |" in text
    assert "| force_trip | 4 |" in text
    assert "| Line delta | UNKNOWN |" in text
    plain = cp.build(_report(), {"core": "Ran 1 test in 0s\nOK\n"}, SHA, EVENT, 5)
    text = cp.render_summary(plain)
    assert "| Adversarial family reach | UNKNOWN |" in text
    assert "| Unique case IDs | UNKNOWN |" in text
    assert "Native adversarial" not in text


def _write_inputs(tmp_path, report=None, family=True):
    paths = {}
    content = {
        "cov": json.dumps(report or _report()),
        "core": _log([("test_a", "t.C.test_a")]),
        "rex": _log([("test_b", "t.C.test_b")]),
        "metrics": _log([("test_c", "t.C.test_c")]),
        "telemetry": _log([("test_d", "t.C.test_d")]),
        "timing": _log([("test_e", "t.C.test_e")]),
        "recovery": _log([("test_f", "t.C.test_f")]),
        "runner": _log([("test_g", "t.C.test_g")]),
        "gate": _log([("test_h", "t.C.test_h")]),
        "jfr": _log([("test_i", "t.C.test_i")]),
        "family": _family_log(),
        "phases": json.dumps([{"phase": "p", "duration_seconds": 1, "exit_code": 0}]),
    }
    for key, text in content.items():
        paths[key] = tmp_path / (key + ".txt")
        paths[key].write_text(text, encoding="utf-8")
    return paths


def _base_args(paths, out):
    return [
        "cp",
        "--coverage-json",
        str(paths["cov"]),
        "--core-log",
        str(paths["core"]),
        "--rex-log",
        str(paths["rex"]),
        "--metrics-log",
        str(paths["metrics"]),
        "--telemetry-tests-log",
        str(paths["telemetry"]),
        "--source-sha",
        SHA,
        "--event-sha",
        EVENT,
        "--run-id",
        "11",
        "--output",
        str(out),
    ]


def _full_args(paths, out, summary, baseline):
    return _base_args(paths, out) + [
        "--timing-log",
        str(paths["phases"]),
        "--timing-tests-log",
        str(paths["timing"]),
        "--recovery-tests-log",
        str(paths["recovery"]),
        "--runner-wait-tests-log",
        str(paths["runner"]),
        "--adversarial-family-tests-log",
        str(paths["family"]),
        "--gate-census-tests-log",
        str(paths["gate"]),
        "--job-first-red-tests-log",
        str(paths["jfr"]),
        "--require-case-ids",
        "--require-adversarial-family",
        "--require-penetration-suites",
        "--baseline",
        str(baseline),
        "--summary",
        str(summary),
    ]


def test_main_full_options(tmp_path, monkeypatch, capsys):
    extra = {"mission_control_lite/runner_wait.py": {"summary": _summary()}}
    paths = _write_inputs(tmp_path, report=_report(extra))
    out = tmp_path / "pulse.json"
    summary = tmp_path / "summary.md"
    baseline = tmp_path / "baseline.json"
    monkeypatch.setattr(sys, "argv", _base_args(paths, baseline))
    cp.main()
    capsys.readouterr()
    monkeypatch.setattr(sys, "argv", _full_args(paths, out, summary, baseline))
    cp.main()
    printed = json.loads(capsys.readouterr().out)
    assert printed["comparison"] == "COMPARABLE"
    pulse = json.loads(out.read_text(encoding="utf-8"))
    assert set(pulse["tests_by_suite"]) >= {"gate_census", "job_first_red"}
    assert "Mission Control Lite" in summary.read_text(encoding="utf-8")


def _expect_parser_error(monkeypatch, capsys, argv, match):
    monkeypatch.setattr(sys, "argv", argv)
    with pytest.raises(SystemExit) as exc:
        cp.main()
    assert exc.value.code == 2
    assert match in capsys.readouterr().err


def test_main_parser_errors(tmp_path, monkeypatch, capsys):
    paths = _write_inputs(tmp_path)
    out = tmp_path / "pulse.json"
    base = _base_args(paths, out)
    _expect_parser_error(
        monkeypatch, capsys, base + ["--require-penetration-suites"], "penetration"
    )
    summary_only = tmp_path / "summary_only.txt"
    summary_only.write_text("Ran 1 test in 0s\nOK\n", encoding="utf-8")
    argv = list(base)
    argv[argv.index(str(paths["core"]))] = str(summary_only)
    _expect_parser_error(
        monkeypatch, capsys, argv + ["--require-case-ids"], "case identities"
    )
    _expect_parser_error(
        monkeypatch,
        capsys,
        base + ["--require-adversarial-family"],
        "adversarial family census missing",
    )
    dup = tmp_path / "dup.txt"
    dup.write_text(_log([("test_a", "t.C.test_a")]), encoding="utf-8")
    argv = list(base)
    argv[argv.index(str(paths["rex"]))] = str(dup)
    argv += ["--adversarial-family-tests-log", str(paths["family"])]
    _expect_parser_error(
        monkeypatch, capsys, argv + ["--require-adversarial-family"], "replayed"
    )
    pen = base + [
        "--recovery-tests-log",
        str(paths["recovery"]),
        "--runner-wait-tests-log",
        str(paths["runner"]),
        "--require-penetration-suites",
    ]
    _expect_parser_error(monkeypatch, capsys, pen, "unpenetrated measured source")
    assert not out.exists()
