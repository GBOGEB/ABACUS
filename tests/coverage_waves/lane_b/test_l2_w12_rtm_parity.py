"""Lane-B wave 12: RTM automation wrappers and the QPS slide-reviewer parity port.

verify_qps_parity.py imports ``kernels.pca_reference`` and
``kernels.bradley_terry`` from the gg_MATH repo, which ABACUS does not vendor.
Independent fakes are injected: PCA via numpy eigen-decomposition of the
correlation matrix, Bradley-Terry via Ford strong-connectivity check plus the
Zermelo/MM iteration without a prior (scores normalised to mean 1). The regenerated vector is compared with
the committed qps_parity_vector.json.
"""

import json
import logging
import math
import sys
import types

import numpy as np
import pytest

from ._l2_loader import REPO_ROOT, load

PARITY_DIR = REPO_ROOT / "qps_slide_reviewer" / "parity"
COMMITTED = json.loads((PARITY_DIR / "qps_parity_vector.json").read_text("utf-8"))

port = load("qps_slide_reviewer/parity/slide_reviewer_port.py")
vr = load("rtm_integration/automation/scripts/automation/validate_requirements.py")


# ------------------------------------------------------- slide_reviewer_port


def test_bt_single_dominant_pair_with_prior():
    ids = ["a", "b"]
    comps = [{"slideAId": "a", "slideBId": "b", "winnerId": "a"}] * 3
    res = port.sr_bradley_terry(ids, comps)
    # geometric-mean normalisation
    assert res["a"] * res["b"] == pytest.approx(1.0)
    assert res["a"] > res["b"]
    # the 0.1 prior keeps the loser finite and positive
    assert 0 < res["b"] < 1


def test_bt_symmetric_ties_and_invalid_rows_give_equal_scores():
    ids = [1, 2, 3]
    comps = [
        {"slideAId": 1, "slideBId": 2, "isTie": True, "winnerId": 1},
        {"slideAId": 2, "slideBId": 3, "winnerId": None},
        {"slideAId": 3, "slideBId": 1, "isTie": True},
        {"slideAId": 1, "slideBId": 9, "winnerId": 1},  # unknown slide
        {"slideAId": 2, "slideBId": 2, "winnerId": 2},  # self pair
        {"slideAId": 1, "slideBId": 3, "winnerId": 7},  # unknown winner
    ]
    res = port.sr_bradley_terry(ids, comps, iterations=50)
    assert res == {1: pytest.approx(1.0), 2: pytest.approx(1.0), 3: pytest.approx(1.0)}


def test_bt_b_side_winner_and_no_comparisons():
    res = port.sr_bradley_terry(
        ["x", "y"], [{"slideAId": "x", "slideBId": "y", "winnerId": "y"}]
    )
    assert res["y"] > res["x"]
    empty = port.sr_bradley_terry(["x", "y"], [], iterations=5)
    assert empty == {"x": pytest.approx(1.0), "y": pytest.approx(1.0)}


def test_pca_matches_numpy_correlation_eigenvalues():
    matrix = [[1.0, 2.0, 0.5], [2.0, 4.1, 0.1], [3.0, 5.9, 0.7], [4.0, 8.2, 0.2]]
    res = port.sr_pca([1, 2, 3, 4], ["a", "b", "c"], matrix, n_components=2)
    ref = sorted(np.linalg.eigvalsh(np.corrcoef(np.array(matrix).T)), reverse=True)
    assert res["eigenvalues"] == pytest.approx(ref[:2], abs=1e-9)
    assert res["explained_variance"] == pytest.approx(
        [e / 3 for e in ref[:2]], abs=1e-9
    )
    for vec in res["components"]:
        assert math.fsum(x * x for x in vec) == pytest.approx(1.0)


def test_pca_constant_column_and_deflated_rank():
    # column b is constant (sd falls back to 1.0); rank-1 data deflates to zero
    matrix = [[1.0, 5.0], [2.0, 5.0], [3.0, 5.0]]
    res = port.sr_pca([1, 2, 3], ["a", "b"], matrix, n_components=3)
    assert res["eigenvalues"] == pytest.approx([1.0, 0.0], abs=1e-9)
    assert res["explained_variance"] == pytest.approx([1.0, 0.0], abs=1e-9)
    assert res["components"][1] == [0.0, 0.0]


def test_pca_all_constant_uses_unit_total_variance():
    res = port.sr_pca([1, 2], ["a"], [[3.0], [3.0]], n_components=1)
    assert res == {
        "explained_variance": [0.0],
        "eigenvalues": [0.0],
        "components": [[0.0]],
    }


# ------------------------------------------------------ verify_qps_parity


def _fake_pca_reference(matrix, scale, components):
    assert scale is True and components == 3
    eig = sorted(np.linalg.eigvalsh(np.corrcoef(np.array(matrix).T)), reverse=True)
    total = float(sum(eig))
    return {
        "eigenvalues": [float(e) for e in eig],
        "explained_variance_ratio": [float(e) / total for e in eig],
    }


def _fake_parallel_analysis(matrix, simulations, percentile, seed, scale):
    pca = COMMITTED["pca"]
    return {
        "retained_candidate": pca["parallel_analysis_PA95_retained_candidate"],
        "null_eigenvalue_thresholds": pca["parallel_analysis_null_thresholds"],
    }


def _strongly_connected(nodes, edges):
    def reach(start, adj):
        seen, todo = {start}, [start]
        while todo:
            for nxt in adj.get(todo.pop(), ()):
                if nxt not in seen:
                    seen.add(nxt)
                    todo.append(nxt)
        return seen

    fwd, back = {}, {}
    for w, l in edges:
        fwd.setdefault(w, set()).add(l)
        back.setdefault(l, set()).add(w)
    first = next(iter(nodes))
    return reach(first, fwd) == nodes and reach(first, back) == nodes


def _fake_rank_pairs(pairs):
    nodes = {n for pair in pairs for n in pair}
    if not _strongly_connected(nodes, pairs):
        return {"status": "DEFER_NO_FINITE_MLE"}
    wins = {n: 0 for n in nodes}
    games = {}
    for w, l in pairs:
        wins[w] += 1
        key = frozenset((w, l))
        games[key] = games.get(key, 0) + 1
    pi = {n: 1.0 for n in nodes}
    for _ in range(2000):
        nxt = {}
        for i in nodes:
            denom = sum(
                cnt / (pi[i] + pi[j])
                for key, cnt in games.items()
                if i in key
                for j in key - {i}
            )
            nxt[i] = wins[i] / denom
        mean = sum(nxt.values()) / len(nxt)
        pi = {k: v / mean for k, v in nxt.items()}
    order = sorted(sorted(pi), key=lambda k: pi[k], reverse=True)
    return {"status": "PASS_TESTABLE_ENGINE", "scores": {k: pi[k] for k in order}}


def _kernels(rank_pairs=_fake_rank_pairs, pca_reference=_fake_pca_reference):
    pkg = types.ModuleType("kernels")
    pca = types.SimpleNamespace(
        pca_reference=pca_reference, parallel_analysis=_fake_parallel_analysis
    )
    bt = types.SimpleNamespace(rank_pairs=rank_pairs)
    return {
        "kernels": pkg,
        "kernels.pca_reference": pca,
        "kernels.bradley_terry": bt,
        "slide_reviewer_port": port,
    }


# The script computes its "repo root" as parity/../../.., one level too high
# for its ABACUS location (it was written for mission/QPS/parity/).
SCRIPT_ROOT = REPO_ROOT.parent


def _run_verify(monkeypatch, deps, preseed_path=False):
    here = str(PARITY_DIR)
    root = str(SCRIPT_ROOT)
    path = [p for p in sys.path if p not in (here, root)]
    if preseed_path:
        path = [here, root, *path]
    monkeypatch.setattr(sys, "path", path)
    return load(
        "qps_slide_reviewer/parity/verify_qps_parity.py",
        name="l2_w12_verify_qps_parity",
        deps=deps,
    )


def test_verify_parity_reproduces_committed_vector(monkeypatch, capsys):
    mod = _run_verify(monkeypatch, _kernels())
    assert sys.path[:2] == [str(PARITY_DIR), str(SCRIPT_ROOT)]
    captured = capsys.readouterr()
    out = json.loads(captured.out)
    assert "PARITY OK" in captured.err
    assert "fail_closed=DEFER_NO_FINITE_MLE" in captured.err
    assert "convergent_BT_order_match=True" in captured.err
    assert len(out["matrix"]) == len(COMMITTED["matrix"]) == 8
    for row, ref_row in zip(out["matrix"], COMMITTED["matrix"]):
        assert row == pytest.approx(ref_row, abs=1e-12)
    assert out["slide_ids"] == COMMITTED["slide_ids"] == list(range(1, 9))
    pca, ref = out["pca"], COMMITTED["pca"]
    assert pca["slide_reviewer_eigenvalues_top3"] == pytest.approx(
        ref["slide_reviewer_eigenvalues_top3"], abs=1e-12
    )
    assert pca["canonical_eigenvalues_top3"] == pytest.approx(
        ref["canonical_eigenvalues_top3"], abs=1e-9
    )
    assert pca["slide_reviewer_explained_variance_top3"] == pytest.approx(
        ref["slide_reviewer_explained_variance_top3"], abs=1e-12
    )
    assert max(pca["eigenvalue_abs_diff"]) < 1e-6
    sparse = out["bradley_terry_fail_closed_case"]
    ref_sparse = COMMITTED["bradley_terry_fail_closed_case"]
    assert sparse["comparisons"] == 28
    assert sparse["canonical_status"] == ref_sparse["canonical_status"]
    assert (
        sparse["slide_reviewer_still_returns_ranking"]
        == ref_sparse["slide_reviewer_still_returns_ranking"]
    )
    conv = out["bradley_terry_convergent_case"]
    ref_conv = COMMITTED["bradley_terry_convergent_case"]
    assert conv["comparisons"] == 112
    assert conv["slide_reviewer_order"] == ref_conv["slide_reviewer_order"]
    assert conv["canonical_order"] == ref_conv["canonical_order"]
    assert conv["order_matches"] is True
    # JSON round-trip turns the integer slide ids into string keys
    assert conv["slide_reviewer_scores"] == pytest.approx(
        ref_conv["slide_reviewer_scores"], abs=1e-12
    )
    assert conv["canonical_scores"] == pytest.approx(
        ref_conv["canonical_scores"], rel=1e-6
    )
    assert mod.SEED == 20260925


def test_verify_parity_existing_sys_path_not_duplicated(monkeypatch, capsys):
    _run_verify(monkeypatch, _kernels(), preseed_path=True)
    capsys.readouterr()
    assert sys.path.count(str(PARITY_DIR)) == 1
    assert sys.path.count(str(SCRIPT_ROOT)) == 1


def test_verify_parity_pca_breach_raises(monkeypatch, capsys):
    def skewed(matrix, scale, components):
        res = _fake_pca_reference(matrix, scale, components)
        res["eigenvalues"][0] += 1e-3
        return res

    with pytest.raises(AssertionError, match="PCA eigenvalue parity failed"):
        _run_verify(monkeypatch, _kernels(pca_reference=skewed))


def test_verify_parity_evr_breach_raises(monkeypatch, capsys):
    def skewed(matrix, scale, components):
        res = _fake_pca_reference(matrix, scale, components)
        res["explained_variance_ratio"][1] += 1e-3
        return res

    with pytest.raises(AssertionError, match="explained-variance parity failed"):
        _run_verify(monkeypatch, _kernels(pca_reference=skewed))


def test_verify_parity_canonical_defer_fails_closed(monkeypatch, capsys):
    def always_defer(pairs):
        return {"status": "DEFER_NO_FINITE_MLE"}

    with pytest.raises(AssertionError, match="convergent BT should pass"):
        _run_verify(monkeypatch, _kernels(rank_pairs=always_defer))
    out = json.loads(capsys.readouterr().out)
    assert out["bradley_terry_convergent_case"]["canonical_order"] == []
    assert out["bradley_terry_convergent_case"]["canonical_scores"] == {}


def test_verify_parity_order_mismatch_raises(monkeypatch, capsys):
    def reversed_order(pairs):
        res = _fake_rank_pairs(pairs)
        if res["status"] == "PASS_TESTABLE_ENGINE":
            res["scores"] = dict(reversed(list(res["scores"].items())))
        return res

    with pytest.raises(AssertionError, match="BT order mismatch"):
        _run_verify(monkeypatch, _kernels(rank_pairs=reversed_order))


def test_verify_parity_without_kernels_package_fails(monkeypatch):
    """production_defect: verify_qps_parity.py imports ``kernels.*`` from the
    gg_MATH repo, which is not vendored in ABACUS, and its sys.path root
    (parity/../../..) points above the ABACUS repo root, so the committed
    script cannot run here; this test fails once fixed."""
    with pytest.raises(ModuleNotFoundError, match="kernels"):
        _run_verify(monkeypatch, {"kernels": None})


# ------------------------------------------------------------ RTM wrappers


class _Generator:
    instances = []
    result = True
    boom = None

    def __init__(self):
        self.calls = []
        _Generator.instances.append(self)

    def generate_rtm(self, **kwargs):
        self.calls.append(kwargs)
        if self.boom:
            raise self.boom
        return self.result


@pytest.fixture
def gen(monkeypatch):
    monkeypatch.setattr(_Generator, "instances", [])
    monkeypatch.setattr(_Generator, "result", True)
    monkeypatch.setattr(_Generator, "boom", None)
    monkeypatch.setattr(sys, "path", list(sys.path))
    return _Generator


def _load_auto_gen():
    return load(
        "rtm_integration/automation/scripts/automation/generate_rtm.py",
        name="l2_w12_auto_generate_rtm",
        deps={"rtm_generator": types.SimpleNamespace(RTMGenerator=_Generator)},
    )


def test_auto_generate_rtm_success(gen, caplog):
    mod = _load_auto_gen()
    assert sys.path[0] == str(REPO_ROOT / "rtm_integration/automation/scripts")
    with caplog.at_level(logging.INFO, logger=mod.logger.name):
        assert mod.main() is True
    assert gen.instances[0].calls == [{"output_dir": "docs/rtm"}]
    assert "RTM generation completed successfully" in caplog.text


def test_auto_generate_rtm_failure(gen, caplog):
    mod = _load_auto_gen()
    gen.result = False
    with caplog.at_level(logging.INFO, logger=mod.logger.name):
        assert mod.main() is False
    assert "RTM generation failed" in caplog.text


def test_auto_generate_rtm_missing_package_exits(gen, caplog):
    with pytest.raises(SystemExit) as exc:
        load(
            "rtm_integration/automation/scripts/automation/generate_rtm.py",
            name="l2_w12_auto_generate_rtm_missing",
            deps={"rtm_generator": None},
        )
    assert exc.value.code == 1
    assert "Failed to import RTMGenerator" in caplog.text


def _load_legacy_gen():
    return load(
        "rtm_integration/automation/scripts/generate_rtm.py",
        name="l2_w12_legacy_generate_rtm",
        deps={
            "rtm_generator.generator": types.SimpleNamespace(RTMGenerator=_Generator)
        },
    )


def test_legacy_generate_rtm_success(gen):
    mod = _load_legacy_gen()
    assert sys.path[0].endswith("..")
    assert mod.main() is True
    assert gen.instances[0].calls == [{}]


def test_legacy_generate_rtm_exception(gen, caplog):
    mod = _load_legacy_gen()
    gen.boom = RuntimeError("disk full")
    with caplog.at_level(logging.ERROR, logger=mod.logger.name):
        assert mod.main() is False
    assert "RTM generation failed: disk full" in caplog.text


# --------------------------------------------------- validate_requirements


def _req(**over):
    req = {
        "req_id": "R-1",
        "description": "Cool the magnet",
        "sbs_l0": "QPS",
        "sbs_l1": "CRYO",
        "sbs_l2": "HP",
        "requirement_type": "functional",
        "priority": "high",
    }
    req.update(over)
    return req


def _write(tmp_path, data):
    path = tmp_path / "requirements.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_validate_ok(tmp_path, caplog):
    path = _write(tmp_path, [_req(), _req(req_id="R-2", sbs_l2="")])
    with caplog.at_level(logging.INFO):
        assert vr.validate_requirements(path) is True
    assert "Validated 2 requirements" in caplog.text
    assert "Validation passed" in caplog.text


@pytest.mark.parametrize(
    "reqs, message",
    [
        ([_req(description="")], "Missing description in R-1"),
        ([_req(priority=None)], "Missing priority in R-1"),
        ([_req(req_id="")], "Missing req_id in "),
        ([_req(), _req()], "Duplicate requirement IDs found"),
        ([_req(sbs_l1="")], "SBS inconsistency in R-1: L2 without L1"),
    ],
)
def test_validate_rejections(tmp_path, caplog, reqs, message):
    path = _write(tmp_path, reqs)
    with caplog.at_level(logging.ERROR):
        assert vr.validate_requirements(path) is False
    assert message in caplog.text
    assert "Validation failed with" in caplog.text


def test_validate_missing_req_id_key_reports_unknown(tmp_path, caplog):
    req = _req()
    del req["req_id"]
    with caplog.at_level(logging.ERROR):
        assert vr.validate_requirements(_write(tmp_path, [req])) is False
    # the duplicate-ID scan raises KeyError before the collected
    # "Missing req_id in UNKNOWN" error is logged
    assert "Missing req_id" not in caplog.text
    assert "Validation failed: 'req_id'" in caplog.text


def test_validate_missing_sbs_l2_key_and_bad_json(tmp_path, caplog):
    req = _req()
    del req["sbs_l2"]
    with caplog.at_level(logging.ERROR):
        assert vr.validate_requirements(_write(tmp_path, [req])) is False
        bad = tmp_path / "bad.json"
        bad.write_text("{not json", encoding="utf-8")
        assert vr.validate_requirements(bad) is False
    assert "Validation failed: 'sbs_l2'" in caplog.text


def test_validate_main(tmp_path, monkeypatch, caplog):
    monkeypatch.chdir(tmp_path)
    with caplog.at_level(logging.ERROR):
        assert vr.main() is False
    assert "Requirements file not found" in caplog.text
    (tmp_path / "data" / "rtm").mkdir(parents=True)
    _write(tmp_path / "data" / "rtm", [_req()])
    assert vr.main() is True
