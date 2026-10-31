"""Lane-B wave 15: qplant API-key middleware.

``fastapi`` is replaced by a minimal fake injected through the loader so the
middleware logic runs in CI jobs without it. The key database lives under
tmp_path (``QPLANT_API_KEYS_DB``). materials_db and analyze_results are owned
by #2533 (lane_ab_next).
"""

import asyncio
import json
import sys
import types

import pytest

from ._l2_loader import load

# --------------------------------------------------------------------------
# authentication/fastapi_middleware.py
# --------------------------------------------------------------------------


class FakeHTTPException(Exception):
    def __init__(self, status_code, detail=None, headers=None):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail
        self.headers = headers


def _fake_fastapi():
    fastapi = types.ModuleType("fastapi")
    fastapi.Security = lambda dep: dep
    fastapi.HTTPException = FakeHTTPException
    fastapi.Request = object
    fastapi.status = types.SimpleNamespace(
        HTTP_401_UNAUTHORIZED=401, HTTP_429_TOO_MANY_REQUESTS=429
    )
    security = types.ModuleType("fastapi.security")

    class APIKeyHeader:
        def __init__(self, name, auto_error=True):
            self.name = name
            self.auto_error = auto_error

    security.APIKeyHeader = APIKeyHeader
    fastapi.security = security
    return {"fastapi": fastapi, "fastapi.security": security}


@pytest.fixture
def mw(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "path", list(sys.path))
    monkeypatch.setenv("QPLANT_API_KEYS_DB", str(tmp_path / "keys" / "db.json"))
    akm = load("qplant/authentication/api_key_manager.py")
    rl = load("qplant/authentication/rate_limiter.py")
    deps = _fake_fastapi()
    deps.update(api_key_manager=akm, rate_limiter=rl)
    return load("qplant/authentication/fastapi_middleware.py", deps=deps)


def _call(mod, key):
    return asyncio.run(mod.verify_api_key(key))


def test_globals_wire_header_and_tmp_key_db(mw, tmp_path):
    assert mw.api_key_header.name == "X-API-Key"
    assert mw.api_key_header.auto_error is False
    assert mw.key_manager.keys_db == tmp_path / "keys" / "db.json"
    assert json.loads(mw.key_manager.keys_db.read_text()) == {}


@pytest.mark.parametrize("key", [None, ""])
def test_missing_key_is_401(mw, key):
    with pytest.raises(FakeHTTPException) as exc:
        _call(mw, key)
    assert exc.value.status_code == 401
    assert "Missing API key" in exc.value.detail
    assert exc.value.headers == {"WWW-Authenticate": "ApiKey"}


def test_invalid_key_reports_reason(mw):
    with pytest.raises(FakeHTTPException) as exc:
        _call(mw, "not" + "_a_key")
    assert exc.value.status_code == 401
    assert exc.value.detail == "Invalid API key: invalid_format"


def test_valid_key_returns_metadata_then_rate_limits(mw):
    key_id, api_key = mw.key_manager.generate_key("svc", rate_limit=1)
    info = _call(mw, api_key)
    assert info == {"valid": True, "key_id": key_id, "name": "svc", "rate_limit": 1}
    with pytest.raises(FakeHTTPException) as exc:
        _call(mw, api_key)
    assert exc.value.status_code == 429
    assert exc.value.headers == {"Retry-After": "60"}
