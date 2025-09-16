"""
Efficiency-focused configuration for training.
"""

from .base import Config

class EfficiencyFocusedConfig(Config):
    """Configuration optimized for efficiency."""
    
    # Override metrics weights for efficiency focus
    ACCURACY_WEIGHT: float = 0.3
    EFFICIENCY_WEIGHT: float = 0.6
    STABILITY_WEIGHT: float = 0.1
    
    # Training parameters optimized for speed
    N_EPOCHS: int = 300
    N_CANDIDATES_PER_BATCH: int = 10
    EVALUATION_FREQUENCY: int = 25
    
    # Integration parameters for speed
    T_END: float = 0.05  # Shorter integration time
    REFERENCE_TOL: float = 1e-6
    TEST_TOL: float = 1e-3
    
    # Results directory
    RESULTS_DIR: str = "results/efficiency_focused"
