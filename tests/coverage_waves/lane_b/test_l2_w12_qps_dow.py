"""Lane-B wave 12: QPS W04/W05 DOW receipt runners and validators."""

import copy
import hashlib
import json
import sys

import pytest
import yaml

from ._l2_loader import REPO_ROOT, load

run04 = load("tools/run_qps_w04_dow_return.py")
run05 = load("tools/run_qps_w05_bidder_eval_dow.py")
val04 = load("tools/validate_qps_w04_dow_receipt.py")
val05 = load("tools/validate_qps_w05_bidder_eval_dow.py")

PARENT_SHA = "c" * 40
CHILD_SHA = "ec12b09873a8e0668176d8212f8d09ecdbe18bad"
W04_REQUEST = REPO_ROOT / "federation/qps/QPS_FED_W04_DOW_REQUEST.yaml"
W04_QA = REPO_ROOT / "ssot/qps_w04_dow_qa_actions.yaml"
W04_SNAPSHOT = (
    REPO_ROOT
    / "federation/qps/snapshots/QPS_FED_W04_SANITIZED_PARENT_SNAPSHOT_v0.2.yaml"
)
W04_FIXTURE = REPO_ROOT / "tests/fixtures/qps_w04_dow_receipt_fixture.yaml"
W05_REQUEST = REPO_ROOT / "federation/qps/QPS_FED_W05_BIDDER_EVAL_DOW_REQUEST.yaml"
W05_SNAPSHOT = (
    REPO_ROOT / "federation/qps/snapshots/QPS_FED_W05_BIDDER_EVAL_SANITIZED_v0.1.yaml"
)


def _yaml(path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _dump(path, data):
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return path


def _fake_git(value=PARENT_SHA):
    calls = []

    def fake(cmd, text):
        calls.append((cmd, text))
        return value + "\n"

    fake.calls = calls
    return fake


# ---------------------------------------------------------------------------
# run_qps_w04_dow_return: helpers
# ---------------------------------------------------------------------------


def test_w04_hash_helpers(tmp_path):
    a = tmp_path / "a.txt"
    a.write_bytes(b"alpha")
    assert run04.file_sha256(a) == hashlib.sha256(b"alpha").hexdigest()
    expected = hashlib.sha256(a.as_posix().encode() + b"\0" + b"alpha").hexdigest()
    assert run04.sha256([a]) == expected
    assert (
        run04.canonical_sha256({"b": 1, "a": [2]})
        == hashlib.sha256(b'{"a":[2],"b":1}').hexdigest()
    )


def test_w04_git_sha_ok_and_invalid(monkeypatch):
    fake = _fake_git()
    monkeypatch.setattr(run04.subprocess, "check_output", fake)
    assert run04.git_sha() == PARENT_SHA
    assert fake.calls == [(["git", "rev-parse", "HEAD"], True)]
    monkeypatch.setattr(run04.subprocess, "check_output", _fake_git("nope"))
    with pytest.raises(SystemExit, match="unable to resolve parent git SHA"):
        run04.git_sha()


def test_w04_load_rejects_non_mapping(tmp_path):
    p = tmp_path / "list.yaml"
    p.write_text("- 1\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="is not a YAML mapping"):
        run04.load(p)
    assert run04.load(W04_REQUEST)["correlation_id"] == run04.CORR


def test_w04_locate_exactly_one(tmp_path):
    (tmp_path / "x").mkdir()
    (tmp_path / "x" / "a.yaml").write_text("a", encoding="utf-8")
    assert run04.locate(tmp_path, "a.yaml") == tmp_path / "x" / "a.yaml"
    with pytest.raises(SystemExit, match="found 0"):
        run04.locate(tmp_path, "missing.yaml")
    (tmp_path / "a.yaml").write_text("a", encoding="utf-8")
    with pytest.raises(SystemExit, match="found 2"):
        run04.locate(tmp_path, "a.yaml")


@pytest.mark.parametrize("raw, expected", [(" TRUE ", True), ("false", False)])
def test_w04_parse_bool(raw, expected):
    assert run04.parse_bool(raw) is expected


def test_w04_parse_bool_rejects():
    with pytest.raises(run04.argparse.ArgumentTypeError, match="true or false"):
        run04.parse_bool("yes")


def test_w04_artifact_identities_sorted(tmp_path):
    b = tmp_path / "b.yaml"
    a = tmp_path / "a.yaml"
    b.write_text("b", encoding="utf-8")
    a.write_text("a", encoding="utf-8")
    out = run04.artifact_identities([b, a])
    assert [item["artifact"] for item in out] == ["a.yaml", "b.yaml"]
    assert out[0]["sha256"] == hashlib.sha256(b"a").hexdigest()


H1 = "1" * 64
H2 = "2" * 64


@pytest.mark.parametrize(
    "prior, semantic, requested, expected",
    [
        (None, True, False, ("DOW_ANALYSIS", None)),
        (H1, False, True, ("DOW_ANALYSIS", False)),
        (H2, True, True, ("DOW_ANALYSIS", True)),
        (H2, False, False, ("LINEAGE_REFRESH_ONLY", True)),
        (H1, False, False, ("IDEMPOTENT_NOOP", False)),
    ],
)
def test_w04_trigger_decision(prior, semantic, requested, expected):
    got = run04.trigger_decision(
        current_artifact_set_sha256=H1,
        prior_artifact_set_sha256=prior,
        semantic_change=semantic,
        analysis_requested=requested,
    )
    assert got == expected


@pytest.mark.parametrize(
    "prior, match",
    [
        ("ABC", "must be a full SHA-256"),
        (None, "lineage-only refresh requires"),
    ],
)
def test_w04_trigger_decision_rejections(prior, match):
    with pytest.raises(SystemExit, match=match):
        run04.trigger_decision(
            current_artifact_set_sha256=H1,
            prior_artifact_set_sha256=prior,
            semantic_change=False,
            analysis_requested=False,
        )


def test_w04_build_findings(tmp_path):
    ev = tmp_path / "ev.yaml"
    ev.write_text("Support and C24 with TBD gaps\n", encoding="utf-8")
    status, findings = run04.build_findings(
        requested=[
            "decompose_support_system_dependency_graph",
            "produce_reverse_catchup_candidates",
        ],
        evidence=[ev],
    )
    first = status["decompose_support_system_dependency_graph"]
    assert first["executed"] is True and first["status"] == "PASS"
    assert "matched 1 governed cues" in first["reason"]
    assert findings[0]["observed_cues"] == ["support"]
    assert findings[1]["observed_cues"] == ["TBD", "gap"]
    assert findings[1]["finding_id"] == (
        "ABACUS-W04-"
        + hashlib.sha256(b"produce_reverse_catchup_candidates").hexdigest()[:12]
    )
    assert all(f["qps_authority"] is False for f in findings)


# ---------------------------------------------------------------------------
# run_qps_w04_dow_return: main
# ---------------------------------------------------------------------------


def _w04_env(monkeypatch, request=W04_REQUEST):
    monkeypatch.setattr(run04, "REQUEST", request)
    monkeypatch.setattr(run04, "QA", W04_QA)
    monkeypatch.setattr(run04.subprocess, "check_output", _fake_git())


def _run04(monkeypatch, tmp_path, *extra, child_sha=CHILD_SHA):
    out = tmp_path / "out" / "receipt.yaml"
    argv = ["run", "--child-sha", child_sha, "--output", str(out)]
    argv += ["--snapshot", str(W04_SNAPSHOT), *extra]
    monkeypatch.setattr(sys, "argv", argv)
    assert run04.main() == 0
    return _yaml(out)


def test_w04_main_snapshot_analysis_validates(tmp_path, monkeypatch, capsys):
    _w04_env(monkeypatch)
    receipt = _run04(monkeypatch, tmp_path)
    assert str(tmp_path / "out" / "receipt.yaml") in capsys.readouterr().out
    assert receipt["analysis_decision"] == "DOW_ANALYSIS"
    assert receipt["input_mode"] == "sanitized_snapshot"
    assert receipt["parent_commit_sha"] == PARENT_SHA
    assert receipt["fail_closed_status"] == "PASS_ALL_DECLARED_MECHANICS_EXECUTED"
    assert len(receipt["typed_findings"]) == len(run04.TERMS)
    assert receipt["trigger_semantics"]["artifact_hash_changed"] is None
    assert val04.validate(receipt) == []


def test_w04_main_lineage_refresh_and_noop(tmp_path, monkeypatch):
    _w04_env(monkeypatch)
    current = run04.canonical_sha256(run04.artifact_identities([W04_SNAPSHOT]))
    flags = ["--semantic-change", "false", "--analysis-requested", "false"]
    refresh = _run04(monkeypatch, tmp_path, "--prior-artifact-set-sha256", H2, *flags)
    assert refresh["analysis_decision"] == "LINEAGE_REFRESH_ONLY"
    assert refresh["fail_closed_status"] == (
        "PASS_HASH_ONLY_LINEAGE_REFRESH_NO_ANALYSIS"
    )
    assert refresh["requested_analysis_scope"] == []
    assert refresh["semantic_trigger_scope"] == []
    assert refresh["typed_findings"] == [] and refresh["stage_status"] == {}
    assert val04.validate(refresh) == []
    noop = _run04(monkeypatch, tmp_path, "--prior-artifact-set-sha256", current, *flags)
    assert noop["analysis_decision"] == "IDEMPOTENT_NOOP"
    assert noop["fail_closed_status"] == "PASS_IDEMPOTENT_NOOP_NO_ANALYSIS"
    assert val04.validate(noop) == []


def test_w04_main_private_child_mode(tmp_path, monkeypatch):
    _w04_env(monkeypatch)
    child = tmp_path / "child" / "deep"
    child.mkdir(parents=True)
    names = _yaml(W04_REQUEST)["input_contract"]["child_artifacts"]
    for name in names:
        (child / name).write_text("C30 lifecycle PCA BT\n", encoding="utf-8")
    receipt = _run04(monkeypatch, tmp_path, "--child-root", str(tmp_path / "child"))
    assert receipt["input_mode"] == "private_child"
    assert sorted(i["artifact"] for i in receipt["source_artifact_identities"]) == (
        sorted(names)
    )
    assert val04.validate(receipt) == []


def test_w04_main_rejects_bad_child_sha(tmp_path, monkeypatch):
    _w04_env(monkeypatch)
    with pytest.raises(SystemExit, match="--child-sha must be a full commit SHA"):
        _run04(monkeypatch, tmp_path, child_sha="abc")


def test_w04_main_rejects_snapshot_lineage(tmp_path, monkeypatch):
    _w04_env(monkeypatch)
    with pytest.raises(SystemExit, match="sanitized snapshot lineage mismatch"):
        _run04(monkeypatch, tmp_path, child_sha="d" * 40)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda r: r.update(requested_DOW_operations="x"),
        lambda r: r["requested_DOW_operations"].pop(),
    ],
)
def test_w04_main_rejects_request_operations(tmp_path, monkeypatch, mutate):
    request = _yaml(W04_REQUEST)
    mutate(request)
    _w04_env(monkeypatch, _dump(tmp_path / "req.yaml", request))
    with pytest.raises(SystemExit, match="do not match implemented mechanics"):
        _run04(monkeypatch, tmp_path)


# ---------------------------------------------------------------------------
# run_qps_w05_bidder_eval_dow
# ---------------------------------------------------------------------------


def _w05_env(monkeypatch, tmp_path, request=W05_REQUEST, snapshot=W05_SNAPSHOT):
    out = tmp_path / "runtime" / "w05.yaml"
    monkeypatch.setattr(run05, "REQUEST", request)
    monkeypatch.setattr(run05, "SNAPSHOT", snapshot)
    monkeypatch.setattr(run05, "OUTPUT", out)
    monkeypatch.setattr(run05.subprocess, "check_output", _fake_git())
    return out


def test_w05_helpers(tmp_path):
    p = tmp_path / "l.yaml"
    p.write_bytes(b"[]\n")
    with pytest.raises(SystemExit, match="is not a YAML mapping"):
        run05.load(p)
    assert (
        run05.digest([p])
        == hashlib.sha256(p.as_posix().encode() + b"\0" + b"[]\n").hexdigest()
    )
    assert run05.stable_id("op") == (
        "ABACUS-W05-" + hashlib.sha256(b"op").hexdigest()[:12]
    )
    snap = {"bidders": {"X": {"family_edges": {"F": ["A", "B"], "G": ["A"]}}}}
    assert run05.edge_counts(snap, "X") == {"A": 2, "B": 1}


def test_w05_main_committed_inputs_validate(tmp_path, monkeypatch, capsys):
    out = _w05_env(monkeypatch, tmp_path)
    assert run05.main() == 0
    assert str(out) in capsys.readouterr().out
    receipt = _yaml(out)
    requested = _yaml(W05_REQUEST)["requested_DOW_operations"]
    assert receipt["executed_operations"] == requested
    assert receipt["parent_commit_sha"] == PARENT_SHA
    status = receipt["operation_status"]
    compare = status[requested[0]]["result"]
    assert compare["cross_bidder_substitution"] is False
    assert compare["family_count_each"] == {"BIDDER_A": 14, "BIDDER_B": 14}
    assert status[requested[1]]["result"]["coverage_pct"] == 100.0
    assert "L4" in status[requested[5]]["result"]
    assert status[requested[9]]["result"]["engineering_credit"] == 0
    payload = {k: v for k, v in receipt.items() if k != "output_hash"}
    assert (
        receipt["output_hash"]
        == hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
    )
    monkeypatch.setattr(sys, "argv", ["v", str(out)])
    assert val05.main() == 0
    assert "VALIDATION PASSED" in capsys.readouterr().out


def test_w05_main_unrecognized_operation(tmp_path, monkeypatch):
    request = _yaml(W05_REQUEST)
    request["requested_DOW_operations"] = ["something_new"]
    out = _w05_env(monkeypatch, tmp_path, _dump(tmp_path / "r.yaml", request))
    assert run05.main() == 0
    result = _yaml(out)["operation_status"]["something_new"]["result"]
    assert result == {"status": "operation_recognized_but_no_specialized_projection"}


def _w05_bad(which, fn):
    def build(tmp_path):
        req = _yaml(W05_REQUEST)
        snap = _yaml(W05_SNAPSHOT)
        fn(req if which == "req" else snap)
        return _dump(tmp_path / "r.yaml", req), _dump(tmp_path / "s.yaml", snap)

    return build


@pytest.mark.parametrize(
    "build, match",
    [
        (_w05_bad("req", lambda d: d.update(correlation_id="X")), "correlation"),
        (_w05_bad("snap", lambda d: d.update(correlation_id="X")), "correlation"),
        (
            _w05_bad("snap", lambda d: d.update(confidentiality={})),
            "must remove bidder names",
        ),
        (
            _w05_bad("req", lambda d: d.update(requested_DOW_operations=[])),
            "missing requested DOW operations",
        ),
        (
            _w05_bad("req", lambda d: d.update(requested_DOW_operations="x")),
            "missing requested DOW operations",
        ),
        (
            _w05_bad("snap", lambda d: d["bidders"].pop("BIDDER_B")),
            "exactly two anonymized bidder lanes",
        ),
        (
            _w05_bad("req", lambda d: d["input_contract"]["priority_families"].pop()),
            "priority-family mismatch",
        ),
    ],
)
def test_w05_main_rejections(tmp_path, monkeypatch, build, match):
    req, snap = build(tmp_path)
    _w05_env(monkeypatch, tmp_path, req, snap)
    with pytest.raises(SystemExit, match=match):
        run05.main()


# ---------------------------------------------------------------------------
# validate_qps_w05_bidder_eval_dow
# ---------------------------------------------------------------------------


def _w05_receipt():
    finding = {
        "qps_authority": False,
        "recommended_child_action": "review_and_disposition_ACCEPT_REJECT_DEFER",
    }
    data = {key: "x" for key in val05.REQUIRED}
    data.update(
        correlation_id="QPS-FED-W05-BIDDER-EVAL",
        parent_repository="GBOGEB/ABACUS",
        requested_operations=["a"],
        executed_operations=["a"],
        child_disposition_placeholder="UNSET",
        typed_findings=[finding],
    )
    return data


def _val05(tmp_path, monkeypatch, data):
    p = tmp_path / "r.yaml"
    if isinstance(data, str):
        p.write_text(data, encoding="utf-8")
    else:
        _dump(p, data)
    monkeypatch.setattr(sys, "argv", ["v", str(p)])
    return val05.main()


def test_val05_valid(tmp_path, monkeypatch, capsys):
    assert _val05(tmp_path, monkeypatch, _w05_receipt()) == 0
    assert "W05 DOW RECEIPT VALIDATION PASSED" in capsys.readouterr().out


def _m05(fn):
    data = _w05_receipt()
    fn(data)
    return data


@pytest.mark.parametrize(
    "data, match",
    [
        ("- 1\n", "receipt is not a mapping"),
        (_m05(lambda d: d.pop("run_id")), r"missing required fields: \['run_id'\]"),
        (_m05(lambda d: d.update(correlation_id="X")), "wrong correlation id"),
        (_m05(lambda d: d.update(parent_repository="X")), "wrong parent repository"),
        (
            _m05(lambda d: d.update(executed_operations=[])),
            "requested/executed operation mismatch",
        ),
        (
            _m05(lambda d: d.update(child_disposition_placeholder="ACCEPT")),
            "must not self-disposition",
        ),
        (_m05(lambda d: d.update(typed_findings=[])), "no typed findings"),
        (
            _m05(lambda d: d["typed_findings"][0].update(qps_authority=True)),
            "incorrectly claims QPS authority",
        ),
        (
            _m05(lambda d: d["typed_findings"][0].pop("recommended_child_action")),
            "missing governed child disposition contract",
        ),
    ],
)
def test_val05_rejections(tmp_path, monkeypatch, data, match):
    with pytest.raises(SystemExit, match=match):
        _val05(tmp_path, monkeypatch, data)


# ---------------------------------------------------------------------------
# validate_qps_w04_dow_receipt
# ---------------------------------------------------------------------------

SCOPE = ["op_a", "op_b"]
IDENTS = [{"artifact": "a.yaml", "sha256": H1}]


def _rehash(receipt):
    payload = json.dumps(
        {k: v for k, v in receipt.items() if k != "output_hash"},
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    receipt["output_hash"] = hashlib.sha256(payload).hexdigest()
    return receipt


def _relineage(receipt):
    trig = receipt["trigger_semantics"]
    receipt["lineage_state_hash"] = val04.canonical_sha256(
        {
            "authoritative_child_sha": receipt.get("authoritative_child_sha"),
            "input_mode": receipt.get("input_mode"),
            "source_artifact_identities": receipt.get("source_artifact_identities"),
            "source_artifact_set_sha256": receipt.get("source_artifact_set_sha256"),
            "semantic_change": trig.get("semantic_change"),
            "analysis_requested": trig.get("analysis_requested"),
        }
    )
    return receipt


def _w04_receipt(decision="DOW_ANALYSIS", prior=None):
    analysis = decision == "DOW_ANALYSIS"
    current = val04.canonical_sha256(IDENTS)
    changed = None if prior is None else prior != current
    stage = {
        "stage_id": "op_a",
        "mechanic_path": "m",
        "executed": True,
        "status": "PASS",
        "reason": "r",
    }
    status = {
        "LINEAGE_REFRESH_ONLY": "PASS_HASH_ONLY_LINEAGE_REFRESH_NO_ANALYSIS",
        "IDEMPOTENT_NOOP": "PASS_IDEMPOTENT_NOOP_NO_ANALYSIS",
    }.get(decision, "PASS_ALL_DECLARED_MECHANICS_EXECUTED")
    receipt = {
        "run_id": "r",
        "artifact_id": "a",
        "parent_repository": "GBOGEB/ABACUS",
        "parent_commit_sha": PARENT_SHA,
        "child_source_ref": "c",
        "authoritative_child_sha": CHILD_SHA,
        "input_mode": "sanitized_snapshot",
        "correlation_id": val04.CORR,
        "input_hash": "h",
        "input_snapshot_hash": "h",
        "source_artifact_identities": copy.deepcopy(IDENTS),
        "source_artifact_set_sha256": current,
        "prior_source_artifact_set_sha256": prior,
        "trigger_semantics": {
            "artifact_hash_changed": changed,
            "semantic_change": analysis,
            "analysis_requested": analysis,
        },
        "analysis_decision": decision,
        "available_analysis_scope": list(SCOPE),
        "requested_analysis_scope": list(SCOPE) if analysis else [],
        "semantic_trigger_scope": list(SCOPE) if analysis else [],
        "executed_analysis_scope": list(SCOPE) if analysis else [],
        "executed_stages": list(SCOPE) if analysis else [],
        "stage_status": {"op_a": stage} if analysis else {},
        "fail_closed_status": status,
        "typed_findings": [{"qps_authority": False}] if analysis else [],
        "child_disposition_placeholder": "UNSET",
        "authority_boundary": "ABACUS_returns_DOW_findings_only_QPS_child_disposes",
    }
    return _rehash(_relineage(receipt))


@pytest.mark.parametrize(
    "decision, prior",
    [
        ("DOW_ANALYSIS", None),
        ("LINEAGE_REFRESH_ONLY", H2),
        ("IDEMPOTENT_NOOP", "SELF"),
    ],
)
def test_val04_valid_receipts(decision, prior):
    if prior == "SELF":
        prior = val04.canonical_sha256(IDENTS)
    assert val04.validate(_w04_receipt(decision, prior)) == []


def _m04(fn, decision="DOW_ANALYSIS", prior=None, relineage=True):
    receipt = _w04_receipt(decision, prior)
    fn(receipt)
    if relineage:
        _relineage(receipt)
    return _rehash(receipt)


def _trig(**kw):
    return lambda r: r["trigger_semantics"].update(kw)


@pytest.mark.parametrize(
    "receipt, expected",
    [
        (
            _m04(lambda r: r.update(correlation_id="X")),
            ["correlation_id mismatch"],
        ),
        (
            _m04(lambda r: r.update(authority_boundary="none")),
            ["child authority boundary missing"],
        ),
        (
            _m04(lambda r: r.pop("run_id")),
            ["missing runtime fields: run_id"],
        ),
        (
            _m04(lambda r: r.update(parent_commit_sha="TBD")),
            ["parent_commit_sha must be resolved"],
        ),
        (
            _m04(lambda r: r.update(authoritative_child_sha="TBD")),
            ["authoritative_child_sha must be resolved"],
        ),
        (
            _m04(lambda r: r.update(source_artifact_identities=[])),
            ["source_artifact_identities must be a non-empty list"],
        ),
        (
            _m04(lambda r: r["source_artifact_identities"].append("x")),
            [
                "source artifact identity must be a mapping",
                "source_artifact_set_sha256 mismatch",
            ],
        ),
        (
            _m04(lambda r: r["source_artifact_identities"].append({"sha256": "z"})),
            [
                "source artifact identity missing artifact",
                "source artifact identity sha256 invalid",
                "source_artifact_set_sha256 mismatch",
            ],
        ),
        (
            _m04(lambda r: r.update(prior_source_artifact_set_sha256="bad")),
            [
                "prior_source_artifact_set_sha256 invalid",
                "artifact_hash_changed does not match current/prior artifact "
                "identities",
            ],
        ),
        (
            _m04(_trig(semantic_change="yes")),
            ["trigger_semantics.semantic_change must be bool"],
        ),
        (
            _m04(_trig(artifact_hash_changed="maybe")),
            [
                "artifact_hash_changed must be bool or null",
                "artifact_hash_changed must be null without prior artifact identity",
            ],
        ),
        (
            _m04(_trig(artifact_hash_changed=False)),
            ["artifact_hash_changed must be null without prior artifact identity"],
        ),
        (
            _m04(_trig(artifact_hash_changed=False), "LINEAGE_REFRESH_ONLY", H2),
            [
                "artifact_hash_changed does not match current/prior artifact "
                "identities",
                "analysis_decision mismatch",
            ],
        ),
        (
            _m04(lambda r: r.update(analysis_decision="IDEMPOTENT_NOOP")),
            [
                "analysis_decision mismatch",
                "non-analysis decision executed DOW scope",
                "non-analysis decision executed stages",
                "non-analysis decision emitted stage status",
                "hash-only/noop decision emitted findings",
                "non-analysis fail_closed_status mismatch",
            ],
        ),
        (
            _m04(lambda r: r.update(lineage_state_hash="0"), relineage=False),
            ["lineage_state_hash mismatch"],
        ),
        (
            _m04(lambda r: r.update(executed_analysis_scope="all")),
            ["analysis scopes must be lists"],
        ),
        (
            _m04(lambda r: r.update(executed_analysis_scope=["op_a"])),
            ["DOW analysis must execute full available controlled scope"],
        ),
        (
            _m04(lambda r: r.update(requested_analysis_scope=[])),
            ["explicit analysis request scope mismatch"],
        ),
        (
            _m04(lambda r: r.update(semantic_trigger_scope=[])),
            ["semantic trigger scope mismatch"],
        ),
        (
            _m04(lambda r: r.update(stage_status=[])),
            ["stage_status must be a mapping"],
        ),
        (
            _m04(lambda r: r["stage_status"].update(op_b={"executed": True})),
            ["stage op_b lacks typed execution status"],
        ),
        (
            _m04(lambda r: r["stage_status"].update(op_b="x")),
            ["stage op_b lacks typed execution status"],
        ),
        (
            _m04(lambda r: r["stage_status"]["op_a"].update(executed=False)),
            ["stage op_a was not executed"],
        ),
        (
            _m04(lambda r: r.update(typed_findings={})),
            ["typed_findings must be a list"],
        ),
        (
            _m04(lambda r: r["typed_findings"].extend(["x", {}])),
            ["typed finding violates QPS authority boundary"] * 2,
        ),
        (
            _m04(
                lambda r: r.update(
                    executed_analysis_scope=["x"],
                    executed_stages=["x"],
                    stage_status={"x": {}},
                    typed_findings=[{}],
                    fail_closed_status="PASS",
                ),
                "LINEAGE_REFRESH_ONLY",
                H2,
            ),
            [
                "non-analysis decision executed DOW scope",
                "non-analysis decision executed stages",
                "non-analysis decision emitted stage status",
                "hash-only/noop decision emitted findings",
                "non-analysis fail_closed_status mismatch",
            ],
        ),
        (
            _m04(_trig(semantic_change=False, analysis_requested=False)),
            ["analysis_decision mismatch"],
        ),
    ],
)
def test_val04_rejections(receipt, expected):
    assert val04.validate(receipt) == expected


def test_val04_accepts_invalid_uncompared_decision():
    """With no prior identity, no semantic change and no analysis request the
    validator expects INVALID_UNCOMPARED_NO_ANALYSIS, so a receipt declaring
    that decision is internally consistent (the runner itself refuses to emit
    it; the validator classifies, it does not run)."""
    receipt = _w04_receipt("INVALID_UNCOMPARED_NO_ANALYSIS")
    assert receipt["fail_closed_status"] == "PASS_ALL_DECLARED_MECHANICS_EXECUTED"
    assert val04.validate(receipt) == []


def test_val04_current_sha_invalid_skips_change_check():
    receipt = _w04_receipt("LINEAGE_REFRESH_ONLY", H2)
    receipt["source_artifact_set_sha256"] = "bad"
    _rehash(_relineage(receipt))
    assert val04.validate(receipt) == ["source_artifact_set_sha256 mismatch"]


def test_val04_trigger_not_mapping():
    """production_defect: validate() raises AttributeError instead of
    reporting an error when trigger_semantics is not a mapping on a
    DOW_ANALYSIS receipt; this test fails once fixed."""
    receipt = _w04_receipt()
    receipt["trigger_semantics"] = "x"
    _rehash(receipt)
    assert val04.validate_trigger_contract(receipt) == [
        "trigger_semantics must be a mapping"
    ]
    with pytest.raises(AttributeError):
        val04.validate(receipt)


def test_val04_output_hash_mismatch():
    receipt = _w04_receipt()
    receipt["output_hash"] = "0"
    assert val04.validate(receipt) == ["output_hash mismatch"]


def test_val04_wrapped_fixture_paths():
    fixture = _yaml(W04_FIXTURE)
    assert val04.validate(fixture) == []
    broken = copy.deepcopy(fixture)
    broken["example_valid_receipt"].pop("run_id")
    broken["example_valid_receipt"]["correlation_id"] = "X"
    assert val04.validate(broken) == [
        "correlation_id mismatch",
        "fixture example missing fields: run_id",
    ]
    assert val04.validate({"example_valid_receipt": None}) == [
        "receipt missing or not a mapping"
    ]
    assert val04.validate({"example_valid_receipt": {}}) == [
        "correlation_id mismatch",
        "child authority boundary missing",
    ]


def test_val04_load_rejects_non_mapping(tmp_path):
    p = tmp_path / "x.yaml"
    p.write_text("- 1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="receipt must be a YAML mapping"):
        val04.load(p)


def test_val04_main_default_fixture(monkeypatch, capsys):
    monkeypatch.chdir(REPO_ROOT)
    assert val04.main(["v"]) == 0
    assert "satisfies QPS W04 DOW receipt contract" in capsys.readouterr().out


def test_val04_main_reports_errors(tmp_path, capsys):
    receipt = _w04_receipt()
    receipt["output_hash"] = "0"
    p = _dump(tmp_path / "r.yaml", receipt)
    assert val04.main(["v", str(p)]) == 1
    assert "ERROR: output_hash mismatch" in capsys.readouterr().err
