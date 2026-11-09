"""Lane-B wave 3: tools/handover_v2 tuple_lineage and wave_telemetry."""

import copy
import json
import sys

import pytest

from ._l2_loader import REPO_ROOT, load

tl = load("tools/handover_v2/tuple_lineage.py")
wt = load("tools/handover_v2/wave_telemetry.py")

FOLDER = REPO_ROOT / "handover" / "mip_20261015"
HEAD = "a" * 40
OTHER = "b" * 40
DIGEST = "c" * 64


# --- tuple_lineage.check ------------------------------------------------------


def _real():
    ledger = json.loads((FOLDER / "CHAT_TUPLE_LEDGER_v1.json").read_bytes())
    narrative = b"golden thread narrative\n"
    return ledger, narrative


def _seal(ledger, narrative, **manifest_overrides):
    """Recompute the tuple chain and manifest so only the intended defect remains."""
    prev = "GENESIS:" + ledger["parent"]["head_at_last_readback"]
    for row in ledger["tuples"]:
        fields = {k: v for k, v in row.items() if k != "cumulative_sha256"}
        digest = tl.h(json.dumps(fields, sort_keys=True).encode("utf-8"))
        prev = tl.h((prev + "|" + digest).encode("utf-8"))
        row["cumulative_sha256"] = prev
    ledger_bytes = json.dumps(ledger).encode("utf-8")
    manifest = {
        "files": {
            "CHAT_TUPLE_LEDGER.json": tl.h(ledger_bytes),
            "GOLDEN_THREAD.md": tl.h(narrative),
        },
        "tuple_chain_tip_sha256": prev,
        "certification": "SEMANTIC_ONLY",
        "tuple_count": len(ledger["tuples"]),
        "todo_count": len(ledger["todo_records"]),
    }
    manifest.update(manifest_overrides)
    return ledger_bytes, narrative, json.dumps(manifest).encode("utf-8")


def test_check_real_capsule_and_resealed_copy():
    result = tl.check(
        (FOLDER / "CHAT_TUPLE_LEDGER_v1.json").read_bytes(),
        (FOLDER / "GOLDEN_THREAD_TUPLES_v1.md").read_bytes(),
        (FOLDER / "TUPLE_MANIFEST_v1.json").read_bytes(),
    )
    assert result["result"] == "PASS" and result["fidelity"] == "SEMANTIC_ONLY"
    ledger, narrative = _real()
    resealed = tl.check(*_seal(ledger, narrative))
    assert (resealed["tuples"], resealed["todos"]) == (
        result["tuples"],
        result["todos"],
    )
    assert resealed["chain_tip"] == result["chain_tip"]


def _mutate_tuple(ledger, key, value):
    ledger["tuples"][0][key] = value


def _mutate_todo(ledger, key, value):
    ledger["todo_records"][0][key] = value


@pytest.mark.parametrize(
    "mutate,message",
    [
        (lambda s: s.update(fidelity="VERBATIM"), "Unproven verbatim fidelity"),
        (lambda s: s.update(session_lossless_certified=True), "Unproven verbatim"),
        (lambda s: s["parent"].update(pr=1), "Canonical V2 parent changed"),
        (lambda s: s.update(tuples=[]), "Missing or duplicate tuple/TODO"),
        (lambda s: s["todo_records"].append(dict(s["todo_records"][0])), "duplicate"),
        (
            lambda s: s["parent"].update(head_at_last_readback="abc"),
            "Unpinned ancestor",
        ),
        (lambda s: _mutate_tuple(s, "id", "T99"), "Unverifiable tuple promoted"),
        (lambda s: _mutate_tuple(s, "raw_user_sha256", "x"), "Unverifiable tuple"),
        (lambda s: _mutate_tuple(s, "status", "VERBATIM"), "Unverifiable tuple"),
        (lambda s: _mutate_todo(s, "source_tuple_ids", []), "Orphan TODO"),
        (lambda s: _mutate_todo(s, "source_tuple_ids", ["T77"]), "Orphan TODO"),
        (
            lambda s: _mutate_todo(s, "operational_root_credit", "GRANTED"),
            "Orphan TODO",
        ),
        (lambda s: _mutate_todo(s, "state", "DONE"), "Invalid TODO disposition"),
        (lambda s: s.update(crew_launch_count=3), "UNKNOWN promoted to numeric"),
        (lambda s: s["coverage_reference"][0].update(n=1), "lacks source-bound"),
    ],
)
def test_check_rejects_defects(mutate, message):
    ledger, narrative = _real()
    mutate(ledger)
    with pytest.raises(ValueError, match=message):
        tl.check(*_seal(ledger, narrative))


def test_check_rejects_manifest_defects():
    ledger, narrative = _real()
    sealed = _seal(copy.deepcopy(ledger), narrative)
    with pytest.raises(ValueError, match="Manifest byte mismatch: GOLDEN_THREAD.md"):
        tl.check(sealed[0], b"tampered", sealed[2])
    for overrides, message in [
        ({"tuple_chain_tip_sha256": "0" * 64}, "chain-tip mismatch"),
        ({"todo_count": 0}, "Census/manifest mismatch"),
        ({"certification": "LOSSLESS"}, "Unsupported completeness"),
    ]:
        with pytest.raises(ValueError, match=message):
            tl.check(*_seal(copy.deepcopy(ledger), narrative, **overrides))


def test_check_detects_tampered_chain():
    ledger, narrative = _real()
    ledger_bytes, narrative, manifest = _seal(ledger, narrative)
    tampered = json.loads(ledger_bytes)
    tampered["tuples"][1]["cumulative_sha256"] = "0" * 64
    tampered_bytes = json.dumps(tampered).encode("utf-8")
    manifest_obj = json.loads(manifest)
    manifest_obj["files"]["CHAT_TUPLE_LEDGER.json"] = tl.h(tampered_bytes)
    with pytest.raises(ValueError, match="Tuple chain tampered: T02"):
        tl.check(tampered_bytes, narrative, json.dumps(manifest_obj).encode("utf-8"))


def test_tuple_lineage_main(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["prog", "--folder", str(FOLDER)])
    tl.main()
    assert json.loads(capsys.readouterr().out)["result"] == "PASS"


# --- tuple_lineage pulse metrics ------------------------------------------------


def _run(
    sha=HEAD,
    conclusion="success",
    url="https://github.com/GBOGEB/ABACUS/actions/runs/1",
):
    return {"source_sha": sha, "conclusion": conclusion, "url": url}


def _ledger():
    return {
        "tuples": [{}, {}],
        "todo_records": [{"state": "HOLD"}, {"state": "VERIFY"}],
    }


def test_pulse_metrics_counts_terminal_runs():
    pulse = tl.pulse_metrics(
        _ledger(),
        head_sha=HEAD,
        observed_ci={
            "10": _run(),
            "2": _run(conclusion="failure"),
            "3": _run(conclusion="skipped"),
        },
    )
    assert [r["id"] for r in pulse["workflow_receipts"]] == [2, 3, 10]
    assert (
        pulse["workflow_pass"],
        pulse["workflow_fail"],
        pulse["workflow_skipped"],
    ) == (1, 1, 1)
    assert pulse["workflow_pass_pct"] == round(100 / 3, 4)
    assert pulse["todo_state_count"] == {
        "BLOCKED": 0,
        "HOLD": 1,
        "VERIFY": 1,
        "UNKNOWN": 0,
    }
    assert pulse["admission"] == "HOLD"
    empty = tl.pulse_metrics(_ledger(), head_sha=HEAD, observed_ci={})
    assert empty["workflow_pass_pct"] is None


@pytest.mark.parametrize(
    "head,ci,message",
    [
        ("abc", {}, "complete exact-head SHA"),
        ("A" * 40, {}, "complete exact-head SHA"),
        (HEAD, {"1": _run(sha=OTHER)}, "CI source SHA mismatch: 1"),
        (HEAD, {"1": _run(conclusion="neutral")}, "Nonterminal run"),
        (HEAD, {"1": _run(url="https://evil.example/runs/1")}, "Untrusted CI URL"),
    ],
)
def test_pulse_metrics_rejections(head, ci, message):
    with pytest.raises(ValueError, match=message):
        tl.pulse_metrics(_ledger(), head_sha=head, observed_ci=ci)


def test_compare_pulses():
    before = tl.pulse_metrics(
        _ledger(), head_sha=HEAD, observed_ci={"1": _run(conclusion="failure")}
    )
    after = tl.pulse_metrics(_ledger(), head_sha=HEAD, observed_ci={"1": _run()})
    delta = tl.compare_pulses(before, after)
    assert delta["same_exact_head_and_run_set"] is True
    assert (delta["workflow_pass_delta"], delta["workflow_pass_pp"]) == (1, 100.0)
    grown = tl.pulse_metrics(
        _ledger(), head_sha=HEAD, observed_ci={"1": _run(), "2": _run()}
    )
    widened = tl.compare_pulses(before, grown)
    assert (
        widened["workflow_pass_delta"] is None
        and widened["observed_run_set_growth"] == 1
    )
    empty = tl.pulse_metrics(_ledger(), head_sha=HEAD, observed_ci={})
    assert tl.compare_pulses(empty, empty)["workflow_pass_pp"] is None
    with pytest.raises(ValueError, match="Different telemetry schema"):
        tl.compare_pulses(before, dict(after, schema="x"))
    with pytest.raises(ValueError, match="Different CI metric basis"):
        tl.compare_pulses(before, dict(after, metric_basis="x"))


def test_workflow_lifecycle_census():
    census = tl.workflow_lifecycle_census(
        HEAD,
        {
            "1": {"source_sha": HEAD, "status": "completed", "conclusion": "success"},
            "2": {"source_sha": HEAD, "status": "completed", "conclusion": "failure"},
            "3": {"source_sha": HEAD, "status": "in_progress", "conclusion": None},
        },
    )
    assert (
        census["statuses"]["completed"] == 2 and census["statuses"]["in_progress"] == 1
    )
    assert census["terminal_pass_fraction"] == {"numerator": 1, "denominator": 2}
    pending = tl.workflow_lifecycle_census(
        HEAD, {"4": {"source_sha": HEAD, "status": "queued", "conclusion": None}}
    )
    assert (
        pending["terminal_denominator"] is None
        and pending["terminal_pass_fraction"] is None
    )


@pytest.mark.parametrize(
    "head,obs,message",
    [
        ("short", {}, "Full SHA required"),
        (HEAD, {"x": {"source_sha": HEAD}}, "Run ID or source mismatch"),
        (HEAD, {"1": {"source_sha": OTHER}}, "Run ID or source mismatch"),
        (
            HEAD,
            {"1": {"source_sha": HEAD, "status": "waiting", "conclusion": None}},
            "Unsupported",
        ),
        (
            HEAD,
            {"1": {"source_sha": HEAD, "status": "completed", "conclusion": None}},
            "lacks terminal",
        ),
        (
            HEAD,
            {"1": {"source_sha": HEAD, "status": "pending", "conclusion": "success"}},
            "Nonterminal",
        ),
    ],
)
def test_workflow_lifecycle_census_rejections(head, obs, message):
    with pytest.raises(ValueError, match=message):
        tl.workflow_lifecycle_census(head, obs)


# --- wave_telemetry -----------------------------------------------------------------


def _basis(**extra):
    basis = {
        "scope_id": "lane_b",
        "unit_definition": "statement",
        "instrumentor": "coverage.py",
        "instrumentor_version": "7.13",
        "configuration_sha256": DIGEST,
        "selection": "tests/coverage_waves",
        "paths": ["src", "tools"],
    }
    basis.update(extra)
    return basis


def _ratio(mid, n, d, sha=HEAD, state="MEASURED", **basis):
    return {
        "id": mid,
        "state": state,
        "measure_type": "RATIO",
        "numerator": n,
        "denominator": d,
        "source_sha": sha,
        "basis": _basis(**basis),
    }


def _state(head=HEAD, **overrides):
    state = {
        "subject": {"repository": "GBOGEB/ABACUS", "head_sha": head},
        "snapshot": {"captured_at_utc": "2026-10-27T00:00:00Z"},
        "metrics": [
            _ratio("line_coverage", 50, 100, sha=head),
            {
                "id": "wall",
                "state": "HISTORICAL",
                "measure_type": "SCALAR",
                "value": 3,
                "unit": "h",
            },
            {"id": "rex", "state": "UNKNOWN", "missing_reason": "no receipts"},
        ],
        "gates": [
            {
                "id": "governance",
                "scope": "MAIN",
                "status": "PASS",
                "source_sha": head,
                "required_for_admission": True,
            },
            {
                "id": "security-scan",
                "scope": "EXACT_HEAD",
                "status": "FAIL",
                "source_sha": head,
            },
            {"id": "old", "scope": "HISTORICAL", "status": "PASS"},
        ],
        "blockers": [
            {"classification": "ROOT", "root_cause_fingerprint": DIGEST},
            {"classification": "NOISE"},
        ],
        "unknowns": [{"id": "U1", "owner": "o", "acquisition": "a", "reason": "r"}],
        "authority": {
            "merge_decision": "ADMIT",
            "independent_approval": "ESTABLISHED",
            "effective_branch_protection": "VERIFIED",
        },
    }
    state.update(overrides)
    return state


def test_canonical_require_and_ratio():
    assert wt.canonical({"b": 1, "a": 2}).endswith(b"}\n")
    assert wt.canonical({"b": 1, "a": 2}).index(b'"a"') < wt.canonical(
        {"b": 1, "a": 2}
    ).index(b'"b"')
    wt.require(True, "unused")
    with pytest.raises(ValueError, match="nope"):
        wt.require(False, "nope")
    assert wt.validate_ratio(
        {"numerator": 1, "denominator": 3, "basis": {"unit_definition": "line"}}
    ) == {
        "covered": 1,
        "eligible": 3,
        "percent": 33.3333,
        "unit": "line",
    }
    for bad in (
        {"numerator": 1.0, "denominator": 2},
        {"numerator": 3, "denominator": 2},
        {"numerator": 0, "denominator": 0},
    ):
        with pytest.raises(ValueError, match="invalid ratio"):
            wt.validate_ratio(bad)


@pytest.mark.parametrize(
    "before,after,ok,reason",
    [
        (_ratio("m", 1, 2), _ratio("m", 1, 2, sha=OTHER), True, "match"),
        (
            _ratio("m", 1, 2, state="HISTORICAL"),
            _ratio("m", 1, 2, sha=OTHER),
            False,
            "MEASURED",
        ),
        (
            _ratio("m", 1, 2),
            _ratio("m", 1, 2, sha=OTHER, selection="all"),
            False,
            "test selection differs",
        ),
        (
            _ratio("m", 1, 2, configuration_sha256=None),
            _ratio("m", 1, 2, sha=OTHER, configuration_sha256=None),
            False,
            "digest missing",
        ),
        (
            _ratio("m", 1, 2),
            _ratio("m", 1, 2, sha=OTHER, paths=["src"]),
            False,
            "path scope differs",
        ),
        (_ratio("m", 1, 2), _ratio("m", 1, 2), False, "different source SHAs"),
    ],
)
def test_comparable(before, after, ok, reason):
    result, why = wt.comparable(before, after)
    assert result is ok and reason in why


def test_summarize_state_full_receipt():
    receipt = wt.summarize_state(_state(), DIGEST)
    assert receipt["metrics"]["current"]["line_coverage"]["percent"] == 50.0
    assert receipt["metrics"]["historical"]["wall"]["value"] == 3
    assert receipt["metrics"]["unknown"] == {"rex": {"reason": "no receipts"}}
    assert (
        receipt["gates"]["total_current"] == 2
        and receipt["gates"]["required_all_pass"] is True
    )
    assert receipt["gates"]["by_status"]["FAIL"] == ["security-scan"]
    assert receipt["roots"] == {
        "root_classified_rows": 1,
        "fingerprinted_count": 1,
        "closed_count": None,
        "root_burndown": "UNVERIFIED",
    }
    dims = receipt["depth"]["dimensions"]
    assert dims["current_coverage_lines"] and dims["current_governance"]
    assert not dims["current_security"] and not dims["current_coverage_branches"]
    assert receipt["admission"] == "CANDIDATE_ONLY_REQUIRES_LIVE_AUTHORITY"
    assert len(receipt["receipt_sha256"]) == 64


def test_summarize_state_hold_and_unfingerprinted_roots():
    state = _state(
        blockers=[{"classification": "GOVERNANCE", "root_cause_fingerprint": "short"}],
        authority={"merge_decision": "HOLD"},
    )
    receipt = wt.summarize_state(state, DIGEST)
    assert receipt["admission"] == "HOLD"
    assert receipt["roots"]["fingerprinted_count"] is None
    assert receipt["depth"]["dimensions"]["fingerprinted_root_census"] is False


@pytest.mark.parametrize(
    "state,root,message",
    [
        (
            _state(subject={"repository": "noslash", "head_sha": HEAD}),
            DIGEST,
            "repository identity",
        ),
        (
            _state(subject={"repository": "o/r", "head_sha": "abc"}),
            DIGEST,
            "exact SHA required",
        ),
        (_state(), "abc", "manifest root required"),
        (
            _state(
                gates=[
                    {"id": "g", "scope": "MAIN", "status": "PASS"},
                    {"id": "g", "scope": "MAIN"},
                ]
            ),
            DIGEST,
            "duplicate current gate id",
        ),
        (
            _state(
                unknowns=[{"id": "U", "owner": "o", "acquisition": "a", "reason": "r"}]
                * 2
            ),
            DIGEST,
            "duplicate UNKNOWN",
        ),
        (
            _state(unknowns=[{"id": "U", "owner": "o"}]),
            DIGEST,
            "requires owner, reason",
        ),
        (_state(metrics=[{"id": ""}]), DIGEST, "metric identifier required"),
        (
            _state(metrics=[{"id": "m", "state": "UNKNOWN"}] * 2),
            DIGEST,
            "duplicate metric identifier",
        ),
        (
            _state(metrics=[{"id": "m", "state": "UNKNOWN", "value": 1}]),
            DIGEST,
            "UNKNOWN cannot contain",
        ),
        (
            _state(metrics=[_ratio("m", 1, 2, sha=OTHER)]),
            DIGEST,
            "current metric source mismatch",
        ),
        (
            _state(metrics=[{"id": "m", "state": "STALE"}]),
            DIGEST,
            "unsupported metric state",
        ),
    ],
)
def test_summarize_state_rejections(state, root, message):
    with pytest.raises(ValueError, match=message):
        wt.summarize_state(state, root)


def test_compare_states():
    before = _state(
        metrics=[
            _ratio("line_coverage", 40, 100),
            {"id": "new_only", "state": "UNKNOWN"},
        ]
    )
    after = _state(
        head=OTHER,
        metrics=[
            _ratio("line_coverage", 55, 110, sha=OTHER),
            _ratio("branch_coverage", 1, 2, sha=OTHER),
            {"id": "new_only", "state": "UNKNOWN"},
        ],
        unknowns=[{"id": "U2", "owner": "o", "acquisition": "a", "reason": "r"}],
    )
    delta = wt.compare_states(before, after, DIGEST, DIGEST)
    assert delta["unknown_ids_no_longer_open"] == ["U1"] and delta[
        "unknown_ids_new"
    ] == ["U2"]
    assert delta["unknown_net_reduction"] == 0
    (row,) = delta["metric_deltas"]
    assert (
        row["covered_delta"],
        row["eligible_delta"],
        row["percentage_point_delta"],
    ) == (15, 10, 10.0)
    same_sha = wt.compare_states(
        before, _state(metrics=[_ratio("line_coverage", 41, 100)]), DIGEST, DIGEST
    )
    assert same_sha["metric_deltas"][0]["comparable"] is False
    assert same_sha["metric_deltas"][0]["covered_delta"] is None
    other_repo = _state(subject={"repository": "GBOGEB/CODEX", "head_sha": OTHER})
    with pytest.raises(ValueError, match="cross-repository"):
        wt.compare_states(before, other_repo, DIGEST, DIGEST)


def test_federate():
    pulse = wt.summarize_state(_state(), DIGEST)
    rollup = wt.federate([pulse], ["GBOGEB/ABACUS", "GBOGEB/CODEX"])
    assert rollup["breadth_percent"] == 50.0
    assert rollup["unobserved_repositories"] == ["GBOGEB/CODEX"]
    assert rollup["per_repo"]["GBOGEB/ABACUS"]["source_sha"] == HEAD
    for pulses, targets, message in [
        ([pulse], [], "nonempty disjoint"),
        ([pulse], ["a/b", "a/b"], "nonempty disjoint"),
        ([pulse, pulse], ["GBOGEB/ABACUS"], "one current pulse"),
        ([pulse], ["GBOGEB/CODEX"], "unscoped federation pulse"),
        (
            [dict(pulse, security_waiver=True)],
            ["GBOGEB/ABACUS"],
            "may not transfer authority",
        ),
    ]:
        with pytest.raises(ValueError, match=message):
            wt.federate(pulses, targets)


def _capsules(monkeypatch, mapping):
    monkeypatch.setattr(
        wt,
        "load_capsule",
        lambda path: (mapping[path.name], {"manifest_root_sha256": DIGEST}),
    )


@pytest.mark.parametrize("action", ["pulse", "compare", "federate"])
def test_wave_telemetry_main(tmp_path, monkeypatch, capsys, action):
    _capsules(monkeypatch, {"a": _state(), "b": _state(head=OTHER)})
    out = tmp_path / "o" / "r.json"
    argv = {
        "pulse": ["pulse", "--capsule", "a"],
        "compare": ["compare", "--before", "a", "--after", "b"],
        "federate": ["federate", "--capsules", "a", "--repositories", "GBOGEB/ABACUS"],
    }[action]
    monkeypatch.setattr(sys, "argv", ["prog", *argv, "--out", str(out)])
    wt.main()
    schema = json.loads(out.read_text(encoding="utf-8"))["schema"]
    expected = {
        "pulse": wt.SCHEMA,
        "compare": "handover.wave.delta.v1",
        "federate": "handover.federation.rollup.v1",
    }[action]
    assert schema == expected
    assert json.loads(capsys.readouterr().out)["schema"] == expected


def test_load_capsule_delegates_to_build_handover(monkeypatch):
    class _Fake:
        @staticmethod
        def capsule_verify(path):
            return {"p": str(path)}, {"manifest_root_sha256": DIGEST}

    monkeypatch.setitem(sys.modules, "build_handover", _Fake)
    assert wt.load_capsule(REPO_ROOT)[0] == {"p": str(REPO_ROOT)}
