"""Lane 3: W80 observed-outcome reversal, contradiction and fail-closed guards.

Governed inputs are read (never written) from the repo. Every mutation is a
deep copy; where a test needs the mutated payload to clear the governed digest
pin it re-pins the module constant with ``monkeypatch`` so that the specific
downstream guard is the one under test. Mutated run receipts are written under
``tmp_path`` and the module's receipt path is redirected there.
"""

from __future__ import annotations

import copy
import functools
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
W79_INPUT = ROOT / "architecture" / "w79" / "W79_W78_INPUT.json"
W80_LEDGER = ROOT / "architecture" / "w80" / "W80_OBSERVED_VALIDATION_LEDGER.json"
W80_RECEIPT = ROOT / "architecture" / "w80" / "W80_GITHUB_ACTIONS_RUN_RECEIPT.json"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


w80 = _load(
    "w80_observed_outcome_validation_lane3",
    TOOLS / "w80_observed_outcome_validation.py",
)
w79 = _load("w79_deterministic_work_pca_lane3", TOOLS / "w79_deterministic_work_pca.py")

DOCS = w80.DOCS_WORKFLOW


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


@functools.lru_cache(maxsize=1)
def _frozen_inputs() -> str:
    return json.dumps([_json(W79_INPUT), _json(W80_LEDGER), _json(W80_RECEIPT)])


def inputs() -> tuple[dict, dict, dict]:
    w79_source, ledger, receipt = json.loads(_frozen_inputs())
    return w79_source, ledger, receipt


@functools.lru_cache(maxsize=1)
def _baseline_json() -> str:
    w79_source, ledger, _ = inputs()
    return json.dumps(w80.evaluate(w79_source, ledger))


def baseline() -> dict:
    return json.loads(_baseline_json())


def repin_ledger(monkeypatch, ledger: dict) -> None:
    monkeypatch.setattr(
        w80, "EXPECTED_LEDGER_CANONICAL_SHA256", w80.canonical_sha256(ledger)
    )


def install_receipt(monkeypatch, tmp_path: Path, receipt: dict) -> Path:
    path = tmp_path / "receipt.json"
    path.write_text(json.dumps(receipt), encoding="utf-8")
    monkeypatch.setattr(w80, "RUN_RECEIPT_PATH", path)
    monkeypatch.setattr(w80, "EXPECTED_RUN_RECEIPT_SHA256", w80.file_sha256(path))
    return path


def observed_states(ledger: dict) -> list[dict]:
    return [s for s in ledger["states"] if s["status"] == "OBSERVED"]


def missing_states(ledger: dict) -> list[dict]:
    return [s for s in ledger["states"] if s["status"] == "NO_ACTIONS_EVIDENCE"]


def receipt_run(receipt: dict, run_id: int) -> dict:
    return next(r for r in receipt["runs"] if int(r["run_id"]) == int(run_id))


def run_named(state: dict, name: str) -> dict:
    return next(r for r in state["runs"] if r["name"] == name)


def flip_consistently(
    ledger: dict, receipt: dict, state: dict, name: str, conclusion: str
) -> None:
    run = run_named(state, name)
    run["conclusion"] = conclusion
    receipt_run(receipt, run["run_id"])["conclusion"] = conclusion


# --------------------------------------------------------------------------- run receipt loader


def test_governed_receipt_copy_loads_when_digest_matches(monkeypatch, tmp_path):
    _, _, receipt = inputs()
    install_receipt(monkeypatch, tmp_path, receipt)
    loaded = w80.load_governed_run_receipt()
    assert loaded["run_count"] == 77
    assert len(loaded["runs"]) == 77


def test_receipt_digest_mismatch_fails_closed(monkeypatch, tmp_path):
    _, _, receipt = inputs()
    path = tmp_path / "receipt.json"
    path.write_text(json.dumps(receipt) + " ", encoding="utf-8")
    monkeypatch.setattr(w80, "RUN_RECEIPT_PATH", path)
    with pytest.raises(ValueError, match="run receipt payload mismatch"):
        w80.load_governed_run_receipt()


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        (
            "schema_version",
            "MC2-W80-GITHUB-ACTIONS-RUN-RECEIPT-9.9.9",
            "receipt schema mismatch",
        ),
        ("repository_id", 1, "receipt repository ID mismatch"),
        ("repository_full_name", "fork/ABACUS", "receipt repository mismatch"),
        ("source_state_count", 12, "source-state count mismatch"),
        ("run_count", 76, "receipt run count mismatch"),
    ],
)
def test_receipt_header_guards(monkeypatch, tmp_path, field, value, message):
    _, _, receipt = inputs()
    receipt[field] = value
    install_receipt(monkeypatch, tmp_path, receipt)
    with pytest.raises(ValueError, match=message):
        w80.load_governed_run_receipt()


def test_receipt_header_missing_counts_default_to_zero(monkeypatch, tmp_path):
    _, _, receipt = inputs()
    del receipt["source_state_count"]
    install_receipt(monkeypatch, tmp_path, receipt)
    with pytest.raises(ValueError, match="source-state count mismatch"):
        w80.load_governed_run_receipt()


# --------------------------------------------------------------------------- ledger guards


def _mut_schema(ledger):
    ledger["schema_version"] = "MC2-W80-OBSERVED-VALIDATION-OUTCOME-0.0.9"


def _mut_repository(ledger):
    ledger["repository"] = "someone/else"


def _mut_w79_identity(ledger):
    ledger["source_w79_input_canonical_sha256"] = "0" * 64


def _mut_stale_state_sha(ledger):
    # The observation is attributed to a head SHA that is not in the W79 population.
    observed_states(ledger)[0]["source_sha"] = "f" * 40


def _mut_core_drift(ledger):
    ledger["outcome_block"]["core_workflows"] = list(reversed(w80.CORE_WORKFLOWS))


def _mut_no_outcome_block(ledger):
    del ledger["outcome_block"]


def _mut_cancelled_policy(ledger):
    ledger["outcome_block"]["cancelled_policy"] = "cancelled_is_failure"


def _mut_missing_policy(ledger):
    ledger["outcome_block"]["missing_state_policy"] = "missing_is_zero"


def _mut_synthetic_runs(ledger):
    donor = observed_states(ledger)[0]["runs"][0]
    missing_states(ledger)[0]["runs"] = [copy.deepcopy(donor)]


def _mut_unknown_status(ledger):
    observed_states(ledger)[0]["status"] = "PARTIAL"


def _mut_incomplete_core(ledger):
    observed_states(ledger)[0]["runs"].pop()


def _mut_duplicate_name(ledger):
    runs = observed_states(ledger)[0]["runs"]
    runs[1]["name"] = runs[0]["name"]


def _mut_zero_run_id(ledger):
    observed_states(ledger)[0]["runs"][0]["run_id"] = 0


def _mut_absent_run_id(ledger):
    del observed_states(ledger)[0]["runs"][0]["run_id"]


def _mut_duplicate_attempt_same_state(ledger):
    runs = observed_states(ledger)[0]["runs"]
    runs[1]["run_id"] = runs[0]["run_id"]


def _mut_duplicate_attempt_cross_state(ledger):
    states = observed_states(ledger)
    states[1]["runs"][0]["run_id"] = states[0]["runs"][0]["run_id"]


def _mut_bad_event(ledger):
    observed_states(ledger)[0]["runs"][0]["event"] = "workflow_dispatch"


def _mut_bad_conclusion(ledger):
    observed_states(ledger)[0]["runs"][0]["conclusion"] = "skipped"


def _mut_unreceipted_run(ledger):
    observed_states(ledger)[0]["runs"][0]["run_id"] = 999


def _mut_target(ledger):
    ledger["population_target_count"] = 16


def _mut_covered(ledger):
    ledger["covered_state_count"] = 10


def _mut_missing_count(ledger):
    ledger["missing_state_count"] = 5


def _mut_demote_observed(ledger):
    state = observed_states(ledger)[0]
    state["status"] = "NO_ACTIONS_EVIDENCE"
    state["runs"] = []
    ledger["covered_state_count"] = 10
    ledger["missing_state_count"] = 5


LEDGER_GUARDS = [
    (_mut_schema, "outcome ledger schema mismatch"),
    (_mut_repository, "outcome ledger repository mismatch"),
    (_mut_w79_identity, "source W79 input identity mismatch"),
    (_mut_stale_state_sha, "population must exactly match W79 source states"),
    (_mut_core_drift, "core validation workflow contract drift"),
    (_mut_no_outcome_block, "core validation workflow contract drift"),
    (_mut_cancelled_policy, "cancelled validation must remain missing"),
    (_mut_missing_policy, "missing source-state validation must remain missing"),
    (_mut_synthetic_runs, "missing state cannot carry synthetic validation runs"),
    (_mut_unknown_status, "unknown W80 outcome state"),
    (_mut_incomplete_core, "requires the complete seven-workflow core"),
    (_mut_duplicate_name, "workflow names must match the core exactly"),
    (_mut_zero_run_id, "run IDs must be positive and unique"),
    (_mut_absent_run_id, "run IDs must be positive and unique"),
    (_mut_duplicate_attempt_same_state, "run IDs must be positive and unique"),
    (_mut_duplicate_attempt_cross_state, "run IDs must be positive and unique"),
    (_mut_bad_event, "event must be push or pull_request"),
    (_mut_bad_conclusion, "conclusion outside governed classes"),
    (_mut_unreceipted_run, "run 999 missing from Actions producer receipt"),
    (_mut_target, "target population must remain 15"),
    (_mut_covered, "covered-state count mismatch"),
    (_mut_missing_count, "missing-state count mismatch"),
    (_mut_demote_observed, "must preserve 11 observed / 4 missing"),
]


@pytest.mark.parametrize(
    ("mutate", "message"), LEDGER_GUARDS, ids=[m.__name__[5:] for m, _ in LEDGER_GUARDS]
)
def test_ledger_guard_rejects_malformed_record(monkeypatch, mutate, message):
    w79_source, ledger, receipt = inputs()
    mutate(ledger)
    repin_ledger(monkeypatch, ledger)
    with pytest.raises(ValueError, match=message):
        w80.validate_ledger(ledger, w79_source, w79, receipt)


def test_ledger_digest_pin_runs_before_any_field_guard():
    w79_source, ledger, receipt = inputs()
    _mut_schema(ledger)
    with pytest.raises(ValueError, match="governed outcome ledger payload mismatch"):
        w80.validate_ledger(ledger, w79_source, w79, receipt)


# --------------------------------------------------------------------------- receipt/ledger contradiction


def test_duplicate_run_ids_in_receipt_fail_closed():
    w79_source, ledger, receipt = inputs()
    receipt["runs"].append(copy.deepcopy(receipt["runs"][0]))
    with pytest.raises(ValueError, match="receipt contains duplicate run IDs"):
        w80.validate_ledger(ledger, w79_source, w79, receipt)


def test_receipt_run_not_claimed_by_ledger_fails_closed():
    w79_source, ledger, receipt = inputs()
    extra = copy.deepcopy(receipt["runs"][0])
    extra["run_id"] = 1
    receipt["runs"].append(extra)
    with pytest.raises(ValueError, match="receipt and ledger run sets differ"):
        w80.validate_ledger(ledger, w79_source, w79, receipt)


def test_receipt_missing_a_claimed_run_fails_closed():
    w79_source, ledger, receipt = inputs()
    claimed = observed_states(ledger)[0]["runs"][0]["run_id"]
    receipt["runs"] = [r for r in receipt["runs"] if int(r["run_id"]) != int(claimed)]
    with pytest.raises(
        ValueError, match=f"run {claimed} missing from Actions producer receipt"
    ):
        w80.validate_ledger(ledger, w79_source, w79, receipt)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("repository_id", 42),
        ("repository_full_name", "GBOGEB/OTHER"),
        ("source_sha", "e" * 40),
        ("workflow_name", "Some Other Workflow"),
        ("event", "pull_request_target"),
    ],
)
def test_authoritative_binding_contradiction_fails_closed(field, value):
    w79_source, ledger, receipt = inputs()
    run_id = observed_states(ledger)[0]["runs"][0]["run_id"]
    receipt_run(receipt, run_id)[field] = value
    with pytest.raises(ValueError, match=f"binding mismatch for {run_id}:{field}"):
        w80.validate_ledger(ledger, w79_source, w79, receipt)


@pytest.mark.parametrize(
    ("before", "after"), [("success", "failure"), ("failure", "success")]
)
def test_ledger_reversal_contradicted_by_receipt_is_not_credited(
    monkeypatch, before, after
):
    w79_source, ledger, receipt = inputs()
    run = next(
        r
        for s in observed_states(ledger)
        for r in s["runs"]
        if r["conclusion"] == before
    )
    run["conclusion"] = after
    repin_ledger(monkeypatch, ledger)
    with pytest.raises(
        ValueError, match=f"binding mismatch for {run['run_id']}:conclusion"
    ):
        w80.validate_ledger(ledger, w79_source, w79, receipt)


def test_receipt_reversal_contradicting_ledger_is_not_credited():
    w79_source, ledger, receipt = inputs()
    run = next(
        r
        for s in observed_states(ledger)
        for r in s["runs"]
        if r["conclusion"] == "success"
    )
    receipt_run(receipt, run["run_id"])["conclusion"] = "failure"
    with pytest.raises(
        ValueError, match=f"binding mismatch for {run['run_id']}:conclusion"
    ):
        w80.validate_ledger(ledger, w79_source, w79, receipt)


# --------------------------------------------------------------------------- consistent reversals via evaluate


def _evaluate_with(monkeypatch, tmp_path, ledger, receipt):
    w79_source, _, _ = inputs()
    repin_ledger(monkeypatch, ledger)
    install_receipt(monkeypatch, tmp_path, receipt)
    return w80.evaluate(w79_source, ledger)


def test_consistent_green_to_red_reversal_moves_the_observed_row(monkeypatch, tmp_path):
    base = baseline()  # computed against the governed pins, before re-pinning
    _, ledger, receipt = inputs()
    state = next(
        s
        for s in observed_states(ledger)
        if all(r["conclusion"] == "success" for r in s["runs"] if r["name"] != DOCS)
    )
    flip_consistently(ledger, receipt, state, "Format Check", "failure")

    result = _evaluate_with(monkeypatch, tmp_path, ledger, receipt)

    before = next(r for r in base["outcome_rows"] if r["label"] == state["label"])
    after = next(r for r in result["outcome_rows"] if r["label"] == state["label"])
    assert after["core_failure_count"] == before["core_failure_count"] + 1
    assert after["core_success_count"] == before["core_success_count"] - 1
    assert after["core_pass_fraction"] < before["core_pass_fraction"]
    assert result["primary_outcome"] != base["primary_outcome"]
    assert (
        result["source_outcome_ledger_canonical_sha256"]
        == w80.EXPECTED_LEDGER_CANONICAL_SHA256
    )
    assert result["status"] == "OUTCOME_VALIDATION_NOT_SUPPORTED"
    assert result["pairwise_events"] == []


def test_consistent_red_to_green_docs_reversal_updates_secondary_outcome(
    monkeypatch, tmp_path
):
    base = baseline()["secondary_outcome"]  # before re-pinning
    _, ledger, receipt = inputs()
    state = next(
        s
        for s in observed_states(ledger)
        if run_named(s, DOCS)["conclusion"] == "failure"
    )
    flip_consistently(ledger, receipt, state, DOCS, "success")

    result = _evaluate_with(monkeypatch, tmp_path, ledger, receipt)

    assert result["secondary_outcome"]["positive_count"] == base["positive_count"] - 1
    assert result["secondary_outcome"]["negative_count"] == base["negative_count"] + 1
    row = next(r for r in result["outcome_rows"] if r["label"] == state["label"])
    assert row["docs_validation_failure"] == 0
    assert result["bt_status"] == "WITHHELD_PC1_NOT_VALIDATED_AGAINST_OBSERVED_OUTCOMES"


def test_two_cancelled_core_runs_leave_state_under_executed(monkeypatch, tmp_path):
    _, ledger, receipt = inputs()
    state = next(
        s
        for s in observed_states(ledger)
        if all(r["conclusion"] != "cancelled" for r in s["runs"])
    )
    for name in ("Format Check", "YAML Validation"):
        flip_consistently(ledger, receipt, state, name, "cancelled")
    with pytest.raises(ValueError, match="insufficient executed core validators"):
        _evaluate_with(monkeypatch, tmp_path, ledger, receipt)


def test_cancelled_docs_run_is_not_credited_as_an_outcome(monkeypatch, tmp_path):
    _, ledger, receipt = inputs()
    state = next(
        s
        for s in observed_states(ledger)
        if all(r["conclusion"] != "cancelled" for r in s["runs"])
    )
    flip_consistently(ledger, receipt, state, DOCS, "cancelled")
    with pytest.raises(
        ValueError, match="docs outcome must be an observed success/failure"
    ):
        _evaluate_with(monkeypatch, tmp_path, ledger, receipt)


def test_evaluate_rejects_tampered_receipt_file_before_scoring(monkeypatch, tmp_path):
    w79_source, ledger, receipt = inputs()
    receipt["run_count"] = 78
    path = tmp_path / "receipt.json"
    path.write_text(json.dumps(receipt), encoding="utf-8")
    monkeypatch.setattr(w80, "RUN_RECEIPT_PATH", path)
    with pytest.raises(ValueError, match="run receipt payload mismatch"):
        w80.evaluate(w79_source, ledger)


def test_evaluate_result_is_self_hashing():
    # Determinism across runs is asserted by the CLI test (fresh evaluate == baseline).
    result = baseline()
    body = {k: v for k, v in result.items() if k != "receipt_sha256"}
    assert result["receipt_sha256"] == w80.canonical_sha256(body)
    assert (
        result["source_actions_run_receipt_sha256"] == w80.EXPECTED_RUN_RECEIPT_SHA256
    )


# --------------------------------------------------------------------------- statistical helpers


def test_load_module_without_loader_raises(tmp_path):
    target = tmp_path / "not_python.txt"
    target.write_text("x = 1\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="unable to load"):
        w80.load_module("lane3_not_python", target)


def test_average_ranks_assigns_mean_rank_to_ties():
    assert w80.average_ranks(np.array([3.0, 1.0, 3.0, 2.0])).tolist() == [
        3.5,
        1.0,
        3.5,
        2.0,
    ]


def test_correlation_rejects_constant_input():
    with pytest.raises(ValueError, match="non-constant inputs"):
        w80.correlation(np.array([1.0, 1.0, 1.0]), np.array([1.0, 2.0, 3.0]))


def test_exact_spearman_constant_outcome_is_rejected_by_correlation_guard_first():
    # The dedicated "at least two outcome values" guard (line 116) is shadowed:
    # spearman_rho(a, b) runs first and a constant b already fails there.
    with pytest.raises(ValueError, match="correlation requires non-constant inputs"):
        w80.exact_multiset_spearman_p(
            np.array([1.0, 2.0, 3.0]), np.array([0.5, 0.5, 0.5])
        )


def test_exact_spearman_rejects_population_above_bound():
    a = np.arange(13, dtype=float)
    b = np.array([0.0, 1.0] * 6 + [0.0])
    with pytest.raises(ValueError, match="bounded to n<=12"):
        w80.exact_multiset_spearman_p(a, b)


def test_exact_spearman_enumerates_multiset_permutations():
    p, total = w80.exact_multiset_spearman_p(
        np.array([1.0, 2.0, 3.0, 4.0]), np.array([0.0, 0.0, 1.0, 1.0])
    )
    assert total == 6
    assert p == pytest.approx(2 / 6)


def test_loocv_rejects_constant_outcome():
    with pytest.raises(ValueError, match="requires outcome variance"):
        w80.loocv_linear_r2(np.array([1.0, 2.0, 3.0]), np.array([4.0, 4.0, 4.0]))


def test_auc_requires_both_classes_and_counts_ties():
    with pytest.raises(ValueError, match="both outcome classes"):
        w80.auc_score(np.array([1, 1, 1]), np.array([0.1, 0.2, 0.3]))
    assert w80.auc_score(np.array([1, 0]), np.array([0.5, 0.5])) == 0.5
    p, total = w80.exact_auc_p(np.array([0, 0, 1, 1]), np.array([0.1, 0.2, 0.3, 0.4]))
    assert total == 6
    assert p == pytest.approx(2 / 6)


def _pc1_rows(values):
    return [
        {"source_sha": f"sha{i}", "semantic_work_vector": {"f": f, "g": g}}
        for i, (f, g) in enumerate(values)
    ]


def test_semantic_pc1_rejects_constant_feature():
    rows = _pc1_rows([(1, 5), (2, 5), (3, 5)])
    with pytest.raises(ValueError, match="requires varying W79 semantic features"):
        w80.semantic_pc1({"semantic_work_features": ["f", "g"]}, rows)


@pytest.mark.parametrize(
    "values",
    [
        [(1, 1), (2, 2), (3, 3.1), (4, 4)],  # eigh already returns a positive pivot
        [
            (1, -2),
            (2, -4.5),
            (3, -6),
            (4, -8.2),
        ],  # eigh returns a negative pivot -> flipped
    ],
)
def test_semantic_pc1_sign_is_canonical(values):
    pc1 = w80.semantic_pc1({"semantic_work_features": ["f", "g"]}, _pc1_rows(values))
    scores = list(pc1["scores"].values())
    # Canonical orientation: the dominant feature (f, increasing) maps to increasing scores.
    assert scores == sorted(scores)
    assert pc1["explained_variance_ratio"] > 0.9


# --------------------------------------------------------------------------- CLI


def test_main_writes_receipt_and_prints_same_payload(monkeypatch, tmp_path, capsys):
    out = tmp_path / "nested" / "dir" / "w80.json"
    monkeypatch.setattr(sys, "argv", ["w80", "--out", str(out)])

    assert w80.main() is None

    written = json.loads(out.read_text(encoding="utf-8"))
    printed = json.loads(capsys.readouterr().out)
    assert written == printed == baseline()
    assert out.read_text(encoding="utf-8").endswith("}\n")


def test_main_requires_out_argument(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["w80"])
    with pytest.raises(SystemExit) as excinfo:
        w80.main()
    assert excinfo.value.code == 2
    assert "--out" in capsys.readouterr().err


def test_main_fails_closed_on_reversed_ledger_and_writes_nothing(monkeypatch, tmp_path):
    _, ledger, _ = inputs()
    run = next(
        r
        for s in observed_states(ledger)
        for r in s["runs"]
        if r["conclusion"] == "success"
    )
    run["conclusion"] = "failure"
    forged = tmp_path / "ledger.json"
    forged.write_text(json.dumps(ledger), encoding="utf-8")
    out = tmp_path / "out.json"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "w80",
            "--w79-input",
            str(W79_INPUT),
            "--outcome-ledger",
            str(forged),
            "--out",
            str(out),
        ],
    )
    with pytest.raises(ValueError, match="governed outcome ledger payload mismatch"):
        w80.main()
    assert not out.exists()


def test_main_missing_ledger_artifact_raises(monkeypatch, tmp_path):
    out = tmp_path / "out.json"
    monkeypatch.setattr(
        sys,
        "argv",
        ["w80", "--outcome-ledger", str(tmp_path / "absent.json"), "--out", str(out)],
    )
    with pytest.raises(FileNotFoundError):
        w80.main()
    assert not out.exists()
