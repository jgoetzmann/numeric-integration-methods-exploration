"""
Diversity-focused configuration to find DIFFERENT butcher tables.
This configuration actively prevents convergence to the known optimal solution.
"""

import os
from dataclasses import dataclass

@dataclass
class Config:
    # Dataset parameters (smaller for faster training)
    N_ODES: int = 800  # Smaller dataset for faster training
    BATCH_SIZE: int = 20  # Smaller batches
    N_STIFF_ODES: int = 300  # 37.5% stiff equations
    N_NONSTIFF_ODES: int = 500  # 62.5% non-stiff equations
    
    # Butcher table parameters (force different stage counts)
    MIN_STAGES: int = 6  # Force 6-stage count (different from optimal 4)
    MAX_STAGES: int = 6  # Fixed at 6 stages to avoid tensor size issues
    DEFAULT_STAGES: int = 6  # Default to 6 stages (different from optimal 4)
    
    # Integration parameters (different from optimal)
    T_START: float = 0.0
    T_END: float = 0.05  # Much shorter integration time
    REFERENCE_TOL: float = 1e-6  # Lower precision reference
    TEST_TOL: float = 1e-3  # Much more relaxed tolerance
    
    # ML model parameters (smaller models for faster training)
    GENERATOR_HIDDEN_SIZE: int = 256
    SURROGATE_HIDDEN_SIZE: int = 128
    LEARNING_RATE: float = 0.001  # Higher learning rate for more exploration
    BATCH_SIZE_ML: int = 32
    
    # Training parameters (shorter training with more exploration)
    N_EPOCHS: int = 100  # Shorter training
    N_CANDIDATES_PER_BATCH: int = 10  # Fewer candidates per batch
    EVALUATION_FREQUENCY: int = 10  # More frequent evaluation
    
    # Paths
    DATA_DIR: str = "data"
    RESULTS_DIR: str = "experiments/run_6_diversity_focused"
    CHECKPOINTS_DIR: str = "experiments/run_6_diversity_focused/checkpoints"
    LOGS_DIR: str = "experiments/run_6_diversity_focused/logs"
    
    # Database
    DB_PATH: str = "experiments/run_6_diversity_focused/integrator_results.db"
    
    # Metrics weights for composite score (Diversity-focused - different balance)
    ACCURACY_WEIGHT: float = 0.1  # Minimal accuracy emphasis
    EFFICIENCY_WEIGHT: float = 0.1  # Minimal efficiency emphasis  
    STABILITY_WEIGHT: float = 0.8  # Heavy emphasis on stability (different from optimal)
    
    # Diversity constraints to prevent convergence to known optimal solution
    DIVERSITY_PENALTY: float = 0.5  # Very high penalty for similarity
    MIN_STABILITY_RADIUS: float = 3.0  # Force higher stability than optimal (~2.0)
    MAX_STABILITY_RADIUS: float = 8.0  # Allow very high stability
    
    # Anti-convergence constraints
    FORBIDDEN_STAGES: int = 4  # Penalize 4-stage methods (the optimal solution)
    STAGE_DIVERSITY_BONUS: float = 0.2  # Bonus for non-4-stage methods
    
    def __post_init__(self):
        """Create necessary directories."""
        for directory in [self.DATA_DIR, self.RESULTS_DIR, self.CHECKPOINTS_DIR, self.LOGS_DIR]:
            os.makedirs(directory, exist_ok=True)

# Create config instance
config = Config()
