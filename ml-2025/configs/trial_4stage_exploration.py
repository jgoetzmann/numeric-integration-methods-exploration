"""
Configuration for 4-stage Butcher table with maximum exploration and no constraint rewards.
"""

from dataclasses import dataclass

@dataclass
class Trial4StageExplorationConfig:
    """Configuration for 4-stage exploration-focused training with no constraint rewards."""
    
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
    N_CANDIDATES_PER_BATCH: int = 100  # More candidates for exploration
    EVALUATION_FREQUENCY: int = 20
    
    # Paths
    DATA_DIR: str = "data"
    RESULTS_DIR: str = "trials/trial_4stage_exploration"
    TRIALS_DIR: str = "trials/trial_4stage_exploration"
    LOGS_DIR: str = "logs"
    CHECKPOINTS_DIR: str = "trials/trial_4stage_exploration/checkpoints"
    
    # Database
    DB_PATH: str = "results/integrator_results.db"
    
    # Metrics weights for composite score - exploration focused
    ACCURACY_WEIGHT: float = 0.7
    EFFICIENCY_WEIGHT: float = 0.2
    STABILITY_WEIGHT: float = 0.1
    
    # Enhanced features
    USE_VARIED_STEPS: bool = True
    C_MATRIX_CONSTRAINED: bool = False  # No constraints for exploration
    COMPLEXITY_LEVEL: int = 2
    
    # Evolution-specific parameters
    USE_EVOLUTION: bool = True
    EVOLUTION_POPULATION_SIZE: int = 100  # Larger population for diversity
    EVOLUTION_MUTATION_RATE: float = 0.3  # Higher mutation for exploration
    EVOLUTION_CROSSOVER_RATE: float = 0.6  # Lower crossover to preserve diversity
    EVOLUTION_ELITE_SIZE: int = 5  # Smaller elite to allow more exploration
    
    # Exploration parameters
    EXPLORATION_BONUS: float = 0.05  # Small bonus for novel coefficient patterns
    SUCCESS_THRESHOLD: float = 0.05  # Very low threshold (5%) for maximum exploration
    DIVERSITY_REWARD: float = 0.02  # Small reward for coefficient diversity
    
    # No constraint rewards for pure exploration
    C_MATRIX_REWARD_WEIGHT: float = 0.0  # No C matrix constraint reward
    B_MATRIX_SUM_REWARD_WEIGHT: float = 0.0  # No B matrix sum constraint reward
    CONSTRAINT_TOLERANCE: float = 1e-6

# Global config instance
trial_4stage_exploration_config = Trial4StageExplorationConfig()
