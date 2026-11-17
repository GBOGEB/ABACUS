"""Lane A wave 4: DMAIC_V3.core.idempotency_wrapper and mcp_execution_contract."""

import importlib
import json
import time
from concurrent.futures import TimeoutError as FutureTimeout
from pathlib import Path

import pytest

from DMAIC_V3.core import mcp_execution_contract as mcp
from DMAIC_V3.core.integrity import sha256_json


@pytest.fixture
def iw(tmp_path, monkeypatch):
    # Importing the module builds a global wrapper that creates .dmaic_cache in
    # the working directory, so import it from inside tmp_path.
    monkeypatch.chdir(tmp_path)
    module = importlib.import_module("DMAIC_V3.core.idempotency_wrapper")
    monkeypatch.setattr(module, "GLOBAL_IDEMPOTENCY", module.GLOBAL_IDEMPOTENCY)
    return module


@pytest.fixture
def wrapper(iw, tmp_path):
    return iw.IdempotentPhaseWrapper(iw.IdempotencyConfig(cache_dir=tmp_path / "c"))


def test_config_defaults_and_cache_file(iw, tmp_path):
    cfg = iw.IdempotencyConfig()
    assert cfg.enabled is True
    assert cfg.cache_dir == Path(".dmaic_cache")
    assert (tmp_path / ".dmaic_cache").is_dir()
    assert cfg.get_cache_file("p1", 2).name == "p1_iter2.cache.json"
    assert iw.IdempotentPhaseWrapper().config.enabled is True


def test_input_hash_is_stable_and_order_insensitive(wrapper):
    h1 = wrapper._compute_input_hash(1, b=2, a=1)
    assert h1 == wrapper._compute_input_hash(1, a=1, b=2)
    assert len(h1) == 16
    assert h1 != wrapper._compute_input_hash(2, a=1, b=2)


def test_encode_decode_roundtrip(wrapper):
    value = {
        "bytes": b"\x00\x01",
        "path": Path("a") / "b",
        "tuple": (1, "x", None),
        "list": [1.5, True],
        "set": {3},
        (1, 2): "tuple-key",
    }
    encoded = wrapper._encode_cache_value(value)
    restored = wrapper._decode_cache_value(json.loads(json.dumps(encoded)))
    assert restored == value
    assert wrapper._decode_cache_value({"plain": 1}) == {"plain": 1}


def test_encode_rejects_unknown_and_decode_rejects_unknown_tag(wrapper):
    with pytest.raises(TypeError, match="Unsupported cache value type: object"):
        wrapper._encode_cache_value(object())
    with pytest.raises(ValueError, match="Unknown cache value type: weird"):
        wrapper._decode_cache_value({"__dmaic_cache_type__": "weird"})


def test_load_cache_missing_and_corrupt(wrapper, tmp_path):
    assert wrapper._load_cache(tmp_path / "none.json") is None
    bad = tmp_path / "bad.json"
    bad.write_bytes(b"{nope")
    assert wrapper._load_cache(bad) is None


def test_save_cache_unsupported_value_is_not_cached(wrapper, tmp_path):
    target = tmp_path / "c" / "x.cache.json"
    assert wrapper._save_cache(target, object(), "h") is False
    assert not target.exists()


def test_save_cache_writes_atomically(wrapper, tmp_path):
    target = tmp_path / "c" / "x.cache.json"
    assert wrapper._save_cache(target, [1, 2], "h") is True
    data = json.loads(target.read_text(encoding="utf-8"))
    assert data["input_hash"] == "h"
    assert wrapper._restore_cached_result(data) == [1, 2]
    assert [p.name for p in target.parent.iterdir()] == ["x.cache.json"]


def test_save_cache_cleans_temp_on_replace_failure(wrapper, tmp_path, monkeypatch):
    def fail(source, target, attempts=6):
        raise PermissionError("locked")

    monkeypatch.setattr(wrapper, "_replace_with_retry", fail)
    target = tmp_path / "c" / "x.cache.json"
    with pytest.raises(PermissionError):
        wrapper._save_cache(target, 1, "h")
    assert list(target.parent.iterdir()) == []


def test_replace_with_retry_retries_then_succeeds(iw, monkeypatch):
    calls = []

    class Flaky:
        def replace(self, target):
            calls.append(target)
            if len(calls) < 3:
                raise PermissionError("busy")

    monkeypatch.setattr(time, "sleep", lambda s: None)
    iw.IdempotentPhaseWrapper._replace_with_retry(Flaky(), "t")
    assert calls == ["t", "t", "t"]


def test_replace_with_retry_gives_up(iw, monkeypatch):
    class Locked:
        def replace(self, target):
            raise PermissionError("busy")

    monkeypatch.setattr(time, "sleep", lambda s: None)
    with pytest.raises(PermissionError):
        iw.IdempotentPhaseWrapper._replace_with_retry(Locked(), "t", attempts=2)


def test_idempotent_decorator_hits_cache(wrapper, capsys):
    calls = []

    @wrapper.idempotent(phase_name="phase1_define")
    def run(x, iteration=1):
        calls.append((x, iteration))
        return {"x": x, "items": (1, 2)}

    first = run(5, iteration=2)
    second = run(5, iteration=2)
    assert first == second == {"x": 5, "items": (1, 2)}
    assert calls == [(5, 2)]
    out = capsys.readouterr().out
    assert "Cache miss - executing phase1_define" in out
    assert "Cache hit for phase1_define iteration 2" in out

    run(6, iteration=2)
    assert calls == [(5, 2), (6, 2)]
    assert run.__name__ == "run"


def test_idempotent_decorator_disabled(iw, tmp_path, capsys):
    off = iw.IdempotentPhaseWrapper(
        iw.IdempotencyConfig(enabled=False, cache_dir=tmp_path / "off")
    )
    calls = []

    @off.idempotent(phase_name="p")
    def run():
        calls.append(1)
        return 1

    run()
    run()
    assert calls == [1, 1]
    assert "[IDEMPOTENCY] Disabled - executing p" in capsys.readouterr().out
    assert list((tmp_path / "off").iterdir()) == []


def test_enable_and_clear_cache(iw, tmp_path, capsys):
    cache = tmp_path / "g"
    iw.enable_idempotency(False, cache_dir=cache)
    assert iw.GLOBAL_IDEMPOTENCY.config.enabled is False
    iw.enable_idempotency(True, cache_dir=cache)
    assert iw.GLOBAL_IDEMPOTENCY.config.cache_dir == cache
    out = capsys.readouterr().out
    assert "Disabled globally" in out and "Enabled globally" in out

    for name in ("a_iter1", "a_iter2", "b_iter1"):
        (cache / (name + ".cache.json")).write_bytes(b"{}")

    iw.clear_cache("a", 1)
    iw.clear_cache("a", 9)
    assert sorted(p.name for p in cache.iterdir()) == [
        "a_iter2.cache.json",
        "b_iter1.cache.json",
    ]
    iw.clear_cache("a")
    assert [p.name for p in cache.iterdir()] == ["b_iter1.cache.json"]
    iw.clear_cache()
    assert list(cache.iterdir()) == []
    out = capsys.readouterr().out
    assert "Cleared cache for a iteration 1" in out
    assert "Cleared all caches for a" in out
    assert "Cleared all caches" in out


def _request(payload, timeout=5.0, parent=None):
    return mcp.MCPRequest(
        task_id="t1",
        mode="AD_HOC",
        payload=payload,
        parent_sha256=parent or sha256_json(payload),
        timeout_seconds=timeout,
    )


def test_execute_mcp_success_receipt():
    payload = {"files": ["a", "b"]}
    finding, receipt = mcp.execute_mcp(_request(payload), lambda p: len(p["files"]))
    assert finding == 2
    assert receipt.status == "success"
    assert receipt.finding_sha256 == sha256_json(2)
    assert receipt.returned_parent_sha256 == receipt.parent_sha256
    assert receipt.to_dict()["authority"] == "ANALYTICAL_FINDING_ONLY"
    assert receipt.error is None


def test_execute_mcp_rejects_parent_mismatch():
    with pytest.raises(ValueError, match="SHA256 mismatch"):
        mcp.execute_mcp(_request({"a": 1}, parent="0" * 64), lambda p: p)


def test_execute_mcp_detects_isolated_mutation():
    def mutate(p):
        p["a"] = 2
        return "x"

    with pytest.raises(RuntimeError, match="mutated isolated parent"):
        mcp.execute_mcp(_request({"a": 1}), mutate)


def test_execute_mcp_detects_parent_mutation_outside_isolation():
    payload = {"a": 1}

    def reach_out(p):
        payload["a"] = 99
        return "x"

    with pytest.raises(RuntimeError, match="changed outside worker isolation"):
        mcp.execute_mcp(_request(payload), reach_out)


def test_execute_mcp_timeout():
    def slow(p):
        time.sleep(0.2)
        return "late"

    with pytest.raises(FutureTimeout, match="worker timeout after 0.01 seconds"):
        mcp.execute_mcp(_request({"a": 1}, timeout=0.01), slow)
