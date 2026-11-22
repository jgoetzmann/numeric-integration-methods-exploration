"""
Configuration for 4-stage Butcher table with 20% accuracy, 80% efficiency focus.
"""

from dataclasses import dataclass

@dataclass
class Trial4StageEfficiencyConfig:
    """Configuration for 4-stage efficiency-focused training."""
    
    # Dataset parameters
    N_ODES: int = 1000
    BATCH_SIZE: int = 100
    N_STIFF_ODES: int = 300
    N_NONSTIFF_ODES: int = 700
    
    # Butcher table parameters
    MIN_STAGES: int = 4
    MAX_STAGES: int = 4
    DEFAULT_STAGES: int = 4
    
    # Integration parameters
    T_START: float = 0.0
    T_END: float = 0.5
    REFERENCE_TOL: float = 1e-6
    TEST_TOL: float = 1e-3
    
    # ML model parameters
    GENERATOR_HIDDEN_SIZE: int = 256
    SURROGATE_HIDDEN_SIZE: int = 128
    LEARNING_RATE: float = 1e-3
    BATCH_SIZE_ML: int = 32
    
    # Training parameters
    N_EPOCHS: int = 100
    N_CANDIDATES_PER_BATCH: int = 15
    EVALUATION_FREQUENCY: int = 20
    
    # Paths
    DATA_DIR: str = "data"
    RESULTS_DIR: str = "trials/trial_4stage_efficiency"
    TRIALS_DIR: str = "trials/trial_4stage_efficiency"
    LOGS_DIR: str = "logs"
    CHECKPOINTS_DIR: str = "trials/trial_4stage_efficiency/checkpoints"
    
    # Database
    DB_PATH: str = "results/integrator_results.db"
    
    # Metrics weights for composite score
    ACCURACY_WEIGHT: float = 0.2
    EFFICIENCY_WEIGHT: float = 0.8
    STABILITY_WEIGHT: float = 0.0
    
    # Enhanced features
    USE_VARIED_STEPS: bool = True
    C_MATRIX_CONSTRAINED: bool = True
    COMPLEXITY_LEVEL: int = 2

# Global config instance
trial_4stage_efficiency_config = Trial4StageEfficiencyConfig()