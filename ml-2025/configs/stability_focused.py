"""
Stability-focused configuration for training.
"""

from .base import Config

class StabilityFocusedConfig(Config):
    """Configuration optimized for stability."""
    
    # Override metrics weights for stability focus
    ACCURACY_WEIGHT: float = 0.2
    EFFICIENCY_WEIGHT: float = 0.3
    STABILITY_WEIGHT: float = 0.5
    
    # Training parameters optimized for stability
    N_EPOCHS: int = 600
    N_CANDIDATES_PER_BATCH: int = 25
    EVALUATION_FREQUENCY: int = 10
    
    # Integration parameters for stability testing
    T_END: float = 0.2  # Longer integration time
    REFERENCE_TOL: float = 1e-9
    TEST_TOL: float = 1e-5
    
    # Results directory
    RESULTS_DIR: str = "results/stability_focused"
