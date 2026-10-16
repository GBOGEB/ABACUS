from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "tools" / "code_maroon" / "reconcile.py"
SPEC = importlib.util.spec_from_file_location("code_maroon_reconcile", MODULE)
M = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(M)


def load_snapshot():
    return json.loads((ROOT / "CODE_MAROON" / "snapshot_20261016.json").read_text())


def test_snapshot_totals_and_root_collapse():
    receipt = M.reconcile(load_snapshot())
    assert receipt["summary"] == {
        "manifestations_total": 37,
        "implemented": 34,
        "closed": 34,
        "deferred": 2,
        "outstanding": 3,
        "failing_active": 1,
        "roots_total": 28,
        "roots_closed": 26,
        "roots_deferred": 1,
        "roots_open": 1,
    }
    assert len(receipt["root_manifestations"]["CM-METHOD-QUALIFICATION-FAILOPEN"]) == 3
    assert len(receipt["root_manifestations"]["CM-ACTION-PINNING"]) == 3
    assert len(receipt["root_manifestations"]["CM-MIP2-CONTRACT-DIAGNOSTICS"]) == 2
    assert len(receipt["root_manifestations"]["CM-GOV-INVENTORY-DRIFT"]) == 2


def test_duplicate_manifestation_identity_fails_closed():
    data = load_snapshot()
    data["manifestations"].append(dict(data["manifestations"][0]))
    try:
        M.reconcile(data)
    except ValueError as exc:
        assert "duplicate manifestation identity" in str(exc)
    else:
        raise AssertionError("duplicate manifestation accepted")


def test_manifestation_cannot_reference_missing_root():
    data = load_snapshot()
    data["manifestations"][0]["root_id"] = "MISSING"
    try:
        M.reconcile(data)
    except ValueError as exc:
        assert "undeclared root" in str(exc)
    else:
        raise AssertionError("missing root accepted")


def test_sarif_groups_are_candidates_not_root_closures(tmp_path):
    sarif = {
        "version": "2.1.0",
        "runs": [
            {
                "tool": {"driver": {"name": "Semgrep"}},
                "results": [
                    {
                        "ruleId": "python.test.rule",
                        "partialFingerprints": {"primaryLocationLineHash": "same-root"},
                        "locations": [
                            {
                                "physicalLocation": {
                                    "artifactLocation": {"uri": "a.py"},
                                    "region": {"startLine": 10},
                                }
                            }
                        ],
                    },
                    {
                        "ruleId": "python.test.rule",
                        "partialFingerprints": {"primaryLocationLineHash": "same-root"},
                        "locations": [
                            {
                                "physicalLocation": {
                                    "artifactLocation": {"uri": "a.py"},
                                    "region": {"startLine": 11},
                                }
                            }
                        ],
                    },
                ],
            }
        ],
    }
    path = tmp_path / "x.sarif"
    path.write_text(json.dumps(sarif), encoding="utf-8")
    receipt = M.reconcile(load_snapshot(), [path])
    assert receipt["sarif"]["findings_total"] == 2
    assert receipt["sarif"]["exact_manifestations"] == 2
    assert receipt["sarif"]["stable_fingerprint_groups"] == 1
    assert receipt["summary"]["roots_total"] == 28


def test_implemented_and_closed_are_independent_kpis():
    data = load_snapshot()
    row = next(x for x in data["manifestations"] if x["status"] == "CLOSED_IMPLEMENTED")
    row["status"] = "IMPLEMENTED_UNRESOLVED"
    row["implementation_state"] = "IMPLEMENTED"
    row["thread_state"] = "OPEN"
    row["disposition"] = "ACTIVE"

    root = next(x for x in data["roots"] if x["root_id"] == row["root_id"])
    # Root state is not automatically reopened by one stale UI thread; root closure
    # and conversation closure are separate dimensions.
    data["summary"]["closed"] -= 1
    data["summary"]["outstanding"] += 1

    receipt = M.reconcile(data)
    assert receipt["summary"]["implemented"] == 34
    assert receipt["summary"]["closed"] == 33
    assert receipt["summary"]["outstanding"] == 4
    assert root["status"] == "CLOSED_IMPLEMENTED"


def test_closed_root_cannot_hide_active_unimplemented_manifestation():
    data = load_snapshot()
    root = next(r for r in data["roots"] if r["status"] == "OPEN_ACTIVE")
    assert any(
        m["root_id"] == root["root_id"] and m["status"] == "OPEN_ACTIVE"
        for m in data["manifestations"]
    )
    root["status"] = "CLOSED_IMPLEMENTED"
    data["summary"]["roots_closed"] += 1
    data["summary"]["roots_open"] -= 1
    try:
        M.reconcile(data)
    except ValueError as exc:
        assert "closed root contains active manifestation" in str(exc)
    else:
        raise AssertionError("closed root incorrectly hid an active failure")
