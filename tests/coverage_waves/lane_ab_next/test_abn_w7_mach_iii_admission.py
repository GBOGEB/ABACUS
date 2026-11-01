"""Gap tests for scripts/mach_iii_admission.py (security unknown, merge, main)."""

import json
import sys

from tests.coverage_waves.lane_b._l2_loader import load

mod = load("scripts/mach_iii_admission.py", name="abn_w7_mach_iii_admission")

POLICY = {"active": True}


def _evidence(**overrides):
    base = {
        "exact_head": True,
        "core_functional_checks": True,
        "effective_ruleset_compliance": True,
        "source_bound_receipt": True,
        "security_severities": [],
        "required_reviews_satisfied": True,
        "mergeable": True,
    }
    base.update(overrides)
    return base


def test_missing_security_severities_is_unknown_hold():
    evidence = _evidence()
    del evidence["security_severities"]
    assert mod.decide(evidence, POLICY) == "HOLD_UNKNOWN_SECURITY"


def test_not_mergeable_holds_on_mergeability():
    assert mod.decide(_evidence(mergeable=False), POLICY) == "HOLD_MERGEABILITY"


def test_main_prints_decision_from_files(monkeypatch, tmp_path, capsys):
    evidence = tmp_path / "evidence.json"
    policy = tmp_path / "policy.json"
    evidence.write_text(json.dumps(_evidence()), encoding="utf-8")
    policy.write_text(json.dumps(POLICY), encoding="utf-8")
    argv = ["mach", str(evidence), "--policy", str(policy)]
    monkeypatch.setattr(sys, "argv", argv)
    mod.main()
    assert capsys.readouterr().out.strip() == "GO_CANDIDATE_RECHECK_HEAD"


def test_main_inactive_policy(monkeypatch, tmp_path, capsys):
    evidence = tmp_path / "evidence.json"
    policy = tmp_path / "policy.json"
    evidence.write_text(json.dumps(_evidence()), encoding="utf-8")
    policy.write_text(json.dumps({"active": False}), encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["mach", str(evidence), "--policy", str(policy)])
    mod.main()
    assert capsys.readouterr().out.strip() == "HOLD_POLICY_NOT_ACTIVE"
