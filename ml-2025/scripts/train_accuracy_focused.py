"""
Training script for accuracy-focused model.
"""

import sys
import os
import numpy as np
import torch
import random
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the accuracy-focused config
from scripts.config_accuracy_focused import config as accuracy_config
from train import TrainingPipeline, main
import train

# Set different random seeds for this run
RANDOM_SEED = 54321  # Different seed for accuracy-focused
np.random.seed(RANDOM_SEED)
torch.manual_seed(RANDOM_SEED)
random.seed(RANDOM_SEED)
if torch.cuda.is_available():
    torch.cuda.manual_seed(RANDOM_SEED)
    torch.cuda.manual_seed_all(RANDOM_SEED)

def main_accuracy_focused():
    """Main training function for accuracy-focused model."""
    
    print("="*60)
    print("ACCURACY-FOCUSED TRAINING")
    print("="*60)
    print(f"Random Seed: {RANDOM_SEED}")
    print(f"Configuration:")
    print(f"  Dataset: {accuracy_config.N_ODES} ODEs ({accuracy_config.N_STIFF_ODES} stiff, {accuracy_config.N_NONSTIFF_ODES} non-stiff)")
    print(f"  Accuracy Weight: {accuracy_config.ACCURACY_WEIGHT}")
    print(f"  Efficiency Weight: {accuracy_config.EFFICIENCY_WEIGHT}")
    print(f"  Stability Weight: {accuracy_config.STABILITY_WEIGHT}")
    print(f"  Stages: {accuracy_config.MIN_STAGES}-{accuracy_config.MAX_STAGES} (default: {accuracy_config.DEFAULT_STAGES})")
    print(f"  Integration Time: {accuracy_config.T_END}")
    print(f"  Reference Tolerance: {accuracy_config.REFERENCE_TOL}")
    print("="*60)
    
    # Initialize training pipeline with specialized config
    pipeline = TrainingPipeline(config_obj=accuracy_config)
    
    # Initialize training with fresh dataset
    pipeline.initialize_training(force_regenerate_dataset=True)
    
    # Run training
    results = pipeline.run_training(
        n_epochs=accuracy_config.N_EPOCHS,
        use_evolution=False,  # Use neural network approach
        save_frequency=20,
        full_eval_frequency=50
    )
    
    # Print final results
    if results:
        print("\n" + "="*60)
        print("ACCURACY-FOCUSED TRAINING RESULTS")
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
    main_accuracy_focused()
