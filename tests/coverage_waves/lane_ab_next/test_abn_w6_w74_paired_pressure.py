"""Gap tests for tools/w74_paired_pressure.py.

Covers the PC1 / eigenvalue / constant-feature guards and the CLI receipt,
including the exact-pair rejection and the withheld-variation status.
"""

import hashlib
import json
import sys

import pytest

from tests.coverage_waves.lane_b._l2_loader import load

mod = load("tools/w74_paired_pressure.py", name="abn_w6_w74_paired_pressure")

SHAS = ["s" + str(i) for i in range(5)]


def _block(features, eig=2.0):
    return {
        "components": [
            {"pc": 2, "eigenvalue": 1.0, "loadings": {}},
            {"pc": 1, "eigenvalue": eig, "loadings": {f: 0.5 for f in features}},
        ]
    }


def test_load_reads_json(tmp_path):
    target = tmp_path / "x.json"
    target.write_text(json.dumps({"k": 1}), encoding="utf-8")
    assert mod.load(str(target)) == {"k": 1}


def test_pc1_missing_raises():
    with pytest.raises(ValueError, match="PC1 missing"):
        mod.pc1({"components": [{"pc": 2}]})
    with pytest.raises(ValueError, match="PC1 missing"):
        mod.pc1({"components": None})


def test_mean_sd_constant_feature_raises():
    with pytest.raises(ValueError, match="constant: f"):
        mod.mean_sd([{"f": 1}, {"f": 1}], ["f"])


def test_frozen_scores_projection_and_eigen_guard():
    rows = [
        {"source_sha": "x", "f": 1.0, "g": 3.0},
        {"source_sha": "y", "f": 3.0, "g": 1.0},
    ]
    scores = mod.frozen_scores(rows, rows, _block(["f", "g"], eig=4.0), ["f", "g"])
    assert scores == {"x": 0.0, "y": 0.0}
    single = mod.frozen_scores(rows, rows, _block(["f"], eig=4.0), ["f"])
    sd = 2**0.5
    assert single["x"] == pytest.approx(round(-1.0 / sd * 0.25, 6))
    with pytest.raises(ValueError, match="eigenvalue must be positive"):
        mod.frozen_scores(rows, rows, _block(["f"], eig=0.0), ["f"])


def _runtime_row(sha, i):
    return dict(
        source_sha=sha,
        steps_executed_total=10 + i,
        queue_seconds_mean=1.0 + i * i,
        execute_seconds_total=5.0 + 2 * i,
        evidence_emit_count=3 + (i % 2),
    )


def _semantic_row(sha, i, constant=False):
    value = 0.0 if constant else float(i)
    return dict(
        source_sha=sha,
        consumer_penetration_rate=value,
        consumer_edge_density=value * 2,
        consumer_degree_concentration=value + 1,
    )


def _write(path, obj):
    path.write_text(json.dumps(obj), encoding="utf-8")
    return str(path)


def _files(tmp_path, runtime_shas, semantic_rows, semantic_block=None):
    runtime_rows = [_runtime_row(sha, i) for i, sha in enumerate(runtime_shas)]
    baseline = [
        dict(row, observation_class="runtime", execution_state="PASS")
        for row in runtime_rows
    ]
    baseline.append(
        dict(runtime_rows[0], observation_class="semantic", execution_state="PASS")
    )
    baseline.append(
        dict(runtime_rows[0], observation_class="runtime", execution_state="FAIL")
    )
    baseline.append(
        dict(
            runtime_rows[0],
            observation_class="runtime",
            execution_state="PASS",
            queue_seconds_mean=None,
        )
    )
    return [
        "--runtime-rows",
        _write(tmp_path / "rr.json", runtime_rows),
        "--runtime-baseline-rows",
        _write(tmp_path / "rb.json", baseline),
        "--runtime-telemetry",
        _write(tmp_path / "rt.json", {"runtime_pca": _block(mod.RUNTIME_FEATURES)}),
        "--semantic-rows",
        _write(tmp_path / "sr.json", semantic_rows),
        "--semantic-telemetry",
        _write(
            tmp_path / "st.json",
            {"semantic_pca": semantic_block or _block(mod.SEMANTIC_FEATURES)},
        ),
        "--out",
        str(tmp_path / "receipt.json"),
    ]


def test_main_writes_paired_receipt(monkeypatch, tmp_path, capsys):
    semantic = [_semantic_row(sha, i) for i, sha in enumerate(SHAS)]
    monkeypatch.setattr(sys, "argv", ["w74"] + _files(tmp_path, SHAS, semantic))
    mod.main()
    receipt = json.loads((tmp_path / "receipt.json").read_text(encoding="utf-8"))
    printed = json.loads(capsys.readouterr().out)
    assert printed == receipt
    assert receipt["status"] == "PAIRED_COORDINATE_DIAGNOSTIC"
    assert receipt["pair_count"] == 5
    assert [p["source_sha"] for p in receipt["pairs"]] == sorted(SHAS)
    assert receipt["association"]["pearson_r"] is not None
    assert receipt["association"]["spearman_rho"] is not None
    body = {k: v for k, v in receipt.items() if k != "receipt_sha256"}
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    assert receipt["receipt_sha256"] == hashlib.sha256(canonical).hexdigest()


def test_main_withholds_when_semantic_scores_do_not_vary(monkeypatch, tmp_path, capsys):
    semantic = [_semantic_row(sha, i) for i, sha in enumerate(SHAS)]
    for i, row in enumerate(semantic):
        row["consumer_edge_density"] = -float(i)
    flat = _block(mod.SEMANTIC_FEATURES)
    flat["components"][1]["loadings"]["consumer_degree_concentration"] = 0.0
    argv = _files(tmp_path, SHAS, semantic, semantic_block=flat)
    monkeypatch.setattr(sys, "argv", ["w74"] + argv)
    mod.main()
    receipt = json.loads(capsys.readouterr().out)
    assert receipt["status"] == "WITHHELD_INSUFFICIENT_PAIRED_VARIATION"
    assert {p["semantic_pc1_frozen_score"] for p in receipt["pairs"]} == {0.0}
    assert receipt["association"]["pearson_r"] is None


def test_main_rejects_unpaired_or_too_few_shas(monkeypatch, tmp_path):
    shas = SHAS[:4]
    semantic = [_semantic_row(sha, i) for i, sha in enumerate(shas)]
    monkeypatch.setattr(sys, "argv", ["w74"] + _files(tmp_path, shas, semantic))
    with pytest.raises(ValueError, match="exact-pair"):
        mod.main()
    semantic = [_semantic_row("z" + sha, i) for i, sha in enumerate(SHAS)]
    monkeypatch.setattr(sys, "argv", ["w74"] + _files(tmp_path, SHAS, semantic))
    with pytest.raises(ValueError, match="exact-pair"):
        mod.main()
