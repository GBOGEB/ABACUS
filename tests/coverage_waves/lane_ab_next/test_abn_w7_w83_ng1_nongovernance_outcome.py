"""Gap tests for tools/w83_ng1_nongovernance_outcome.py (fail-closed gates, CLI)."""

import copy
import json
import sys

import pytest

from tests.coverage_waves.lane_b._l2_loader import REPO_ROOT, load

mod = load("tools/w83_ng1_nongovernance_outcome.py", name="abn_w7_w83_ng1")

LEDGER = REPO_ROOT / "architecture/w83/W83_NG1_NON_GOVERNANCE_OUTCOME_LEDGER_v0.1.json"


def _ledger():
    return json.loads(LEDGER.read_text(encoding="utf-8"))


def test_auc_requires_both_classes():
    with pytest.raises(ValueError, match="both outcome classes"):
        mod.auc([1, 1], [0.1, 0.2])


def _set(ledger, path, value):
    target = ledger
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value


@pytest.mark.parametrize(
    "path, value, message",
    [
        (["schema_version"], "other", "schema mismatch"),
        (["repository"], "x/y", "repository mismatch"),
        (["rows"], [], "exact s05..s15 population"),
        (["feature_policy", "included_blocks"], ["x"], "block contract drift"),
        (["feature_policy", "excluded_blocks"], [], "governance exclusion drift"),
        (["feature_policy", "pca_fit_permitted"], True, "non-promotional"),
        (["rows", 0, "source_sha"], "f" * 40, "source mismatch for"),
        (["rows", 0, "w83_source_receipt", "run_id"], 1, "lineage missing"),
        (
            ["rows", 0, "w83_source_receipt", "artifact_digest"],
            "md5:x",
            "artifact digest missing",
        ),
    ],
)
def test_evaluate_fails_closed(path, value, message):
    ledger = _ledger()
    _set(ledger, path, value)
    with pytest.raises(ValueError, match=message):
        mod.evaluate(ledger)


def test_evaluate_rejects_wrong_outcome_geometry():
    ledger = _ledger()
    for row in ledger["rows"]:
        row["outcome"]["docs_failure"] = 1
    with pytest.raises(ValueError, match="8-fail/3-pass"):
        mod.evaluate(ledger)


def test_evaluate_rejects_feature_schema_drift():
    ledger = _ledger()
    last = ledger["rows"][-1]["semantic_composition"]
    last["extra_feature_not_in_others"] = 1
    with pytest.raises(ValueError, match="feature schema drift"):
        mod.evaluate(ledger)


def test_main_writes_canonical_result(monkeypatch, tmp_path, capsys):
    src = tmp_path / "ledger.json"
    src.write_bytes(LEDGER.read_bytes())
    out = tmp_path / "result.json"
    monkeypatch.setattr(sys, "argv", ["w83", str(src), "--out", str(out)])
    assert mod.main() is None
    written = json.loads(out.read_text(encoding="utf-8"))
    assert written == mod.evaluate(copy.deepcopy(_ledger()))
    assert json.loads(capsys.readouterr().out) == written
