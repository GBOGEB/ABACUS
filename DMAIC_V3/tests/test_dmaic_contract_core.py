import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT_DIR / "src"))

from dmaic.contract import (  # noqa: E402
    DOWNSTREAM_CONSUMERS,
    ensure_contract,
    get_downstream_consumer,
    register_downstream_consumer,
    validate_contract,
)
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


def test_ensure_contract_appends_current_version_to_history():
    enriched = ensure_contract(
        {},
        iteration=0,
        phase="phase0",
        version="3.3.0",
        version_history=["3.2.0", ""],
    )

    assert enriched["lineage"]["version_history"] == ["3.2.0", "3.3.0"]
    assert enriched["recursive_hooks"]["version_history"] == [
        "3.2.0",
        "3.3.0",
    ]


def test_contract_error_branches_are_fail_closed():
    assert validate_contract([]) == ["payload is not an object"]

    missing = validate_contract({})
    for field in (
        "metadata",
        "idempotency",
        "lineage",
        "recursive_hooks",
        "convergence_metrics",
        "knowledge_gain",
    ):
        assert f"missing top-level field: {field}" in missing
    assert "metadata is not an object" in missing
    assert "idempotency is not an object" in missing
    assert "lineage is not an object" in missing
    assert "recursive_hooks is not an object" in missing

    incomplete = validate_contract(
        {
            "metadata": {},
            "idempotency": {},
            "lineage": {},
            "recursive_hooks": {},
            "convergence_metrics": {},
            "knowledge_gain": {},
        }
    )

    for key in (
        "version",
        "timestamp",
        "iteration",
        "phase",
        "contract_version",
    ):
        assert f"metadata missing: {key}" in incomplete
    assert "idempotency missing: enabled" in incomplete
    assert "idempotency missing: input_hash" in incomplete
    assert "idempotency missing: output_hash" in incomplete
    assert "lineage missing: iteration_lineage" in incomplete
    assert "lineage missing: version_history" in incomplete
    assert "recursive_hooks missing: consumed_from" in incomplete
    assert "recursive_hooks missing: feeds_into" in incomplete
    assert "recursive_hooks missing: iteration_lineage" in incomplete


def test_downstream_consumer_registry_defaults_and_lookup():
    name = "unit_test_consumer"
    DOWNSTREAM_CONSUMERS.pop(name, None)

    try:
        entry = register_downstream_consumer(
            name,
            "GBOGEB/unit-test",
        )

        assert entry == {
            "repo": "GBOGEB/unit-test",
            "plane": "auxiliary",
            "federation_moniker": "DELTA_1",
            "contract_path": "",
            "consumes_phases": [],
            "produces_for_phases": [],
            "tuple_source": "GBOGEB/unit-test",
        }
        assert get_downstream_consumer(name) is entry
        assert get_downstream_consumer("missing-consumer") is None
    finally:
        DOWNSTREAM_CONSUMERS.pop(name, None)
