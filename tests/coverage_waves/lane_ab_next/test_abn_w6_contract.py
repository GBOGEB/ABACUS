"""Behaviour tests for src/dmaic/contract.py."""

from src.dmaic import contract as mod


def test_ensure_contract_on_empty_dict_fills_all_sections(monkeypatch):
    monkeypatch.setattr(mod, "_now_iso", lambda: "2026-01-01T00:00:00")
    out = mod.ensure_contract({}, iteration=2, phase="phase1_define")
    assert mod.validate_contract(out) == []
    assert out["metadata"]["version"] == "3.3.0"
    assert out["metadata"]["timestamp"] == "2026-01-01T00:00:00"
    assert out["metadata"]["contract_version"] == mod.CONTRACT_VERSION
    assert out["metadata"]["generator"] == "unknown"
    assert out["idempotency"]["input_hash"] == ""
    assert out["lineage"]["iteration_lineage"] == [0, 1, 2]
    assert out["lineage"]["version_history"] == ["3.3.0"]
    assert out["recursive_hooks"]["iteration_lineage"] == [0, 1, 2]
    assert out["convergence_metrics"]["convergence_status"] == "not_evaluated"
    assert out["knowledge_gain"]["patterns_discovered"] == []


def test_now_iso_is_parseable():
    from datetime import datetime

    assert isinstance(datetime.fromisoformat(mod._now_iso()), datetime)


def test_ensure_contract_non_dict_and_explicit_args():
    out = mod.ensure_contract(
        ["not", "a", "dict"],
        iteration="1",
        phase="p",
        version="4.0",
        generator="gen",
        input_hash="in",
        output_hash="out",
        version_history=["3.0", "", None, 3.5],
    )
    assert out["metadata"]["generator"] == "gen"
    assert out["idempotency"]["input_hash"] == "in"
    assert out["idempotency"]["output_hash"] == "out"
    assert out["lineage"]["iteration_lineage"] == [0, 1]
    assert out["lineage"]["version_history"] == ["3.0", "3.5", "4.0"]


def test_ensure_contract_keeps_existing_values_and_version_in_history():
    data = {"metadata": {"version": "keep", "phase": "old"}, "extra": 1}
    out = mod.ensure_contract(
        data, iteration=0, phase="new", version="2.0", version_history=["2.0"]
    )
    assert out["metadata"]["version"] == "keep"
    assert out["metadata"]["phase"] == "old"
    assert out["extra"] == 1
    assert out["lineage"]["version_history"] == ["2.0"]


def test_validate_contract_non_dict():
    assert mod.validate_contract("x") == ["payload is not an object"]


def test_validate_contract_all_sections_wrong_type():
    errors = mod.validate_contract(
        {
            "metadata": 1,
            "idempotency": [],
            "lineage": None,
            "recursive_hooks": "x",
        }
    )
    assert "missing top-level field: convergence_metrics" in errors
    assert "missing top-level field: knowledge_gain" in errors
    assert "metadata is not an object" in errors
    assert "idempotency is not an object" in errors
    assert "lineage is not an object" in errors
    assert "recursive_hooks is not an object" in errors


def test_validate_contract_missing_nested_keys():
    errors = mod.validate_contract(
        {
            "metadata": {},
            "idempotency": {},
            "lineage": {},
            "recursive_hooks": {},
            "convergence_metrics": {},
            "knowledge_gain": {},
        }
    )
    for key in ["version", "timestamp", "iteration", "phase", "contract_version"]:
        assert "metadata missing: " + key in errors
    for key in ["enabled", "input_hash", "output_hash"]:
        assert "idempotency missing: " + key in errors
    for key in ["iteration_lineage", "version_history"]:
        assert "lineage missing: " + key in errors
    for key in ["consumed_from", "feeds_into", "iteration_lineage"]:
        assert "recursive_hooks missing: " + key in errors
    assert len(errors) == 13


def test_default_consumer_registered():
    entry = mod.get_downstream_consumer("codespace_jyperter")
    assert entry["federation_moniker"] == "DELTA_1"
    assert mod.get_downstream_consumer("nope") is None


def test_register_downstream_consumer_defaults(monkeypatch):
    monkeypatch.setattr(mod, "DOWNSTREAM_CONSUMERS", dict(mod.DOWNSTREAM_CONSUMERS))
    entry = mod.register_downstream_consumer("c1", "GBOGEB/repo")
    assert entry == {
        "repo": "GBOGEB/repo",
        "plane": "auxiliary",
        "federation_moniker": "DELTA_1",
        "contract_path": "",
        "consumes_phases": [],
        "produces_for_phases": [],
        "tuple_source": "GBOGEB/repo",
    }
    assert mod.get_downstream_consumer("c1") is entry


def test_register_downstream_consumer_overrides(monkeypatch):
    monkeypatch.setattr(mod, "DOWNSTREAM_CONSUMERS", {})
    entry = mod.register_downstream_consumer(
        "c2",
        "o/r",
        plane="runtime",
        federation_moniker="X",
        contract_path="a.yaml",
        consumes_phases=["p1"],
        produces_for_phases=["p2"],
        tuple_source="src",
    )
    assert entry["plane"] == "runtime"
    assert entry["consumes_phases"] == ["p1"]
    assert entry["produces_for_phases"] == ["p2"]
    assert entry["tuple_source"] == "src"
    assert list(mod.DOWNSTREAM_CONSUMERS) == ["c2"]
