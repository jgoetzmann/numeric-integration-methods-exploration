"""
Machine learning models for discovering novel integration methods.

This module contains:
- Neural network generators for creating Butcher tables
- Surrogate evaluators for fast performance prediction
- Evolutionary algorithms for optimization
- Model configuration and training utilities
"""

from .model import *

__all__ = [
    "MLPipeline",
    "ModelConfig",
    "ButcherTableGenerator",
    "SurrogateEvaluator"
]
