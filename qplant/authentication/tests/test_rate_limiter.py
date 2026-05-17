"""Unit tests for RateLimiter — token-bucket algorithm."""

import os
import sys
import time
import threading

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from rate_limiter import RateLimiter


@pytest.fixture
def limiter():
    return RateLimiter()


class TestTokenBucket:
    def test_first_request_allowed(self, limiter):
        allowed, remaining = limiter.allow_request("key_1", 100)
        assert allowed is True
        assert remaining >= 0

    def test_burst_within_limit(self, limiter):
        """All requests in a burst within the limit should succeed."""
        for i in range(50):
            allowed, _ = limiter.allow_request("key_burst", 100)
            assert allowed is True, f"Request {i} should be allowed"

    def test_exceeds_limit(self, limiter):
        """Exceeding the bucket should be rejected."""
        # Drain all tokens
        for _ in range(100):
            limiter.allow_request("key_drain", 100)
        # Next request should fail
        allowed, remaining = limiter.allow_request("key_drain", 100)
        assert allowed is False
        assert remaining == 0

    def test_independent_keys(self, limiter):
        """Different keys have independent buckets."""
        for _ in range(100):
            limiter.allow_request("key_a", 100)
        # key_b should still be allowed
        allowed, _ = limiter.allow_request("key_b", 100)
        assert allowed is True

    def test_refill_over_time(self, limiter):
        """Tokens should refill over time."""
        # Use a high rate so refill is measurable in a short sleep
        rate = 36000  # 10 tokens/second
        for _ in range(36000):
            limiter.allow_request("key_refill", rate)
        # Wait for refill
        time.sleep(0.2)
        allowed, _ = limiter.allow_request("key_refill", rate)
        assert allowed is True

    def test_status_reporting(self, limiter):
        limiter.allow_request("key_status", 100)
        status = limiter.get_status("key_status")
        assert status["key_id"] == "key_status"
        assert status["tokens_remaining"] is not None
        assert status["last_refill"] is not None

    def test_status_unknown_key(self, limiter):
        status = limiter.get_status("key_unknown")
        assert status["tokens_remaining"] is None

    def test_reset_bucket(self, limiter):
        for _ in range(100):
            limiter.allow_request("key_reset", 100)
        limiter.reset("key_reset")
        # After reset, bucket is fresh
        allowed, remaining = limiter.allow_request("key_reset", 100)
        assert allowed is True
        assert remaining >= 0


class TestConcurrency:
    def test_thread_safety(self, limiter):
        """Rate limiter should be thread-safe."""
        results = []

        def make_requests():
            for _ in range(50):
                allowed, _ = limiter.allow_request("key_thread", 1000)
                results.append(allowed)

        threads = [threading.Thread(target=make_requests) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(results) == 200
        allowed_count = sum(1 for r in results if r)
        # Most should be allowed (1000 limit, 200 requests)
        assert allowed_count >= 190
