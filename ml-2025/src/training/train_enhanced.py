"""
Enhanced training script with varied ODE complexity and robust evaluation.
"""

import sys
import os
import numpy as np
import torch
import random
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from configs.base import config
from src.training.train import TrainingPipeline, main
from src.models.model import ModelConfig

# Set different random seeds for this run
RANDOM_SEED = 54321  # Different seed for enhanced training
np.random.seed(RANDOM_SEED)
torch.manual_seed(RANDOM_SEED)
random.seed(RANDOM_SEED)
if torch.cuda.is_available():
    torch.cuda.manual_seed(RANDOM_SEED)
    torch.cuda.manual_seed_all(RANDOM_SEED)

def main_enhanced_training():
    """Main training function with enhanced ODE complexity and evaluation."""
    
    print("="*60)
    print("ENHANCED TRAINING WITH VARIED COMPLEXITY")
    print("="*60)
    print(f"Random Seed: {RANDOM_SEED}")
    print(f"Configuration:")
    print(f"  Dataset: {config.N_ODES} ODEs ({config.N_STIFF_ODES} stiff, {config.N_NONSTIFF_ODES} non-stiff)")
    print(f"  Accuracy Weight: {config.ACCURACY_WEIGHT}")
    print(f"  Efficiency Weight: {config.EFFICIENCY_WEIGHT}")
    print(f"  Stability Weight: {config.STABILITY_WEIGHT}")
    print(f"  Stages: {config.MIN_STAGES}-{config.MAX_STAGES} (default: {config.DEFAULT_STAGES})")
    print(f"  Integration Time: {config.T_END}")
    print(f"  Reference Tolerance: {config.REFERENCE_TOL}")
    print(f"  Enhanced Features:")
    print(f"    - Varied ODE complexity levels")
    print(f"    - C matrix constrained to [0,1]")
    print(f"    - Multiple step size evaluation")
    print(f"    - Trial-specific datasets")
    print("="*60)
    
    # Create trial-specific configuration
    trial_id = f"enhanced_trial_{RANDOM_SEED}"
    complexity_level = 2  # Medium complexity
    
    # Initialize training pipeline with enhanced features
    pipeline = TrainingPipeline(
        config_obj=config,
        trial_id=trial_id,
        complexity_level=complexity_level
    )
    
    # Initialize training with fresh dataset
    pipeline.initialize_training(force_regenerate_dataset=True)
    
    # Run training
    results = pipeline.run_training(
        n_epochs=config.N_EPOCHS,
        use_evolution=False,  # Use neural network approach
        save_frequency=15,
        full_eval_frequency=30
    )
    
    # Print final results
    if results:
        print("\n" + "="*60)
        print("ENHANCED TRAINING RESULTS")
        print("="*60)
        
        best_metrics = results['best_table_metrics']
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
        
        # Verify c matrix constraints
        c_values = pipeline.best_table.c
        print(f"\nC Matrix Constraints Verification:")
        print(f"  C values: {c_values}")
        print(f"  All in [0,1]: {np.all((c_values >= 0) & (c_values <= 1))}")
        print(f"  Monotonic: {np.all(np.diff(c_values) >= 0)}")

if __name__ == "__main__":
    main_enhanced_training()
