"""
Configuration management for the Novel Numerical Integration Methods project.

This module provides a unified configuration system that allows easy switching
between different training objectives and experimental setups.
"""

from .base import Config, config
from .accuracy_focused import AccuracyFocusedConfig
from .efficiency_focused import EfficiencyFocusedConfig  
from .stability_focused import StabilityFocusedConfig
from .mixed_focus import MixedFocusConfig

__all__ = [
    "Config",
    "config",
    "AccuracyFocusedConfig",
    "EfficiencyFocusedConfig", 
    "StabilityFocusedConfig",
    "MixedFocusConfig"
]
