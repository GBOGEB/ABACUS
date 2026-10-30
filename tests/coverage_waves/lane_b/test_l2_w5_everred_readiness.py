"""Lane-B wave 5: everred_v3 model readiness, unlock yield and mission cycle."""

import copy

import pytest

from ._l2_loader import load

SRC = "tools/everred_v3/src/"
mr = load(SRC + "model_readiness.py")
uy = load(SRC + "unlock_yield.py", deps={"model_readiness": mr})
mc = load(SRC + "mission_cycle.py", deps={"model_readiness": mr, "unlock_yield": uy})

A, B = "a" * 40, "b" * 40
REPO = "GBOGEB/ABACUS"
CONFIG = "c" * 64


# --- PCA readiness --------------------------------------------------------------------


def _panel(n=30, p=2, **overrides):
    panel = {
        "schema": "abacus.everred.pca.panel.v1",
        "source_sha": A,
        "columns": [f"v{j}" for j in range(p)],
        "rows": [
            {"independent_unit": f"u{i}", "values": [float(i + j) for j in range(p)]}
            for i in range(n)
        ],
    }
    panel.update(overrides)
    return panel


def test_pca_fit_eligible():
    reply = mr.pca_readiness(_panel())
    assert reply["decision"] == "FIT_ELIGIBLE_NOT_FITTED" and reply["reasons"] == []
    assert (reply["n"], reply["p"]) == (30, 2)
    assert reply["fitted"] is False and reply["merge_authorized"] is False


@pytest.mark.parametrize(
    "panel,reasons",
    [
        ("x", ["INVALID_SCHEMA"]),
        (_panel(schema="other"), ["INVALID_SCHEMA"]),
        (
            _panel(source_sha="short", columns=["a"]),
            ["EXACT_SHA_UNKNOWN", "INVALID_VARIABLES"],
        ),
        (_panel(columns=["a", "a"]), ["INVALID_VARIABLES"]),
        (_panel(rows=None), ["ROWS_MISSING"]),
        (_panel(rows=[{"values": [1, 2]}]), ["UNIT_ID_MISSING"]),
        (
            _panel(rows=[{"independent_unit": "u", "values": [1]}]),
            ["NONFINITE_OR_INCOMPLETE"],
        ),
        (
            _panel(rows=[{"independent_unit": "u", "values": [1, float("nan")]}]),
            ["NONFINITE_OR_INCOMPLETE"],
        ),
        (
            _panel(rows=[{"independent_unit": "u", "values": [1, True]}]),
            ["NONFINITE_OR_INCOMPLETE"],
        ),
        (_panel(n=5), ["INSUFFICIENT_INDEPENDENT_UNITS"]),
        (_panel(rows=[]), ["INSUFFICIENT_INDEPENDENT_UNITS"]),
    ],
)
def test_pca_not_qualified(panel, reasons):
    reply = mr.pca_readiness(panel)
    assert reply["decision"] == "NOT_QUALIFIED" and reply["reasons"] == sorted(reasons)


def test_pca_duplicate_units_and_constant_column():
    panel = _panel()
    panel["rows"][1]["independent_unit"] = "u0"
    for row in panel["rows"]:
        row["values"][1] = 7.0
    assert mr.pca_readiness(panel)["reasons"] == [
        "CONSTANT_VARIABLE",
        "DEPENDENT_OR_DUPLICATED_UNITS",
    ]


# --- Bradley-Terry readiness ---------------------------------------------------------


def _pairs(n=30, items=("x", "y", "z")):
    cycle = list(items) + [items[0]]
    comparisons = [
        {
            "winner": cycle[i % len(items)],
            "loser": cycle[i % len(items) + 1],
            "independent_unit": f"m{i}",
        }
        for i in range(n)
    ]
    return {
        "schema": "abacus.everred.bt.pairs.v1",
        "source_sha": A,
        "items": list(items),
        "comparisons": comparisons,
    }


def test_bt_fit_eligible():
    reply = mr.bt_readiness(_pairs())
    assert reply["decision"] == "FIT_ELIGIBLE_NOT_FITTED"
    assert (reply["n"], reply["independent_units"]) == (30, 30)


def test_bt_not_qualified_cases():
    assert mr.bt_readiness({"schema": "x"})["reasons"] == ["INVALID_SCHEMA"]
    bad_items = dict(_pairs(), items=["x"], source_sha=None)
    assert mr.bt_readiness(bad_items)["reasons"] == [
        "EXACT_SHA_UNKNOWN",
        "INVALID_ITEMS",
    ]
    assert mr.bt_readiness(dict(_pairs(), comparisons=None))["reasons"] == [
        "PAIRS_MISSING"
    ]
    assert mr.bt_readiness(dict(_pairs(), comparisons=["x"]))["reasons"] == [
        "INVALID_PAIR"
    ]
    self_win = dict(_pairs(), comparisons=[{"winner": "x", "loser": "x"}])
    assert mr.bt_readiness(self_win)["reasons"] == ["INVALID_PAIR"]
    one_way = _pairs(n=4)
    one_way["comparisons"] = [
        {"winner": "x", "loser": "y", "independent_unit": "same"}
    ] * 2
    assert mr.bt_readiness(one_way)["reasons"] == [
        "NONINDEPENDENT_PAIRS",
        "SMALL_PAIR_SAMPLE",
        "WIN_GRAPH_NOT_STRONGLY_CONNECTED",
    ]


# --- reverse pressure ------------------------------------------------------------------


def _dag(**overrides):
    dag = {
        "schema": "abacus.everred.blocking-dag.v1",
        "source_sha": B,
        "nodes": [
            {"id": "r1", "type": "root", "causal_status": "CONFIRMED"},
            {"id": "r2", "type": "root", "causal_status": "CONFIRMED"},
            {"id": "r3", "type": "root", "causal_status": "SUSPECTED"},
            {"id": "mid", "type": "job"},
            {"id": "g1", "type": "gate", "mandatory": True},
            {"id": "g2", "type": "gate", "mandatory": True},
            {"id": "g3", "type": "gate", "mandatory": False},
        ],
        "edges": [
            {"from": "r1", "to": "mid", "causally_supported": True},
            {"from": "mid", "to": "g1", "causally_supported": True},
            {"from": "mid", "to": "g2", "causally_supported": True},
            {"from": "r2", "to": "g1", "causally_supported": True},
            {"from": "r2", "to": "g3", "causally_supported": True},
        ],
    }
    dag.update(overrides)
    return dag


def test_reverse_pressure_ranks_roots():
    reply = mr.reverse_pressure(_dag())
    assert reply["decision"] == "STRUCTURAL_DIAGNOSTIC_ONLY"
    assert reply["root_impacts"] == [
        {"root_id": "r1", "reachable_mandatory_gates": ["g1", "g2"]},
        {"root_id": "r2", "reachable_mandatory_gates": ["g1"]},
    ]
    unpinned = mr.reverse_pressure(_dag(source_sha="nope"))
    assert unpinned["decision"] == "NOT_QUALIFIED" and unpinned["reasons"] == [
        "EXACT_SHA_UNKNOWN"
    ]


@pytest.mark.parametrize(
    "dag,reason",
    [
        ([], "INVALID_SCHEMA"),
        (_dag(nodes=None), "GRAPH_MISSING"),
        (_dag(nodes=[{"id": 1}]), "INVALID_NODE"),
        (_dag(nodes=[{"id": "a"}, {"id": "a"}], edges=[]), "DUPLICATED_NODE"),
        (_dag(edges=["x"]), "UNVERIFIED_EDGE"),
        (
            _dag(edges=[{"from": "r1", "to": "nope", "causally_supported": True}]),
            "UNVERIFIED_EDGE",
        ),
        (
            _dag(edges=[{"from": "r1", "to": "r1", "causally_supported": True}]),
            "UNVERIFIED_EDGE",
        ),
        (
            _dag(edges=[{"from": "r1", "to": "g1", "causally_supported": "yes"}]),
            "UNVERIFIED_EDGE",
        ),
        (
            _dag(
                edges=[
                    {"from": "r1", "to": "mid", "causally_supported": True},
                    {"from": "mid", "to": "r1", "causally_supported": True},
                ]
            ),
            "CYCLE",
        ),
    ],
)
def test_reverse_pressure_rejections(dag, reason):
    assert mr.reverse_pressure(dag)["reasons"] == [reason]


# --- unlock yield ----------------------------------------------------------------------------


def _receipt(gate, sha, result, run=11, job=22):
    return {
        "source_sha": sha,
        "repository": REPO,
        "gate_id": gate,
        "config_digest": CONFIG,
        "run_id": run,
        "job_id": job,
        "evidence_url": f"https://github.com/{REPO}/actions/runs/{run}/job/{job}",
        "result": result,
    }


def _unlock(**overrides):
    payload = {
        "schema": "abacus.everred.unlock-yield.v1",
        "authority_transfer": False,
        "security_waiver": False,
        "before_sha": A,
        "after_sha": B,
        "blocking_dag": _dag(),
        "root_id": "r1",
        "complete_denominator": True,
        "repository": REPO,
        "config_digest": CONFIG,
        "dependencies": [
            {
                "gate_id": "g1",
                "before": _receipt("g1", A, "BLOCKED"),
                "after": _receipt("g1", B, "READY"),
            },
            {
                "gate_id": "g2",
                "before": _receipt("g2", A, "BLOCKED"),
                "after": _receipt("g2", B, "BLOCKED"),
            },
        ],
    }
    payload.update(overrides)
    return payload


def test_unlock_yield_verified_and_unknown_states():
    assert uy.evaluate()["reason"] == "NO_COMPARABLE_EVIDENCE"
    missing = uy.evaluate(_unlock())
    assert (missing["reason"], missing["denominator"], missing["yield_pct"]) == (
        "NATIVE_VERIFIER_MISSING",
        2,
        None,
    )
    failed = uy.evaluate(_unlock(), native_verifier=lambda row: row["gate_id"] == "g1")
    assert failed["reason"] == "NATIVE_AUTHENTICATION_FAILED"
    assert (
        uy.evaluate(_unlock(), native_verifier="yes")["reason"]
        == "NATIVE_AUTHENTICATION_FAILED"
    )
    verified = uy.evaluate(_unlock(), native_verifier=lambda row: True)
    assert verified["status"] == "VERIFIED_ASSOCIATION_NOT_CAUSAL_PROOF"
    assert (verified["numerator"], verified["denominator"], verified["yield_pct"]) == (
        1,
        2,
        50.0,
    )
    assert verified["unblocked_gates"] == ["g1"] and verified["admission"] == "HOLD"


def _bad_receipt(field, value, side="after"):
    payload = _unlock()
    payload["dependencies"][0][side][field] = value
    return payload


@pytest.mark.parametrize(
    "payload,message",
    [
        (_unlock(schema="v0"), "unsupported unlock schema"),
        (_unlock(security_waiver=True), "authority boundary"),
        (_unlock(after_sha=A), "source identity"),
        (_unlock(before_sha="xyz"), "source identity"),
        (_unlock(blocking_dag=None), "source-bound DAG missing"),
        (_unlock(blocking_dag=_dag(source_sha=A)), "source-bound DAG missing"),
        (
            _unlock(blocking_dag=_dag(source_sha=B, nodes=None)),
            "unconfirmed dependency DAG",
        ),
        (_unlock(root_id="r3"), "eligible denominator unknown"),
        (_unlock(complete_denominator=False), "eligible denominator unknown"),
        (_unlock(dependencies=[]), "eligible denominator unknown"),
        (_unlock(root_id="r2"), "missing or duplicate eligible dependencies"),
        (_unlock(repository="not a repo"), "repository missing"),
        (_unlock(config_digest="short"), "configuration missing"),
        (_bad_receipt("source_sha", A), "source receipt mismatch"),
        (_bad_receipt("gate_id", "g2", side="before"), "unbound receipt"),
        (_bad_receipt("run_id", 0), "invalid native job"),
        (_bad_receipt("evidence_url", "https://example.com"), "invalid native job"),
        (_bad_receipt("result", "MAYBE"), "unqualified disposition"),
    ],
)
def test_unlock_yield_rejections(payload, message):
    with pytest.raises(ValueError, match=message):
        uy.evaluate(payload)


def test_unlock_yield_rejects_non_dict_receipt():
    payload = _unlock()
    payload["dependencies"][1]["before"] = None
    with pytest.raises(ValueError, match="source receipt mismatch"):
        uy.evaluate(payload)


# --- mission cycle projection ------------------------------------------------------------------


def _family(fid, severity="P1", **extra):
    family = {
        "id": fid,
        "severity": severity,
        "justification": "why " + fid,
        "remediation": "fix " + fid,
        "dov": "dov " + fid,
    }
    family.update(extra)
    return family


def test_project_cards_with_all_inputs():
    bd = {
        "families": [
            _family("r1", "P0"),
            _family("r2", hard_gate=True),
            _family("other", "P3"),
        ]
    }
    guidance = mc.project(
        bd,
        pca_panel=_panel(),
        bt_pairs=_pairs(n=3),
        blocking_dag=_dag(),
        unlock_inputs={"r1": _unlock()},
        native_verifier=lambda row: True,
    )
    assert guidance["schema"] == mc.SCHEMA and guidance["stages"][0] == "Mission"
    r1, r2, other = (guidance["cards"][k] for k in ("r1", "r2", "other"))
    assert r1["priority_policy"] == r2["priority_policy"] == "P0_HARD_GATE_FIRST"
    assert other["priority_policy"] == "PRIORITY_NOT_BT"
    assert (
        r1["pca_readiness"] == "FIT_ELIGIBLE_NOT_FITTED"
        and r1["bt_readiness"] == "NOT_QUALIFIED"
    )
    assert (r1["reverse_pressure"], r1["what_it_unblocks"]) == (2, "g1, g2")
    assert (r1["unlock_yield_pct"], r1["unlock_status"]) == (
        50.0,
        "VERIFIED_ASSOCIATION_NOT_CAUSAL_PROOF",
    )
    assert other["reverse_pressure"] is None and other["what_it_unblocks"].startswith(
        "UNKNOWN"
    )
    assert other["unlock_status"] == "UNKNOWN"
    assert guidance["merge_authorized"] is False


def test_project_without_optional_inputs_and_rejections():
    cards = mc.project({"families": [_family("r9")]}, blocking_dag=_dag(nodes=None))[
        "cards"
    ]
    assert (
        cards["r9"]["pca_readiness"] == "UNQUALIFIED"
        and cards["r9"]["bt_readiness"] == "WITHHELD"
    )
    assert cards["r9"]["reverse_pressure"] is None
    with pytest.raises(ValueError, match="missing canonical BD queue"):
        mc.project({"families": "x"})
    with pytest.raises(ValueError, match="duplicate root or unsupported priority"):
        mc.project({"families": [_family("a"), _family("a")]})
    with pytest.raises(ValueError, match="duplicate root or unsupported priority"):
        mc.project({"families": [_family("a", "P9")]})


def test_inputs_are_not_mutated():
    dag = _dag()
    snapshot = copy.deepcopy(dag)
    mr.reverse_pressure(dag)
    uy.evaluate(_unlock(blocking_dag=dag), native_verifier=lambda row: True)
    assert dag == snapshot
