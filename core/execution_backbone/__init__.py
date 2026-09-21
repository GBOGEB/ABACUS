"""Canonical bounded task-execution runtime.

The KEB acronym is reserved for Knowledge Exchange Bridge. Runtime scheduling
uses :class:`ExecutionBackbone`.
"""

from .backbone import ExecutionBackbone

__all__ = ["ExecutionBackbone"]
