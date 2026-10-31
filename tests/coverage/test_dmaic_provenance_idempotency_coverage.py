"""Behavioral coverage for src/dmaic provenance and idempotency helpers.

Re-landed from branch mip/dmaic-provenance-idempotency-pressure-20261002
(80d4f6ee); test-only, no production source change.
"""

import hashlib
import json

from src.dmaic import idempotency, provenance


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

    assert (
        idempotency.hash_json([1, 2, 3])
        == hashlib.sha256(json.dumps([1, 2, 3]).encode()).hexdigest()
    )

    payload = tmp_path / "payload.bin"
    payload.write_bytes(b"ABACUS\x00pressure")
    assert (
        idempotency.compute_file_hash(payload)
        == hashlib.sha256(b"ABACUS\x00pressure").hexdigest()
    )


def test_provenance_file_backed_lifecycle_and_missing_run(tmp_path, monkeypatch):
    """Exercise persistence and explicit metadata without relying on global memory."""
    db_path = tmp_path / "nested" / "provenance.json"
    monkeypatch.setenv("DMAIC_PROVENANCE_DB", str(db_path))
    empty = {"runs": [], "phases": [], "artifacts": []}

    # Both a missing database and the initial schema creation have defined behavior.
    assert provenance._load_db() == empty
    provenance.ensure_schema()
    assert json.loads(db_path.read_text(encoding="utf-8")) == empty

    run_id = provenance.begin_run("0123456789abcdef", "input-sha")
    provenance.record_phase(run_id, "analyze", 3, "ok", "in", "out", {"n": 3})
    artifact_id = provenance.record_artifact(
        run_id,
        "analyze",
        "json",
        "result.json",
        "feedbead1234",
        meta={"origin": "file-backed"},
    )
    provenance.finish_run(run_id, "success", {"score": 9})

    persisted = json.loads(db_path.read_text(encoding="utf-8"))
    assert persisted["runs"][0]["run_id"] == run_id
    assert persisted["runs"][0]["status"] == "success"
    assert persisted["runs"][0]["metrics"] == {"score": 9}
    assert persisted["phases"][0]["iteration"] == 3
    assert persisted["artifacts"][0]["artifact_id"] == artifact_id
    assert persisted["artifacts"][0]["meta"] == {"origin": "file-backed"}
    assert provenance.get_run(run_id)["status"] == "success"
    assert provenance.get_run("nonexistent-run") is None
    assert provenance.get_recent_runs(1)[0]["run_id"] == run_id

    # A missing ID must not mutate the persisted records.
    provenance.finish_run("nonexistent-run", "failed", {"unexpected": True})
    assert json.loads(db_path.read_text(encoding="utf-8")) == persisted


def test_provenance_os_error_returns_empty_db(tmp_path, monkeypatch):
    """A failure reading a present file follows the documented empty-DB fallback."""
    db_path = tmp_path / "provenance.json"
    db_path.write_text("{}", encoding="utf-8")
    monkeypatch.setenv("DMAIC_PROVENANCE_DB", str(db_path))

    def fail_to_read(*_args, **_kwargs):
        raise OSError("simulated transient read failure")

    monkeypatch.setattr(provenance, "open", fail_to_read, raising=False)
    assert provenance._load_db() == {"runs": [], "phases": [], "artifacts": []}


def test_hash_json_dictionary_is_independent_of_insertion_order():
    """Dictionary hashing should be reproducible across key orders."""
    expected = hashlib.sha256(
        json.dumps({"alpha": 1, "zeta": 2}, sort_keys=True).encode()
    ).hexdigest()
    assert idempotency.hash_json({"zeta": 2, "alpha": 1}) == expected
    assert idempotency.hash_json({"alpha": 1, "zeta": 2}) == expected
