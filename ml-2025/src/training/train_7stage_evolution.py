"""
Training script for 7-stage Butcher table with evolution learning and constraint rewards.
"""

import sys
import os
import numpy as np
import torch
import random
import time
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from configs.trial_7stage_evolution import trial_7stage_evolution_config as config
from src.training.train import TrainingPipeline
from src.models.model import ModelConfig

# Set unique random seed for this trial
RANDOM_SEED = 1006
np.random.seed(RANDOM_SEED)
torch.manual_seed(RANDOM_SEED)
random.seed(RANDOM_SEED)
if torch.cuda.is_available():
    torch.cuda.manual_seed(RANDOM_SEED)
    torch.cuda.manual_seed_all(RANDOM_SEED)

def main_7stage_evolution():
    """Main training function for 7-stage evolution-focused model."""
    
    print("="*70)
    print("TRAINING: 7-STAGE BUTCHER TABLE - EVOLUTION LEARNING")
    print("="*70)
    print(f"Random Seed: {RANDOM_SEED}")
    print(f"Configuration:")
    print(f"  Stages: {config.MIN_STAGES}-{config.MAX_STAGES} (fixed at {config.DEFAULT_STAGES})")
    print(f"  Accuracy Weight: {config.ACCURACY_WEIGHT}")
    print(f"  Efficiency Weight: {config.EFFICIENCY_WEIGHT}")
    print(f"  Stability Weight: {config.STABILITY_WEIGHT}")
    print(f"  C Matrix Reward Weight: {config.C_MATRIX_REWARD_WEIGHT}")
    print(f"  B Matrix Sum Reward Weight: {config.B_MATRIX_SUM_REWARD_WEIGHT}")
    print(f"  Epochs: {config.N_EPOCHS}")
    print(f"  Candidates per Epoch: {config.N_CANDIDATES_PER_BATCH}")
    print(f"  Dataset: {config.N_ODES} ODEs ({config.N_STIFF_ODES} stiff, {config.N_NONSTIFF_ODES} non-stiff)")
    print(f"  Complexity Level: {config.COMPLEXITY_LEVEL}")
    print(f"  Integration Time: {config.T_END}")
    print(f"  Reference Tolerance: {config.REFERENCE_TOL}")
    print(f"  Evolution: {config.USE_EVOLUTION}")
    print(f"  Population Size: {config.EVOLUTION_POPULATION_SIZE}")
    print(f"  Mutation Rate: {config.EVOLUTION_MUTATION_RATE}")
    print(f"  Crossover Rate: {config.EVOLUTION_CROSSOVER_RATE}")
    
    # CUDA status
    if torch.cuda.is_available():
        print(f"  CUDA: ⚠️  Available but disabled - {torch.cuda.get_device_name(0)}")
        print(f"  GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
        print(f"  Reason: Using CPU for stability and to avoid CUDA memory issues")
    else:
        print(f"  CUDA: ❌ Not available - Using CPU")
    
    print("="*70)
    
    # Create trial-specific configuration
    trial_id = f"7stage_evolution_{RANDOM_SEED}"
    
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
    print(f"\nStarting evolution training for {config.N_EPOCHS} epochs...")
    print(f"Expected improvements:")
    print(f"  - Lower success threshold (10% vs 50%)")
    print(f"  - More candidates per epoch ({config.N_CANDIDATES_PER_BATCH} vs 15)")
    print(f"  - Fallback mechanism for failed epochs")
    print(f"  - Constraint rewards: C matrix [0,1] ({config.C_MATRIX_REWARD_WEIGHT:.0%}), B sum=1 ({config.B_MATRIX_SUM_REWARD_WEIGHT:.0%})")
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
        print("7-STAGE EVOLUTION TRAINING RESULTS")
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
        
        # Verify constraint satisfaction
        c_values = pipeline.best_table.c
        b_values = pipeline.best_table.b
        print(f"\nConstraint Verification:")
        print(f"  C values: {c_values}")
        c_in_range = np.all((c_values >= 0) & (c_values <= 1))
        print(f"  All C in [0,1]: {'✅ YES' if c_in_range else '❌ NO'}")
        c_reward = config.C_MATRIX_REWARD_WEIGHT * pipeline.metrics_calculator._compute_c_matrix_constraint_reward(c_values)
        print(f"  C constraint reward: {c_reward:.4f} ({c_reward/config.C_MATRIX_REWARD_WEIGHT:.0%} of max)")
        print(f"  B values: {b_values}")
        b_sum = np.sum(b_values)
        print(f"  B sum: {b_sum:.6f} {'✅' if abs(b_sum - 1.0) < 1e-6 else '❌'}")
        b_reward = config.B_MATRIX_SUM_REWARD_WEIGHT * pipeline.metrics_calculator._compute_b_matrix_sum_constraint_reward(b_values)
        print(f"  B sum constraint reward: {b_reward:.4f} ({b_reward/config.B_MATRIX_SUM_REWARD_WEIGHT:.0%} of max)")
        total_constraint_reward = c_reward + b_reward
        print(f"  Total constraint reward: {total_constraint_reward:.4f}")
        print(f"  Stages: {len(c_values)}")

if __name__ == "__main__":
    main_7stage_evolution()
