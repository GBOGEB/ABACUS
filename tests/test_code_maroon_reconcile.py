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
        "implemented": 33,
        "closed": 33,
        "deferred": 2,
        "outstanding": 4,
        "failing_active": 2,
        "roots_total": 28,
        "roots_closed": 25,
        "roots_deferred": 1,
        "roots_open": 2,
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
