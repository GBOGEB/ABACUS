"""
DMAIC V3.0 - Core Package
Core utilities and modules for the DMAIC engine
"""

__version__ = "3.0.0"
__author__ = "DMAIC Team"

from .state import StateManager, PhaseStatus, PhaseState, IterationState

__all__ = [
    "StateManager",
    "PhaseStatus",
    "PhaseState",
    "IterationState",
]
