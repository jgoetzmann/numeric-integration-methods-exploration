"""
Training script for 4-stage Butcher table with maximum exploration and no constraint rewards.
"""

import sys
import os
import numpy as np
import torch
import random
import time
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from configs.trial_4stage_exploration import trial_4stage_exploration_config as config
from src.training.train import TrainingPipeline
from src.models.model import ModelConfig

# Set unique random seed for this trial
RANDOM_SEED = 1008
np.random.seed(RANDOM_SEED)
torch.manual_seed(RANDOM_SEED)
random.seed(RANDOM_SEED)
if torch.cuda.is_available():
    torch.cuda.manual_seed(RANDOM_SEED)
    torch.cuda.manual_seed_all(RANDOM_SEED)

def main_4stage_exploration():
    """Main training function for 4-stage exploration-focused model."""
    
    print("="*70)
    print("TRAINING: 4-STAGE BUTCHER TABLE - MAXIMUM EXPLORATION")
    print("="*70)
    print(f"Random Seed: {RANDOM_SEED}")
    print(f"Configuration:")
    print(f"  Stages: {config.MIN_STAGES}-{config.MAX_STAGES} (fixed at {config.DEFAULT_STAGES})")
    print(f"  Accuracy Weight: {config.ACCURACY_WEIGHT}")
    print(f"  Efficiency Weight: {config.EFFICIENCY_WEIGHT}")
    print(f"  Stability Weight: {config.STABILITY_WEIGHT}")
    print(f"  Success Threshold: {config.SUCCESS_THRESHOLD:.1%} (very low for exploration)")
    print(f"  Candidates per Epoch: {config.N_CANDIDATES_PER_BATCH}")
    print(f"  Population Size: {config.EVOLUTION_POPULATION_SIZE}")
    print(f"  Mutation Rate: {config.EVOLUTION_MUTATION_RATE}")
    print(f"  Crossover Rate: {config.EVOLUTION_CROSSOVER_RATE}")
    print(f"  Exploration Bonus: {config.EXPLORATION_BONUS:.1%}")
    print(f"  Diversity Reward: {config.DIVERSITY_REWARD:.1%}")
    print(f"  C Matrix Constraint: {'❌ DISABLED' if config.C_MATRIX_REWARD_WEIGHT == 0 else '✅ ENABLED'}")
    print(f"  B Matrix Constraint: {'❌ DISABLED' if config.B_MATRIX_SUM_REWARD_WEIGHT == 0 else '✅ ENABLED'}")
    
    # CUDA status
    if torch.cuda.is_available():
        print(f"  CUDA: ⚠️  Available but disabled - {torch.cuda.get_device_name(0)}")
        print(f"  GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
        print(f"  Reason: Using CPU for stability and to avoid CUDA memory issues")
    else:
        print(f"  CUDA: ❌ Not available - Using CPU")
    
    print("="*70)
    
    # Create trial-specific configuration
    trial_id = f"4stage_exploration_{RANDOM_SEED}"
    
    # Initialize training pipeline with CPU for stability
    pipeline = TrainingPipeline(
        config_obj=config,
        trial_id=trial_id,
        complexity_level=config.COMPLEXITY_LEVEL,
        use_cuda=False  # Use CPU for stability and to avoid CUDA memory issues
    )
    
    # Initialize training with fresh dataset
    print("Initializing training pipeline...")
    pipeline.initialize_training(force_regenerate_dataset=True)
    
    # Run training
    print(f"\nStarting exploration training for {config.N_EPOCHS} epochs...")
    print(f"Exploration features:")
    print(f"  - No constraint rewards (pure performance focus)")
    print(f"  - Very low success threshold ({config.SUCCESS_THRESHOLD:.1%})")
    print(f"  - High mutation rate ({config.EVOLUTION_MUTATION_RATE:.1%}) for diversity")
    print(f"  - Large population ({config.EVOLUTION_POPULATION_SIZE}) for exploration")
    print(f"  - Exploration bonus for coefficient diversity")
    print(f"  - Many candidates per epoch ({config.N_CANDIDATES_PER_BATCH})")
    start_time = time.time()
    
    try:
        results = pipeline.run_training(
            n_epochs=config.N_EPOCHS,
            use_evolution=config.USE_EVOLUTION,  # Use evolution approach
            save_frequency=20,
            full_eval_frequency=40
        )
    except KeyboardInterrupt:
        print("\nTraining interrupted by user")
        results = pipeline.evaluate_on_full_dataset()
    except Exception as e:
        print(f"\nTraining error: {e}")
        print("Attempting to save current progress...")
        results = pipeline.evaluate_on_full_dataset() if pipeline.best_table else None
    
    training_time = time.time() - start_time
    
    # Print final results
    if results:
        print("\n" + "="*70)
        print("4-STAGE EXPLORATION TRAINING RESULTS")
        print("="*70)
        
        best_metrics = results['best_table_metrics']
        print(f"Training completed in {training_time:.2f} seconds")
        print(f"Best Butcher Table Performance:")
        print(f"  Composite Score: {best_metrics.composite_score:.4f}")
        print(f"  Max Error: {best_metrics.max_error:.2e}")
        print(f"  Efficiency Score: {best_metrics.efficiency_score:.4f}")
        print(f"  Stability Score: {best_metrics.stability_score:.4f}")
        print(f"  Success Rate: {best_metrics.success_rate:.2%}")
        
        print(f"\nComparison to Baselines:")
        for baseline_name, comparison in results['comparisons'].items():
            print(f"  vs {baseline_name}:")
            print(f"    Accuracy: {comparison['accuracy_ratio']:.2f}x")
            print(f"    Efficiency: {comparison['efficiency_ratio']:.2f}x")
            print(f"    Overall: {comparison['score_ratio']:.2f}x")
        
        print(f"\nBest Butcher Table:")
        print(pipeline.best_table)
        
        # Analyze exploration results
        c_values = pipeline.best_table.c
        b_values = pipeline.best_table.b
        print(f"\nExploration Analysis:")
        print(f"  C values: {c_values}")
        print(f"  C range: [{np.min(c_values):.3f}, {np.max(c_values):.3f}]")
        print(f"  B values: {b_values}")
        print(f"  B sum: {np.sum(b_values):.6f}")
        
        # Check if it's novel compared to baselines
        from src.core.butcher_tables import get_all_baseline_tables
        baseline_tables = get_all_baseline_tables()
        rk4 = baseline_tables['rk4']
        
        c_diff = np.mean(np.abs(c_values - rk4.c))
        b_diff = np.mean(np.abs(b_values - rk4.b))
        a_diff = pipeline.metrics_calculator._compute_matrix_difference(pipeline.best_table.A, rk4.A)
        
        print(f"  Novelty vs RK4:")
        print(f"    C vector difference: {c_diff:.4f}")
        print(f"    B vector difference: {b_diff:.4f}")
        print(f"    A matrix difference: {a_diff:.4f}")
        print(f"    Overall novelty: {(c_diff + b_diff + a_diff) / 3:.4f}")
        
        # Exploration bonus analysis
        exploration_bonus = pipeline.metrics_calculator._compute_exploration_bonus(pipeline.best_table)
        print(f"  Exploration bonus: {config.EXPLORATION_BONUS * exploration_bonus:.4f}")
        print(f"  Stages: {len(c_values)}")

if __name__ == "__main__":
    main_4stage_exploration()
