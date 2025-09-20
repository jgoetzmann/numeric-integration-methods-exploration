"""
Configuration for 4-stage Butcher table with enhanced novelty search and two-phase training.

This configuration addresses the issues from trial_4stage_novelty by:
1. Significantly increasing novelty reward weight (30%)
2. Implementing two-phase training: aggressive exploration -> optimization
3. Using diversity preservation in the first phase
4. Adjusting evolution parameters dynamically
"""

from dataclasses import dataclass

@dataclass
class Trial4StageNovelty2Config:
    """Configuration for enhanced 4-stage novelty search with two-phase training."""
    
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
    N_EPOCHS: int = 100  # Full training for overnight run
    N_CANDIDATES_PER_BATCH: int = 75  # Balanced for exploration and speed
    EVALUATION_FREQUENCY: int = 20
    
    # Two-phase training parameters
    PHASE_1_EPOCHS: int = 50  # First half: aggressive exploration
    PHASE_2_EPOCHS: int = 50  # Second half: optimization
    DIVERSITY_PRESERVATION_SIZE: int = 5  # Keep top 5 diverse solutions
    
    # Paths
    DATA_DIR: str = "data"
    RESULTS_DIR: str = "trials/trial_4stage_novelty_2"
    TRIALS_DIR: str = "trials/trial_4stage_novelty_2"
    LOGS_DIR: str = "logs"
    CHECKPOINTS_DIR: str = "trials/trial_4stage_novelty_2/checkpoints"
    
    # Database
    DB_PATH: str = "results/integrator_results.db"
    
    # Enhanced metrics weights for composite score
    # Total should be 1.3 (allowing novelty to boost beyond perfect performance)
    ACCURACY_WEIGHT: float = 0.7
    EFFICIENCY_WEIGHT: float = 0.2
    STABILITY_WEIGHT: float = 0.1
    NOVELTY_WEIGHT: float = 0.3  # Significantly increased from 0.03!
    
    # Enhanced features
    USE_VARIED_STEPS: bool = True
    C_MATRIX_CONSTRAINED: bool = True
    COMPLEXITY_LEVEL: int = 2
    
    # Evolution-specific parameters - Phase 1 (Exploration)
    USE_EVOLUTION: bool = True
    EVOLUTION_POPULATION_SIZE: int = 100  # Increased for diversity
    
    # Phase 1 parameters (aggressive exploration)
    PHASE1_MUTATION_RATE: float = 0.4  # Very high mutation for exploration
    PHASE1_CROSSOVER_RATE: float = 0.3  # Low crossover to maintain diversity
    PHASE1_ELITE_SIZE: int = 5  # Keep only top 5 diverse solutions
    
    # Phase 2 parameters (optimization)
    PHASE2_MUTATION_RATE: float = 0.1  # Lower mutation for fine-tuning
    PHASE2_CROSSOVER_RATE: float = 0.8  # High crossover for optimization
    PHASE2_ELITE_SIZE: int = 15  # More elites for convergence
    
    # Enhanced constraint reward parameters
    C_MATRIX_REWARD_WEIGHT: float = 0.1  # Part of 20% constraint rewards
    B_MATRIX_SUM_REWARD_WEIGHT: float = 0.1  # Part of 20% constraint rewards
    CONSTRAINT_TOLERANCE: float = 1e-6
    
    # Enhanced novelty search parameters
    NOVELTY_REWARD_WEIGHT: float = 0.3  # 30% reward for novelty!
    NOVELTY_TOLERANCE: float = 0.05  # Stricter tolerance (5% instead of 10%)
    BASELINE_PENALTY_WEIGHT: float = 0.1  # Higher penalty for similarity
    NOVELTY_THRESHOLD: float = 0.15  # Lower threshold for easier novelty
    
    # Diversity preservation parameters
    DIVERSITY_THRESHOLD: float = 0.2  # Minimum difference between preserved solutions
    MAX_SIMILARITY_TOLERANCE: float = 0.1  # Maximum allowed similarity in top-5
    
    # Phase switching parameters
    PHASE_SWITCH_EPOCH: int = 50  # Switch from exploration to optimization
    PERFORMANCE_THRESHOLD: float = 0.8  # Minimum performance to consider for phase 2
    
    # Enhanced exploration parameters
    EXPLORATION_BONUS_WEIGHT: float = 0.05  # Additional exploration reward
    COEFFICIENT_DIVERSITY_BONUS: float = 0.03  # Reward for diverse coefficients
    
    # Anti-convergence mechanisms
    ANTI_RK4_PENALTY: float = 0.2  # Explicit penalty for being too close to RK4
    KNOWN_METHOD_PENALTY: float = 0.15  # Penalty for being close to any known method
    
    # Adaptive parameters
    ADAPTIVE_MUTATION: bool = True  # Increase mutation if diversity drops
    MIN_POPULATION_DIVERSITY: float = 0.3  # Minimum required population diversity
    DIVERSITY_BOOST_FACTOR: float = 1.5  # Mutation boost when diversity is low

# Global config instance
trial_4stage_novelty_2_config = Trial4StageNovelty2Config()
