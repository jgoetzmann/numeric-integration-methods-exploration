import os
from dataclasses import dataclass

@dataclass
class Config:
    """Configuration for alternative 6-stage butcher table generation."""
    
    # Dataset parameters (medium size)
    N_ODES: int = 700
    BATCH_SIZE: int = 18
    N_STIFF_ODES: int = 250
    N_NONSTIFF_ODES: int = 450
    
    # Butcher table parameters (force 6-stage but different from diversity-focused)
    MIN_STAGES: int = 6
    MAX_STAGES: int = 6
    DEFAULT_STAGES: int = 6
    
    # Integration parameters (different from diversity-focused)
    T_START: float = 0.0
    T_END: float = 0.08  # Different integration time
    REFERENCE_TOL: float = 1e-7  # Different tolerance
    TEST_TOL: float = 1e-3
    
    # ML model parameters (different architecture)
    GENERATOR_HIDDEN_SIZE: int = 320
    SURROGATE_HIDDEN_SIZE: int = 160
    LEARNING_RATE: float = 6e-4  # Different learning rate
    BATCH_SIZE_ML: int = 40
    
    # Training parameters (medium training)
    N_EPOCHS: int = 120
    N_CANDIDATES_PER_BATCH: int = 12
    EVALUATION_FREQUENCY: int = 12
    
    # Paths
    DATA_DIR: str = "data"
    RESULTS_DIR: str = "experiments/run_8_alternative_6stage"
    CHECKPOINTS_DIR: str = "experiments/run_8_alternative_6stage/checkpoints"
    LOGS_DIR: str = "experiments/run_8_alternative_6stage/logs"
    
    # Database
    DB_PATH: str = "experiments/run_8_alternative_6stage/integrator_results.db"
    
    # Metrics weights for composite score (efficiency-focused)
    ACCURACY_WEIGHT: float = 0.25
    EFFICIENCY_WEIGHT: float = 0.50
    STABILITY_WEIGHT: float = 0.25
    
    # Anti-convergence constraints
    DIVERSITY_PENALTY: float = 0.4  # Higher penalty for similarity
    FORBIDDEN_COEFFICIENTS: list = None  # Will be set to penalize diversity-focused coefficients
    COEFFICIENT_DIVERSITY_BONUS: float = 0.2  # Higher bonus for different patterns
    MIN_STABILITY_RADIUS: float = 2.5  # Different stability constraint
    MAX_STABILITY_RADIUS: float = 6.0  # Allow different stability range
    
    def __post_init__(self):
        """Create necessary directories and set forbidden coefficients."""
        for directory in [self.DATA_DIR, self.RESULTS_DIR, self.CHECKPOINTS_DIR, self.LOGS_DIR]:
            os.makedirs(directory, exist_ok=True)
        
        # Set forbidden coefficients from the diversity-focused solution
        # These are the key coefficients from the 6-stage diversity table
        self.FORBIDDEN_COEFFICIENTS = [
            -0.250919762305275,  # c[1] from diversity table
            0.9014286128198323,  # A[2,0] from diversity table
            0.4639878836228102,  # A[2,1] from diversity table
            0.1973169683940732,  # A[3,0] from diversity table
            -0.687962719115127,  # A[3,1] from diversity table
            -0.6880109593275947, # A[3,2] from diversity table
            1.3654164964426425,  # c[2] from diversity table
            -1.1786567100486485, # c[3] from diversity table
            -0.8838327756636011, # A[4,0] from diversity table
            0.7323522915498704,  # A[4,1] from diversity table
            0.2022300234864176,  # A[4,2] from diversity table
            0.416145155592091,   # A[4,3] from diversity table
            -0.9588310114083951, # A[5,0] from diversity table
            0.9398197043239886,  # A[5,1] from diversity table
            0.6648852816008435,  # A[5,2] from diversity table
            -0.5753217786434477, # A[5,3] from diversity table
            -0.6363500655857988, # A[5,4] from diversity table
            0.46689469496477787, # c[4] from diversity table
            -0.5657978697128094  # c[5] from diversity table
        ]

# Create config instance
config = Config()

