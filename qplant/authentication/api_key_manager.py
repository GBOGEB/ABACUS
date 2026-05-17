"""
Simple API Key Authentication Manager
Production-ready security without OAuth2 complexity

Features:
- Secure key generation (cryptographically random)
- Key hashing (SHA-256, never store plaintext)
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


class APIKeyManager:
    """
    Manages API keys for secure service access.

    Keys are stored as SHA-256 hashes — plaintext keys are never persisted.
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
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()

        metadata: Dict[str, Any] = {
            "key_id": key_id,
            "name": name,
            "key_hash": key_hash,
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

        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        db = self._load_db()

        for key_id, meta in db.items():
            if meta["key_hash"] == key_hash:
                # Check expiration
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
        logger.info("Rotated API key %s → %s", old_key_id, new_key_id)
        return new_key_id, new_api_key

    def list_keys(self) -> Dict[str, Dict[str, Any]]:
        """List all API keys with metadata (excluding hashes)."""
        db = self._load_db()
        return {
            k: {key: val for key, val in v.items() if key != "key_hash"}
            for k, v in db.items()
        }

    def get_key_info(self, key_id: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a specific key (excluding hash)."""
        db = self._load_db()
        if key_id in db:
            return {k: v for k, v in db[key_id].items() if k != "key_hash"}
        return None

    # ── Internal helpers ─────────────────────────────────────────────────

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
