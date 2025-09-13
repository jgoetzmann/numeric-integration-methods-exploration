"""
Configuration settings for the Novel Numerical Integration Methods project.
"""

import os
from dataclasses import dataclass
from typing import List, Tuple

@dataclass
class Config:
    """Main configuration class for the project."""
    
    # Dataset parameters (optimized for speed)
    N_ODES: int = 500  # Further reduced for faster training
    BATCH_SIZE: int = 20  # Much smaller batches for faster evaluation
    N_STIFF_ODES: int = 150  # 30% stiff equations
    N_NONSTIFF_ODES: int = 350  # 70% non-stiff equations
    
    # Butcher table parameters
    MIN_STAGES: int = 4
    MAX_STAGES: int = 6
    DEFAULT_STAGES: int = 4
    
    # Integration parameters (optimized for maximum speed)
    T_START: float = 0.0
    T_END: float = 0.1  # Very short integration time for speed
    REFERENCE_TOL: float = 1e-8  # Further relaxed tolerance
    TEST_TOL: float = 1e-4  # Much more relaxed tolerance
    
    # ML model parameters
    GENERATOR_HIDDEN_SIZE: int = 256
    SURROGATE_HIDDEN_SIZE: int = 128
    LEARNING_RATE: float = 1e-3
    BATCH_SIZE_ML: int = 32
    
    # Training parameters (optimized for maximum speed)
    N_EPOCHS: int = 20  # Much fewer epochs for quick testing
    N_CANDIDATES_PER_BATCH: int = 10  # Very few candidates per batch
    EVALUATION_FREQUENCY: int = 10  # Less frequent full evaluation
    
    # Paths
    DATA_DIR: str = "data"
    RESULTS_DIR: str = "results"
    CHECKPOINTS_DIR: str = "checkpoints"
    LOGS_DIR: str = "logs"
    
    # Database
    DB_PATH: str = "results/integrator_results.db"
    
    # Metrics weights for composite score (Efficiency-focused)
    ACCURACY_WEIGHT: float = 0.35
    EFFICIENCY_WEIGHT: float = 0.55
    STABILITY_WEIGHT: float = 0.10
    
    def __post_init__(self):
        """Create necessary directories."""
        for directory in [self.DATA_DIR, self.RESULTS_DIR, self.CHECKPOINTS_DIR, self.LOGS_DIR]:
            os.makedirs(directory, exist_ok=True)

# Global config instance
config = Config()
