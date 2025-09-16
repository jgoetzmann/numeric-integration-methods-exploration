"""
Configuration settings for mixed-focus training run.
"""

import os
from dataclasses import dataclass
from typing import List, Tuple

@dataclass
class Config:
    """Configuration class for mixed-focus training."""
    
    # Dataset parameters (balanced approach)
    N_ODES: int = 2000  # Largest dataset for comprehensive training
    BATCH_SIZE: int = 40  # Large batches
    N_STIFF_ODES: int = 1000  # 50% stiff equations (balanced)
    N_NONSTIFF_ODES: int = 1000  # 50% non-stiff equations
    
    # Butcher table parameters
    MIN_STAGES: int = 3
    MAX_STAGES: int = 8  # Allow wide range of stages
    DEFAULT_STAGES: int = 5  # Higher default for better performance
    
    # Integration parameters (balanced)
    T_START: float = 0.0
    T_END: float = 0.25  # Longer integration time
    REFERENCE_TOL: float = 1e-11  # High precision
    TEST_TOL: float = 1e-5  # Moderate tolerance
    
    # ML model parameters (large models)
    GENERATOR_HIDDEN_SIZE: int = 640  # Large generator
    SURROGATE_HIDDEN_SIZE: int = 320  # Large surrogate
    LEARNING_RATE: float = 3e-4  # Lower learning rate
    BATCH_SIZE_ML: int = 80  # Large ML batches
    
    # Training parameters (comprehensive)
    N_EPOCHS: int = 600  # Longest training
    N_CANDIDATES_PER_BATCH: int = 25  # Most candidates
    EVALUATION_FREQUENCY: int = 10  # Most frequent evaluation
    
    # Paths
    DATA_DIR: str = "data"
    RESULTS_DIR: str = "experiments/run_5_mixed_focus"
    CHECKPOINTS_DIR: str = "experiments/run_5_mixed_focus/checkpoints"
    LOGS_DIR: str = "experiments/run_5_mixed_focus/logs"
    
    # Database
    DB_PATH: str = "experiments/run_5_mixed_focus/integrator_results.db"
    
    # Metrics weights for composite score (Balanced)
    ACCURACY_WEIGHT: float = 0.45  # Balanced accuracy emphasis
    EFFICIENCY_WEIGHT: float = 0.35  # Balanced efficiency emphasis
    STABILITY_WEIGHT: float = 0.20  # Balanced stability emphasis
    
    def __post_init__(self):
        """Create necessary directories."""
        for directory in [self.DATA_DIR, self.RESULTS_DIR, self.CHECKPOINTS_DIR, self.LOGS_DIR]:
            os.makedirs(directory, exist_ok=True)

# Global config instance
config = Config()
