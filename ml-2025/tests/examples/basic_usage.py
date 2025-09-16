"""
Basic Usage Examples for Novel Numerical Integration Methods.

This script demonstrates the core functionality of the system.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ode_dataset import ODEDataset
from butcher_tables import ButcherTableGenerator, get_rk4, get_rk45_dormand_prince
from integrator_runner import IntegratorBenchmark, ReferenceSolver
from metrics import MetricsCalculator, BaselineComparator
from visualization import ButcherTableVisualizer
from database import ExperimentLogger

def example_1_generate_and_evaluate_butcher_table():
    """Example 1: Generate a random Butcher table and evaluate its performance."""
    
    print("=" * 60)
    print("EXAMPLE 1: Generate and Evaluate Random Butcher Table")
    print("=" * 60)
    
    # Generate a random Butcher table
    generator = ButcherTableGenerator()
    table = generator.generate_random_explicit(stages=4)
    
    print("Generated Butcher Table:")
    print(table)
    
    # Load ODE dataset
    dataset = ODEDataset()
    dataset.generate_dataset(force_regenerate=False)  # Use existing if available
    
    # Get a small batch for testing
    test_batch = dataset.get_batch(50)
    print(f"\nTesting on {len(test_batch)} ODEs...")
    
    # Set up evaluation
    ref_solver = ReferenceSolver()
    benchmark = IntegratorBenchmark(ref_solver)
    metrics_calc = MetricsCalculator(benchmark)
    
    # Evaluate performance
    metrics = metrics_calc.evaluate_on_ode_batch(table, test_batch)
    
    print(f"\nPerformance Results:")
    print(f"  Success Rate: {metrics.success_rate:.2%}")
    print(f"  Max Error: {metrics.max_error:.2e}")
    print(f"  Efficiency Score: {metrics.efficiency_score:.4f}")
    print(f"  Stability Score: {metrics.stability_score:.4f}")
    print(f"  Composite Score: {metrics.composite_score:.4f}")

def example_2_compare_with_baselines():
    """Example 2: Compare a custom method with baseline methods."""
    
    print("\n" + "=" * 60)
    print("EXAMPLE 2: Compare with Baseline Methods")
    print("=" * 60)
    
    # Load dataset
    dataset = ODEDataset()
    dataset.generate_dataset(force_regenerate=False)
    test_batch = dataset.get_batch(100)
    
    # Set up evaluation
    ref_solver = ReferenceSolver()
    benchmark = IntegratorBenchmark(ref_solver)
    metrics_calc = MetricsCalculator(benchmark)
    baseline_comp = BaselineComparator(metrics_calc)
    
    # Get baseline methods
    from butcher_tables import get_all_baseline_tables
    baselines = get_all_baseline_tables()
    
    print("Evaluating baseline methods...")
    baseline_metrics = baseline_comp.compute_baseline_metrics(test_batch)
    
    print(f"\nBaseline Results:")
    for name, metrics in baseline_metrics.items():
        print(f"  {name:20s}: Score={metrics.composite_score:.4f}, "
              f"Error={metrics.max_error:.2e}")
    
    # Generate a custom method
    generator = ButcherTableGenerator()
    custom_table = generator.generate_random_explicit(stages=4)
    
    print(f"\nEvaluating custom method...")
    custom_metrics = metrics_calc.evaluate_on_ode_batch(custom_table, test_batch)
    
    print(f"Custom method: Score={custom_metrics.composite_score:.4f}, "
          f"Error={custom_metrics.max_error:.2e}")
    
    # Compare
    comparisons = baseline_comp.compare_to_baselines(custom_metrics, baseline_metrics)
    
    print(f"\nComparison Results:")
    for baseline_name, comparison in comparisons.items():
        better = "✓" if comparison['better_overall'] else "✗"
        print(f"  vs {baseline_name:15s}: {better} "
              f"(Score ratio: {comparison['score_ratio']:.2f}x)")

def example_3_visualize_butcher_tables():
    """Example 3: Visualize Butcher tables."""
    
    print("\n" + "=" * 60)
    print("EXAMPLE 3: Visualize Butcher Tables")
    print("=" * 60)
    
    # Get some methods to visualize
    rk4 = get_rk4()
    rk45 = get_rk45_dormand_prince()
    
    generator = ButcherTableGenerator()
    random_table = generator.generate_random_explicit(stages=4)
    
    # Create visualizer
    visualizer = ButcherTableVisualizer()
    
    print("Visualizing RK4 method...")
    visualizer.plot_butcher_table(rk4, "Classic RK4 Method")
    
    print("Visualizing RK45 method...")
    visualizer.plot_butcher_table(rk45, "Dormand-Prince RK45 Method")
    
    print("Visualizing random method...")
    visualizer.plot_butcher_table(random_table, "Random Generated Method")

def example_4_database_logging():
    """Example 4: Use database for logging results."""
    
    print("\n" + "=" * 60)
    print("EXAMPLE 4: Database Logging")
    print("=" * 60)
    
    # Set up experiment logger
    logger = ExperimentLogger("examples/example_results.db")
    experiment_name = logger.start_experiment("Basic Usage Example", "Demonstration experiment")
    
    # Load dataset
    dataset = ODEDataset()
    dataset.generate_dataset(force_regenerate=False)
    test_batch = dataset.get_batch(50)
    
    # Set up evaluation
    ref_solver = ReferenceSolver()
    benchmark = IntegratorBenchmark(ref_solver)
    metrics_calc = MetricsCalculator(benchmark)
    
    # Generate and evaluate several methods
    generator = ButcherTableGenerator()
    
    for i in range(5):
        print(f"Evaluating method {i+1}/5...")
        
        # Generate method
        table = generator.generate_random_explicit(stages=4)
        
        # Evaluate
        metrics = metrics_calc.evaluate_on_ode_batch(table, test_batch)
        
        # Log to database
        table_id = logger.log_butcher_table_evaluation(table, metrics)
        print(f"  Logged with table_id: {table_id}")
    
    # Get experiment summary
    summary = logger.get_experiment_summary()
    print(f"\nExperiment Summary:")
    print(f"  Total evaluations: {summary['n_evaluations']}")
    print(f"  Best performers:")
    
    for i, performer in enumerate(summary['best_performers'][:3]):
        print(f"    {i+1}. Table ID {performer['table_id']}: Score = {performer['score']:.4f}")
    
    # Export results
    logger.export_results("examples/exported_results")
    print(f"\nResults exported to examples/exported_results/")

def example_5_simple_training():
    """Example 5: Run a simple training experiment."""
    
    print("\n" + "=" * 60)
    print("EXAMPLE 5: Simple Training Experiment")
    print("=" * 60)
    
    from model import MLPipeline, ModelConfig
    
    # Create a small ML pipeline for demonstration
    config = ModelConfig(
        generator_input_size=64,
        generator_hidden_size=128,
        surrogate_hidden_size=64,
        n_epochs=10  # Very short for demo
    )
    
    ml_pipeline = MLPipeline(config)
    
    # Load dataset
    dataset = ODEDataset()
    dataset.generate_dataset(force_regenerate=False)
    
    print("Running short training experiment...")
    
    # Generate initial candidates
    candidates = ml_pipeline.generate_candidates(n_candidates=20, stages=4)
    print(f"Generated {len(candidates)} candidate methods")
    
    # Set up evaluation
    ref_solver = ReferenceSolver()
    benchmark = IntegratorBenchmark(ref_solver)
    metrics_calc = MetricsCalculator(benchmark)
    
    # Evaluate candidates
    test_batch = dataset.get_batch(100)
    candidate_metrics = []
    valid_candidates = []
    
    for i, candidate in enumerate(candidates):
        try:
            metrics = metrics_calc.evaluate_on_ode_batch(candidate, test_batch)
            if metrics.success_rate > 0.5:
                candidate_metrics.append(metrics)
                valid_candidates.append(candidate)
                print(f"  Candidate {i+1}: Score = {metrics.composite_score:.4f}")
        except Exception as e:
            print(f"  Candidate {i+1}: Failed ({e})")
    
    if valid_candidates:
        print(f"\nFound {len(valid_candidates)} valid candidates")
        
        # Train surrogate model
        print("Training surrogate model...")
        ml_pipeline.update_training_data(valid_candidates, candidate_metrics)
        ml_pipeline.train_surrogate(valid_candidates, candidate_metrics, n_epochs=10)
        
        # Test surrogate predictions
        print("Testing surrogate predictions...")
        predictions = ml_pipeline.predict_performance(valid_candidates[:3])
        for i, pred in enumerate(predictions):
            actual = candidate_metrics[i].composite_score
            predicted = pred[3].item()  # Composite score is 4th output
            print(f"  Method {i+1}: Actual={actual:.4f}, Predicted={predicted:.4f}")
    
    else:
        print("No valid candidates found")

def main():
    """Run all examples."""
    
    print("Novel Numerical Integration Methods - Basic Usage Examples")
    print("=" * 80)
    
    try:
        example_1_generate_and_evaluate_butcher_table()
        example_2_compare_with_baselines()
        example_3_visualize_butcher_tables()
        example_4_database_logging()
        example_5_simple_training()
        
        print("\n" + "=" * 80)
        print("All examples completed successfully!")
        print("Check the generated files and plots for results.")
        
    except Exception as e:
        print(f"\nError running examples: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
