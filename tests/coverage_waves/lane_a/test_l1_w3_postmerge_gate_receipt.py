"""Lane A wave 3: MIP/G3CS_CONVERGENCE_V2/tools/postmerge_gate_receipt.py."""

import json
import sys

import pytest

from tests.coverage_waves.lane_a._load import load

pg = load("MIP/G3CS_CONVERGENCE_V2/tools/postmerge_gate_receipt.py")

HEAD = "1" * 40
BASE = "2" * 40
MAIN = "3" * 40
H64 = "d" * 64


def ci(sha, rid, **kw):
    r = {
        "id": rid,
        "attempt": 1,
        "url": "https://github.com/GBOGEB/ABACUS/actions/runs/" + str(rid),
        "head_sha": sha,
        "status": "completed",
        "conclusion": "success",
    }
    r.update(kw)
    return r


def measure(sha, covered=50, eligible=100, **kw):
    m = {
        "source_sha": sha,
        "covered": covered,
        "eligible": eligible,
        "selection_sha256": H64,
        "tool_sha256": H64,
        "scope_sha256": H64,
    }
    m.update(kw)
    return m


def packet():
    return {
        "schema": "codepurple.g3cs.postmerge-evidence.v1",
        "repository": "GBOGEB/ABACUS",
        "pr": {
            "number": 7,
            "head_sha": HEAD,
            "parent_main_sha": BASE,
            "main_sha": MAIN,
            "merge_commit_sha": MAIN,
            "merged": True,
            "url": "https://github.com/GBOGEB/ABACUS/pull/7",
        },
        "head_ci": {
            "B0": ci(HEAD, 1),
            "MATRIX": ci(HEAD, 2),
            "A10": ci(HEAD, 3),
            "SECURITY": ci(HEAD, 4),
        },
        "main_ci": {"B0": ci(MAIN, 11), "MATRIX": ci(MAIN, 12)},
        "governance": {
            "required_statuses_enforced": True,
            "last_push_approval_enforced": True,
            "thread_resolution_enforced": True,
            "red_canary_blocked": True,
            "independent_security_review_verified": True,
            "required_approvals": 1,
            "eligible_approvals": 2,
        },
        "coverage": {
            "main": {"before": measure(BASE), "after": measure(MAIN, 60)},
            "pr_broad": None,
            "pr_diff": {"before": measure(BASE), "after": None},
        },
        "first_red": {"before": "x", "after": "y"},
    }


def test_evaluate_complete_packet():
    out = pg.evaluate(packet())
    assert out["source_reported_proofs_complete"] is True
    assert out["merge_admission"] == "HOLD"
    assert out["unmet_or_unverified"] == [
        "independent server-side merge-admission attestation not present"
    ]
    assert out["main_coverage"] == {
        "status": "PAIRED_SOURCE_REPORTED",
        "before": 50,
        "after": 60,
        "eligible": 100,
        "delta_covered": 10,
        "delta_pp": 10.0,
    }
    assert out["pr_broad_coverage"]["status"] == "UNKNOWN"
    assert out["pr_diff_coverage"] == {"status": "UNKNOWN", "delta_pp": None}
    assert out["first_red_transition"] == "CANDIDATE_DISPLACED_NOT_ROOT_CLOSED"
    assert out["pr_number"] == 7


def test_first_red_same_and_default():
    p = packet()
    p["first_red"] = {"before": "z", "after": "z"}
    assert pg.evaluate(p)["first_red_transition"] == "SAME"
    p.pop("first_red")
    assert pg.evaluate(p)["first_red_transition"] == "UNKNOWN"


def test_missing_ci_and_governance_gaps():
    p = packet()
    p["head_ci"] = None
    del p["main_ci"]["MATRIX"]
    p["main_ci"]["B0"]["conclusion"] = "failure"
    p["governance"] = {"required_approvals": 2, "eligible_approvals": 1}
    out = pg.evaluate(p)
    assert out["source_reported_proofs_complete"] is False
    reasons = out["unmet_or_unverified"]
    assert "head_ci.B0" in reasons and "head_ci.SECURITY" in reasons
    assert "main_ci.B0" in reasons and "main_ci.MATRIX" in reasons
    assert "governance.red_canary_blocked" in reasons
    assert "governance.eligible_approvals" in reasons
    assert "governance.required_approvals" not in reasons
    assert out["first_red_transition"] == "UNKNOWN"


def test_bad_approval_types():
    p = packet()
    p["governance"]["required_approvals"] = True
    p["governance"]["eligible_approvals"] = 0
    reasons = pg.evaluate(p)["unmet_or_unverified"]
    assert "governance.required_approvals" in reasons
    assert "governance.eligible_approvals" in reasons


def test_coverage_noncomparable():
    p = packet()
    p["coverage"]["pr_broad"] = {
        "before": measure(BASE),
        "after": measure(HEAD, tool_sha256="e" * 64),
    }
    assert pg.evaluate(p)["pr_broad_coverage"] == {
        "status": "NONCOMPARABLE",
        "delta_pp": None,
    }


def _set(path, value):
    def fn(p):
        target = p
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = value

    return fn


@pytest.mark.parametrize(
    "mutate,msg",
    [
        (lambda p: p.clear() or p.update(x=1), "unknown postmerge receipt schema"),
        (_set(["repository"], "o/r"), "wrong source repository"),
        (_set(["pr"], []), "pr must be an object"),
        (_set(["pr", "number"], 0), "positive integer"),
        (_set(["pr", "head_sha"], "ABC"), "pr.head_sha requires"),
        (_set(["pr", "merged"], False), "do not reconcile"),
        (_set(["pr", "merge_commit_sha"], BASE), "do not reconcile"),
        (_set(["pr", "parent_main_sha"], HEAD), "degenerate"),
        (_set(["pr", "url"], "x"), "PR URL"),
        (_set(["head_ci"], "x"), "head_ci must be an object"),
        (_set(["head_ci", "B0", "id"], 0), "positive native run ID"),
        (_set(["head_ci", "B0", "attempt"], 0), "positive native attempt"),
        (_set(["head_ci", "B0", "url"], "u"), "run URL"),
        (_set(["head_ci", "B0", "head_sha"], MAIN), "not bound"),
        (_set(["head_ci", "B0", "status"], "odd"), "unknown workflow status"),
        (_set(["head_ci", "B0", "status"], "queued"), "nonterminal conclusion"),
        (_set(["head_ci", "B0", "conclusion"], None), "terminal conclusion"),
        (_set(["head_ci", "MATRIX"], ci(HEAD, 1)), "reuses one workflow"),
        (_set(["governance"], None), "governance must be an object"),
        (_set(["coverage"], None), "coverage must be an object"),
        (_set(["coverage", "main"], 3), "coverage.main must be an object"),
        (_set(["coverage", "main", "before"], 3), "before must be an object"),
        (
            _set(["coverage", "main", "before", "source_sha"], MAIN),
            "pinned baseline",
        ),
        (
            _set(["coverage", "main", "after", "source_sha"], BASE),
            "pinned outcome",
        ),
        (_set(["coverage", "main", "after", "covered"], -1), "requires an integer"),
        (_set(["coverage", "main", "before", "eligible"], 0), "denominator"),
        (_set(["coverage", "main", "before", "covered"], 101), "denominator"),
        (_set(["coverage", "main", "after", "scope_sha256"], "x"), "scope_sha256"),
        (_set(["first_red"], "x"), "first_red must be an object"),
        (_set(["first_red", "before"], 1), "first_red.before"),
        (_set(["first_red", "after"], 1), "first_red.after"),
    ],
)
def test_evaluate_rejections(mutate, msg):
    p = packet()
    mutate(p)
    with pytest.raises(ValueError, match=msg):
        pg.evaluate(p)


def test_nonsuccess_run_still_checks_duplicate_identity():
    p = packet()
    p["head_ci"]["MATRIX"] = ci(HEAD, 1, status="in_progress", conclusion=None)
    with pytest.raises(ValueError, match="reuses"):
        pg.evaluate(p)


def test_main_writes_receipt(tmp_path, monkeypatch):
    src = tmp_path / "in.json"
    dst = tmp_path / "nested" / "out.json"
    src.write_text(json.dumps(packet()), encoding="utf-8")
    monkeypatch.setattr(
        sys, "argv", ["prog", "--input", str(src), "--output", str(dst)]
    )
    pg.main()
    data = json.loads(dst.read_text(encoding="utf-8"))
    assert data["schema"] == "codepurple.g3cs.postmerge-evaluation.v1"
    assert data["authority_transfer"] is False
