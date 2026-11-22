"""
Enhanced configuration with varied complexity levels.
"""

from .base import Config

class EnhancedConfig(Config):
    """Configuration with enhanced features and varied complexity."""
    
    # Override metrics weights for balanced focus
    ACCURACY_WEIGHT: float = 0.4
    EFFICIENCY_WEIGHT: float = 0.4
    STABILITY_WEIGHT: float = 0.2
    
    # Training parameters optimized for enhanced evaluation
    N_EPOCHS: int = 200
    N_CANDIDATES_PER_BATCH: int = 12
    EVALUATION_FREQUENCY: int = 15
    
    # Integration parameters for robust testing
    REFERENCE_TOL: float = 1e-8
    TEST_TOL: float = 1e-4
    
    # Enhanced dataset parameters
    N_ODES: int = 800
    N_STIFF_ODES: int = 240  # 30% stiff
    N_NONSTIFF_ODES: int = 560  # 70% non-stiff
    
    # Results directory
    RESULTS_DIR: str = "results/enhanced"
    TRIALS_DIR: str = "trials/enhanced"
    
    # Enhanced features
    USE_VARIED_STEPS: bool = True
    C_MATRIX_CONSTRAINED: bool = True
    COMPLEXITY_LEVEL: int = 2

# Global enhanced config instance
enhanced_config = EnhancedConfig()
