import hashlib
import json

from dmaic import idempotency
from dmaic import provenance


def test_provenance_memory_mode_and_recent_run_lookup(monkeypatch):
    monkeypatch.delenv("DMAIC_PROVENANCE_DB", raising=False)
    monkeypatch.setattr(
        provenance,
        "_provenance_db",
        {"runs": [], "phases": [], "artifacts": []},
    )

    assert provenance._db_path() is None
    provenance.ensure_schema()

    run_id = provenance.begin_run("abcdef123456", "inputs")
    provenance.record_phase(
        run_id,
        "measure",
        2,
        "success",
        "in-hash",
        "out-hash",
        {"score": 2},
    )
    artifact_id = provenance.record_artifact(
        run_id,
        "measure",
        "json",
        "report.json",
        "feedface1234",
    )
    provenance.finish_run(run_id, "success", {"total": 2})

    recent = provenance.get_recent_runs(1)
    assert [row["run_id"] for row in recent] == [run_id]
    assert provenance.get_run(run_id)["metrics"] == {"total": 2}
    assert provenance.get_run("missing-run") is None
    assert provenance._provenance_db["phases"][0]["phase_name"] == "measure"
    assert provenance._provenance_db["artifacts"][0]["artifact_id"] == artifact_id
    assert provenance._provenance_db["artifacts"][0]["meta"] == {}


def test_provenance_file_load_falls_back_on_invalid_json(tmp_path, monkeypatch):
    db_path = tmp_path / "provenance.json"
    db_path.write_text("{not-json", encoding="utf-8")
    monkeypatch.setenv("DMAIC_PROVENANCE_DB", str(db_path))

    assert provenance._load_db() == {
        "runs": [],
        "phases": [],
        "artifacts": [],
    }

    provenance.ensure_schema()
    # Existing files are not overwritten by ensure_schema.
    assert db_path.read_text(encoding="utf-8") == "{not-json"


def test_idempotent_reloads_persistent_cache_across_wrappers(tmp_path):
    cache_dir = tmp_path / "cache"
    calls = {"first": 0, "second": 0}

    @idempotency.idempotent(lambda **kwargs: f"item::{kwargs['x']}", cache_dir)
    def first(**kwargs):
        calls["first"] += 1
        return {"value": kwargs["x"]}

    assert first(x=9) == {"value": 9}
    assert calls["first"] == 1

    @idempotency.idempotent(lambda **kwargs: f"item::{kwargs['x']}", cache_dir)
    def second(**kwargs):
        calls["second"] += 1
        return {"value": -1}

    assert second(x=9) == {"value": 9}
    assert calls["second"] == 0


def test_idempotent_memory_only_and_hash_helpers(tmp_path):
    calls = {"count": 0}

    @idempotency.idempotent(lambda **kwargs: str(kwargs["x"]))
    def run(**kwargs):
        calls["count"] += 1
        return kwargs["x"] * 2

    assert run(x=4) == 8
    assert run(x=4) == 8
    assert calls["count"] == 1

    assert idempotency.hash_json([1, 2, 3]) == hashlib.sha256(
        json.dumps([1, 2, 3]).encode()
    ).hexdigest()

    payload = tmp_path / "payload.bin"
    payload.write_bytes(b"ABACUS\x00pressure")
    assert idempotency.compute_file_hash(payload) == hashlib.sha256(
        b"ABACUS\x00pressure"
    ).hexdigest()
