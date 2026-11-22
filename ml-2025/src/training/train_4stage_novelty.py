"""
Training script for 4-stage Butcher table with novelty search and constraint rewards.
"""

import sys
import os
import numpy as np
import torch
import random
import time
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from configs.trial_4stage_novelty import trial_4stage_novelty_config as config
from src.training.train import TrainingPipeline
from src.models.model import ModelConfig

# Set unique random seed for this trial
RANDOM_SEED = 1009
np.random.seed(RANDOM_SEED)
torch.manual_seed(RANDOM_SEED)
random.seed(RANDOM_SEED)
if torch.cuda.is_available():
    torch.cuda.manual_seed(RANDOM_SEED)
    torch.cuda.manual_seed_all(RANDOM_SEED)

def main_4stage_novelty():
    """Main training function for 4-stage novelty search model."""
    
    print("="*70)
    print("TRAINING: 4-STAGE BUTCHER TABLE - NOVELTY SEARCH")
    print("="*70)
    print(f"Random Seed: {RANDOM_SEED}")
    print(f"Configuration:")
    print(f"  Stages: {config.MIN_STAGES}-{config.MAX_STAGES} (fixed at {config.DEFAULT_STAGES})")
    print(f"  Accuracy Weight: {config.ACCURACY_WEIGHT}")
    print(f"  Efficiency Weight: {config.EFFICIENCY_WEIGHT}")
    print(f"  Stability Weight: {config.STABILITY_WEIGHT}")
    print(f"  C Matrix Reward: {config.C_MATRIX_REWARD_WEIGHT:.1%}")
    print(f"  B Matrix Sum Reward: {config.B_MATRIX_SUM_REWARD_WEIGHT:.1%}")
    print(f"  Novelty Reward: {config.NOVELTY_REWARD_WEIGHT:.1%}")
    print(f"  Baseline Penalty: {config.BASELINE_PENALTY_WEIGHT:.1%}")
    print(f"  Candidates per Epoch: {config.N_CANDIDATES_PER_BATCH}")
    print(f"  Population Size: {config.EVOLUTION_POPULATION_SIZE}")
    print(f"  Mutation Rate: {config.EVOLUTION_MUTATION_RATE}")
    print(f"  Crossover Rate: {config.EVOLUTION_CROSSOVER_RATE}")
    print(f"  Novelty Threshold: {config.NOVELTY_THRESHOLD}")
    
    # CUDA status
    if torch.cuda.is_available():
        print(f"  CUDA: ⚠️  Available but disabled - {torch.cuda.get_device_name(0)}")
        print(f"  GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
        print(f"  Reason: Using CPU for stability and to avoid CUDA memory issues")
    else:
        print(f"  CUDA: ❌ Not available - Using CPU")
    
    print("="*70)
    
    # Create trial-specific configuration
    trial_id = f"4stage_novelty_{RANDOM_SEED}"
    
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
    print(f"\nStarting novelty search training for {config.N_EPOCHS} epochs...")
    print(f"Novelty search features:")
    print(f"  - Reduced constraint rewards ({config.C_MATRIX_REWARD_WEIGHT:.1%} + {config.B_MATRIX_SUM_REWARD_WEIGHT:.1%})")
    print(f"  - Novelty reward ({config.NOVELTY_REWARD_WEIGHT:.1%}) for being different from baselines")
    print(f"  - Baseline penalty ({config.BASELINE_PENALTY_WEIGHT:.1%}) for being too similar")
    print(f"  - Balanced exploration vs exploitation")
    print(f"  - Novelty threshold: {config.NOVELTY_THRESHOLD}")
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
        print("4-STAGE NOVELTY SEARCH TRAINING RESULTS")
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
        
        # Verify constraint satisfaction and novelty
        c_values = pipeline.best_table.c
        b_values = pipeline.best_table.b
        print(f"\nConstraint & Novelty Verification:")
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
        
        # Novelty analysis
        novelty_reward = config.NOVELTY_REWARD_WEIGHT * pipeline.metrics_calculator._compute_novelty_reward(pipeline.best_table)
        print(f"  Novelty reward: {novelty_reward:.4f} ({novelty_reward/config.NOVELTY_REWARD_WEIGHT:.0%} of max)")
        
        total_constraint_reward = c_reward + b_reward + novelty_reward
        print(f"  Total constraint + novelty reward: {total_constraint_reward:.4f}")
        
        # Compare to baselines for novelty
        from src.core.butcher_tables import get_all_baseline_tables
        baseline_tables = get_all_baseline_tables()
        rk4 = baseline_tables['rk4']
        
        c_diff = np.mean(np.abs(c_values - rk4.c))
        b_diff = np.mean(np.abs(b_values - rk4.b))
        a_diff = pipeline.metrics_calculator._compute_matrix_difference(pipeline.best_table.A, rk4.A)
        
        print(f"\nNovelty Analysis vs RK4:")
        print(f"  C vector difference: {c_diff:.4f}")
        print(f"  B vector difference: {b_diff:.4f}")
        print(f"  A matrix difference: {a_diff:.4f}")
        print(f"  Overall novelty: {(c_diff + b_diff + a_diff) / 3:.4f}")
        print(f"  Novelty threshold: {config.NOVELTY_THRESHOLD}")
        print(f"  Above threshold: {'✅ YES' if (c_diff + b_diff + a_diff) / 3 > config.NOVELTY_THRESHOLD else '❌ NO'}")
        print(f"  Stages: {len(c_values)}")

if __name__ == "__main__":
    main_4stage_novelty()
