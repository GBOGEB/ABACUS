"""Lane-B wave 7: everred_v3 spine_census coverage, LDAB and pulse telemetry."""

import copy

import pytest

from ._l2_loader import load

sc = load("tools/everred_v3/src/spine_census.py")

A, B = "a" * 40, "b" * 40
REPO = "GBOGEB/ABACUS"


def _identity(sha=A, **overrides):
    identity = {
        "repository": REPO,
        "sha": sha,
        "run_id": 11,
        "artifact_id": 12,
        "artifact_sha256": "1" * 64,
        "workflow_sha256": "2" * 64,
        "config_sha256": "3" * 64,
    }
    identity.update(overrides)
    return identity


def _module(statements=10, missing=2, branches=4, missing_branches=1):
    return {
        "summary": {
            "num_statements": statements,
            "missing_lines": missing,
            "num_branches": branches,
            "missing_branches": missing_branches,
        }
    }


def _raw(files=None):
    return {
        "meta": {"version": "7.13.3"},
        "files": files or {"src/a.py": _module(), "./src/b.py": _module(5, 0, 0, 0)},
    }


def _receipt(sha=A, **overrides):
    receipt = {
        "schema": "bandit.coverage.receipt.v1",
        "exact_head_sha": sha,
        "producer_run_id": "11",
        "tests": 3,
        "failures": 0,
        "errors": 0,
        "source_scope": ["src/a.py", "src/b.py"],
        "selected_modules_totals": {
            "covered_lines": 13,
            "eligible_lines": 15,
            "covered_branches": 3,
            "eligible_branches": 4,
        },
    }
    receipt.update(overrides)
    return receipt


def _snapshot(sha=A, raw=None, receipt=None, **identity):
    return sc.coverage_snapshot(
        raw or _raw(), receipt or _receipt(sha), _identity(sha, **identity)
    )


# --- helpers / coverage_snapshot ---------------------------------------------------------------


def test_primitives():
    assert sc.integer(0) and not sc.integer(-1) and not sc.integer(True)
    assert sc.percentage(1, 3) == 33.3333 and sc.percentage(0, 0) is None
    sc.require(True, "unused")
    with pytest.raises(ValueError, match="why"):
        sc.require(False, "why")


def test_coverage_snapshot_totals():
    snap = _snapshot()
    assert snap["totals"] == {
        "statements": {"covered": 13, "eligible": 15},
        "branches": {"covered": 3, "eligible": 4},
    }
    assert [m["path"] for m in snap["modules"]] == ["src/a.py", "src/b.py"]
    assert snap["tool_version"] == "7.13.3" and snap["tests_executed"] == 3
    assert snap["state"] == "MEASURED_SOURCE_BOUND_NOT_ADMISSION"


@pytest.mark.parametrize(
    "identity,message",
    [
        ("x", "invalid source identity"),
        (_identity(repository=None), "missing repository"),
        (_identity(repository=""), "empty repository"),
        (_identity(sha="short"), "missing exact SHA"),
        (_identity(run_id=0), "missing native run"),
        (_identity(artifact_id=-1), "missing artifact ID"),
        (_identity(config_sha256="x"), "invalid identity: config_sha256"),
    ],
)
def test_identity_rejections(identity, message):
    with pytest.raises(ValueError, match=message):
        sc.coverage_snapshot(_raw(), _receipt(), identity)


@pytest.mark.parametrize(
    "raw,receipt,message",
    [
        (None, "x", "coverage receipt must be an object"),
        (None, _receipt(schema="v0"), "unrecognized coverage contract"),
        (None, _receipt(exact_head_sha=B), "coverage head differs"),
        (None, _receipt(producer_run_id=99), "coverage run mismatch"),
        (None, _receipt(tests=None), "JUnit counters missing"),
        (None, _receipt(failures=1), "failing or empty JUnit"),
        (None, _receipt(tests=0), "failing or empty JUnit"),
        (None, _receipt(source_scope=[]), "missing coverage source scope"),
        (None, _receipt(source_scope=["/abs.py"]), "unsafe source scope"),
        (None, _receipt(source_scope=["a/../b.py"]), "unsafe source scope"),
        (None, _receipt(source_scope=["src/b.py", "src/a.py"]), "not canonical"),
        ({"files": {}}, None, "missing Coverage.py files or metadata"),
        ({"files": {}, "meta": {"version": ""}}, None, "missing instrumentor version"),
        ({"files": {1: {}}, "meta": {"version": "7"}}, None, "invalid coverage path"),
        (
            {
                "files": {"src/a.py": _module(), "./src/a.py": _module()},
                "meta": {"version": "7"},
            },
            None,
            "duplicate normalized coverage path",
        ),
        (_raw({"src/a.py": _module()}), None, "source-matched module absent"),
        (_raw({"src/a.py": "x", "src/b.py": _module()}), None, "invalid coverage file"),
        (
            _raw({"src/a.py": {}, "src/b.py": _module()}),
            None,
            "missing module coverage summary",
        ),
        (
            _raw({"src/a.py": _module(missing=-1), "src/b.py": _module()}),
            None,
            "invalid module coverage counts",
        ),
        (
            _raw({"src/a.py": _module(0, 0), "src/b.py": _module()}),
            None,
            "invalid eligible statements",
        ),
        (
            _raw({"src/a.py": _module(missing_branches=9), "src/b.py": _module()}),
            None,
            "invalid eligible branches",
        ),
        (None, _receipt(selected_modules_totals=None), "missing producer totals"),
        (
            None,
            _receipt(
                selected_modules_totals=dict(
                    _receipt()["selected_modules_totals"], covered_lines=1
                )
            ),
            "producer totals conflict",
        ),
    ],
)
def test_coverage_snapshot_rejections(raw, receipt, message):
    with pytest.raises(ValueError, match=message):
        sc.coverage_snapshot(
            _raw() if raw is None else raw,
            _receipt() if receipt is None else receipt,
            _identity(),
        )


def test_coverage_snapshot_accepts_windows_paths():
    files = {"src" + chr(92) + "a.py": _module(), "src/b.py": _module(5, 0, 0, 0)}
    assert _snapshot(raw=_raw(files))["totals"]["statements"]["eligible"] == 15


# --- compare_coverage --------------------------------------------------------------------------


def _with_totals(snap, stmts, branches):
    snap = copy.deepcopy(snap)
    snap["totals"] = {"statements": stmts, "branches": branches}
    return snap


def test_compare_coverage_statuses():
    before = _snapshot()
    same = sc.compare_coverage(before, copy.deepcopy(before))
    assert same["status"] == "SAME_SOURCE_METRIC_RECONFIRMED"
    assert same["families"]["statements"]["additional_covered_for_goal"] == 1
    drift = _with_totals(
        before, {"covered": 14, "eligible": 15}, {"covered": 3, "eligible": 4}
    )
    assert sc.compare_coverage(before, drift)["status"] == "SAME_SOURCE_METRIC_DRIFT"
    after = _snapshot(B, receipt=_receipt(B))
    grown = _with_totals(
        after, {"covered": 20, "eligible": 20}, {"covered": 0, "eligible": 0}
    )
    delta = sc.compare_coverage(before, grown, goal_pct=95)
    assert delta["status"] == "SOURCE_DENOMINATOR_EVOLVED"
    stmts, branches = delta["families"]["statements"], delta["families"]["branches"]
    assert (
        stmts["eligible_net_delta"],
        stmts["covered_net_delta"],
        stmts["uncovered_net_delta"],
    ) == (5, 7, -2)
    assert stmts["delta_percentage_points"] == round(100 - 100 * 13 / 15, 4)
    assert stmts["additional_covered_for_goal"] == 0
    assert branches["after_pct"] is None and branches["delta_percentage_points"] is None
    assert branches["additional_covered_for_goal"] is None
    steady = sc.compare_coverage(before, after)
    assert steady["status"] == "SOURCE_DENOMINATOR_UNCHANGED"
    other_config = _snapshot(B, receipt=_receipt(B), config_sha256="9" * 64)
    assert (
        sc.compare_coverage(before, other_config)["status"]
        == "PROFILE_CHANGED_DESCRIPTIVE_ONLY"
    )


def test_compare_coverage_rejections():
    good = _snapshot()
    with pytest.raises(ValueError, match="invalid coverage snapshot"):
        sc.compare_coverage({}, good)
    with pytest.raises(ValueError, match="invalid coverage goal"):
        sc.compare_coverage(good, good, goal_pct=0)
    foreign = copy.deepcopy(good)
    foreign["source"]["repository"] = "GBOGEB/CODEX"
    with pytest.raises(ValueError, match="cross-repository coverage"):
        sc.compare_coverage(good, foreign)
    broken = _with_totals(
        good, {"covered": 9, "eligible": 1}, {"covered": 0, "eligible": 0}
    )
    with pytest.raises(ValueError, match="invalid coverage family totals"):
        sc.compare_coverage(good, broken)


# --- ldab_snapshot --------------------------------------------------------------------------------


def _ldab(**overrides):
    report = {
        "repository": REPO,
        "head_sha": A,
        "verification": "PASS",
        "ldab_telemetry": {
            "schema": "mip.ldab.telemetry.v1",
            "source_sha": A,
            "repository": REPO,
            "source_census": {
                "root": {
                    "candidate_file_count": 4,
                    "inventory_complete": True,
                    "evidence_level": "SOURCE_DISCOVERY_ONLY",
                },
                "nested": {"candidate_file_count": 2},
            },
            "runtime": {},
        },
    }
    report.update(overrides)
    return report


def test_ldab_snapshot():
    snap = sc.ldab_snapshot(_ldab(), REPO, A, artifact_sha256="f" * 64)
    assert (snap["root_candidate_files"], snap["nested_candidate_files"]) == (4, 2)
    assert snap["state"] == "SOURCE_DISCOVERY_VERIFIED_RUNTIME_UNKNOWN"
    flat = _ldab()
    del flat["ldab_telemetry"]["source_census"]["nested"]
    assert (
        sc.ldab_snapshot(flat, REPO, A, artifact_sha256="f" * 64)[
            "nested_candidate_files"
        ]
        is None
    )


def _ldab_mutation(path, value):
    report = _ldab()
    target = report
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    return report


@pytest.mark.parametrize(
    "report,digest,message",
    [
        ("x", "f" * 64, "must be an object"),
        (_ldab(), "short", "missing LDAB artifact hash"),
        (_ldab(ldab_telemetry={"schema": "x"}), "f" * 64, "unrecognized LDAB producer"),
        (_ldab(head_sha=B), "f" * 64, "stale or mismatched"),
        (_ldab(verification="FAIL"), "f" * 64, "producer not verified"),
        (
            _ldab_mutation(("ldab_telemetry", "runtime"), None),
            "f" * 64,
            "LDAB surfaces missing",
        ),
        (
            _ldab_mutation(
                ("ldab_telemetry", "source_census", "root", "inventory_complete"), False
            ),
            "f" * 64,
            "invalid root LDAB discovery census",
        ),
        (
            _ldab_mutation(("ldab_telemetry", "runtime", "ldab_verified_repairs"), 3),
            "f" * 64,
            "cannot claim runtime proof",
        ),
    ],
)
def test_ldab_rejections(report, digest, message):
    with pytest.raises(ValueError, match=message):
        sc.ldab_snapshot(report, REPO, A, artifact_sha256=digest)


# --- pulse fingerprints and comparison -------------------------------------------------------------


def _pulse(main=A, conclusion="success", run=1, coverage=None):
    return {
        "schema": sc.SCHEMA,
        "repository": REPO,
        "main_sha": main,
        "active_heads": [main],
        "inventory_complete": True,
        "observed_at": "2026-10-27T00:00:0%dZ" % run,
        "observations": [
            {"id": run, "kind": "note", "text": "hello"},
            {
                "pr_number": 7,
                "source_sha": main,
                "ci": {
                    "current_window_complete": True,
                    "matched_runs": [
                        {
                            "name": "CI",
                            "event": "push",
                            "status": "completed",
                            "conclusion": conclusion,
                            "id": run,
                        },
                        {
                            "name": "CI",
                            "event": "push",
                            "status": "completed",
                            "conclusion": "failure",
                        },
                        {"name": "EVERRED V3 Governed Control Plane", "id": run},
                    ],
                },
                "producers": {
                    "coverage": coverage,
                    "ldab": sc.ldab_snapshot(
                        _ldab(), REPO, A, artifact_sha256="f" * 64
                    ),
                },
            },
        ],
    }


def test_material_state_strips_volatile_ids():
    first = _pulse(run=1, coverage=_snapshot())
    second = _pulse(
        run=2, coverage=_snapshot(run_id=99, receipt=_receipt(producer_run_id=99))
    )
    assert sc.state_fingerprint(first) == sc.state_fingerprint(second)
    assert sc.receipt_fingerprint(first) != sc.receipt_fingerprint(second)
    material = sc._material_state(first)
    obs = material["observations"]
    assert obs[0] == {"kind": "note", "text": "hello"}
    assert obs[1]["ci"]["workflow_states"] == [
        {
            "workflow": "CI",
            "event": "push",
            "status": "completed",
            "conclusion": "success",
        }
    ]
    assert obs[1]["coverage"]["totals"]["statements"]["eligible"] == 15
    assert obs[1]["ldab"]["root_candidate_files"] == 4


def test_material_producer_fallbacks():
    assert sc._material_producer(None) == {"state": "UNKNOWN_PRODUCER"}
    assert sc._material_producer(
        {"state": "BLOCKED", "source_sha": A, "reason": "r", "id": 5}
    ) == {
        "state": "BLOCKED",
        "source_sha": A,
        "reason": "r",
    }
    bare = sc._material_producer({"state": "MEASURED_SOURCE_BOUND_NOT_ADMISSION"})
    assert bare["source_sha"] is None and bare["totals"] is None


@pytest.mark.parametrize(
    "census,message",
    [
        ("x", "invalid workflow census"),
        ({"matched_runs": None}, "native run window missing"),
        ({"matched_runs": ["x"]}, "invalid native workflow record"),
        ({"matched_runs": [{"name": ""}]}, "missing workflow identity"),
        ({"matched_runs": [{"name": "CI", "event": None}]}, "missing workflow event"),
    ],
)
def test_material_ci_rejections(census, message):
    with pytest.raises(ValueError, match=message):
        sc._material_ci(census)


def test_material_state_rejections():
    with pytest.raises(ValueError, match="invalid spine snapshot"):
        sc._material_state({"schema": "x"})
    with pytest.raises(ValueError, match="observations must be a list"):
        sc._material_state({"schema": sc.SCHEMA, "observations": {}})
    with pytest.raises(ValueError, match="invalid observation"):
        sc._material_state({"schema": sc.SCHEMA, "observations": ["x"]})
    bad_producers = {
        "schema": sc.SCHEMA,
        "observations": [{"ci": {"matched_runs": []}, "producers": []}],
    }
    with pytest.raises(ValueError, match="invalid producer observations"):
        sc._material_state(bad_producers)
    with pytest.raises(ValueError, match="invalid receipt input"):
        sc.receipt_fingerprint([])


def test_compare_pulses_states():
    base = _pulse()
    stable = sc.compare_pulses(base, _pulse(run=2))
    assert stable["state"] == "N_PLUS_1_EQUALS_N_OBSERVED_STATE"
    assert (
        stable["new_evidence_receipts"] is True
        and stable["material_state_changed"] is False
    )
    changed = sc.compare_pulses(base, _pulse(conclusion="failure"))
    assert changed["state"] == "SAME_HEADS_EVIDENCE_CHANGED"
    moved = sc.compare_pulses(base, _pulse(main=B))
    assert (
        moved["state"] == "SOURCE_REVISION_OR_PR_SET_CHANGED"
        and moved["source_heads_identical"] is False
    )
    assert moved["merge_authorized"] is False


def test_compare_pulses_rejections():
    good = _pulse()
    with pytest.raises(ValueError, match="invalid previous spine"):
        sc.compare_pulses({}, good)
    with pytest.raises(ValueError, match="invalid current spine"):
        sc.compare_pulses(good, {})
    with pytest.raises(ValueError, match="spine repository mismatch"):
        sc.compare_pulses(good, dict(good, repository="GBOGEB/CODEX"))
    with pytest.raises(ValueError, match="incomplete inventory"):
        sc.compare_pulses(good, dict(good, inventory_complete=False))
