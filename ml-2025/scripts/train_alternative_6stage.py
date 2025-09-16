import sys
import os
import numpy as np
import torch
import random
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the alternative 6-stage config
from scripts.config_alternative_6stage import config as alt_6stage_config
from scripts.model_config_diversity import config as model_config
from train import TrainingPipeline, main
import train

# Set different random seeds for this run
RANDOM_SEED = 88888  # Different seed for alternative 6-stage
np.random.seed(RANDOM_SEED)
torch.manual_seed(RANDOM_SEED)
random.seed(RANDOM_SEED)
if torch.cuda.is_available():
    torch.cuda.manual_seed(RANDOM_SEED)
    torch.cuda.manual_seed_all(RANDOM_SEED)

def main_alternative_6stage():
    print("="*60)
    print("ALTERNATIVE 6-STAGE TRAINING")
    print("="*60)
    print(f"Random Seed: {RANDOM_SEED}")
    print(f"Configuration:")
    print(f"  Dataset: {alt_6stage_config.N_ODES} ODEs ({alt_6stage_config.N_STIFF_ODES} stiff, {alt_6stage_config.N_NONSTIFF_ODES} non-stiff)")
    print(f"  Accuracy Weight: {alt_6stage_config.ACCURACY_WEIGHT}")
    print(f"  Efficiency Weight: {alt_6stage_config.EFFICIENCY_WEIGHT}")
    print(f"  Stability Weight: {alt_6stage_config.STABILITY_WEIGHT}")
    print(f"  Stages: {alt_6stage_config.MIN_STAGES}-{alt_6stage_config.MAX_STAGES} (default: {alt_6stage_config.DEFAULT_STAGES})")
    print(f"  Integration Time: {alt_6stage_config.T_END}")
    print(f"  Reference Tolerance: {alt_6stage_config.REFERENCE_TOL}")
    print(f"  Diversity Penalty: {alt_6stage_config.DIVERSITY_PENALTY}")
    print(f"  Coefficient Diversity Bonus: {alt_6stage_config.COEFFICIENT_DIVERSITY_BONUS}")
    print(f"  Min Stability Radius: {alt_6stage_config.MIN_STABILITY_RADIUS}")
    print(f"  Forbidden Coefficients: {len(alt_6stage_config.FORBIDDEN_COEFFICIENTS)} coefficients")
    print("="*60)
    
    # Initialize training pipeline with alternative 6-stage config and model config
    pipeline = TrainingPipeline(model_config=model_config, config_obj=alt_6stage_config)
    
    # Initialize training with fresh dataset
    pipeline.initialize_training(force_regenerate_dataset=True)
    
    # Run training
    results = pipeline.run_training(
        n_epochs=alt_6stage_config.N_EPOCHS,
        use_evolution=False,  # Use neural network approach
        save_frequency=12,
        full_eval_frequency=24
    )
    
    # Print final results
    if results:
        print("\n" + "="*60)
        print("ALTERNATIVE 6-STAGE TRAINING RESULTS")
        print("="*60)
        print(f"Best Butcher Table Performance:")
        print(f"  Composite Score: {results.composite_score:.4f}")
        print(f"  Max Error: {results.max_error:.2e}")
        print(f"  Efficiency Score: {results.efficiency_score:.4f}")
        print(f"  Stability Score: {results.stability_score:.4f}")
        print(f"  Success Rate: {results.success_rate:.2%}")
        print("\nComparison to Baselines:")
        for baseline, comp in results.comparisons.items():
            print(f"  vs {baseline}:")
            print(f"    Accuracy: {comp['accuracy_ratio']:.2f}x")
            print(f"    Efficiency: {comp['efficiency_ratio']:.2f}x")
            print(f"    Overall: {comp['score_ratio']:.2f}x")
        print("\nBest Butcher Table:")
        print(results.butcher_table)
        print("="*60)

if __name__ == "__main__":
    main_alternative_6stage()

