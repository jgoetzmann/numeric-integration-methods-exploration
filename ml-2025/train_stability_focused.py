"""
Training script for stability-focused model.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the stability-focused config
from config_stability_focused import config
from train import TrainingPipeline, main

def main_stability_focused():
    """Main training function for stability-focused model."""
    
    print("="*60)
    print("STABILITY-FOCUSED TRAINING")
    print("="*60)
    print(f"Configuration:")
    print(f"  Dataset: {config.N_ODES} ODEs ({config.N_STIFF_ODES} stiff, {config.N_NONSTIFF_ODES} non-stiff)")
    print(f"  Accuracy Weight: {config.ACCURACY_WEIGHT}")
    print(f"  Efficiency Weight: {config.EFFICIENCY_WEIGHT}")
    print(f"  Stability Weight: {config.STABILITY_WEIGHT}")
    print(f"  Stages: {config.MIN_STAGES}-{config.MAX_STAGES} (default: {config.DEFAULT_STAGES})")
    print(f"  Integration Time: {config.T_END}")
    print(f"  Reference Tolerance: {config.REFERENCE_TOL}")
    print("="*60)
    
    # Initialize training pipeline
    pipeline = TrainingPipeline()
    
    # Initialize training with fresh dataset
    pipeline.initialize_training(force_regenerate_dataset=True)
    
    # Run training
    results = pipeline.run_training(
        n_epochs=config.N_EPOCHS,
        use_evolution=False,  # Use neural network approach
        save_frequency=15,
        full_eval_frequency=35
    )
    
    # Print final results
    if results:
        print("\n" + "="*60)
        print("STABILITY-FOCUSED TRAINING RESULTS")
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
    main_stability_focused()
