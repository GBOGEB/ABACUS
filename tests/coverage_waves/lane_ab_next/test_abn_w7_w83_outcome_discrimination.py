"""Gap tests for tools/w83_outcome_discrimination.py.

Covers the exact-statistics branches on a perfectly separated table, every
fail-closed ledger guard not exercised by tests/test_w83_outcome_discrimination.py
(via mutations of the committed ledger) and the CLI writer.
"""

import copy
import json
import sys

import pytest

from tests.coverage_waves.lane_b._l2_loader import REPO_ROOT, load

mod = load("tools/w83_outcome_discrimination.py", name="abn_w7_w83_outcome_disc")

LEDGER_PATH = REPO_ROOT / "architecture" / "w83" / "W83_OUTCOME_LEDGER_v0.1.json"
LEDGER = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))


def test_fisher_separated_table_skips_more_likely_tables():
    assert mod.fisher_two_sided(3, 0, 0, 3) == pytest.approx(0.1)
    assert mod.fisher_two_sided(1, 1, 1, 1) == pytest.approx(1.0)


def test_mutual_information_skips_zero_cells():
    assert mod.mutual_information_bits([[3, 0], [0, 3]]) == pytest.approx(1.0)
    assert mod.mutual_information_bits([[1, 1], [1, 1]]) == pytest.approx(0.0)


def _top(key, value):
    def apply(ledger):
        ledger[key] = value

    return apply


def _source(key):
    def apply(ledger):
        ledger["source_probe"][key] = "forged"

    return apply


def _row(path, value):
    def apply(ledger):
        node = ledger["rows"][0]
        for key in path[:-1]:
            node = node[key]
        node[path[-1]] = value

    return apply


def _rows(transform):
    def apply(ledger):
        ledger["rows"] = transform(ledger["rows"])

    return apply


@pytest.mark.parametrize(
    "mutate,message",
    [
        (_top("schema_version", "x"), "ledger schema mismatch"),
        (_top("repository", "x/y"), "repository mismatch"),
        (_source("run_id"), "aggregate lineage mismatch: run_id"),
        (_top("source_probe", None), "aggregate lineage mismatch"),
        (_top("recent_semantic_composition_unique_count", 2), "semantic composition"),
        (_top("recent_consumer_graph_unique_count", 2), "consumer graph"),
        (_rows(lambda rows: rows[:5]), "exactly six recent outcome rows"),
        (
            _rows(lambda rows: rows[:5] + [dict(rows[0])]),
            "recent label set mismatch",
        ),
        (_row(("outcome", "conclusion"), "failure"), "conclusion mismatch"),
        (_row(("vector",), {"keep_rules": 1}), "compact vector schema drift"),
        (_row(("w83_probe", "artifact_id"), 0), "probe artifact ID missing"),
        (_row(("w83_probe", "artifact_digest"), "md5:x"), "probe digest missing"),
    ],
)
def test_validate_guards(mutate, message):
    ledger = copy.deepcopy(LEDGER)
    mutate(ledger)
    with pytest.raises(ValueError, match=message):
        mod.validate(ledger)


def test_evaluate_requires_two_vectors():
    ledger = copy.deepcopy(LEDGER)
    for row in ledger["rows"]:
        row["vector"] = dict(ledger["rows"][0]["vector"])
    with pytest.raises(ValueError, match="exactly two observed governance vectors"):
        mod.evaluate(ledger)


def test_main_writes_and_prints_receipt(monkeypatch, tmp_path, capsys):
    out = tmp_path / "result.json"
    monkeypatch.setattr(sys, "argv", ["w83", str(LEDGER_PATH), "--out", str(out)])
    assert mod.main() is None
    printed = json.loads(capsys.readouterr().out)
    written = json.loads(out.read_text(encoding="utf-8"))
    assert printed == written
    assert written["outcome_discrimination_supported"] is False
    assert written["source_ledger_sha256"] == mod.canonical_sha256(LEDGER)
