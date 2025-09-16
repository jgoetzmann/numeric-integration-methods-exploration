"""
Accuracy-focused configuration for training.
"""

from .base import Config

class AccuracyFocusedConfig(Config):
    """Configuration optimized for accuracy."""
    
    # Override metrics weights for accuracy focus
    ACCURACY_WEIGHT: float = 0.7
    EFFICIENCY_WEIGHT: float = 0.2
    STABILITY_WEIGHT: float = 0.1
    
    # Training parameters optimized for accuracy
    N_EPOCHS: int = 500
    N_CANDIDATES_PER_BATCH: int = 20
    EVALUATION_FREQUENCY: int = 15
    
    # Integration parameters for higher precision
    REFERENCE_TOL: float = 1e-10
    TEST_TOL: float = 1e-6
    
    # Results directory
    RESULTS_DIR: str = "results/accuracy_focused"
