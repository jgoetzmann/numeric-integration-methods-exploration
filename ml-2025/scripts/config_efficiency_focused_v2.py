"""
Configuration settings for efficiency-focused training run (Version 2).
This is different from the original efficiency-focused run to ensure different results.
"""

import os
from dataclasses import dataclass
from typing import List, Tuple

@dataclass
class Config:
    """Configuration class for efficiency-focused training (V2)."""
    
    # Dataset parameters (different from original efficiency run)
    N_ODES: int = 1200  # Different size from original (1000)
    BATCH_SIZE: int = 30  # Different batch size from original (25)
    N_STIFF_ODES: int = 400  # Different ratio: 33% stiff vs 30% in original
    N_NONSTIFF_ODES: int = 800  # 67% non-stiff vs 70% in original
    
    # Butcher table parameters (different from original)
    MIN_STAGES: int = 3  # Different from original (4)
    MAX_STAGES: int = 5  # Different from original (6)
    DEFAULT_STAGES: int = 4  # Same as original but different range
    
    # Integration parameters (different from original)
    T_START: float = 0.0
    T_END: float = 0.12  # Different from original (0.1)
    REFERENCE_TOL: float = 1e-9  # Different from original (1e-8)
    TEST_TOL: float = 1e-5  # Different from original (1e-4)
    
    # ML model parameters (different from original)
    GENERATOR_HIDDEN_SIZE: int = 320  # Different from original (256)
    SURROGATE_HIDDEN_SIZE: int = 160  # Different from original (128)
    LEARNING_RATE: float = 8e-4  # Different from original (1e-3)
    BATCH_SIZE_ML: int = 40  # Different from original (32)
    
    # Training parameters (different from original)
    N_EPOCHS: int = 300  # Different from original (400)
    N_CANDIDATES_PER_BATCH: int = 18  # Different from original (15)
    EVALUATION_FREQUENCY: int = 25  # Different from original (20)
    
    # Paths
    DATA_DIR: str = "data"
    RESULTS_DIR: str = "experiments/run_2_efficiency_focused_v2"
    CHECKPOINTS_DIR: str = "experiments/run_2_efficiency_focused_v2/checkpoints"
    LOGS_DIR: str = "experiments/run_2_efficiency_focused_v2/logs"
    
    # Database
    DB_PATH: str = "experiments/run_2_efficiency_focused_v2/integrator_results.db"
    
    # Metrics weights for composite score (Efficiency-focused V2)
    ACCURACY_WEIGHT: float = 0.30  # Different from original (0.35)
    EFFICIENCY_WEIGHT: float = 0.60  # Different from original (0.55)
    STABILITY_WEIGHT: float = 0.10  # Same as original
    
    # Diversity constraints to prevent convergence to same solution
    DIVERSITY_PENALTY: float = 0.2  # Highest penalty for efficiency-focused
    MIN_STABILITY_RADIUS: float = 0.5  # Lower minimum stability radius
    MAX_STABILITY_RADIUS: float = 2.0  # Lower maximum stability radius
    
    def __post_init__(self):
        """Create necessary directories."""
        for directory in [self.DATA_DIR, self.RESULTS_DIR, self.CHECKPOINTS_DIR, self.LOGS_DIR]:
            os.makedirs(directory, exist_ok=True)

# Global config instance
config = Config()
