"""
DMAIC Handover Module - Stub Implementation
Provides compatibility layer for handover_bridge functionality
"""

__version__ = "1.0.0"

from . import config, idempotency, metrics, provenance, recursion

__all__ = ["idempotency", "provenance", "metrics", "recursion", "config"]
