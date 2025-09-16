"""
Training pipeline for discovering novel integration methods.

This module contains:
- Complete optimization loop implementation
- Batch processing with ODE rotation
- Surrogate model training
- Checkpointing and progress tracking
"""

from .train import *

__all__ = [
    "TrainingPipeline",
    "main"
]
