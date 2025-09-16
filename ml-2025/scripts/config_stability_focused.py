"""
Configuration settings for stability-focused training run.
"""

import os
from dataclasses import dataclass
from typing import List, Tuple

@dataclass
class Config:
    """Configuration class for stability-focused training."""
    
    # Dataset parameters (focused on stability - more stiff problems)
    N_ODES: int = 1200  # Moderate dataset size
    BATCH_SIZE: int = 20  # Smaller batches for stability
    N_STIFF_ODES: int = 800  # 67% stiff equations (stability focus)
    N_NONSTIFF_ODES: int = 400  # 33% non-stiff equations
    
    # Butcher table parameters
    MIN_STAGES: int = 3
    MAX_STAGES: int = 6
    DEFAULT_STAGES: int = 4  # Standard stages
    
    # Integration parameters (stability-focused)
    T_START: float = 0.0
    T_END: float = 0.15  # Moderate integration time
    REFERENCE_TOL: float = 1e-10  # High precision
    TEST_TOL: float = 1e-5  # Moderate tolerance
    
    # ML model parameters (stable training)
    GENERATOR_HIDDEN_SIZE: int = 384  # Moderate size
    SURROGATE_HIDDEN_SIZE: int = 192  # Moderate surrogate
    LEARNING_RATE: float = 8e-4  # Moderate learning rate
    BATCH_SIZE_ML: int = 48  # Moderate ML batches
    
    # Training parameters (stability-focused)
    N_EPOCHS: int = 350  # Moderate training length
    N_CANDIDATES_PER_BATCH: int = 12  # Fewer candidates for stability
    EVALUATION_FREQUENCY: int = 25  # Less frequent evaluation
    
    # Paths
    DATA_DIR: str = "data"
    RESULTS_DIR: str = "experiments/run_4_stability_focused"
    CHECKPOINTS_DIR: str = "experiments/run_4_stability_focused/checkpoints"
    LOGS_DIR: str = "experiments/run_4_stability_focused/logs"
    
    # Database
    DB_PATH: str = "experiments/run_4_stability_focused/integrator_results.db"
    
    # Metrics weights for composite score (Stability-focused)
    ACCURACY_WEIGHT: float = 0.30  # Moderate accuracy emphasis
    EFFICIENCY_WEIGHT: float = 0.20  # Moderate efficiency emphasis
    STABILITY_WEIGHT: float = 0.50  # Heavy emphasis on stability
    
    # Diversity constraints to prevent convergence to same solution
    DIVERSITY_PENALTY: float = 0.15  # Higher penalty for stability-focused
    MIN_STABILITY_RADIUS: float = 2.5  # Higher minimum stability radius
    MAX_STABILITY_RADIUS: float = 5.0  # Higher maximum stability radius
    
    def __post_init__(self):
        """Create necessary directories."""
        for directory in [self.DATA_DIR, self.RESULTS_DIR, self.CHECKPOINTS_DIR, self.LOGS_DIR]:
            os.makedirs(directory, exist_ok=True)

# Global config instance
config = Config()
