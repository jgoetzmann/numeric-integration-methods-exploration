"""
Mixed-focus configuration for balanced training.
"""

from .base import Config

class MixedFocusConfig(Config):
    """Configuration with balanced focus on all metrics."""
    
    # Balanced metrics weights
    ACCURACY_WEIGHT: float = 0.4
    EFFICIENCY_WEIGHT: float = 0.4
    STABILITY_WEIGHT: float = 0.2
    
    # Balanced training parameters
    N_EPOCHS: int = 400
    N_CANDIDATES_PER_BATCH: int = 15
    EVALUATION_FREQUENCY: int = 20
    
    # Standard integration parameters
    T_END: float = 0.1
    REFERENCE_TOL: float = 1e-8
    TEST_TOL: float = 1e-4
    
    # Results directory
    RESULTS_DIR: str = "results/mixed_focus"
