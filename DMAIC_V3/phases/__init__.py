"""
DMAIC V3.0 - Phases Package
Modular phase implementations for the DMAIC engine
"""

__version__ = "3.0.0"

from .phase0_setup import Phase0Setup

__all__ = [
    "Phase0Setup",
]
