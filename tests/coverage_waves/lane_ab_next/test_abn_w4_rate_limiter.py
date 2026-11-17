"""Behaviour tests for qplant/authentication/rate_limiter.py.

The module clock (``datetime.now``) is replaced with a controllable fake so the
token-bucket refill is exercised without sleeping.
"""

from datetime import datetime, timedelta

import pytest

from tests.coverage_waves.lane_b._l2_loader import load

mod = load("qplant/authentication/rate_limiter.py", name="abn_rate_limiter")

T0 = datetime(2026, 1, 1, 12, 0, 0)


class _Clock:
    def __init__(self, start):
        self.current = start

    def now(self):
        return self.current

    def advance(self, seconds):
        self.current = self.current + timedelta(seconds=seconds)


@pytest.fixture
def clock(monkeypatch):
    fake = _Clock(T0)
    monkeypatch.setattr(mod, "datetime", fake)
    return fake


def test_first_request_creates_full_bucket_and_consumes_one(clock):
    limiter = mod.RateLimiter()
    assert limiter.allow_request("k1", 10) == (True, 9)
    status = limiter.get_status("k1")
    assert status == {
        "key_id": "k1",
        "tokens_remaining": 9,
        "last_refill": T0.isoformat(),
    }


def test_bucket_exhausts_then_denies(clock):
    limiter = mod.RateLimiter()
    results = [limiter.allow_request("k", 3) for _ in range(3)]
    assert results == [(True, 2), (True, 1), (True, 0)]
    assert limiter.allow_request("k", 3) == (False, 0)


def test_refill_after_elapsed_time(clock):
    limiter = mod.RateLimiter()
    # 3600 per hour -> 1 token per second
    for _ in range(3600):
        limiter.allow_request("k", 3600)
    assert limiter.allow_request("k", 3600) == (False, 0)
    clock.advance(2.5)
    allowed, remaining = limiter.allow_request("k", 3600)
    assert allowed is True
    assert remaining == 1
    assert limiter.get_status("k")["last_refill"] == clock.current.isoformat()


def test_refill_is_capped_at_limit(clock):
    limiter = mod.RateLimiter()
    limiter.allow_request("k", 5)
    clock.advance(10 * 3600)
    assert limiter.allow_request("k", 5) == (True, 4)


def test_keys_are_independent(clock):
    limiter = mod.RateLimiter()
    assert limiter.allow_request("a", 1) == (True, 0)
    assert limiter.allow_request("a", 1) == (False, 0)
    assert limiter.allow_request("b", 1) == (True, 0)


def test_zero_limit_always_denies(clock):
    limiter = mod.RateLimiter()
    assert limiter.allow_request("z", 0) == (False, 0)


def test_status_for_unknown_key(clock):
    limiter = mod.RateLimiter()
    assert limiter.get_status("nope") == {
        "key_id": "nope",
        "tokens_remaining": None,
        "last_refill": None,
    }


def test_reset_removes_bucket_and_unknown_reset_is_noop(clock):
    limiter = mod.RateLimiter()
    limiter.allow_request("k", 1)
    assert limiter.allow_request("k", 1) == (False, 0)
    limiter.reset("k")
    assert limiter.get_status("k")["tokens_remaining"] is None
    assert limiter.allow_request("k", 1) == (True, 0)
    limiter.reset("missing")
    assert limiter.get_status("missing")["last_refill"] is None
