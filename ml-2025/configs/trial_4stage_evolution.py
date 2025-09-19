"""
Configuration for 4-stage Butcher table with evolution learning and constraint rewards.
"""

from dataclasses import dataclass

@dataclass
class Trial4StageEvolutionConfig:
    """Configuration for 4-stage evolution-focused training with constraint rewards."""
    
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
    T_END: float = 1.0
    REFERENCE_TOL: float = 1e-10
    TEST_TOL: float = 1e-6
    
    # ML model parameters
    GENERATOR_HIDDEN_SIZE: int = 256
    SURROGATE_HIDDEN_SIZE: int = 128
    LEARNING_RATE: float = 1e-3
    BATCH_SIZE_ML: int = 32
    
    # Training parameters
    N_EPOCHS: int = 100
    N_CANDIDATES_PER_BATCH: int = 50
    EVALUATION_FREQUENCY: int = 20
    
    # Paths
    DATA_DIR: str = "data"
    RESULTS_DIR: str = "trials/trial_4stage_evolution"
    TRIALS_DIR: str = "trials/trial_4stage_evolution"
    LOGS_DIR: str = "logs"
    CHECKPOINTS_DIR: str = "trials/trial_4stage_evolution/checkpoints"
    
    # Database
    DB_PATH: str = "results/integrator_results.db"
    
    # Metrics weights for composite score
    ACCURACY_WEIGHT: float = 0.7
    EFFICIENCY_WEIGHT: float = 0.2
    STABILITY_WEIGHT: float = 0.1
    
    # Enhanced features
    USE_VARIED_STEPS: bool = True
    C_MATRIX_CONSTRAINED: bool = True
    COMPLEXITY_LEVEL: int = 2
    
    # Evolution-specific parameters
    USE_EVOLUTION: bool = True
    EVOLUTION_POPULATION_SIZE: int = 50
    EVOLUTION_MUTATION_RATE: float = 0.1
    EVOLUTION_CROSSOVER_RATE: float = 0.8
    EVOLUTION_ELITE_SIZE: int = 10
    
    # Constraint reward parameters
    C_MATRIX_REWARD_WEIGHT: float = 0.15  # 15% bonus for C matrix [0,1] constraint
    B_MATRIX_SUM_REWARD_WEIGHT: float = 0.10  # 10% bonus for B matrix sum=1 constraint
    CONSTRAINT_TOLERANCE: float = 1e-6  # Tolerance for constraint satisfaction

# Global config instance
trial_4stage_evolution_config = Trial4StageEvolutionConfig()
