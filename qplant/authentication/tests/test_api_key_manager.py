"""Unit tests for APIKeyManager — generation, validation, rotation, revocation."""

import json
import os
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path

import pytest
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from api_key_manager import APIKeyManager


@pytest.fixture
def tmp_db(tmp_path):
    """Provide a temporary database file for each test."""
    return str(tmp_path / "test_keys.json")


@pytest.fixture
def mgr(tmp_db):
    """APIKeyManager backed by a temporary database."""
    return APIKeyManager(keys_db_path=tmp_db)


# ── Generation ───────────────────────────────────────────────────────

class TestGeneration:
    def test_generate_returns_key_id_and_key(self, mgr):
        key_id, api_key = mgr.generate_key("Test Key")
        assert key_id.startswith("key_")
        assert api_key.startswith("qplant_")

    def test_generate_stores_hash_not_plaintext(self, mgr, tmp_db):
        key_id, api_key = mgr.generate_key("Test Key")
        raw = json.loads(Path(tmp_db).read_text())
        stored = raw[key_id]
        assert "key_hash" in stored
        assert api_key not in json.dumps(stored)

    def test_generate_with_custom_expiry(self, mgr):
        key_id, _ = mgr.generate_key("Short Lived", expiry_days=30)
        info = mgr.get_key_info(key_id)
        expires = datetime.fromisoformat(info["expires_at"])
        assert expires < datetime.now() + timedelta(days=31)
        assert expires > datetime.now() + timedelta(days=29)

    def test_generate_with_custom_rate_limit(self, mgr):
        key_id, _ = mgr.generate_key("Rate Limited", rate_limit=500)
        info = mgr.get_key_info(key_id)
        assert info["rate_limit_per_hour"] == 500

    def test_generate_multiple_unique(self, mgr):
        keys = [mgr.generate_key(f"Key {i}") for i in range(5)]
        ids = {k[0] for k in keys}
        vals = {k[1] for k in keys}
        assert len(ids) == 5
        assert len(vals) == 5


# ── Validation ───────────────────────────────────────────────────────

class TestValidation:
    def test_validate_valid_key(self, mgr):
        _, api_key = mgr.generate_key("Valid Key")
        result = mgr.validate_key(api_key)
        assert result["valid"] is True
        assert result["name"] == "Valid Key"

    def test_validate_invalid_key(self, mgr):
        result = mgr.validate_key("qplant_bad_key_1234567890")
        assert result["valid"] is False
        assert result["reason"] == "invalid_key"

    def test_validate_empty_key(self, mgr):
        result = mgr.validate_key("")
        assert result["valid"] is False

    def test_validate_wrong_format(self, mgr):
        result = mgr.validate_key("not_a_qplant_key")
        assert result["valid"] is False
        assert result["reason"] == "invalid_format"

    def test_validate_increments_usage(self, mgr):
        key_id, api_key = mgr.generate_key("Usage Counter")
        for _ in range(5):
            mgr.validate_key(api_key)
        info = mgr.get_key_info(key_id)
        assert info["usage_count"] == 5

    def test_validate_updates_last_used(self, mgr):
        key_id, api_key = mgr.generate_key("Last Used")
        mgr.validate_key(api_key)
        info = mgr.get_key_info(key_id)
        assert info["last_used"] is not None

    def test_validate_expired_key(self, mgr, tmp_db):
        key_id, api_key = mgr.generate_key("Expired Key", expiry_days=0)
        # Manually expire
        db = json.loads(Path(tmp_db).read_text())
        db[key_id]["expires_at"] = (datetime.now() - timedelta(days=1)).isoformat()
        Path(tmp_db).write_text(json.dumps(db))
        result = mgr.validate_key(api_key)
        assert result["valid"] is False
        assert result["reason"] == "expired"


# ── Revocation ───────────────────────────────────────────────────────

class TestRevocation:
    def test_revoke_existing_key(self, mgr):
        key_id, api_key = mgr.generate_key("Revoke Me")
        assert mgr.revoke_key(key_id) is True
        result = mgr.validate_key(api_key)
        assert result["valid"] is False
        assert result["reason"] == "revoked"

    def test_revoke_nonexistent_key(self, mgr):
        assert mgr.revoke_key("key_doesnotexist") is False

    def test_revoke_adds_timestamp(self, mgr):
        key_id, _ = mgr.generate_key("Revoke Timestamp")
        mgr.revoke_key(key_id)
        info = mgr.get_key_info(key_id)
        assert "revoked_at" in info


# ── Rotation ─────────────────────────────────────────────────────────

class TestRotation:
    def test_rotate_creates_new_revokes_old(self, mgr):
        old_id, old_key = mgr.generate_key("Rotate Me")
        result = mgr.rotate_key(old_id)
        assert result is not None
        new_id, new_key = result

        # Old key revoked
        assert mgr.validate_key(old_key)["valid"] is False
        # New key valid
        assert mgr.validate_key(new_key)["valid"] is True
        assert new_id != old_id

    def test_rotate_preserves_name(self, mgr):
        old_id, _ = mgr.generate_key("Keep Name", rate_limit=999)
        new_id, _ = mgr.rotate_key(old_id)
        info = mgr.get_key_info(new_id)
        assert info["name"] == "Keep Name"
        assert info["rate_limit_per_hour"] == 999

    def test_rotate_nonexistent_key(self, mgr):
        assert mgr.rotate_key("key_nope") is None


# ── Listing ──────────────────────────────────────────────────────────

class TestListing:
    def test_list_empty(self, mgr):
        assert mgr.list_keys() == {}

    def test_list_returns_all(self, mgr):
        for i in range(3):
            mgr.generate_key(f"Key {i}")
        keys = mgr.list_keys()
        assert len(keys) == 3

    def test_list_excludes_hash(self, mgr):
        mgr.generate_key("Secure")
        keys = mgr.list_keys()
        for v in keys.values():
            assert "key_hash" not in v

    def test_get_key_info(self, mgr):
        key_id, _ = mgr.generate_key("Info Test")
        info = mgr.get_key_info(key_id)
        assert info["name"] == "Info Test"
        assert info["status"] == "active"

    def test_get_key_info_nonexistent(self, mgr):
        assert mgr.get_key_info("key_nope") is None
