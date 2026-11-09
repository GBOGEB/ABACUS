"""Lane-B wave 10: everred_v3 admission eligibility evaluator and policy collector."""

import copy
import datetime as dt
import json
import sys
import types

import pytest

from ._l2_loader import load

fake_fcntl = types.SimpleNamespace(
    LOCK_EX=2, LOCK_UN=8, LOCK_SH=1, flock=lambda fd, op: None
)
mt = load("tools/everred_v3/src/metrics.py")
ev = load("tools/everred_v3/src/everred.py", deps={"fcntl": fake_fcntl, "metrics": mt})
ni = load("tools/everred_v3/src/native_ingest.py", deps={"everred": ev})
adm = load(
    "tools/everred_v3/src/admission.py", deps={"everred": ev, "native_ingest": ni}
)

A, B = "a" * 40, "b" * 40
REPO = "GBOGEB/ABACUS"
NOW = dt.datetime(2026, 10, 1, 12, 0, tzinfo=dt.timezone.utc)
FETCHED = "2026-10-01T11:55:00Z"
CONTEXTS = ["build", "PR Feedback Gate"]
HARD_GATE = {
    "id": 24494381,
    "source": REPO,
    "target": "branch",
    "enforcement": "active",
    "bypass_actors": [],
}


def _policy(**overrides):
    pol = {
        "source": "effective_branch_rules",
        "repository": REPO,
        "branch": "main",
        "main_sha": B,
        "fetched_at": FETCHED,
        "protected": True,
        "required_pr": True,
        "strict_checks": True,
        "block_force_push": True,
        "block_deletion": True,
        "require_resolved_conversations": True,
        "require_last_push_approval": True,
        "dismiss_stale_reviews_on_push": True,
        "main_hard_gate_active": True,
        "main_hard_gate_no_bypass": True,
        "min_approvals": 1,
        "status_contexts": list(CONTEXTS),
    }
    pol.update(overrides)
    return pol


def _receipt(decision="PASS", sha=A):
    return {"sha": sha, "decision": decision}


def _inputs(**overrides):
    x = {
        "schema": "abacus.everred.admission.inputs.v1",
        "repository": REPO,
        "candidate_sha": A,
        "main_sha": B,
        "target_branch": "main",
        "required_checks": list(CONTEXTS),
        "checks": [
            {"name": n, "sha": A, "conclusion": "success", "status": "completed"}
            for n in CONTEXTS
        ]
        + [{"name": "build", "sha": B, "conclusion": "failure"}, "junk"],
        "security": _receipt(),
        "coverage": _receipt(),
        "workflow_governance": _receipt(),
        "policy": _policy(),
        "pr_author": "alice",
        "reviews": [
            {"state": "APPROVED", "login": "bob", "commit_id": A, "eligible": True},
            {"state": "COMMENTED", "login": "carol"},
            "junk",
        ],
        "unresolved_review_conversations": 0,
    }
    x.update(overrides)
    return x


def _eval(x, authenticated=True):
    return adm.evaluate(x, authenticated=authenticated, now=NOW)


# -------------------------------------------------------------------- utc


def test_utc_parses_zulu_and_offset():
    assert adm.utc("2026-10-01T00:00:00Z") == dt.datetime(
        2026, 10, 1, tzinfo=dt.timezone.utc
    )
    assert adm.utc("2026-10-01T02:00:00+02:00").utcoffset() == dt.timedelta(hours=2)


@pytest.mark.parametrize("value", ["2026-10-01T00:00:00", "nonsense", None, 5])
def test_utc_rejects(value):
    with pytest.raises(ev.InvalidEvidence, match="invalid UTC timestamp"):
        adm.utc(value)


# --------------------------------------------------------------- evaluate


def test_evaluate_all_pass_authenticated_is_eligible():
    out = _eval(_inputs())
    assert out["gates"] == {g: "PASS" for g in adm.GATES}
    assert out["uncertainty"] == {}
    assert out["decision"] == "ELIGIBLE_PENDING_AUTHORIZED_MERGE"
    assert out["evidence_authentication"] == "AUTHENTICATED_COLLECTOR"
    assert out["merge_authorized"] is False
    assert out["security_waiver"] is False
    assert out["authority_transfer"] is False
    assert (out["repository"], out["candidate_sha"], out["main_sha"]) == (REPO, A, B)


def test_evaluate_all_pass_unauthenticated_holds():
    out = _eval(_inputs(), authenticated=False)
    assert out["decision"] == "HOLD"
    assert out["evidence_authentication"] == "UNVERIFIED_IMPORT"


def test_evaluate_uses_wall_clock_when_now_missing():
    fresh = dt.datetime.now(dt.timezone.utc).isoformat()
    out = adm.evaluate(_inputs(policy=_policy(fetched_at=fresh)), authenticated=True)
    assert out["gates"]["branch_protection"] == "PASS"


@pytest.mark.parametrize(
    "x, msg",
    [
        ("nope", "bad admission input schema"),
        (_inputs(schema="v0"), "bad admission input schema"),
        (_inputs(repository=5), "repository/exact SHA binding"),
        (_inputs(repository="no slash"), "repository/exact SHA binding"),
        (_inputs(candidate_sha="abc"), "repository/exact SHA binding"),
        (_inputs(main_sha=None), "repository/exact SHA binding"),
        (_inputs(target_branch="dev"), "only main admission"),
        (_inputs(policy=_policy(fetched_at="bad")), "invalid UTC timestamp"),
    ],
)
def test_evaluate_rejections(x, msg):
    with pytest.raises(ev.InvalidEvidence, match=msg):
        _eval(x)


def _failing_checks():
    return [
        {"name": "build", "sha": A, "conclusion": "failure", "status": "completed"},
        {"name": "PR Feedback Gate", "sha": A, "conclusion": "success"},
    ]


@pytest.mark.parametrize(
    "overrides, state, reason",
    [
        ({"checks": _failing_checks()}, "RED", None),
        ({"checks": None}, "UNKNOWN", "missing complete required-check set"),
        ({"required_checks": []}, "UNKNOWN", "missing complete required-check set"),
        (
            {"required_checks": ["build", "build"]},
            "UNKNOWN",
            "missing complete required-check set",
        ),
        (
            {"checks": [{"name": "build", "sha": A}]},
            "UNKNOWN",
            "missing, ambiguous or mismatched-SHA native checks",
        ),
        (
            {"checks": [{"name": n, "sha": A} for n in CONTEXTS + ["build"]]},
            "UNKNOWN",
            "missing, ambiguous or mismatched-SHA native checks",
        ),
    ],
)
def test_exact_head_ci_gate(overrides, state, reason):
    out = _eval(_inputs(**overrides))
    assert out["gates"]["exact_head_ci"] == state
    assert out["uncertainty"].get("exact_head_ci") == reason
    assert out["decision"] == "HOLD"


@pytest.mark.parametrize("field", ["security", "coverage", "workflow_governance"])
@pytest.mark.parametrize(
    "value, state",
    [
        (_receipt("RED"), "RED"),
        (_receipt("WAIVED"), "UNKNOWN"),
        (_receipt(sha=B), "UNKNOWN"),
        ("PASS", "UNKNOWN"),
        (None, "UNKNOWN"),
    ],
)
def test_receipt_gates(field, value, state):
    out = _eval(_inputs(**{field: value}))
    assert out["gates"][field] == state
    if state == "UNKNOWN":
        assert "exact-SHA independent receipt" in out["uncertainty"][field]
    else:
        assert field not in out["uncertainty"]


@pytest.mark.parametrize(
    "policy",
    [
        None,
        "x",
        _policy(source="classic"),
        _policy(repository="Other/Repo"),
        _policy(branch="dev"),
        _policy(main_sha=A),
    ],
)
def test_branch_protection_unbound_receipt(policy):
    out = _eval(_inputs(policy=policy))
    assert out["gates"]["branch_protection"] == "UNKNOWN"
    assert out["uncertainty"]["branch_protection"] == (
        "no bound effective-server-rules receipt"
    )


@pytest.mark.parametrize("fetched", ["2026-10-01T11:40:00Z", "2026-10-01T12:20:00Z"])
def test_branch_protection_stale_snapshot(fetched):
    out = _eval(_inputs(policy=_policy(fetched_at=fetched)))
    assert out["gates"]["branch_protection"] == "UNKNOWN"
    assert "older than 15 minutes" in out["uncertainty"]["branch_protection"]


def test_branch_protection_boundary_fresh_at_900_seconds():
    out = _eval(_inputs(policy=_policy(fetched_at="2026-10-01T11:45:00Z")))
    assert out["gates"]["branch_protection"] == "PASS"


@pytest.mark.parametrize(
    "overrides",
    [
        {"protected": False},
        {"strict_checks": "yes"},
        {"main_hard_gate_no_bypass": False},
        {"min_approvals": 0},
        {"min_approvals": True},
        {"min_approvals": "1"},
        {"status_contexts": None},
        {"status_contexts": []},
        {"status_contexts": ["build", "build", "PR Feedback Gate"]},
        {"status_contexts": ["", "PR Feedback Gate"]},
        {"status_contexts": [3, "PR Feedback Gate"]},
        {"status_contexts": ["build"]},
    ],
)
def test_branch_protection_red_on_missing_rule(overrides):
    out = _eval(_inputs(policy=_policy(**overrides)))
    assert out["gates"]["branch_protection"] == "RED"
    assert out["uncertainty"]["branch_protection"] == (
        "one or more mandatory effective rules missing"
    )


@pytest.mark.parametrize("needed", [None, ["build", "unlisted"], ["build", 7]])
def test_branch_protection_red_when_required_checks_unprotected(needed):
    out = _eval(_inputs(required_checks=needed))
    assert out["gates"]["branch_protection"] == "RED"


@pytest.mark.parametrize(
    "reviews, author, state, reason",
    [
        (
            [{"state": "APPROVED", "login": "alice", "commit_id": A, "eligible": True}],
            "alice",
            "RED",
            "no eligible independent exact-head approval",
        ),
        (
            [{"state": "APPROVED", "login": "bob", "commit_id": B, "eligible": True}],
            "alice",
            "RED",
            "no eligible independent exact-head approval",
        ),
        (
            [{"state": "APPROVED", "login": "bob", "commit_id": A, "eligible": 1}],
            "alice",
            "RED",
            "no eligible independent exact-head approval",
        ),
        (
            [
                {"state": "APPROVED", "login": "bob", "commit_id": A, "eligible": True},
                {"state": "CHANGES_REQUESTED", "login": "carol"},
            ],
            "alice",
            "RED",
            "no eligible independent exact-head approval",
        ),
        ([], "alice", "RED", "no eligible independent exact-head approval"),
        (None, "alice", "UNKNOWN", "review roster unavailable"),
        ([], "", "UNKNOWN", "review roster unavailable"),
        ([], None, "UNKNOWN", "review roster unavailable"),
    ],
)
def test_independent_review_gate(reviews, author, state, reason):
    out = _eval(_inputs(reviews=reviews, pr_author=author))
    assert out["gates"]["independent_review"] == state
    assert out["uncertainty"]["independent_review"] == reason


@pytest.mark.parametrize(
    "conv, state", [(0, "PASS"), (3, "RED"), (-1, "UNKNOWN"), (True, "UNKNOWN")]
)
def test_review_conversations_gate(conv, state):
    out = _eval(_inputs(unresolved_review_conversations=conv))
    assert out["gates"]["review_conversations"] == state
    if state == "UNKNOWN":
        assert out["uncertainty"]["review_conversations"] == (
            "unresolved thread census unavailable"
        )
    else:
        assert "review_conversations" not in out["uncertainty"]


# ---------------------------------------------- effective_policy_from_rules


def _rules():
    return [
        {
            "type": "pull_request",
            "parameters": {
                "required_approving_review_count": 1,
                "require_last_push_approval": True,
                "dismiss_stale_reviews_on_push": True,
                "required_review_thread_resolution": True,
            },
        },
        {
            "type": "required_status_checks",
            "parameters": {
                "strict_required_status_checks_policy": True,
                "required_status_checks": [{"context": c} for c in CONTEXTS],
            },
        },
        {"type": "non_fast_forward"},
        {"type": "deletion", "parameters": None},
        "junk",
    ]


def test_effective_policy_complete_rules():
    pol = adm.effective_policy_from_rules(
        REPO, B, _rules(), {"protected": True}, FETCHED, main_hard_gate=HARD_GATE
    )
    assert pol["status_contexts"] == CONTEXTS
    assert pol["min_approvals"] == 1
    assert pol["effective_rules_count"] == 5
    for key in (
        "protected",
        "required_pr",
        "strict_checks",
        "require_last_push_approval",
        "dismiss_stale_reviews_on_push",
        "main_hard_gate_active",
        "main_hard_gate_no_bypass",
        "block_force_push",
        "block_deletion",
        "require_resolved_conversations",
    ):
        assert pol[key] is True, key
    out = _eval(_inputs(policy=pol))
    assert out["gates"]["branch_protection"] == "PASS"


def test_effective_policy_empty_rules_fail_closed():
    pol = adm.effective_policy_from_rules(REPO, B, [], {}, FETCHED)
    assert pol["status_contexts"] is None
    assert pol["min_approvals"] is None
    assert pol["protected"] is False
    assert pol["required_pr"] is False
    assert pol["main_hard_gate_active"] is False
    assert pol["main_hard_gate_no_bypass"] is False
    assert pol["effective_rules_count"] == 0
    assert _eval(_inputs(policy=pol))["gates"]["branch_protection"] == "RED"


@pytest.mark.parametrize(
    "contexts", ["build", [{"context": "build"}, "PR Feedback Gate"]]
)
def test_effective_policy_malformed_contexts(contexts):
    rules = [
        {
            "type": "required_status_checks",
            "parameters": {"required_status_checks": contexts},
        }
    ]
    pol = adm.effective_policy_from_rules(REPO, B, rules, {}, FETCHED)
    assert pol["status_contexts"] is None


@pytest.mark.parametrize(
    "gate, active, no_bypass",
    [
        (dict(HARD_GATE, bypass_actors=[{"actor_id": 1}]), True, False),
        (dict(HARD_GATE, id=1), False, False),
        (dict(HARD_GATE, source="Other/Repo"), False, False),
        (dict(HARD_GATE, target="tag"), False, False),
        (dict(HARD_GATE, enforcement="evaluate"), False, False),
        ("gate", False, False),
    ],
)
def test_effective_policy_hard_gate(gate, active, no_bypass):
    pol = adm.effective_policy_from_rules(
        REPO, B, _rules(), {"protected": True}, FETCHED, main_hard_gate=gate
    )
    assert pol["main_hard_gate_active"] is active
    assert pol["main_hard_gate_no_bypass"] is no_bypass


@pytest.mark.parametrize("rules, branch", [("x", {}), ([], None), (None, None)])
def test_effective_policy_rejects_invalid_shapes(rules, branch):
    with pytest.raises(ev.InvalidEvidence, match="invalid GitHub effective policy"):
        adm.effective_policy_from_rules(REPO, B, rules, branch, FETCHED)


# -------------------------------------------------- collect_readonly_policy


class FakeReader:
    """Offline stand-in for native_ingest.GitHubReadOnly."""

    def __init__(self, routes):
        self.routes = routes
        self.calls = []

    def get(self, route):
        self.calls.append(route)
        return self.routes[route]


def _routes(head=B):
    return {
        "/repos/"
        + REPO
        + "/branches/main": {
            "protected": True,
            "commit": {"sha": head},
        },
        "/repos/" + REPO + "/rules/branches/main": _rules(),
        "/repos/" + REPO + "/rulesets/24494381": copy.deepcopy(HARD_GATE),
    }


def test_collect_readonly_policy_binds_head_and_feeds_evaluate():
    reader = FakeReader(_routes())
    pol = adm.collect_readonly_policy(reader, REPO, B)
    assert reader.calls == list(_routes())
    assert pol["main_sha"] == B
    assert pol["main_hard_gate_no_bypass"] is True
    fetched = adm.utc(pol["fetched_at"])
    assert abs((dt.datetime.now(dt.timezone.utc) - fetched).total_seconds()) < 60
    out = adm.evaluate(_inputs(policy=pol), authenticated=True)
    assert out["gates"]["branch_protection"] == "PASS"
    assert out["decision"] == "ELIGIBLE_PENDING_AUTHORIZED_MERGE"


def test_collect_readonly_policy_rejects_bad_sha():
    reader = FakeReader({})
    with pytest.raises(ev.InvalidEvidence, match="invalid branch SHA"):
        adm.collect_readonly_policy(reader, REPO, "main")
    assert reader.calls == []


def test_collect_readonly_policy_rejects_advanced_main():
    reader = FakeReader(_routes(head=A))
    with pytest.raises(ev.InvalidEvidence, match="main advanced"):
        adm.collect_readonly_policy(reader, REPO, B)
    assert len(reader.calls) == 1


def test_collect_readonly_policy_branch_without_commit():
    routes = _routes()
    routes["/repos/" + REPO + "/branches/main"] = {}
    with pytest.raises(ev.InvalidEvidence, match="main advanced"):
        adm.collect_readonly_policy(FakeReader(routes), REPO, B)


# --------------------------------------------------------------------- CLI


def test_main_prints_and_writes_output(monkeypatch, tmp_path, capsys):
    src = tmp_path / "in.json"
    dst = tmp_path / "out.json"
    src.write_text(json.dumps(_inputs(policy=None)))
    monkeypatch.setattr(
        sys, "argv", ["admission", "--input", str(src), "--output", str(dst)]
    )
    adm.main()
    printed = json.loads(capsys.readouterr().out)
    assert printed == json.loads(dst.read_text())
    assert printed["decision"] == "HOLD"
    assert printed["evidence_authentication"] == "UNVERIFIED_IMPORT"
    assert printed["gates"]["branch_protection"] == "UNKNOWN"


def test_main_without_output(monkeypatch, tmp_path, capsys):
    src = tmp_path / "in.json"
    src.write_text(json.dumps(_inputs(policy=None)))
    monkeypatch.setattr(sys, "argv", ["admission", "--input", str(src)])
    adm.main()
    printed = json.loads(capsys.readouterr().out)
    assert printed["schema"] == "abacus.everred.admission.evaluation.v1"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["in.json"]
