"""
Training script for efficiency-focused model (Version 2).
This ensures different results from the original efficiency-focused run.
"""

import sys
import os
import numpy as np
import torch
import random
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

# Import the efficiency-focused config V2 (using efficiency focused as base)
from configs.efficiency_focused import config as efficiency_config_v2
from src.training.train import TrainingPipeline, main
import src.training.train as train

# Set different random seeds for this run
RANDOM_SEED = 12345  # Different seed for efficiency-focused V2
np.random.seed(RANDOM_SEED)
torch.manual_seed(RANDOM_SEED)
random.seed(RANDOM_SEED)
if torch.cuda.is_available():
    torch.cuda.manual_seed(RANDOM_SEED)
    torch.cuda.manual_seed_all(RANDOM_SEED)

def main_efficiency_focused_v2():
    """Main training function for efficiency-focused model (V2)."""
    
    print("="*60)
    print("EFFICIENCY-FOCUSED TRAINING (VERSION 2)")
    print("="*60)
    print(f"Random Seed: {RANDOM_SEED}")
    print(f"Configuration:")
    print(f"  Dataset: {efficiency_config_v2.N_ODES} ODEs ({efficiency_config_v2.N_STIFF_ODES} stiff, {efficiency_config_v2.N_NONSTIFF_ODES} non-stiff)")
    print(f"  Accuracy Weight: {efficiency_config_v2.ACCURACY_WEIGHT}")
    print(f"  Efficiency Weight: {efficiency_config_v2.EFFICIENCY_WEIGHT}")
    print(f"  Stability Weight: {efficiency_config_v2.STABILITY_WEIGHT}")
    print(f"  Stages: {efficiency_config_v2.MIN_STAGES}-{efficiency_config_v2.MAX_STAGES} (default: {efficiency_config_v2.DEFAULT_STAGES})")
    print(f"  Integration Time: {efficiency_config_v2.T_END}")
    print(f"  Reference Tolerance: {efficiency_config_v2.REFERENCE_TOL}")
    print(f"  ML Model Size: {efficiency_config_v2.GENERATOR_HIDDEN_SIZE} hidden units")
    print("="*60)
    
    # Initialize training pipeline with specialized config
    pipeline = TrainingPipeline(config_obj=efficiency_config_v2)
    
    # Initialize training with fresh dataset
    pipeline.initialize_training(force_regenerate_dataset=True)
    
    # Run training
    results = pipeline.run_training(
        n_epochs=efficiency_config_v2.N_EPOCHS,
        use_evolution=False,  # Use neural network approach
        save_frequency=15,
        full_eval_frequency=30
    )
    
    # Print final results
    if results:
        print("\n" + "="*60)
        print("EFFICIENCY-FOCUSED TRAINING RESULTS (V2)")
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

if __name__ == "__main__":
    main_efficiency_focused_v2()
