"""Deprecated runtime compatibility module.

KEB is reserved for Knowledge Exchange Bridge. The former runtime meaning has
moved to :mod:`core.execution_backbone`.
"""

from core.execution_backbone import ExecutionBackbone

LegacyExecutionBackbone = ExecutionBackbone

__all__ = ["ExecutionBackbone", "LegacyExecutionBackbone"]
