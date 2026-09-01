"""
Idempotency Module - Stub Implementation
Provides hashing and idempotent execution support
"""

import json
import hashlib
import functools
from pathlib import Path
from typing import Any, Callable, Dict


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


def idempotent(run_key_fn: Callable, cache_dir: Any = None) -> Callable:
    """
    Decorator to make a function idempotent based on a run key.

    Args:
        run_key_fn: Function that generates a unique key from kwargs.
        cache_dir: Optional directory for persistent JSON-file caching.
                   When provided, results survive across process restarts.

    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        in_memory_cache: Dict[str, Any] = {}

        @functools.wraps(func)
        def wrapper(**kwargs):
            run_key = run_key_fn(**kwargs)
            safe_key = hashlib.sha256(run_key.encode()).hexdigest()

            # Check in-memory cache first
            if run_key in in_memory_cache:
                return in_memory_cache[run_key]

            # Check persistent cache when cache_dir is given
            if cache_dir is not None:
                cache_path = Path(cache_dir) / f"{safe_key}.json"
                if cache_path.exists():
                    with open(cache_path, "r", encoding="utf-8") as fh:
                        result = json.load(fh)
                    in_memory_cache[run_key] = result
                    return result

            result = func(**kwargs)
            in_memory_cache[run_key] = result

            # Persist to disk when cache_dir is given
            if cache_dir is not None:
                Path(cache_dir).mkdir(parents=True, exist_ok=True)
                with open(Path(cache_dir) / f"{safe_key}.json", "w", encoding="utf-8") as fh:
                    json.dump(result, fh)

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
