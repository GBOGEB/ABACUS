from pathlib import Path

import pytest

from DMAIC_V3.core import idempotency_wrapper as idem


@pytest.mark.unit
def test_config_cache_path_and_hash_are_deterministic(tmp_path):
    config = idem.IdempotencyConfig(enabled=True, cache_dir=tmp_path / "cache")
    wrapper = idem.IdempotentPhaseWrapper(config)

    assert config.cache_dir.exists()
    assert config.get_cache_file("phase1", 3) == config.cache_dir / "phase1_iter3.cache.json"

    first = wrapper._compute_input_hash("x", iteration=2, b=1, a=2)
    second = wrapper._compute_input_hash("x", a=2, b=1, iteration=2)
    changed = wrapper._compute_input_hash("x", a=3, b=1, iteration=2)

    assert first == second
    assert first != changed
    assert len(first) == 16


@pytest.mark.unit
def test_cache_load_missing_corrupt_and_roundtrip(tmp_path):
    wrapper = idem.IdempotentPhaseWrapper(
        idem.IdempotencyConfig(cache_dir=tmp_path / "cache")
    )
    cache_file = wrapper.config.get_cache_file("measure", 1)

    assert wrapper._load_cache(cache_file) is None

    cache_file.write_text("{not-json", encoding="utf-8")
    assert wrapper._load_cache(cache_file) is None

    wrapper._save_cache(cache_file, {"value": 7}, "abc123")
    loaded = wrapper._load_cache(cache_file)

    assert loaded["input_hash"] == "abc123"
    assert loaded["result"] == {"value": 7}
    assert "timestamp" in loaded


@pytest.mark.unit
def test_enabled_decorator_caches_same_input_and_reexecutes_changed_input(tmp_path):
    wrapper = idem.IdempotentPhaseWrapper(
        idem.IdempotencyConfig(enabled=True, cache_dir=tmp_path / "cache")
    )
    calls = []

    @wrapper.idempotent("phase2_measure")
    def phase(value, *, iteration=1):
        calls.append(value)
        return {"value": value, "call": len(calls)}

    first = phase("alpha", iteration=4)
    second = phase("alpha", iteration=4)
    changed = phase("beta", iteration=4)

    assert first == {"value": "alpha", "call": 1}
    assert second == first
    assert changed == {"value": "beta", "call": 2}
    assert calls == ["alpha", "beta"]
    assert wrapper.config.get_cache_file("phase2_measure", 4).exists()


@pytest.mark.unit
def test_disabled_decorator_always_executes_without_cache(tmp_path):
    wrapper = idem.IdempotentPhaseWrapper(
        idem.IdempotencyConfig(enabled=False, cache_dir=tmp_path / "cache")
    )
    calls = []

    @wrapper.idempotent("phase3_analyze")
    def phase(value, *, iteration=1):
        calls.append(value)
        return value.upper()

    assert phase("a", iteration=2) == "A"
    assert phase("a", iteration=2) == "A"
    assert calls == ["a", "a"]
    assert not wrapper.config.get_cache_file("phase3_analyze", 2).exists()


@pytest.mark.unit
def test_non_dict_result_preserves_same_output_on_cache_hit(tmp_path):
    wrapper = idem.IdempotentPhaseWrapper(
        idem.IdempotencyConfig(enabled=True, cache_dir=tmp_path / "cache")
    )
    calls = []

    @wrapper.idempotent("phase4_improve")
    def phase(*, iteration=1):
        calls.append(iteration)
        return "raw-result"

    first = phase(iteration=5)
    second = phase(iteration=5)

    assert first == "raw-result"
    assert second == first
    assert calls == [5]


@pytest.mark.unit
def test_tuple_result_preserves_phase_return_contract_on_cache_hit(tmp_path):
    wrapper = idem.IdempotentPhaseWrapper(
        idem.IdempotencyConfig(enabled=True, cache_dir=tmp_path / "cache")
    )
    calls = []

    @wrapper.idempotent("phase0_init")
    def phase(*, iteration=1):
        calls.append(iteration)
        return True, {"iteration": iteration}

    first = phase(iteration=6)
    second = phase(iteration=6)

    assert first == (True, {"iteration": 6})
    assert second == first
    assert isinstance(second, tuple)
    assert calls == [6]


@pytest.mark.unit
def test_nested_container_types_round_trip_recursively(tmp_path):
    wrapper = idem.IdempotentPhaseWrapper(
        idem.IdempotencyConfig(enabled=True, cache_dir=tmp_path / "cache")
    )
    calls = []

    @wrapper.idempotent("phase_nested")
    def phase(*, iteration=1):
        calls.append(iteration)
        return {
            "rows": [("a", 1), ("b", 2)],
            "path": tmp_path / "artifact.json",
            "tags": {"x", "y"},
            "payload": b"abc",
        }

    first = phase(iteration=7)
    second = phase(iteration=7)

    assert second == first
    assert isinstance(second["rows"][0], tuple)
    assert isinstance(second["path"], type(tmp_path))
    assert isinstance(second["tags"], set)
    assert isinstance(second["payload"], bytes)
    assert calls == [7]


@pytest.mark.unit
def test_unsupported_result_skips_cache_without_changing_return(tmp_path):
    wrapper = idem.IdempotentPhaseWrapper(
        idem.IdempotencyConfig(enabled=True, cache_dir=tmp_path / "cache")
    )
    calls = []

    class Unsupported:
        pass

    @wrapper.idempotent("phase_unsupported")
    def phase(*, iteration=1):
        calls.append(iteration)
        return Unsupported()

    first = phase(iteration=8)
    second = phase(iteration=8)

    assert isinstance(first, Unsupported)
    assert isinstance(second, Unsupported)
    assert first is not second
    assert calls == [8, 8]
    assert not wrapper.config.get_cache_file("phase_unsupported", 8).exists()


@pytest.mark.unit
def test_enable_idempotency_rebinds_global_configuration(tmp_path, capsys):
    original = idem.GLOBAL_IDEMPOTENCY
    try:
        idem.enable_idempotency(enabled=False, cache_dir=tmp_path / "global-cache")

        assert idem.GLOBAL_IDEMPOTENCY.config.enabled is False
        assert idem.GLOBAL_IDEMPOTENCY.config.cache_dir == tmp_path / "global-cache"
        assert "Disabled globally" in capsys.readouterr().out

        idem.enable_idempotency(enabled=True, cache_dir=tmp_path / "enabled-cache")
        assert idem.GLOBAL_IDEMPOTENCY.config.enabled is True
        assert "Enabled globally" in capsys.readouterr().out
    finally:
        idem.GLOBAL_IDEMPOTENCY = original


@pytest.mark.unit
def test_clear_cache_specific_phase_and_all_modes(tmp_path, capsys):
    original = idem.GLOBAL_IDEMPOTENCY
    try:
        config = idem.IdempotencyConfig(cache_dir=tmp_path / "cache")
        idem.GLOBAL_IDEMPOTENCY = idem.IdempotentPhaseWrapper(config)

        p1_i1 = config.get_cache_file("phase1", 1)
        p1_i2 = config.get_cache_file("phase1", 2)
        p2_i1 = config.get_cache_file("phase2", 1)
        for path in (p1_i1, p1_i2, p2_i1):
            path.write_text("{}", encoding="utf-8")

        idem.clear_cache("phase1", 1)
        assert not p1_i1.exists()
        assert p1_i2.exists()
        assert p2_i1.exists()

        idem.clear_cache("phase1")
        assert not p1_i2.exists()
        assert p2_i1.exists()

        idem.clear_cache()
        assert not p2_i1.exists()

        output = capsys.readouterr().out
        assert "Cleared cache for phase1 iteration 1" in output
        assert "Cleared all caches for phase1" in output
        assert "Cleared all caches" in output
    finally:
        idem.GLOBAL_IDEMPOTENCY = original


@pytest.mark.unit
def test_clear_specific_nonexistent_cache_is_safe(tmp_path):
    original = idem.GLOBAL_IDEMPOTENCY
    try:
        config = idem.IdempotencyConfig(cache_dir=tmp_path / "cache")
        idem.GLOBAL_IDEMPOTENCY = idem.IdempotentPhaseWrapper(config)

        idem.clear_cache("missing", 99)

        assert list(config.cache_dir.glob("*.cache.json")) == []
    finally:
        idem.GLOBAL_IDEMPOTENCY = original
