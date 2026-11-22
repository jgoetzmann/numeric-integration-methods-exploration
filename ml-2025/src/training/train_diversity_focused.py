"""
Diversity-focused training script to find DIFFERENT butcher tables.
This script actively prevents convergence to the known optimal solution.
"""

import sys
import os
import numpy as np
import torch
import random
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

# Import the diversity-focused config (using mixed focus as base)
from configs.mixed_focus import config as diversity_config
from configs.mixed_focus import config as model_config
from src.training.train import TrainingPipeline, main
import src.training.train as train

# Set different random seeds for this run
RANDOM_SEED = 99999  # Very different seed for diversity-focused
np.random.seed(RANDOM_SEED)
torch.manual_seed(RANDOM_SEED)
random.seed(RANDOM_SEED)
if torch.cuda.is_available():
    torch.cuda.manual_seed(RANDOM_SEED)
    torch.cuda.manual_seed_all(RANDOM_SEED)

def main_diversity_focused():
    print("="*60)
    print("DIVERSITY-FOCUSED TRAINING")
    print("="*60)
    print(f"Random Seed: {RANDOM_SEED}")
    print(f"Configuration:")
    print(f"  Dataset: {diversity_config.N_ODES} ODEs ({diversity_config.N_STIFF_ODES} stiff, {diversity_config.N_NONSTIFF_ODES} non-stiff)")
    print(f"  Accuracy Weight: {diversity_config.ACCURACY_WEIGHT}")
    print(f"  Efficiency Weight: {diversity_config.EFFICIENCY_WEIGHT}")
    print(f"  Stability Weight: {diversity_config.STABILITY_WEIGHT}")
    print(f"  Stages: {diversity_config.MIN_STAGES}-{diversity_config.MAX_STAGES} (default: {diversity_config.DEFAULT_STAGES})")
    print(f"  Integration Time: {diversity_config.T_END}")
    print(f"  Reference Tolerance: {diversity_config.REFERENCE_TOL}")
    print(f"  Diversity Penalty: {diversity_config.DIVERSITY_PENALTY}")
    print(f"  Forbidden Stages: {diversity_config.FORBIDDEN_STAGES}")
    print(f"  Min Stability Radius: {diversity_config.MIN_STABILITY_RADIUS}")
    print("="*60)
    
    # Initialize training pipeline with specialized config and model config
    pipeline = TrainingPipeline(model_config=model_config, config_obj=diversity_config)
    
    # Initialize training with fresh dataset
    pipeline.initialize_training(force_regenerate_dataset=True)
    
    # Run training with shorter epochs
    results = pipeline.run_training(
        n_epochs=diversity_config.N_EPOCHS,
        use_evolution=False,  # Use neural network approach
        save_frequency=10,
        full_eval_frequency=20
    )
    
    # Print final results
    if results:
        print("\n" + "="*60)
        print("DIVERSITY-FOCUSED TRAINING RESULTS")
        print("="*60)
        print(f"Best Butcher Table Performance:")
        print(f"  Composite Score: {results['best_composite_score']:.4f}")
        print(f"  Max Error: {results['best_max_error']:.2e}")
        print(f"  Efficiency Score: {results['best_efficiency_score']:.4f}")
        print(f"  Stability Score: {results['best_stability_score']:.4f}")
        print(f"  Success Rate: {results['best_success_rate']:.2%}")
        print(f"  Stages: {len(results['best_butcher_table'].b)}")
        print(f"  Stability Radius: {results['best_butcher_table'].stability_radius:.4f}")
        
        print(f"\nComparison to Baselines:")
        for baseline, comparison in results['comparisons'].items():
            print(f"  vs {baseline}:")
            print(f"    Accuracy: {comparison['accuracy_ratio']:.2f}x")
            print(f"    Efficiency: {comparison['efficiency_ratio']:.2f}x")
            print(f"    Overall: {comparison['score_ratio']:.2f}x")
        
        print(f"\nBest Butcher Table:")
        print(results['best_butcher_table'])
        
        # Check if this is different from the optimal solution
        stages = len(results['best_butcher_table'].b)
        stability_radius = results['best_butcher_table'].stability_radius
        
        print(f"\nDIVERSITY ANALYSIS:")
        if stages != 4:
            print(f"✓ SUCCESS: Found {stages}-stage method (different from optimal 4-stage)")
        else:
            print(f"✗ FAILED: Still found 4-stage method (same as optimal)")
            
        if abs(stability_radius - 2.0) > 0.5:
            print(f"✓ SUCCESS: Stability radius {stability_radius:.2f} (different from optimal ~2.0)")
        else:
            print(f"✗ FAILED: Stability radius {stability_radius:.2f} (similar to optimal ~2.0)")
        
        if stages != 4 or abs(stability_radius - 2.0) > 0.5:
            print(f"🎉 DIVERSITY SUCCESS: Found genuinely different solution!")
        else:
            print(f"😞 DIVERSITY FAILED: Still converged to similar solution")

if __name__ == "__main__":
    main_diversity_focused()
