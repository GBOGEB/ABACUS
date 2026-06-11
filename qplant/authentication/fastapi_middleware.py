"""
FastAPI middleware for API key authentication.

Usage::

    from authentication.fastapi_middleware import verify_api_key

    @app.get("/protected", dependencies=[Depends(verify_api_key)])
    async def protected_endpoint():
        return {"message": "Authenticated"}

    # Or inject key metadata into the endpoint:
    @app.get("/me")
    async def whoami(key_info: dict = Depends(verify_api_key)):
        return {"key_name": key_info["name"]}
"""

from __future__ import annotations

import os
import sys
from typing import Dict, Any

from fastapi import Security, HTTPException, status, Request
from fastapi.security import APIKeyHeader

# Ensure the authentication package is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from api_key_manager import APIKeyManager
from rate_limiter import RateLimiter

# ── Globals ──────────────────────────────────────────────────────────────────

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

_keys_db_path = os.environ.get(
    "QPLANT_API_KEYS_DB",
    "/home/ubuntu/authentication/api_keys.json",
)
key_manager = APIKeyManager(keys_db_path=_keys_db_path)
rate_limiter = RateLimiter()


# ── Dependency ───────────────────────────────────────────────────────────────

async def verify_api_key(
    api_key: str | None = Security(api_key_header),
) -> Dict[str, Any]:
    """
    FastAPI dependency that validates the ``X-API-Key`` header.

    Raises:
        HTTPException 401 — missing, invalid, expired, or revoked key.
        HTTPException 429 — rate limit exceeded.

    Returns:
        Key metadata dict on success (key_id, name, rate_limit).
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Provide X-API-Key header.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    validation = key_manager.validate_key(api_key)

    if not validation["valid"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid API key: {validation['reason']}",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Rate limiting
    allowed, remaining = rate_limiter.allow_request(
        validation["key_id"],
        validation["rate_limit"],
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Try again later.",
            headers={"Retry-After": "60"},
        )

    return validation
