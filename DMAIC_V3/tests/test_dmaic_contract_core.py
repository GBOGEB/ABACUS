import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT_DIR / "src"))

from dmaic.contract import ensure_contract, validate_contract  # noqa: E402
from dmaic.idempotency import hash_json, idempotent  # noqa: E402
from dmaic import provenance  # noqa: E402


def test_hash_json_is_deterministic():
    left = {"b": 2, "a": 1}
    right = {"a": 1, "b": 2}
    assert hash_json(left) == hash_json(right)


def test_ensure_and_validate_contract():
    payload = {"value": 1}
    enriched = ensure_contract(
        payload,
        iteration=2,
        phase="phase2",
        version="3.3.0",
        generator="unit-test",
    )
    errors = validate_contract(enriched)
    assert errors == []
    assert enriched["metadata"]["iteration"] == 2
    assert "lineage" in enriched
    assert "idempotency" in enriched


def test_idempotent_persistent_cache(tmp_path):
    calls = {"count": 0}
    cache_dir = tmp_path / "cache"

    @idempotent(lambda **kwargs: f"rk::{kwargs['x']}", cache_dir=cache_dir)
    def run(**kwargs):
        calls["count"] += 1
        return {"value": kwargs["x"]}

    first = run(x=7)
    second = run(x=7)
    assert first == second
    assert calls["count"] == 1
    assert len(list(cache_dir.glob("*.json"))) == 1


def test_provenance_persists_runs(tmp_path, monkeypatch):
    db_path = tmp_path / "provenance.db"
    monkeypatch.setenv("DMAIC_PROVENANCE_DB", str(db_path))

    provenance.ensure_schema()
    run_id = provenance.begin_run("cfg_hash", "inputs_hash")
    provenance.record_phase(
        run_id=run_id,
        phase_name="define",
        iteration=1,
        status="success",
        inputs_hash="in",
        outputs_hash="out",
        metrics={"ok": True},
    )
    provenance.record_artifact(
        run_id=run_id,
        phase="define",
        kind="report",
        path="x.json",
        bytes_hash="abcd1234",
        meta={"x": 1},
    )
    provenance.finish_run(run_id, "success", {"score": 1.0})

    run = provenance.get_run(run_id)
    assert run is not None
    assert run["status"] == "success"
    assert Path(db_path).exists()
