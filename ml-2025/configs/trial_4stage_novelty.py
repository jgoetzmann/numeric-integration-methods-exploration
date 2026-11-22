"""
Configuration for 4-stage Butcher table with novelty search and constraint rewards.
"""

from dataclasses import dataclass

@dataclass
class Trial4StageNoveltyConfig:
    """Configuration for 4-stage novelty search training with constraint rewards."""
    
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
    N_CANDIDATES_PER_BATCH: int = 75  # Moderate candidates for balanced exploration
    EVALUATION_FREQUENCY: int = 20
    
    # Paths
    DATA_DIR: str = "data"
    RESULTS_DIR: str = "trials/trial_4stage_novelty"
    TRIALS_DIR: str = "trials/trial_4stage_novelty"
    LOGS_DIR: str = "logs"
    CHECKPOINTS_DIR: str = "trials/trial_4stage_novelty/checkpoints"
    
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
    EVOLUTION_POPULATION_SIZE: int = 75
    EVOLUTION_MUTATION_RATE: float = 0.15  # Moderate mutation
    EVOLUTION_CROSSOVER_RATE: float = 0.75  # Higher crossover for exploitation
    EVOLUTION_ELITE_SIZE: int = 8
    
    # Constraint reward parameters (reduced from original)
    C_MATRIX_REWARD_WEIGHT: float = 0.08  # Reduced from 0.15 to 8%
    B_MATRIX_SUM_REWARD_WEIGHT: float = 0.05  # Reduced from 0.10 to 5%
    CONSTRAINT_TOLERANCE: float = 1e-6
    
    # Novelty search parameters
    NOVELTY_REWARD_WEIGHT: float = 0.03  # 3% reward for novelty
    NOVELTY_TOLERANCE: float = 0.1  # Tolerance for coefficient similarity
    BASELINE_PENALTY_WEIGHT: float = 0.02  # 2% penalty for being too similar to baselines
    NOVELTY_THRESHOLD: float = 0.2  # Minimum difference to be considered novel

# Global config instance
trial_4stage_novelty_config = Trial4StageNoveltyConfig()
