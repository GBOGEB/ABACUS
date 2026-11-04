"""Behaviour tests for scripts/qps_w189_validate_federation_sample4.py.

The four input JSON paths are redirected to synthetic documents in tmp_path;
each guard is exercised by mutating one field of an otherwise valid set.
"""

import json

import pytest

from tests.coverage_waves.lane_b._l2_loader import load

mod = load(
    "scripts/qps_w189_validate_federation_sample4.py",
    name="abn_w5_validate_federation_sample4",
)

SAMPLE4 = "FED-SAMPLE-004"
CARRIER = "766f064e561c28e41cc70dd1a17a29cd71343da5"


def _valid():
    control = {
        "wave": "W189",
        "sample_id": SAMPLE4,
        "namespace": {"w188": "OCCUPIED_VISUAL"},
        "surface": {"repaired_carrier_head": CARRIER},
        "observed_runtime": {
            "exact_hash_mirror_pass": {
                "run_id": 34868622367,
                "job_id": 104058671463,
                "runner_id": 7,
                "result": "PASS",
            }
        },
        "measurement": {
            "breadth": {"numerator": 30, "denominator": 30},
            "depth_candidate": {"numerator": 7, "denominator": 8, "value": 0.875},
        },
        "formal_credit_delta": {"engineering": 0, "release": 0},
    }
    rows = [
        {"sample_id": "S1", "accepted_sample": 1, "depth_ratio": 1.0},
        {"sample_id": "S2", "accepted_sample": 1, "depth_ratio": 1.0},
        {"sample_id": "S3", "accepted_sample": 1, "depth_ratio": 1.0},
        {"sample_id": SAMPLE4, "accepted_sample": 0, "depth_ratio": 0.875},
    ]
    matrix = {
        "rows": rows,
        "analytics_gate": {"pca_state": "N4_STABILITY_CANDIDATE_WITHHELD_X"},
        "candidate_n4_stability": {
            "pc1_loading_congruence_abs": 0.999,
            "pc2_loading_congruence_abs": 0.11,
        },
    }
    pairwise = {
        "outcomes": [1, 2, 3, 4],
        "bt_gate": {
            "repeated_comparable_component": {
                "observed_comparisons": 2,
                "graph_connected": True,
                "unregularized_mle_state": "SEPARATED_2_TO_0_NO_FINITE_MLE",
            },
            "global_connected_comparison_graph": False,
            "global_fit_state": "WITHHELD_PENDING",
        },
    }
    census = {
        "denominator_model": {
            "accessible_repository_universe": {"value": None},
            "mission_relevant_governed_surface_universe": {"value": None},
        },
        "confirmed_core_repositories": ["r1", "r2", "r3", "r4", "r5", "r6"],
    }
    return control, matrix, pairwise, census


def _install(tmp_path, monkeypatch, docs):
    names = ("CONTROL", "MATRIX", "PAIRWISE", "CENSUS")
    for name, doc in zip(names, docs):
        path = tmp_path / (name.lower() + ".json")
        path.write_text(json.dumps(doc), encoding="utf-8")
        monkeypatch.setattr(mod, name, path)


def test_load_reads_json(tmp_path):
    path = tmp_path / "x.json"
    path.write_text('{"k": [1, 2]}', encoding="utf-8")
    assert mod.load(path) == {"k": [1, 2]}


def test_require_passes_and_rejects():
    assert mod.require(True, "unused") is None
    with pytest.raises(SystemExit, match="W189 REJECT: boom"):
        mod.require(False, "boom")


def test_main_passes_on_valid_documents(tmp_path, monkeypatch, capsys):
    _install(tmp_path, monkeypatch, _valid())
    mod.main()
    assert "W189 PASS: sample4 candidate bound" in capsys.readouterr().out


def _set(doc, path, value):
    target = doc
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value


MUTATIONS = [
    (0, ("wave",), "W188", "wrong wave"),
    (0, ("namespace", "w188"), "FREE", "W188 collision guard missing"),
    (0, ("surface", "repaired_carrier_head"), "0" * 40, "carrier head mismatch"),
    (0, ("observed_runtime", "exact_hash_mirror_pass", "job_id"), 1, "runtime vector"),
    (0, ("observed_runtime", "exact_hash_mirror_pass", "runner_id"), 0, "real runner"),
    (0, ("measurement", "breadth", "denominator"), 31, "B denominator mismatch"),
    (0, ("measurement", "depth_candidate", "numerator"), 6, "D candidate mismatch"),
    (0, ("measurement", "depth_candidate", "value"), 0.5, "D candidate value"),
    (0, ("formal_credit_delta", "release"), 1, "formal credit changed"),
    (1, ("rows", 0, "accepted_sample"), 0, "sample4 admitted before proof"),
    (1, ("rows", 3, "depth_ratio"), 0.5, "sample4 candidate state weakened"),
    (1, ("analytics_gate", "pca_state"), "N4_ADMITTED", "n4 PCA admitted early"),
    (1, ("candidate_n4_stability", "pc1_loading_congruence_abs"), 0.9, "PC1 stab"),
    (1, ("candidate_n4_stability", "pc2_loading_congruence_abs"), 0.5, "PC2 rot"),
    (2, ("outcomes",), [1], "pairwise outcome count mismatch"),
    (
        2,
        ("bt_gate", "repeated_comparable_component", "observed_comparisons"),
        1,
        "transport repeat missing",
    ),
    (
        2,
        ("bt_gate", "repeated_comparable_component", "graph_connected"),
        1,
        "transport component not connected",
    ),
    (
        2,
        ("bt_gate", "repeated_comparable_component", "unregularized_mle_state"),
        "FINITE",
        "complete separation guard missing",
    ),
    (2, ("bt_gate", "global_connected_comparison_graph"), True, "fabricated"),
    (2, ("bt_gate", "global_fit_state"), "FITTED", "global BT fitted prematurely"),
    (
        3,
        ("denominator_model", "accessible_repository_universe", "value"),
        100,
        "raw repo universe incorrectly frozen",
    ),
    (
        3,
        ("denominator_model", "mission_relevant_governed_surface_universe", "value"),
        5,
        "surface denominator fabricated",
    ),
    (3, ("confirmed_core_repositories",), ["r1"], "core census unexpectedly"),
]


@pytest.mark.parametrize("doc_index, path, value, message", MUTATIONS)
def test_main_rejects_each_guard(
    tmp_path, monkeypatch, doc_index, path, value, message
):
    docs = list(_valid())
    _set(docs[doc_index], path, value)
    _install(tmp_path, monkeypatch, docs)
    with pytest.raises(SystemExit) as excinfo:
        mod.main()
    assert message in str(excinfo.value)


def test_main_rejects_matrix_without_four_rows(tmp_path, monkeypatch):
    docs = list(_valid())
    docs[1]["rows"] = docs[1]["rows"][:3]
    _install(tmp_path, monkeypatch, docs)
    with pytest.raises(SystemExit, match="matrix must have four rows"):
        mod.main()
