import os
from dataclasses import dataclass

@dataclass
class Config:
    """Configuration for alternative 4-stage butcher table generation."""
    
    # Dataset parameters (smaller for faster training)
    N_ODES: int = 600
    BATCH_SIZE: int = 15
    N_STIFF_ODES: int = 200
    N_NONSTIFF_ODES: int = 400
    
    # Butcher table parameters (force 4-stage but different from optimal)
    MIN_STAGES: int = 4
    MAX_STAGES: int = 4
    DEFAULT_STAGES: int = 4
    
    # Integration parameters (different from optimal)
    T_START: float = 0.0
    T_END: float = 0.1  # Different integration time
    REFERENCE_TOL: float = 1e-8  # Different tolerance
    TEST_TOL: float = 1e-4
    
    # ML model parameters (different architecture)
    GENERATOR_HIDDEN_SIZE: int = 384
    SURROGATE_HIDDEN_SIZE: int = 192
    LEARNING_RATE: float = 8e-4  # Different learning rate
    BATCH_SIZE_ML: int = 48
    
    # Training parameters (shorter training)
    N_EPOCHS: int = 150
    N_CANDIDATES_PER_BATCH: int = 8
    EVALUATION_FREQUENCY: int = 15
    
    # Paths
    DATA_DIR: str = "data"
    RESULTS_DIR: str = "experiments/run_7_alternative_4stage"
    CHECKPOINTS_DIR: str = "experiments/run_7_alternative_4stage/checkpoints"
    LOGS_DIR: str = "experiments/run_7_alternative_4stage/logs"
    
    # Database
    DB_PATH: str = "experiments/run_7_alternative_4stage/integrator_results.db"
    
    # Metrics weights for composite score (balanced but different)
    ACCURACY_WEIGHT: float = 0.40
    EFFICIENCY_WEIGHT: float = 0.35
    STABILITY_WEIGHT: float = 0.25
    
    # Anti-convergence constraints
    DIVERSITY_PENALTY: float = 0.3  # Penalty for similarity to known optimal
    FORBIDDEN_COEFFICIENTS: list = None  # Will be set to penalize optimal coefficients
    COEFFICIENT_DIVERSITY_BONUS: float = 0.15  # Bonus for different coefficient patterns
    MIN_STABILITY_RADIUS: float = 1.0  # Different stability constraint
    MAX_STABILITY_RADIUS: float = 4.0  # Allow higher stability
    
    def __post_init__(self):
        """Create necessary directories and set forbidden coefficients."""
        for directory in [self.DATA_DIR, self.RESULTS_DIR, self.CHECKPOINTS_DIR, self.LOGS_DIR]:
            os.makedirs(directory, exist_ok=True)
        
        # Set forbidden coefficients from the optimal solution
        self.FORBIDDEN_COEFFICIENTS = [
            -0.250919762305275,  # c[1] from optimal
            0.9014286128198323,  # A[2,0] from optimal
            0.4639878836228102,  # A[2,1] from optimal
            0.1973169683940732,  # A[3,0] from optimal
            -0.687962719115127,  # A[3,1] from optimal
            -0.6880109593275947, # A[3,2] from optimal
            1.3654164964426425,  # c[2] from optimal
            -1.1786567100486485  # c[3] from optimal
        ]

# Create config instance
config = Config()

