"""
Training script for 4-stage Butcher table with 20% accuracy, 80% efficiency focus.
"""

import sys
import os
import numpy as np
import torch
import random
import time
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from configs.trial_4stage_efficiency import trial_4stage_efficiency_config as config
from src.training.train import TrainingPipeline
from src.models.model import ModelConfig

# Set unique random seed for this trial
RANDOM_SEED = 1002
np.random.seed(RANDOM_SEED)
torch.manual_seed(RANDOM_SEED)
random.seed(RANDOM_SEED)
if torch.cuda.is_available():
    torch.cuda.manual_seed(RANDOM_SEED)
    torch.cuda.manual_seed_all(RANDOM_SEED)

def main_4stage_efficiency():
    """Main training function for 4-stage efficiency-focused model."""
    
    print("="*70)
    print("TRAINING: 4-STAGE BUTCHER TABLE - EFFICIENCY FOCUSED")
    print("="*70)
    print(f"Random Seed: {RANDOM_SEED}")
    print(f"Configuration:")
    print(f"  Stages: {config.MIN_STAGES}-{config.MAX_STAGES} (fixed at {config.DEFAULT_STAGES})")
    print(f"  Accuracy Weight: {config.ACCURACY_WEIGHT}")
    print(f"  Efficiency Weight: {config.EFFICIENCY_WEIGHT}")
    print(f"  Stability Weight: {config.STABILITY_WEIGHT}")
    print(f"  Epochs: {config.N_EPOCHS}")
    print(f"  Candidates per Epoch: {config.N_CANDIDATES_PER_BATCH}")
    print(f"  Dataset: {config.N_ODES} ODEs ({config.N_STIFF_ODES} stiff, {config.N_NONSTIFF_ODES} non-stiff)")
    print(f"  Complexity Level: {config.COMPLEXITY_LEVEL}")
    print(f"  Integration Time: {config.T_END}")
    print(f"  Reference Tolerance: {config.REFERENCE_TOL}")
    
    # CUDA status
    if torch.cuda.is_available():
        print(f"  CUDA: ✅ Enabled - {torch.cuda.get_device_name(0)}")
        print(f"  GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
    else:
        print(f"  CUDA: ❌ Not available - Using CPU")
    
    print("="*70)
    
    # Create trial-specific configuration
    trial_id = f"4stage_efficiency_{RANDOM_SEED}"
    
    # Initialize training pipeline with CUDA support (disabled for laptop GPU)
    # RTX 3050 Ti laptop GPU is slower than CPU for small operations
    pipeline = TrainingPipeline(
        config_obj=config,
        trial_id=trial_id,
        complexity_level=config.COMPLEXITY_LEVEL,
        use_cuda=False  # Disable CUDA for laptop GPU performance
    )
    
    # Initialize training with fresh dataset
    print("Initializing training pipeline...")
    pipeline.initialize_training(force_regenerate_dataset=True)
    
    # Run training
    print(f"\nStarting training for {config.N_EPOCHS} epochs...")
    start_time = time.time()
    
    results = pipeline.run_training(
        n_epochs=config.N_EPOCHS,
        use_evolution=False,  # Use neural network approach
        save_frequency=20,
        full_eval_frequency=40
    )
    
    training_time = time.time() - start_time
    
    # Print final results
    if results:
        print("\n" + "="*70)
        print("4-STAGE EFFICIENCY-FOCUSED TRAINING RESULTS")
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
        
        # Verify c matrix constraints
        c_values = pipeline.best_table.c
        print(f"\nC Matrix Constraints Verification:")
        print(f"  C values: {c_values}")
        print(f"  All in [0,1]: {np.all((c_values >= 0) & (c_values <= 1))}")
        print(f"  Monotonic: {np.all(np.diff(c_values) >= 0)}")
        print(f"  Stages: {len(c_values)}")

if __name__ == "__main__":
    main_4stage_efficiency()
