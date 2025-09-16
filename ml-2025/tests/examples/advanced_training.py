"""
Advanced Training Examples for Novel Numerical Integration Methods.

This script demonstrates advanced usage of the training pipeline.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from train import TrainingPipeline
from model import ModelConfig
from database import ExperimentLogger
from visualization import ReportGenerator

def example_1_custom_training_configuration():
    """Example 1: Custom training configuration."""
    
    print("=" * 60)
    print("EXAMPLE 1: Custom Training Configuration")
    print("=" * 60)
    
    # Create custom model configuration
    model_config = ModelConfig(
        generator_input_size=256,      # Larger input space
        generator_hidden_size=512,     # Larger generator network
        surrogate_hidden_size=256,     # Larger surrogate network
        surrogate_output_size=4,       # Full metrics prediction
        learning_rate=5e-4,           # Lower learning rate
        batch_size=64,                # Larger batch size
        n_epochs=50,                  # More epochs for surrogate training
        weight_decay=1e-4             # Regularization
    )
    
    # Create training pipeline with custom config
    pipeline = TrainingPipeline(model_config)
    
    print("Initializing training with custom configuration...")
    pipeline.initialize_training(force_regenerate_dataset=False)
    
    print("Running short training session...")
    results = pipeline.run_training(
        n_epochs=20,                  # Short run for demo
        use_evolution=False,          # Use neural network approach
        save_frequency=5,             # Save every 5 epochs
        full_eval_frequency=10        # Full evaluation every 10 epochs
    )
    
    if results:
        print(f"\nTraining Results:")
        best_metrics = results['best_table_metrics']
        print(f"  Best Composite Score: {best_metrics.composite_score:.4f}")
        print(f"  Best Max Error: {best_metrics.max_error:.2e}")
        print(f"  Best Efficiency: {best_metrics.efficiency_score:.4f}")
        print(f"  Success Rate: {best_metrics.success_rate:.2%}")

def example_2_evolutionary_approach():
    """Example 2: Evolutionary algorithm approach."""
    
    print("\n" + "=" * 60)
    print("EXAMPLE 2: Evolutionary Algorithm Approach")
    print("=" * 60)
    
    # Create pipeline
    pipeline = TrainingPipeline()
    pipeline.initialize_training(force_regenerate_dataset=False)
    
    print("Running evolutionary training...")
    results = pipeline.run_training(
        n_epochs=15,                  # Fewer epochs for evolution
        use_evolution=True,           # Use evolutionary approach
        save_frequency=3,             # More frequent saves
        full_eval_frequency=5         # More frequent full evaluations
    )
    
    if results:
        print(f"\nEvolutionary Results:")
        best_metrics = results['best_table_metrics']
        print(f"  Best Composite Score: {best_metrics.composite_score:.4f}")
        print(f"  Best Table Order: {pipeline.best_table.consistency_order}")

def example_3_experiment_logging():
    """Example 3: Comprehensive experiment logging."""
    
    print("\n" + "=" * 60)
    print("EXAMPLE 3: Comprehensive Experiment Logging")
    print("=" * 60)
    
    # Set up experiment logger
    logger = ExperimentLogger("examples/advanced_experiment.db")
    experiment_name = logger.start_experiment(
        "Advanced Training Example",
        "Demonstration of advanced training features with comprehensive logging"
    )
    
    # Create custom pipeline
    model_config = ModelConfig(
        generator_hidden_size=256,
        surrogate_hidden_size=128,
        learning_rate=1e-3
    )
    
    pipeline = TrainingPipeline(model_config)
    pipeline.initialize_training(force_regenerate_dataset=False)
    
    print("Running logged training experiment...")
    
    # Run training with logging
    for epoch in range(10):  # Short run for demo
        epoch_results = pipeline.train_epoch(use_evolution=False)
        
        # Log epoch results
        logger.log_training_epoch(epoch_results)
        
        print(f"Epoch {epoch_results['epoch']}: "
              f"Best={epoch_results['best_score']:.4f}, "
              f"Valid={epoch_results['n_valid_candidates']}")
    
    # Final evaluation and logging
    final_results = pipeline.evaluate_on_full_dataset()
    
    if final_results and pipeline.best_table:
        logger.log_butcher_table_evaluation(
            pipeline.best_table,
            final_results['best_table_metrics']
        )
    
    # Generate experiment summary
    summary = logger.get_experiment_summary()
    print(f"\nExperiment Summary:")
    print(f"  Total evaluations: {summary['n_evaluations']}")
    print(f"  Training epochs: {len(summary['training_history'])}")
    
    # Export results
    logger.export_results("examples/advanced_export")
    print("Results exported to examples/advanced_export/")

def example_4_comparative_study():
    """Example 4: Comparative study of different approaches."""
    
    print("\n" + "=" * 60)
    print("EXAMPLE 4: Comparative Study")
    print("=" * 60)
    
    approaches = [
        ("Neural Network", False),
        ("Evolutionary", True)
    ]
    
    results_comparison = {}
    
    for approach_name, use_evolution in approaches:
        print(f"\nRunning {approach_name} approach...")
        
        # Create fresh pipeline for each approach
        pipeline = TrainingPipeline()
        pipeline.initialize_training(force_regenerate_dataset=False)
        
        # Run training
        results = pipeline.run_training(
            n_epochs=10,  # Short run for comparison
            use_evolution=use_evolution,
            save_frequency=5,
            full_eval_frequency=10
        )
        
        if results:
            results_comparison[approach_name] = {
                'best_score': results['best_table_metrics'].composite_score,
                'best_error': results['best_table_metrics'].max_error,
                'efficiency': results['best_table_metrics'].efficiency_score,
                'stability': results['best_table_metrics'].stability_score,
                'success_rate': results['best_table_metrics'].success_rate
            }
    
    # Compare results
    print(f"\nComparative Results:")
    print(f"{'Approach':<15} {'Score':<8} {'Error':<12} {'Efficiency':<10} {'Stability':<10}")
    print("-" * 70)
    
    for approach, results in results_comparison.items():
        print(f"{approach:<15} {results['best_score']:<8.4f} "
              f"{results['best_error']:<12.2e} {results['efficiency']:<10.4f} "
              f"{results['stability']:<10.4f}")

def example_5_report_generation():
    """Example 5: Generate comprehensive reports."""
    
    print("\n" + "=" * 60)
    print("EXAMPLE 5: Report Generation")
    print("=" * 60)
    
    # Run a short experiment to generate data
    pipeline = TrainingPipeline()
    pipeline.initialize_training(force_regenerate_dataset=False)
    
    print("Running experiment for report generation...")
    results = pipeline.run_training(
        n_epochs=8,
        use_evolution=False,
        save_frequency=2,
        full_eval_frequency=4
    )
    
    if results:
        # Generate comprehensive report
        report_gen = ReportGenerator("examples/reports")
        
        print("Generating comprehensive report...")
        summary_path = report_gen.generate_experiment_report(
            "results/integrator_results.db",
            "Advanced Example",
            include_interactive=True
        )
        
        if summary_path:
            print(f"Report generated: {summary_path}")
            
            # Display summary
            with open(summary_path, 'r') as f:
                print("\nReport Summary:")
                print("-" * 40)
                print(f.read())

def example_6_hyperparameter_sensitivity():
    """Example 6: Hyperparameter sensitivity analysis."""
    
    print("\n" + "=" * 60)
    print("EXAMPLE 6: Hyperparameter Sensitivity Analysis")
    print("=" * 60)
    
    # Test different learning rates
    learning_rates = [1e-2, 1e-3, 1e-4]
    lr_results = {}
    
    for lr in learning_rates:
        print(f"\nTesting learning rate: {lr}")
        
        model_config = ModelConfig(
            learning_rate=lr,
            generator_hidden_size=128,  # Smaller for faster training
            surrogate_hidden_size=64,
            n_epochs=5  # Very short for sensitivity test
        )
        
        pipeline = TrainingPipeline(model_config)
        pipeline.initialize_training(force_regenerate_dataset=False)
        
        # Run short training
        results = pipeline.run_training(
            n_epochs=5,
            use_evolution=False,
            save_frequency=5,
            full_eval_frequency=5
        )
        
        if results:
            lr_results[lr] = results['best_table_metrics'].composite_score
    
    # Display results
    print(f"\nLearning Rate Sensitivity Results:")
    for lr, score in lr_results.items():
        print(f"  LR = {lr:>8}: Score = {score:.4f}")

def main():
    """Run all advanced examples."""
    
    print("Novel Numerical Integration Methods - Advanced Training Examples")
    print("=" * 80)
    
    try:
        example_1_custom_training_configuration()
        example_2_evolutionary_approach()
        example_3_experiment_logging()
        example_4_comparative_study()
        example_5_report_generation()
        example_6_hyperparameter_sensitivity()
        
        print("\n" + "=" * 80)
        print("All advanced examples completed successfully!")
        print("Check the generated reports and databases for detailed results.")
        
    except Exception as e:
        print(f"\nError running advanced examples: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
