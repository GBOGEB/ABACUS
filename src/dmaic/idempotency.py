"""
Idempotency module.
Provides deterministic hashing and persistent idempotent execution support.
"""

import functools
import hashlib
import json
import logging
import os
from pathlib import Path
from typing import Any, Callable, Dict, Optional

LOGGER = logging.getLogger(__name__)


def hash_json(data: Any) -> str:
    """
    Compute SHA256 hash of JSON-serializable data
    
    Args:
        data: JSON-serializable data to hash
        
    Returns:
        Hexadecimal hash string
    """
    if isinstance(data, dict):
        # Sort dict keys for consistent hashing
        json_str = json.dumps(data, sort_keys=True)
    else:
        json_str = json.dumps(data)
    return hashlib.sha256(json_str.encode()).hexdigest()


def _default_cache_dir() -> Path:
    base = os.environ.get("DMAIC_CACHE_DIR")
    if base:
        path = Path(base)
    else:
        path = Path.cwd() / ".dmaic" / "idempotency"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _cache_file_for_key(run_key: str, cache_dir: Path) -> Path:
    key_hash = hashlib.sha256(run_key.encode("utf-8")).hexdigest()
    return cache_dir / f"{key_hash}.json"


def _load_cache(cache_file: Path) -> Optional[Any]:
    if not cache_file.exists():
        return None
    try:
        return json.loads(cache_file.read_text(encoding="utf-8")).get("result")
    except (json.JSONDecodeError, OSError, AttributeError):
        LOGGER.warning("Unreadable cache file: %s", cache_file)
        return None


def _save_cache(cache_file: Path, run_key: str, result: Any) -> None:
    payload = {
        "run_key": run_key,
        "result": result,
    }
    cache_file.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def idempotent(run_key_fn: Callable, cache_dir: Optional[Path] = None, enabled: bool = True) -> Callable:
    """
    Decorator to make a function idempotent based on a run key
    
    Args:
        run_key_fn: Function that generates a unique key from kwargs
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        mem_cache: Dict[str, Any] = {}
        resolved_cache_dir = cache_dir or _default_cache_dir()
        resolved_cache_dir.mkdir(parents=True, exist_ok=True)

        @functools.wraps(func)
        def wrapper(**kwargs):
            if not enabled:
                return func(**kwargs)

            run_key = run_key_fn(**kwargs)
            if run_key in mem_cache:
                return mem_cache[run_key]

            cache_file = _cache_file_for_key(run_key, resolved_cache_dir)
            persisted = _load_cache(cache_file)
            if persisted is not None:
                mem_cache[run_key] = persisted
                return persisted

            result = func(**kwargs)
            mem_cache[run_key] = result
            _save_cache(cache_file, run_key, result)
            return result

        return wrapper

    return decorator


def compute_file_hash(file_path: Path) -> str:
    """
    Compute SHA256 hash of a file
    
    Args:
        file_path: Path to file
        
    Returns:
        Hexadecimal hash string
    """
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()
