"""
Base configuration class for the Novel Numerical Integration Methods project.
"""

import os
from dataclasses import dataclass
from typing import List, Tuple

@dataclass
class Config:
    """Main configuration class for the project."""
    
    # Dataset parameters
    N_ODES: int = 1000
    BATCH_SIZE: int = 100  # Increased for better CPU utilization
    N_STIFF_ODES: int = 300
    N_NONSTIFF_ODES: int = 700
    
    # Butcher table parameters
    MIN_STAGES: int = 4
    MAX_STAGES: int = 6
    DEFAULT_STAGES: int = 4
    
    # Integration parameters
    T_START: float = 0.0
    T_END: float = 0.1
    REFERENCE_TOL: float = 1e-8
    TEST_TOL: float = 1e-4
    
    # ML model parameters
    GENERATOR_HIDDEN_SIZE: int = 256
    SURROGATE_HIDDEN_SIZE: int = 128
    LEARNING_RATE: float = 1e-3
    BATCH_SIZE_ML: int = 32
    
    # Training parameters
    N_EPOCHS: int = 400
    N_CANDIDATES_PER_BATCH: int = 50  # Increased for better parallelization
    EVALUATION_FREQUENCY: int = 20
    
    # Paths
    DATA_DIR: str = "data"
    RESULTS_DIR: str = "results"
    TRIALS_DIR: str = "trials"
    LOGS_DIR: str = "logs"
    
    # Database
    DB_PATH: str = "results/integrator_results.db"
    
    # Metrics weights for composite score
    ACCURACY_WEIGHT: float = 0.4
    EFFICIENCY_WEIGHT: float = 0.4
    STABILITY_WEIGHT: float = 0.2
    
    def __post_init__(self):
        """Create necessary directories."""
        for directory in [self.DATA_DIR, self.RESULTS_DIR, self.TRIALS_DIR, self.LOGS_DIR]:
            os.makedirs(directory, exist_ok=True)

# Global config instance
config = Config()