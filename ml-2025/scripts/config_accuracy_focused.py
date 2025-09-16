"""
Configuration settings for accuracy-focused training run.
"""

import os
from dataclasses import dataclass
from typing import List, Tuple

@dataclass
class Config:
    """Configuration class for accuracy-focused training."""
    
    # Dataset parameters (focused on accuracy - more diverse ODEs)
    N_ODES: int = 1500  # Larger dataset for better accuracy training
    BATCH_SIZE: int = 30  # Larger batches for stability
    N_STIFF_ODES: int = 600  # 40% stiff equations (more challenging)
    N_NONSTIFF_ODES: int = 900  # 60% non-stiff equations
    
    # Butcher table parameters
    MIN_STAGES: int = 4
    MAX_STAGES: int = 7  # Allow higher stage methods for accuracy
    DEFAULT_STAGES: int = 5  # Default to 5 stages for better accuracy
    
    # Integration parameters (focused on accuracy)
    T_START: float = 0.0
    T_END: float = 0.2  # Longer integration time for accuracy testing
    REFERENCE_TOL: float = 1e-12  # Higher precision reference
    TEST_TOL: float = 1e-6  # Stricter tolerance for accuracy
    
    # ML model parameters (larger models for accuracy)
    GENERATOR_HIDDEN_SIZE: int = 512  # Larger generator
    SURROGATE_HIDDEN_SIZE: int = 256  # Larger surrogate
    LEARNING_RATE: float = 5e-4  # Lower learning rate for stability
    BATCH_SIZE_ML: int = 64  # Larger ML batches
    
    # Training parameters (accuracy-focused)
    N_EPOCHS: int = 500  # Longer training for accuracy
    N_CANDIDATES_PER_BATCH: int = 20  # More candidates
    EVALUATION_FREQUENCY: int = 15  # More frequent evaluation
    
    # Paths
    DATA_DIR: str = "data"
    RESULTS_DIR: str = "experiments/run_3_accuracy_focused"
    CHECKPOINTS_DIR: str = "experiments/run_3_accuracy_focused/checkpoints"
    LOGS_DIR: str = "experiments/run_3_accuracy_focused/logs"
    
    # Database
    DB_PATH: str = "experiments/run_3_accuracy_focused/integrator_results.db"
    
    # Metrics weights for composite score (Accuracy-focused)
    ACCURACY_WEIGHT: float = 0.70  # Heavy emphasis on accuracy
    EFFICIENCY_WEIGHT: float = 0.20  # Less emphasis on efficiency
    STABILITY_WEIGHT: float = 0.10  # Some emphasis on stability
    
    # Diversity constraints to prevent convergence to same solution
    DIVERSITY_PENALTY: float = 0.1  # Penalty for similarity to previous solutions
    MIN_STABILITY_RADIUS: float = 1.5  # Minimum stability radius constraint
    MAX_STABILITY_RADIUS: float = 3.0  # Maximum stability radius constraint
    
    def __post_init__(self):
        """Create necessary directories."""
        for directory in [self.DATA_DIR, self.RESULTS_DIR, self.CHECKPOINTS_DIR, self.LOGS_DIR]:
            os.makedirs(directory, exist_ok=True)

# Global config instance
config = Config()
