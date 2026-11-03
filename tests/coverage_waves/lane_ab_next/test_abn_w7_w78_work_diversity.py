"""Gap tests for tools/w78_work_diversity.py.

The bare sibling import chain (w78_deterministic_work_probe -> w72/w77) is
loaded by path and supplied through ``deps`` so nothing leaks onto sys.path.
Covers the replay-panel guards not exercised by tests/test_w78_deterministic_work.py,
the rank helper edge cases, ``load`` and the CLI.
"""

import json
import sys

import pytest

from tests.coverage_waves.lane_b._l2_loader import load

w72 = load("tools/w72_semantic_census.py", name="abn_w7_w78_w72")
w77 = load(
    "tools/w77_instrumented_semantic_census.py",
    name="abn_w7_w78_w77",
    deps={"w72_semantic_census": w72},
)
probe = load(
    "tools/w78_deterministic_work_probe.py",
    name="abn_w7_w78_probe",
    deps={"w72_semantic_census": w72, "w77_instrumented_semantic_census": w77},
)
mod = load(
    "tools/w78_work_diversity.py",
    name="abn_w7_w78_work_diversity",
    deps={"w78_deterministic_work_probe": probe},
)


def _receipts():
    rows = []
    for index in range(15):
        work = {
            feature: (index + 1) * (pos + 2)
            for pos, feature in enumerate(probe.WORK_FEATURES)
        }
        semantic = {f: work[f] for f in probe.SEMANTIC_WORK_FEATURES}
        feature_row = {"source_sha": "sha-" + str(index), "n": index}
        for repeat in (1, 2):
            rows.append(
                {
                    "source_sha": "sha-" + str(index),
                    "matrix_label": "s" + str(index),
                    "repeat": repeat,
                    "execution_state": "PASS",
                    "semantic_parity_with_w72": True,
                    "feature_row": feature_row,
                    "feature_row_sha256": probe.canonical_sha256(feature_row),
                    "work_vector": work,
                    "work_vector_sha256": probe.canonical_sha256(work),
                    "semantic_work_vector": semantic,
                    "semantic_work_vector_sha256": probe.canonical_sha256(semantic),
                }
            )
    return rows


def _drop_last(rows):
    rows.pop()


def _merge_shas(rows):
    for row in rows[2:4]:
        row["source_sha"] = rows[0]["source_sha"]
    rows[0]["source_sha"] = "sha-extra-a"
    rows[1]["source_sha"] = "sha-extra-b"


def _same_repeat(rows):
    rows[1]["repeat"] = 1


def _non_pass(rows):
    rows[0]["execution_state"] = "FAIL"


def _parity(rows):
    rows[1]["semantic_parity_with_w72"] = False


def _label_drift(rows):
    rows[1]["matrix_label"] = "other"


def _label_collision(rows):
    rows[2]["matrix_label"] = rows[0]["matrix_label"]
    rows[3]["matrix_label"] = rows[0]["matrix_label"]


@pytest.mark.parametrize(
    "mutate,message",
    [
        (_drop_last, "exactly 30 receipts"),
        (_merge_shas, "15 distinct source SHAs"),
        (_same_repeat, "unbalanced W78 replay panel"),
        (_non_pass, "non-PASS W78 receipt"),
        (_parity, "semantic parity failure"),
        (_label_drift, "matrix label drift"),
        (_label_collision, "matrix label collision"),
    ],
)
def test_validate_guards(mutate, message):
    rows = _receipts()
    mutate(rows)
    with pytest.raises(ValueError, match=message):
        mod.validate(rows)


def test_centered_rank_empty_matrix_is_zero():
    assert mod.centered_scaled_rank([], ("a",), "v") == 0


def test_centered_rank_never_exceeds_row_count_minus_one():
    rows = [{"v": {"a": 1, "b": 5, "c": 2}}, {"v": {"a": 3, "b": 1, "c": 7}}]
    assert mod.centered_scaled_rank(rows, ("a", "b", "c"), "v") == 1


def test_centered_rank_non_finite_values_saturate_at_row_count():
    rows = [{"v": {"a": "nan", "b": "nan"}}]
    assert mod.centered_scaled_rank(rows, ("a", "b"), "v") == 1


def test_main_loads_receipts_and_writes_result(monkeypatch, tmp_path, capsys):
    paths = []
    for index, row in enumerate(_receipts()):
        path = tmp_path / ("r" + str(index) + ".json")
        path.write_text(json.dumps(row), encoding="utf-8")
        paths.append(str(path))
    assert len(mod.load(paths[:2])) == 2
    out = tmp_path / "diversity.json"
    monkeypatch.setattr(sys, "argv", ["w78", *paths, "--out", str(out)])
    assert mod.main() is None
    printed = json.loads(capsys.readouterr().out)
    written = json.loads(out.read_text(encoding="utf-8"))
    assert printed == written
    assert written["target_count"] == 15
    assert written["observation_count"] == 30
    assert written["distinct_work_state_count"] == 15
