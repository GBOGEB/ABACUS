"""
DMAIC V3.3 - Idempotent Phase Wrapper with User Control
Provides @idempotent decorator for phases with enable/disable option
Bridges to existing ranking, self-ranking, and validation systems
"""

import functools
import hashlib
import json
from pathlib import Path
from typing import Any, Callable, Dict, Optional
from datetime import datetime


class IdempotencyConfig:
    """Configuration for idempotency behavior"""
    def __init__(self, enabled: bool = True, cache_dir: Path = None):
        self.enabled = enabled
        self.cache_dir = cache_dir or Path(".dmaic_cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
    def get_cache_file(self, phase_name: str, iteration: int) -> Path:
        return self.cache_dir / f"{phase_name}_iter{iteration}.cache.json"


class IdempotentPhaseWrapper:
    """
    Wrapper to make DMAIC phases idempotent with user control
    
    Usage:
        wrapper = IdempotentPhaseWrapper(enabled=True)
        @wrapper.idempotent(phase_name="phase1_define")
        def execute_phase1(iteration=1):
            # Phase logic here
            return results
    """
    
    def __init__(self, config: Optional[IdempotencyConfig] = None):
        self.config = config or IdempotencyConfig()
        
    def _compute_input_hash(self, *args, **kwargs) -> str:
        """Compute hash of input parameters"""
        input_data = {
            'args': str(args),
            'kwargs': str(sorted(kwargs.items()))
        }
        data_str = json.dumps(input_data, sort_keys=True)
        return hashlib.sha256(data_str.encode()).hexdigest()[:16]
    
    def _load_cache(self, cache_file: Path) -> Optional[Dict]:
        """Load cached results"""
        if not cache_file.exists():
            return None
        try:
            with open(cache_file, 'r') as f:
                return json.load(f)
        except Exception:
            return None
    
    def _save_cache(self, cache_file: Path, result: Any, input_hash: str):
        """Save results to cache"""
        cache_data = {
            'timestamp': datetime.now().isoformat(),
            'input_hash': input_hash,
            'result': result if isinstance(result, dict) else {'status': 'completed'}
        }
        with open(cache_file, 'w') as f:
            json.dump(cache_data, f, indent=2)
    
    def idempotent(self, phase_name: str):
        """
        Decorator to make phase execution idempotent
        
        Args:
            phase_name: Name of the phase (e.g., 'phase1_define')
        """
        def decorator(func: Callable):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                iteration = kwargs.get('iteration', 1)
                
                if not self.config.enabled:
                    print(f"[IDEMPOTENCY] Disabled - executing {phase_name}")
                    return func(*args, **kwargs)
                
                cache_file = self.config.get_cache_file(phase_name, iteration)
                input_hash = self._compute_input_hash(*args, **kwargs)
                
                cached = self._load_cache(cache_file)
                if cached and cached.get('input_hash') == input_hash:
                    print(f"[IDEMPOTENCY] [OK] Cache hit for {phase_name} iteration {iteration}")
                    print(f"[IDEMPOTENCY] Skipping execution - returning cached result")
                    return cached.get('result')
                
                print(f"[IDEMPOTENCY] Cache miss - executing {phase_name}")
                result = func(*args, **kwargs)
                
                self._save_cache(cache_file, result, input_hash)
                return result
                
            return wrapper
        return decorator


GLOBAL_IDEMPOTENCY = IdempotentPhaseWrapper()


def enable_idempotency(enabled: bool = True, cache_dir: Optional[Path] = None):
    """
    Enable or disable idempotency globally
    
    Args:
        enabled: True to enable, False to disable
        cache_dir: Custom cache directory (optional)
    """
    global GLOBAL_IDEMPOTENCY
    config = IdempotencyConfig(enabled=enabled, cache_dir=cache_dir)
    GLOBAL_IDEMPOTENCY = IdempotentPhaseWrapper(config)
    print(f"[IDEMPOTENCY] {'Enabled' if enabled else 'Disabled'} globally")


def clear_cache(phase_name: Optional[str] = None, iteration: Optional[int] = None):
    """
    Clear idempotency cache
    
    Args:
        phase_name: Specific phase to clear (or None for all)
        iteration: Specific iteration to clear (or None for all)
    """
    cache_dir = GLOBAL_IDEMPOTENCY.config.cache_dir
    
    if phase_name and iteration:
        cache_file = cache_dir / f"{phase_name}_iter{iteration}.cache.json"
        if cache_file.exists():
            cache_file.unlink()
            print(f"[IDEMPOTENCY] Cleared cache for {phase_name} iteration {iteration}")
    elif phase_name:
        for cache_file in cache_dir.glob(f"{phase_name}_iter*.cache.json"):
            cache_file.unlink()
        print(f"[IDEMPOTENCY] Cleared all caches for {phase_name}")
    else:
        for cache_file in cache_dir.glob("*.cache.json"):
            cache_file.unlink()
        print(f"[IDEMPOTENCY] Cleared all caches")
