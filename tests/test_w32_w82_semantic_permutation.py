"""W32: adversarial provenance and exact permutation tests for W82.

Separate production module from W31. The canonical observation is never changed;
synthetic corruption and rank permutations are not new native outcome evidence.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

import numpy as np
import pytest

from tools import w82_semantic_diversity_diagnostic as w82

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "architecture/w82/W82_SEMANTIC_DIVERSITY_LEDGER_v0.1.json"


def canonical_ledger():
    return json.loads(LEDGER.read_text(encoding="utf-8"))


def test_unmodified_canonical_ledger_revalidates_without_authority_upgrade():
    original = canonical_ledger()
    snapshot = copy.deepcopy(original)
    rows = w82.validate_ledger(original)
    assert len(rows) == 6
    assert original == snapshot
    assert len({x["source_sha"] for x in rows}) == 6
    assert original["authority_transfer"] is False


def corrupt(ledger, defect):
    row = ledger["states"][0]
    outcome = row["outcome"]
    probe = row["probe"]
    source_probe = ledger["source_probe"]
    if defect == "schema":
        ledger["schema_version"] = "unsafe-schema"
    elif defect == "foreign_repository":
        ledger["repository"] = "foreign/repository"
    elif defect == "authority_upgrade":
        ledger["authority_transfer"] = True
    elif defect == "probe_pr":
        source_probe["pr"] += 1
    elif defect == "probe_head":
        source_probe["head_sha"] = "f" * 40
    elif defect == "probe_run":
        source_probe["run_id"] += 1
    elif defect == "probe_state":
        source_probe["disposition"] = "MERGED_WITHOUT_EVIDENCE"
    elif defect == "not_draft":
        source_probe["draft_merge_prevention"] = False
    elif defect == "missing_state":
        ledger["states"].pop()
    elif defect == "duplicate_label":
        ledger["states"][1]["label"] = row["label"]
    elif defect == "state_pr":
        row["pr"] += 1
    elif defect == "state_sha":
        row["source_sha"] = "0" * 40
    elif defect == "outcome_run":
        outcome["run_id"] += 1
    elif defect == "reversed_outcome":
        outcome["failure_label"] = 1 - int(outcome["failure_label"])
    elif defect == "conclusion_mismatch":
        outcome["conclusion"] = (
            "failure" if outcome["conclusion"] == "success" else "success"
        )
    elif defect == "job_identity":
        probe["job_id"] += 1
    elif defect == "artifact_identity":
        probe["artifact_id"] += 1
    elif defect == "digest_missing":
        probe["artifact_digest"] = ""
    elif defect == "semantic_hash":
        row["semantic_work_vector_sha256"] = "0" * 64
    elif defect == "work_hash":
        row["work_vector_sha256"] = "f" * 64
    elif defect == "semantic_data_tamper":
        key = next(iter(row["semantic_work_vector"]))
        row["semantic_work_vector"][key] += 1
    elif defect == "work_data_tamper":
        key = next(iter(row["work_vector"]))
        row["work_vector"][key] += 1
    else:
        raise AssertionError(defect)


@pytest.mark.parametrize(
    "defect",
    [
        "schema", "foreign_repository", "authority_upgrade",
        "probe_pr", "probe_head", "probe_run", "probe_state", "not_draft",
        "missing_state", "duplicate_label", "state_pr", "state_sha",
        "outcome_run", "reversed_outcome", "conclusion_mismatch",
        "job_identity", "artifact_identity", "digest_missing",
        "semantic_hash", "work_hash", "semantic_data_tamper",
        "work_data_tamper",
    ],
)
def test_w82_ledger_rejects_identity_or_content_corruption(defect):
    original = canonical_ledger()
    candidate = copy.deepcopy(original)
    corrupt(candidate, defect)
    with pytest.raises(ValueError, match="W82"):
        w82.validate_ledger(candidate)
    assert candidate != original


def test_canonical_hash_independent_of_dictionary_insertion_order():
    a = {"source_sha": "abc", "vector": {"b": 2, "a": 1}}
    b = {"vector": {"a": 1, "b": 2}, "source_sha": "abc"}
    assert w82.canonical_sha256(a) == w82.canonical_sha256(b)
    assert len(w82.canonical_sha256(a)) == 64
    b["vector"]["a"] = 3
    assert w82.canonical_sha256(a) != w82.canonical_sha256(b)


@pytest.mark.parametrize(
    ("scores", "auc"),
    [
        ([0.0, 1.0, 2.0, 3.0], 1.0),
        ([3.0, 2.0, 1.0, 0.0], 0.0),
        ([1.0, 1.0, 1.0, 1.0], 0.5),
        ([0.0, 1.0, 0.0, 1.0], 0.5),
    ],
)
def test_auc_ties_reversal_and_exact_rank_direction(scores, auc):
    labels = np.array([0, 0, 1, 1])
    assert w82.auc_score(labels, np.array(scores)) == pytest.approx(auc)


def test_two_sided_exact_permutation_invariant_to_reversal():
    labels = np.array([0, 0, 1, 1])
    forward = np.array([0.0, 1.0, 2.0, 3.0])
    reversed_scores = -forward
    p1, n1 = w82.exact_auc_p(labels, forward)
    p2, n2 = w82.exact_auc_p(labels, reversed_scores)
    assert (n1, n2) == (6, 6)
    assert p1 == pytest.approx(1 / 3)
    assert p2 == pytest.approx(1 / 3)
    assert p1 == pytest.approx(p2)


def test_all_tied_permutations_withhold_predictive_claim():
    labels = np.array([0, 0, 1, 1])
    pvalue, permutations = w82.exact_auc_p(labels, np.zeros(4))
    assert permutations == 6
    assert pvalue == 1.0
    assert w82.auc_score(labels, np.zeros(4)) == 0.5


def test_frozen_pc1_basis_is_deterministic_and_no_retraining_required():
    matrix = np.array([[1., 8.], [2., 6.], [3., 4.], [4., 2.]])
    m1, s1, v1, e1, explained1, scores1 = w82.frozen_pc1(matrix)
    m2, s2, v2, e2, explained2, scores2 = w82.frozen_pc1(matrix.copy())
    for lhs, rhs in ((m1, m2), (s1, s2), (v1, v2), (scores1, scores2)):
        np.testing.assert_allclose(lhs, rhs)
    assert e1 == pytest.approx(e2)
    assert explained1 == pytest.approx(explained2)
    assert explained1 == pytest.approx(1.0)
    assert scores1.shape == (4,)


def test_constant_training_feature_is_withheld():
    matrix = np.array([[1., 4.], [1., 5.], [1., 6.], [1., 7.]])
    with pytest.raises(ValueError, match="varying training features"):
        w82.frozen_pc1(matrix)


def test_w35_w82_real_cli_entrypoint_roundtrips_canonical_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    """Exercise the actual __main__ branch, not a mocked CLI or altered source."""
    import runpy
    import sys

    output = tmp_path / "w82-recomputed.json"
    script = ROOT / "tools/w82_semantic_diversity_diagnostic.py"
    monkeypatch.setattr(sys, "argv", [
        str(script),
        "--w79-input", str(w82.W79_INPUT),
        "--ledger", str(LEDGER),
        "--out", str(output),
    ])
    runpy.run_path(str(script), run_name="__main__")
    observed = json.loads(output.read_text(encoding="utf-8"))
    canonical = json.loads((
        ROOT / "architecture/w82/W82_SEMANTIC_DIVERSITY_DIAGNOSTIC_v0.1.json"
    ).read_text(encoding="utf-8"))
    assert observed == canonical
    assert observed["formal_credit_delta"] == 0
    assert observed["global_allocation_authority"] is False
    assert '"bt_status"' in capsys.readouterr().out


def test_w35_w82_cli_rejects_tampered_authority_without_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Invalid ledger never produces a forged canonical or admission artifact."""
    import runpy
    import sys

    data = canonical_ledger()
    data["authority_transfer"] = True
    forged = tmp_path / "bad-ledger.json"
    forged.write_text(json.dumps(data), encoding="utf-8")
    output = tmp_path / "must-not-exist.json"
    script = ROOT / "tools/w82_semantic_diversity_diagnostic.py"
    monkeypatch.setattr(sys, "argv", [
        str(script), "--w79-input", str(w82.W79_INPUT),
        "--ledger", str(forged), "--out", str(output),
    ])
    with pytest.raises(ValueError, match="authority transfer"):
        runpy.run_path(str(script), run_name="__main__")
    assert not output.exists()
