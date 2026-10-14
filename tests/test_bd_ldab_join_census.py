"""Regression contracts for exact-head BD/LDAB observational join."""
import importlib.util
import json
from pathlib import Path

import pytest

SOURCE = Path(__file__).resolve().parents[1] / "scripts" / "bd_ldab_join_census.py"
SPEC = importlib.util.spec_from_file_location("bd_ldab_join_census", SOURCE)
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)
HEAD = "a" * 40
OLD = "b" * 40
FP = "c" * 64
REPO = "GBOGEB/ABACUS"
URL = "https://github.com/GBOGEB/ABACUS/actions/runs/38531518523"


def census(sha=HEAD, rows=None):
    if rows is None:
        rows = [{"path": "scripts/a.py", "rule": "B603", "line": 7, "fingerprint": FP}]
    lanes = {}
    for name in module.LANES:
        items = rows if name == "B3-subprocess" else []
        lanes[name] = {
            "items": items, "findings": len(items),
            "files": len({x["path"] for x in items}),
        }
    return {"schema": "bandit.disjoint.census.v1", "exact_sha": sha,
            "total_unique": len(rows), "lanes": lanes}


def bundle():
    return {
        "schema": "bd.ldab.input.v1",
        "scope": {"repository": REPO, "head_sha": HEAD,
                  "scan_configuration": "full-default-v1",
                  "run_id": 38531518523, "job_id": 115744267733,
                  "evidence_url": URL},
        "bandit_disjoint": census(),
    }


def ci(**kwargs):
    row = {"repository": REPO, "source_sha": HEAD,
           "run_id": 38531518668, "job_id": 115744268133,
           "evidence_url": "https://github.com/GBOGEB/ABACUS/actions/runs/38531518668",
           "source_path": "docs/ci/a.md",
           "signature": "MD013 over length", "rule_or_error_code": "MD013"}
    row.update(kwargs)
    return row


def debug(**kwargs):
    row = {"repository": REPO, "source_sha": HEAD,
           "run_id": 456, "job_id": 789,
           "evidence_url": URL, "session_id": "s-1",
           "runner_id": "runner-1", "real_probe_steps": 10}
    row.update(kwargs)
    return row


def test_empty_disjoint_preserves_unknown_metrics_without_approval():
    b = bundle()
    b["bandit_disjoint"] = census(rows=[])
    out = module.join(b)
    assert out["metrics"]["full_bandit_unique"] == 0
    assert out["metrics"]["comparable_delta"] is None
    assert out["metrics"]["active_workers"] is None
    assert out["merge_admission"] == "HOLD"
    assert out["authority_transfer"] is False
    assert out["security_waiver"] is False


def test_one_bandit_has_exclusive_owner_and_stable_root():
    out = module.join(bundle())
    assert len(out["roots"]) == 1
    assert out["roots"][0]["owner_lane"] == "B3-subprocess"
    assert out["metrics"]["assigned_files"] == 1
    assert out["metrics"]["duplicate_file_owners"] == 0
    assert module.join(bundle()) == out


def test_explicit_same_head_ci_and_debug_join_but_do_not_promote():
    b = bundle()
    b["ci_failures"] = [ci(related_bandit_fingerprint=FP)]
    b["debug_receipts"] = [debug(related_bandit_fingerprint=FP)]
    out = module.join(b)
    assert len(out["roots"]) == 1
    sources = {x["source"] for x in out["roots"][0]["observations"]}
    assert sources == {"bandit_disjoint", "ci_failure", "debug_receipt"}
    assert out["metrics"]["debug_reported_sessions"] == 1
    assert out["merge_admission"] == "HOLD"


def test_unlinked_ci_becomes_independent_first_red():
    b = bundle()
    b["ci_failures"] = [ci()]
    out = module.join(b)
    assert len(out["roots"]) == 2
    assert any(x["category"] == "CI" for x in out["roots"])
    assert out["metrics"]["ci_observations"] == 1


def test_repeat_ci_signature_deduplicates_root_but_not_occurrences():
    b = bundle()
    b["ci_failures"] = [ci(), ci(job_id=115744268134)]
    out = module.join(b)
    assert len([x for x in out["roots"] if x["category"] == "CI"]) == 1
    assert out["metrics"]["ci_observations"] == 2


def test_codex_runtime_stays_unlinked_without_cross_repo_authority():
    b = bundle()
    b["debug_receipts"] = [debug(repository="GBOGEB/CODEX",
        source_sha="d" * 40, run_id=38523894832, job_id=115719629787,
        evidence_url="https://github.com/GBOGEB/CODEX/actions/runs/38523894832",
        host_binding="127.0.0.1:32768", container_id="container-1",
        image_digest="sha256:" + "e" * 64)]
    out = module.join(b)
    assert len(out["unlinked_debug_receipts"]) == 1
    assert out["unlinked_debug_receipts"][0]["proof_level"] == "REPORTED_UNVERIFIED"
    assert out["roots"][0]["observations"][0]["source"] == "bandit_disjoint"


def test_partial_debug_is_not_counted_as_real_session():
    b = bundle()
    b["debug_receipts"] = [debug(session_id=None, real_probe_steps=10)]
    out = module.join(b)
    assert out["metrics"]["debug_reported_sessions"] == 0
    assert out["unlinked_debug_receipts"][0]["proof_level"] == "PARTIAL"


@pytest.mark.parametrize("unsafe", ["", ".", "././", "../outside", "/etc/passwd",
                                     "src/../../outside", r"C:\Windows\system32"])
def test_unsafe_bandit_paths_rejected(unsafe):
    b = bundle()
    b["bandit_disjoint"] = census(rows=[
        {"path": unsafe, "rule": "B603", "line": 1, "fingerprint": FP}])
    with pytest.raises(ValueError):
        module.join(b)


def test_multiple_owner_for_same_file_fails_closed():
    b = bundle()
    b["bandit_disjoint"]["lanes"]["B2-source"] = {
        "items": [{"path": "scripts/a.py", "rule": "B105", "line": 8,
                   "fingerprint": "d" * 64}], "findings": 1, "files": 1}
    b["bandit_disjoint"]["total_unique"] = 2
    with pytest.raises(ValueError, match="multiple disjoint owners"):
        module.join(b)


def test_duplicate_fingerprint_fails_closed():
    b = bundle()
    row = dict(b["bandit_disjoint"]["lanes"]["B3-subprocess"]["items"][0])
    b["bandit_disjoint"]["lanes"]["B3-subprocess"]["items"].append(row)
    b["bandit_disjoint"]["lanes"]["B3-subprocess"]["findings"] = 2
    b["bandit_disjoint"]["total_unique"] = 2
    with pytest.raises(ValueError, match="Duplicate Bandit fingerprint"):
        module.join(b)


@pytest.mark.parametrize("wrong", ["e" * 40, "short", "A" * 40])
def test_exact_head_mismatch_or_invalid_sha_rejected(wrong):
    b = bundle()
    b["scope"]["head_sha"] = wrong
    with pytest.raises(ValueError):
        module.join(b)


def test_cross_repo_debug_cannot_claim_bandit_fingerprint():
    b = bundle()
    b["debug_receipts"] = [debug(repository="GBOGEB/CODEX",
                                 related_bandit_fingerprint=FP)]
    with pytest.raises(ValueError, match="same-head"):
        module.join(b)


def test_unbacked_ci_fingerprint_fails_closed():
    b = bundle()
    b["ci_failures"] = [ci(related_bandit_fingerprint="1" * 64)]
    with pytest.raises(ValueError, match="same-head"):
        module.join(b)


def test_comparable_burndown_same_config():
    b = bundle()
    b["previous"] = {"repository": REPO, "head_sha": OLD,
                     "scan_configuration": "full-default-v1",
                     "bandit_disjoint": census(sha=OLD, rows=[])}
    delta = module.join(b)["metrics"]["comparable_delta"]
    assert delta["new"] == 1
    assert delta["resolved"] == 0
    assert delta["net_reduction"] == -1
    assert delta["status"] == "FINGERPRINT_DELTA_ONLY_REVIEW_REQUIRED"


def test_config_mismatch_fails_closed_without_artificial_reduction():
    b = bundle()
    b["previous"] = {"repository": REPO, "head_sha": OLD,
                     "scan_configuration": "configured-with-exclusions",
                     "bandit_disjoint": census(sha=OLD, rows=[])}
    with pytest.raises(ValueError, match="configuration/repository mismatch"):
        module.join(b)


def test_no_implicit_mutation_and_deterministic_json():
    b = bundle()
    before = json.dumps(b, sort_keys=True)
    first = json.dumps(module.join(b), sort_keys=True)
    assert json.dumps(b, sort_keys=True) == before
    assert json.dumps(module.join(b), sort_keys=True) == first


def test_cli_two_pass_byte_identity(tmp_path, monkeypatch):
    source = tmp_path / "in.json"
    target = tmp_path / "out" / "joined.json"
    source.write_text(json.dumps(bundle()), encoding="utf-8")
    import sys
    monkeypatch.setattr(sys, "argv", ["join", "--input", str(source),
                                      "--out", str(target)])
    module.main()
    first = target.read_bytes()
    module.main()
    assert target.read_bytes() == first
    assert json.loads(first)["metrics"]["full_bandit_unique"] == 1
