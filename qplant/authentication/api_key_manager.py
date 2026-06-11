"""
Simple API Key Authentication Manager
Production-ready security without OAuth2 complexity

Features:
- Secure key generation (cryptographically random)
- Key hashing (PBKDF2-HMAC-SHA256, never store plaintext)
- Expiration support
- Rate limiting metadata
- Audit logging
- Key rotation
"""

import secrets
import hashlib
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Tuple, Dict, Any

logger = logging.getLogger(__name__)

# PBKDF2-HMAC-SHA256 iteration count (OWASP 2023 recommendation)
_PBKDF2_ITERATIONS = 260_000
# First N chars of a key stored for O(1) lookup; the remaining chars stay secret.
_KEY_PREFIX_LEN = 15
# Fields stored for internal use only — excluded from all public listings.
_INTERNAL_FIELDS: frozenset = frozenset({"key_hash", "key_salt", "key_prefix"})


class APIKeyManager:
    """
    Manages API keys for secure service access.

    Keys are stored as PBKDF2-HMAC-SHA256 hashes — plaintext keys are never
    persisted.  A random per-key salt is generated at creation time.  A
    non-secret prefix of the key is stored to enable O(1) candidate lookup
    before the expensive hash verification.

    Each key carries metadata: name, expiry, rate-limit, status, usage count.
    """

    def __init__(self, keys_db_path: str = "/home/ubuntu/authentication/api_keys.json") -> None:
        self.keys_db = Path(keys_db_path)
        self._ensure_db()

    # ── Key lifecycle ────────────────────────────────────────────────────

    def generate_key(
        self,
        name: str,
        expiry_days: int = 365,
        rate_limit: int = 1000,
    ) -> Tuple[str, str]:
        """
        Generate a new API key.

        Returns:
            (key_id, api_key) — caller must store `api_key` securely; it is
            never persisted on disk.
        """
        api_key = f"qplant_{secrets.token_urlsafe(32)}"
        key_id = f"key_{secrets.token_hex(8)}"
        salt = secrets.token_bytes(32)
        key_hash = self._hash_key(api_key, salt)
        key_prefix = api_key[:_KEY_PREFIX_LEN]

        metadata: Dict[str, Any] = {
            "key_id": key_id,
            "name": name,
            "key_hash": key_hash,
            "key_salt": salt.hex(),
            "key_prefix": key_prefix,
            "created_at": datetime.now().isoformat(),
            "expires_at": (datetime.now() + timedelta(days=expiry_days)).isoformat(),
            "rate_limit_per_hour": rate_limit,
            "status": "active",
            "last_used": None,
            "usage_count": 0,
        }

        db = self._load_db()
        db[key_id] = metadata
        self._save_db(db)

        logger.info("Generated API key '%s' (id=%s, expires=%s)", name, key_id, metadata["expires_at"])
        return key_id, api_key

    def validate_key(self, api_key: str) -> Dict[str, Any]:
        """
        Validate an API key and return metadata.

        Returns dict with ``valid`` boolean plus either key metadata or
        a ``reason`` string explaining the failure.
        """
        if not api_key or not api_key.startswith("qplant_"):
            return {"valid": False, "reason": "invalid_format"}

        key_prefix = api_key[:_KEY_PREFIX_LEN]
        db = self._load_db()

        for key_id, meta in db.items():
            # Fast prefix filter — only compute PBKDF2 for matching candidates.
            if meta.get("key_prefix") != key_prefix:
                continue
            if "key_salt" not in meta:
                continue  # Skip legacy or malformed entries
            salt = bytes.fromhex(meta["key_salt"])
            if meta["key_hash"] != self._hash_key(api_key, salt):
                continue

            # Hash matches — check expiration
            if datetime.fromisoformat(meta["expires_at"]) < datetime.now():
                logger.warning("Expired API key used: %s", key_id)
                return {"valid": False, "reason": "expired"}

            # Check status
            if meta["status"] != "active":
                logger.warning("Revoked API key used: %s", key_id)
                return {"valid": False, "reason": "revoked"}

            # Update usage stats
            meta["last_used"] = datetime.now().isoformat()
            meta["usage_count"] += 1
            db[key_id] = meta
            self._save_db(db)

            return {
                "valid": True,
                "key_id": key_id,
                "name": meta["name"],
                "rate_limit": meta["rate_limit_per_hour"],
            }

        return {"valid": False, "reason": "invalid_key"}

    def revoke_key(self, key_id: str) -> bool:
        """Revoke an API key by key_id."""
        db = self._load_db()
        if key_id in db:
            db[key_id]["status"] = "revoked"
            db[key_id]["revoked_at"] = datetime.now().isoformat()
            self._save_db(db)
            logger.info("Revoked API key: %s", key_id)
            return True
        return False

    def rotate_key(self, old_key_id: str) -> Optional[Tuple[str, str]]:
        """
        Rotate an API key — create a replacement and revoke the old one.

        Returns:
            (new_key_id, new_api_key) or None if old_key_id not found.
        """
        db = self._load_db()
        if old_key_id not in db:
            return None

        old_meta = db[old_key_id]
        new_key_id, new_api_key = self.generate_key(
            name=old_meta["name"],
            expiry_days=365,
            rate_limit=old_meta["rate_limit_per_hour"],
        )
        self.revoke_key(old_key_id)
        logger.info("API key rotated: %s (replaced by new key)", old_key_id)
        return new_key_id, new_api_key

    def list_keys(self) -> Dict[str, Dict[str, Any]]:
        """List all API keys with metadata (excluding internal fields)."""
        db = self._load_db()
        return {
            k: {key: val for key, val in v.items() if key not in _INTERNAL_FIELDS}
            for k, v in db.items()
        }

    def get_key_info(self, key_id: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a specific key (excluding internal fields)."""
        db = self._load_db()
        if key_id in db:
            return {k: v for k, v in db[key_id].items() if k not in _INTERNAL_FIELDS}
        return None

    # ── Internal helpers ─────────────────────────────────────────────────

    def _hash_key(self, api_key: str, salt: bytes) -> str:
        """Hash an API key with PBKDF2-HMAC-SHA256 (computationally expensive)."""
        return hashlib.pbkdf2_hmac(
            "sha256", api_key.encode(), salt, _PBKDF2_ITERATIONS
        ).hex()

    def _ensure_db(self) -> None:
        """Create the key database file if it does not exist."""
        self.keys_db.parent.mkdir(parents=True, exist_ok=True)
        if not self.keys_db.exists():
            self._save_db({})

    def _load_db(self) -> Dict[str, Any]:
        """Load the key database from disk."""
        try:
            with open(self.keys_db, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}

    def _save_db(self, db: Dict[str, Any]) -> None:
        """Persist the key database to disk."""
        with open(self.keys_db, "w") as f:
            json.dump(db, f, indent=2, default=str)
