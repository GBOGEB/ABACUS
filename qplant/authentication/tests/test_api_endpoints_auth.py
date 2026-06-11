"""Integration tests for API authentication middleware."""

import json
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from api_key_manager import APIKeyManager

# We test the middleware logic directly without needing a running FastAPI server.
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient
from fastapi.security import APIKeyHeader


@pytest.fixture
def tmp_db(tmp_path):
    return str(tmp_path / "test_keys.json")


@pytest.fixture
def auth_app(tmp_db):
    """Create a minimal FastAPI app with authentication middleware."""
    from api_key_manager import APIKeyManager
    from rate_limiter import RateLimiter
    from fastapi import Security, HTTPException, status
    from fastapi.security import APIKeyHeader

    mgr = APIKeyManager(keys_db_path=tmp_db)
    limiter = RateLimiter()
    header = APIKeyHeader(name="X-API-Key", auto_error=False)

    async def verify(api_key: str = Security(header)):
        if not api_key:
            raise HTTPException(status_code=401, detail="Missing API key")
        result = mgr.validate_key(api_key)
        if not result["valid"]:
            raise HTTPException(status_code=401, detail=f"Invalid: {result['reason']}")
        allowed, _ = limiter.allow_request(result["key_id"], result["rate_limit"])
        if not allowed:
            raise HTTPException(status_code=429, detail="Rate limited")
        return result

    app = FastAPI()

    @app.get("/public")
    async def public():
        return {"message": "public"}

    @app.get("/protected", dependencies=[Depends(verify)])
    async def protected():
        return {"message": "authenticated"}

    @app.get("/me")
    async def me(key_info: dict = Depends(verify)):
        return {"name": key_info["name"], "key_id": key_info["key_id"]}

    return app, mgr


@pytest.fixture
def client(auth_app):
    app, _ = auth_app
    return TestClient(app)


@pytest.fixture
def api_key(auth_app):
    _, mgr = auth_app
    _, key = mgr.generate_key("Test Client", rate_limit=100)
    return key


class TestPublicEndpoints:
    def test_public_no_key(self, client):
        r = client.get("/public")
        assert r.status_code == 200
        assert r.json()["message"] == "public"


class TestProtectedEndpoints:
    def test_no_key_returns_401(self, client):
        r = client.get("/protected")
        assert r.status_code == 401

    def test_invalid_key_returns_401(self, client):
        r = client.get("/protected", headers={"X-API-Key": "qplant_invalid"})
        assert r.status_code == 401

    def test_valid_key_returns_200(self, client, api_key):
        r = client.get("/protected", headers={"X-API-Key": api_key})
        assert r.status_code == 200
        assert r.json()["message"] == "authenticated"

    def test_me_returns_key_info(self, client, api_key):
        r = client.get("/me", headers={"X-API-Key": api_key})
        assert r.status_code == 200
        assert r.json()["name"] == "Test Client"

    def test_revoked_key_returns_401(self, auth_app, client):
        _, mgr = auth_app
        key_id, api_key = mgr.generate_key("Revoke Test")
        mgr.revoke_key(key_id)
        r = client.get("/protected", headers={"X-API-Key": api_key})
        assert r.status_code == 401

    def test_rate_limit_returns_429(self, auth_app, client):
        _, mgr = auth_app
        _, api_key = mgr.generate_key("Rate Test", rate_limit=5)
        for _ in range(5):
            client.get("/protected", headers={"X-API-Key": api_key})
        r = client.get("/protected", headers={"X-API-Key": api_key})
        assert r.status_code == 429
