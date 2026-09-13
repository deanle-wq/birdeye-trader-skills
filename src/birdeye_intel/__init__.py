"""Birdeye-only, read-only Solana trader intelligence."""

from .analysis import (
    analyze_copyability,
    analyze_early_participants,
    analyze_exit_trace,
    analyze_holder_composition,
    analyze_quick_screen,
)
from .client import BirdeyeClient

__all__ = [
    "BirdeyeClient",
    "analyze_copyability",
    "analyze_early_participants",
    "analyze_exit_trace",
    "analyze_holder_composition",
    "analyze_quick_screen",
]

__version__ = "0.1.0rc1"
