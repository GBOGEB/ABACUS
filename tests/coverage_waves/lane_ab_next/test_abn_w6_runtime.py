"""Gap tests for src/qplant_presentation_engine/runtime.py.

Artifacts are written relative to ``Path.cwd()``, so every writing test
chdirs into ``tmp_path``.
"""

import json

from src.qplant_presentation_engine import runtime as mod

ALL_OK = dict(
    package_import=True,
    runtime_entry=True,
    metrics_availability=True,
    truth_matrix_availability=True,
    schema_consistency=True,
)


def _read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_resolve_entrypoint_prefers_top_level_package():
    # The repo ships a top-level qplant_presentation_engine/__main__.py.
    assert mod._resolve_entrypoint_module() == "qplant_presentation_engine"


def test_resolve_entrypoint_falls_back_to_package(tmp_path, monkeypatch):
    fake = tmp_path / "a" / "b" / "runtime.py"
    monkeypatch.setattr(mod, "__file__", str(fake))
    assert mod._resolve_entrypoint_module() == mod.__package__


def test_load_runtime_metadata_is_a_copy():
    meta = mod.load_runtime_metadata()
    assert meta["version"] == "W001.1"
    assert meta["entrypoint"].startswith("python -m ")
    meta["version"] = "changed"
    assert mod.load_runtime_metadata()["version"] == "W001.1"


def test_utc_timestamp_has_no_microseconds():
    ts = mod._utc_timestamp()
    assert ts.endswith("+00:00")
    assert "." not in ts


def test_run_smoke_test_all_ok(monkeypatch):
    monkeypatch.setattr(mod, "load_metrics", lambda: {"geti": 1.0})
    monkeypatch.setattr(mod, "validate_runtime", lambda: dict(ALL_OK))
    assert mod.run_smoke_test() == [
        "[OK] Runtime Started",
        "[OK] Metrics Loaded",
        "[OK] Truth Matrix Loaded",
        "[OK] Validation Ready",
    ]


def test_run_smoke_test_all_fail(monkeypatch):
    monkeypatch.setattr(mod, "load_metrics", lambda: {})
    monkeypatch.setattr(mod, "TRUTH_RULES", [])
    monkeypatch.setattr(mod, "validate_runtime", lambda: dict(a=True, b=False))
    assert mod.run_smoke_test() == [
        "[OK] Runtime Started",
        "[FAIL] Metrics Loaded",
        "[FAIL] Truth Matrix Loaded",
        "[FAIL] Validation Ready",
    ]


def test_generate_runtime_evidence_success(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(mod, "_utc_timestamp", lambda: "T0")
    metrics = {
        "forward_pca": 1.0,
        "backward_pca": 0.5,
        "geti": 0.75,
        "truth_score": 0.75,
        "truth_matrix_snapshot": {
            "principles": [{"principle": "p"}],
            "truth_score": 0.75,
            "evidence": {"e": True},
        },
    }
    mod.generate_runtime_evidence(0, ["[OK] a", "[OK] b"], metrics, dict(ALL_OK))
    status = _read(tmp_path / "runtime_status.json")
    assert status["runtime_status"] == "ok"
    assert status["validation_status"] == "ready"
    assert status["exit_code"] == 0
    assert status["generated_at"] == "T0"
    assert _read(tmp_path / "reports" / "runtime_status.json") == status
    assert _read(tmp_path / "validation_report.json")["checks"] == ALL_OK
    pca = _read(tmp_path / "pca_snapshot.json")
    assert pca == {
        "backward_pca": 0.5,
        "forward_pca": 1.0,
        "generated_at": "T0",
        "geti": 0.75,
    }
    assert "geti" not in _read(tmp_path / "reports" / "pca_snapshot.json")
    geti = _read(tmp_path / "reports" / "geti_snapshot.json")
    assert geti["truth_score"] == 0.75
    truth = _read(tmp_path / "reports" / "truth_matrix_snapshot.json")
    assert truth["principles"] == [{"principle": "p"}]
    assert truth["evidence"] == {"e": True}


def test_generate_runtime_evidence_failure_and_bad_snapshot(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    metrics = {"truth_matrix_snapshot": ["not", "a", "dict"]}
    mod.generate_runtime_evidence(
        1, ["[OK] a", "[FAIL] b"], metrics, dict(a=True, b=False)
    )
    status = _read(tmp_path / "runtime_status.json")
    assert status["runtime_status"] == "failed"
    assert status["validation_status"] == "failed"
    assert _read(tmp_path / "validation_report.json")["validation_status"] == "failed"
    pca = _read(tmp_path / "pca_snapshot.json")
    assert pca["forward_pca"] == 0 and pca["geti"] == 0
    truth = _read(tmp_path / "reports" / "truth_matrix_snapshot.json")
    assert truth["principles"] == []
    assert truth["truth_score"] == 0
    assert truth["evidence"] == {}


def test_run_runtime_success(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    monkeypatch.setattr(mod, "validate_runtime", lambda: dict(ALL_OK))
    exit_code, report, metadata = mod.run_runtime()
    assert exit_code == 0
    assert all(line.startswith("[OK]") for line in report)
    assert metadata == mod.load_runtime_metadata()
    truth = _read(tmp_path / "reports" / "truth_matrix_snapshot.json")
    assert truth["evidence"]["claimed_runtime_ready"] is True
    assert truth["evidence"]["validation_ready"] is True
    assert truth["truth_score"] == 0.75


def test_run_runtime_validation_failure(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(mod, "validate_runtime", lambda: dict(a=False))
    exit_code, report, _ = mod.run_runtime()
    assert exit_code == 1
    assert report[-1] == "[FAIL] Validation Ready"
    status = _read(tmp_path / "runtime_status.json")
    assert status["exit_code"] == 1
    assert status["runtime_status"] == "failed"
    truth = _read(tmp_path / "reports" / "truth_matrix_snapshot.json")
    assert truth["evidence"]["validation_ready"] is False
