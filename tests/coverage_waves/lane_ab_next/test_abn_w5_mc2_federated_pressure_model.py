"""Behaviour tests for tools/mc2_federated_pressure_model.py."""

import hashlib
import json

from tests.coverage_waves.lane_b._l2_loader import load

mod = load("tools/mc2_federated_pressure_model.py", name="abn_w5_pressure_model")

MEASURED = "MEASURED_PCA_DIAGNOSTIC"


def _pca_block(rows=6, with_pc1=True, status=MEASURED):
    components = [{"pc": 2, "eigenvalue": 0.4}]
    if with_pc1:
        components.insert(
            0,
            {
                "pc": 1,
                "eigenvalue": 2.5,
                "explained_variance_ratio": 0.62,
                "loadings": {"x": 0.9, "y": -0.7},
            },
        )
    return {"status": status, "numeric_comparable_rows": rows, "components": components}


def _pa(retained_pcs, status="PA95_DIAGNOSTIC"):
    return {"status": status, "retained_pcs": retained_pcs}


def _run(tmp_path, monkeypatch, runtime_t, runtime_pa, semantic_t, semantic_pa):
    paths = {}
    for name, doc in (
        ("rt", runtime_t),
        ("rpa", runtime_pa),
        ("st", semantic_t),
        ("spa", semantic_pa),
    ):
        path = tmp_path / (name + ".json")
        path.write_text(json.dumps(doc), encoding="utf-8")
        paths[name] = str(path)
    out = tmp_path / "out.json"
    argv = [
        "prog",
        "--runtime-telemetry",
        paths["rt"],
        "--runtime-pa95",
        paths["rpa"],
        "--semantic-telemetry",
        paths["st"],
        "--semantic-pa95",
        paths["spa"],
        "--out",
        str(out),
    ]
    monkeypatch.setattr("sys.argv", argv)
    mod.main()
    return json.loads(out.read_text(encoding="utf-8"))


def test_pc1_finds_first_component_or_none():
    block = _pca_block()
    assert mod.pc1(block)["eigenvalue"] == 2.5
    assert mod.pc1(_pca_block(with_pc1=False)) is None
    assert mod.pc1({}) is None
    assert mod.pc1({"components": None}) is None


def test_retained_requires_status_and_pc1():
    assert mod.retained(_pa([1, 2])) is True
    assert mod.retained(_pa([2])) is False
    assert mod.retained(_pa([1], status="WITHHELD")) is False
    assert mod.retained({"status": "PA95_DIAGNOSTIC", "retained_pcs": None}) is False


def test_load_reads_json(tmp_path):
    path = tmp_path / "a.json"
    path.write_text('{"a": 1}', encoding="utf-8")
    assert mod.load(str(path)) == {"a": 1}


def test_main_ready_two_axis_receipt(tmp_path, monkeypatch, capsys):
    receipt = _run(
        tmp_path,
        monkeypatch,
        {"runtime_pca": _pca_block(rows=7)},
        _pa([1]),
        {"semantic_pca": _pca_block(rows=9)},
        _pa([1, 2]),
    )
    assert receipt["status"] == "MEASURED_TWO_AXIS_DIAGNOSTIC"
    assert all(receipt["gates"].values())
    assert receipt["runtime_axis"]["sample_size"] == 7
    assert receipt["runtime_axis"]["loadings"] == {"x": 0.9, "y": -0.7}
    assert receipt["runtime_axis"]["pa95_retained"] is True
    assert receipt["semantic_axis"]["sample_size"] == 9
    assert receipt["semantic_axis"]["name"].startswith("semantic_topology")
    assert receipt["coupling"]["paired_observations"] is False
    assert receipt["global_allocation_authority"] is False
    body = {k: v for k, v in receipt.items() if k != "receipt_sha256"}
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    assert receipt["receipt_sha256"] == hashlib.sha256(canonical).hexdigest()
    printed = json.loads(capsys.readouterr().out)
    assert printed == receipt


def test_main_withheld_when_semantic_not_retained(tmp_path, monkeypatch):
    receipt = _run(
        tmp_path,
        monkeypatch,
        {"runtime_pca": _pca_block()},
        _pa([1]),
        {"semantic_pca": _pca_block()},
        _pa([2]),
    )
    assert receipt["status"] == "WITHHELD_AXIS_RETENTION_GATE"
    assert receipt["gates"]["semantic_pc1_pa95_retained"] is False
    assert receipt["semantic_axis"]["pa95_retained"] is False


def test_main_withheld_when_pc1_missing_or_blocks_absent(tmp_path, monkeypatch):
    receipt = _run(
        tmp_path,
        monkeypatch,
        {"runtime_pca": _pca_block(with_pc1=False)},
        _pa([1]),
        {"semantic_pca": None},
        {},
    )
    assert receipt["status"] == "WITHHELD_AXIS_RETENTION_GATE"
    assert receipt["runtime_axis"] is None
    assert receipt["semantic_axis"] is None
    assert receipt["gates"] == {
        "runtime_pca_measured": True,
        "runtime_pc1_pa95_retained": True,
        "semantic_pca_measured": False,
        "semantic_pc1_pa95_retained": False,
    }


def test_main_withheld_when_all_gates_pass_but_pc1_absent(tmp_path, monkeypatch):
    receipt = _run(
        tmp_path,
        monkeypatch,
        {"runtime_pca": _pca_block()},
        _pa([1]),
        {"semantic_pca": _pca_block(with_pc1=False)},
        _pa([1]),
    )
    assert all(receipt["gates"].values())
    assert receipt["status"] == "WITHHELD_AXIS_RETENTION_GATE"
    assert receipt["runtime_axis"] is not None
    assert receipt["semantic_axis"] is None
