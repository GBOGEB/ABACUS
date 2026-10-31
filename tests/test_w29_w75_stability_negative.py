"""W29 W75 source-owned regression expansion: freeze PC1, fail closed on
invalid sample geometry, singular environment projection and forged identity.
No change to W75 production logic or acceptance thresholds.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import w75_stability_diagnostic as w75  # noqa: E402


def runtime_rows() -> list[dict]:
    rows = []
    for repeat in range(1, 4):
        for i in range(5):
            executed = float(20 + 2 * i + repeat + (i % 2) * repeat)
            probe = float(5 + i + repeat / 10)
            rows.append({
                "source_sha": f"{i + 1:040x}", "repeat": repeat,
                "steps_executed_total": float(10 + 3 * i + 2 * repeat),
                "queue_seconds_mean": float(7 + i * i + repeat),
                "execute_seconds_total": executed,
                "probe_execute_seconds": probe,
                "orchestration_overhead_seconds": executed - probe,
                "evidence_emit_count": float(4 + i + 3 * repeat + i * repeat),
                "runtime_pc1_frozen_score": float(i + 0.3 * repeat + .04 * i * repeat),
            })
    return rows


def semantic_rows() -> list[dict]:
    return [
        {"source_sha": f"{i + 1:040x}", "consumer_penetration_rate": .2 + .03 * i,
         "consumer_edge_density": .8 + .07 * i + .01 * (i % 2),
         "consumer_degree_concentration": .5 + .02 * i + .015 * (i % 3)}
        for i in range(5)
    ]


def telemetry(features: list[str]) -> dict:
    return {"components": [{
        "pc": 1, "eigenvalue": float(len(features)),
        "loadings": {key: 1.0 for key in features},
    }]}


def write(path: Path, value: object) -> Path:
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


@pytest.mark.parametrize("bad_eigen", [0, -1, -50])
def test_frozen_axis_rejects_nonpositive_eigenvalues(bad_eigen: int) -> None:
    block = telemetry(["a"])
    block["components"][0]["eigenvalue"] = bad_eigen
    with pytest.raises(ValueError, match="PC1 eigenvalue must be positive"):
        w75.vector_from_pc1(block, ["a"])


def test_frozen_axis_does_not_refit_weights() -> None:
    vector = w75.vector_from_pc1(telemetry(["a", "b"]), ["a", "b"])
    assert vector == pytest.approx({"a": 1 / math.sqrt(2), "b": 1 / math.sqrt(2)})


@pytest.mark.parametrize("matrix,vector", [
    ([[1., 2.], [2., 4.]], [3., 6.]),
    ([[0., 0.], [0., 1.]], [0., 3.]),
])
def test_singular_environment_design_rejected(matrix: list, vector: list) -> None:
    with pytest.raises(ValueError, match="singular deconfounding design matrix"):
        w75.solve_linear(matrix, vector)


def test_gaussian_elimination_pivots_without_mutating_inputs() -> None:
    matrix = [[0., 1.], [2., 3.]]
    rhs = [2., 8.]
    assert w75.solve_linear(matrix, rhs) == pytest.approx([1., 2.])
    assert matrix == [[0., 1.], [2., 3.]]
    assert rhs == [2., 8.]


def test_residuals_preserve_intrinsic_probe_and_remove_fitted_environment() -> None:
    rows = runtime_rows()
    out, metadata = w75.residualize(rows)
    assert len(out) == 15
    assert metadata["intrinsic_probe_time_regressed_out"] is False
    assert metadata["causal_inference_authority"] is False
    assert "runtime_pc1_environment_residual" not in rows[0]
    residuals = [r["runtime_pc1_environment_residual"] for r in out]
    assert sum(residuals) == pytest.approx(0., abs=1e-8)
    for feature in ("queue_seconds_mean", "orchestration_overhead_seconds"):
        assert sum(r[feature] * r["runtime_pc1_environment_residual"] for r in out) == pytest.approx(0., abs=1e-7)


def test_environment_perfectly_confounded_inputs_are_withheld() -> None:
    rows = runtime_rows()
    for row in rows:
        row["orchestration_overhead_seconds"] = row["queue_seconds_mean"] * 2
    with pytest.raises(ValueError, match="singular deconfounding design matrix"):
        w75.residualize(rows)


@pytest.mark.parametrize("values,expect", [
    ([0., 0., 0.], None),
    ([-1., 1.], None),
    ([2., 2., 2.], 0.),
    ([2., 4.], math.sqrt(2) / 3),
])
def test_cv_handles_zero_and_stable_means(values: list, expect: float | None) -> None:
    result = w75.cv(values)
    if expect is None:
        assert result is None
    else:
        assert result == pytest.approx(expect)


@pytest.mark.parametrize("group_count,repeats", [(4, 3), (5, 2), (6, 3), (5, 4)])
def test_icc_rejects_noncomparable_repeat_geometry(group_count: int, repeats: int) -> None:
    rows = [{"source_sha": f"{i:040x}", "v": float(i + r)}
            for i in range(group_count) for r in range(repeats)]
    with pytest.raises(ValueError, match="five source SHAs with three repeats"):
        w75.icc_one_way(rows, "v")


def test_icc_no_variation_is_unknown_not_zero() -> None:
    rows = [{"source_sha": f"{i:040x}", "v": 3.0}
            for i in range(5) for _ in range(3)]
    assert w75.icc_one_way(rows, "v") is None


def test_icc_identical_repeats_reproduces_one() -> None:
    rows = [{"source_sha": f"{i:040x}", "v": float(i)}
            for _ in range(3) for i in range(5)]
    assert w75.icc_one_way(rows, "v") == pytest.approx(1.0)


def test_pairwise_rank_reversal_is_detected_not_mislabeled_stable() -> None:
    rows = [{"source_sha": f"{i:040x}", "repeat": r,
             "v": float(i if r < 3 else 4 - i)}
            for r in range(1, 4) for i in range(5)]
    pairs = w75.pairwise_rank_stability(rows, "v")
    assert len(pairs["pairs"]) == 3
    assert pairs["median_spearman_rho"] == pytest.approx(-1.0)


def test_frozen_project_does_not_mutate_raw_rows() -> None:
    raw = runtime_rows()
    block = telemetry(w75.RUNTIME_FEATURES)
    result = w75.project_rows(raw, raw, block, w75.RUNTIME_FEATURES)
    assert len(result) == 15
    assert all(math.isfinite(x["runtime_pc1_frozen_score"]) for x in result)
    assert result[0] is not raw[0]
    assert result[0]["runtime_pc1_frozen_score"] != raw[0]["runtime_pc1_frozen_score"]


def test_semantic_association_reports_three_independent_repeats() -> None:
    sem_rows = semantic_rows()
    score = w75.semantic_scores(sem_rows, telemetry(w75.SEMANTIC_FEATURES))
    rows = runtime_rows()
    associations = w75.association_by_repeat(rows, score, "runtime_pc1_frozen_score")
    assert [x["repeat"] for x in associations] == [1, 2, 3]
    assert all(x["pearson_r"] is not None for x in associations)
    assert all(x["spearman_rho"] is not None for x in associations)


def test_nested_rounding_keeps_unknown_as_null() -> None:
    assert w75.round_tree({"x": [1.23456789, None, {"n": .333333333}]}) == {
        "x": [1.234568, None, {"n": .333333}],
    }


def test_per_source_repeatability_has_real_denominators() -> None:
    rows, _ = w75.residualize(runtime_rows())
    stats = w75.per_sha_stats(rows)
    assert len(stats) == 5
    assert all(row["repeat_count"] == 3 for row in stats)
    assert all(row["queue_seconds_mean"]["min"] <= row["queue_seconds_mean"]["max"] for row in stats)


def invoke_cli(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
               runtime: list[dict], semantic: list[dict]) -> dict:
    files = {
        "runtime-rows": write(tmp_path / "runtime.json", runtime),
        "runtime-baseline-rows": write(
            tmp_path / "baseline.json",
            [dict(row, observation_class="runtime", execution_state="PASS") for row in runtime],
        ),
        "runtime-telemetry": write(tmp_path / "runtime-pca.json", {
            "runtime_pca": telemetry(w75.RUNTIME_FEATURES),
        }),
        "semantic-rows": write(tmp_path / "semantic.json", semantic),
        "semantic-telemetry": write(tmp_path / "semantic-pca.json", {
            "semantic_pca": telemetry(w75.SEMANTIC_FEATURES),
        }),
        "out": tmp_path / "w75-receipt.json",
    }
    args = ["w75"]
    for key, path in files.items():
        args.extend([f"--{key}", str(path)])
    monkeypatch.setattr(sys, "argv", args)
    w75.main()
    return json.loads(files["out"].read_text())


def test_complete_w75_cli_keeps_nonpromotional_authority(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    result = invoke_cli(tmp_path, monkeypatch, runtime_rows(), semantic_rows())
    assert result["observation_count"] == 15
    assert result["source_state_count"] == 5
    assert result["repeat_count_per_source"] == 3
    assert result["joint_pca_performed"] is False
    assert result["global_allocation_authority"] is False
    assert result["engineering_compliance_release_authority"] is False
    assert result["bt_status"].startswith("WITHHELD")
    assert len(result["per_source_repeatability"]) == 5
    assert len(result["receipt_sha256"]) == 64
    assert json.loads(capsys.readouterr().out) == result


def test_w75_cli_rejects_missing_fifteenth_observation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(ValueError, match="exactly 15 measured runtime rows"):
        invoke_cli(tmp_path, monkeypatch, runtime_rows()[:-1], semantic_rows())


def test_w75_cli_rejects_foreign_semantic_sha(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    semantic = semantic_rows()
    semantic[0]["source_sha"] = "f" * 40
    with pytest.raises(ValueError, match="exact-pair on five SHAs"):
        invoke_cli(tmp_path, monkeypatch, runtime_rows(), semantic)
