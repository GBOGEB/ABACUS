"""
Rate limiter for API key usage.
Implements token-bucket algorithm with thread safety.
"""

import threading
from collections import defaultdict
from datetime import datetime
from typing import Tuple, Dict, Any


class RateLimiter:
    """
    Thread-safe token-bucket rate limiter.

    Each key_id gets an independent bucket that refills at
    ``rate_limit_per_hour / 3600`` tokens per second, capped at
    ``rate_limit_per_hour``.
    """

    def __init__(self) -> None:
        self._buckets: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def allow_request(self, key_id: str, rate_limit_per_hour: int) -> Tuple[bool, int]:
        """
        Check whether a request is allowed under the rate limit.

        Args:
            key_id: Unique identifier for the API key.
            rate_limit_per_hour: Maximum requests per hour for this key.

        Returns:
            (allowed, remaining) — ``allowed`` is True if the request
            may proceed; ``remaining`` is the approximate token count
            after this call.
        """
        with self._lock:
            now = datetime.now()

            if key_id not in self._buckets:
                self._buckets[key_id] = {
                    "tokens": float(rate_limit_per_hour),
                    "last_refill": now,
                }

            bucket = self._buckets[key_id]

            # Refill tokens based on elapsed time
            elapsed_s = (now - bucket["last_refill"]).total_seconds()
            refill_rate = rate_limit_per_hour / 3600.0  # tokens per second
            tokens_to_add = elapsed_s * refill_rate

            bucket["tokens"] = min(
                float(rate_limit_per_hour),
                bucket["tokens"] + tokens_to_add,
            )
            bucket["last_refill"] = now

            # Consume one token if available
            if bucket["tokens"] >= 1.0:
                bucket["tokens"] -= 1.0
                return True, int(bucket["tokens"])
            else:
                return False, 0

    def get_status(self, key_id: str) -> Dict[str, Any]:
        """Return current bucket status for a key."""
        with self._lock:
            if key_id in self._buckets:
                b = self._buckets[key_id]
                return {
                    "key_id": key_id,
                    "tokens_remaining": int(b["tokens"]),
                    "last_refill": b["last_refill"].isoformat(),
                }
            return {"key_id": key_id, "tokens_remaining": None, "last_refill": None}

    def reset(self, key_id: str) -> None:
        """Reset bucket for a key (e.g. after key rotation)."""
        with self._lock:
            if key_id in self._buckets:
                del self._buckets[key_id]
