"""
Comprehensive Test Runner with Progress Bars

This script runs the comprehensive test with clear progress indicators
and avoids torch dependencies by using a simplified approach.
"""

import os
import sys
import time
import json
import numpy as np
from tqdm import tqdm
from typing import List, Dict, Any

# Add parent directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

def test_imports():
    """Test that all required modules can be imported."""
    print("🔍 Testing imports...")
    
    try:
        from src.core.butcher_tables import ButcherTable, get_rk4, get_rk45_dormand_prince, get_gauss_legendre_2, get_gauss_legendre_3
        print("✓ butcher_tables imported successfully")
        
        from src.core.integrator_runner import IntegratorBenchmark
        print("✓ integrator_runner imported successfully")
        
        from src.core.ode_dataset import ODEParameters, ODEDataset
        print("✓ ode_dataset imported successfully")
        
        print("✅ All imports successful!")
        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

def load_optimal_table():
    """Load the optimal Butcher table."""
    print("\n📊 Loading optimal Butcher table...")
    
    try:
        # Try to load from run_1 first
        run1_path = os.path.join(os.path.dirname(__file__), '..', '..', 'experiments', 'run_1_balanced_weights', 'best_butcher_table.json')
        optimal_path = os.path.join(os.path.dirname(__file__), '..', '..', 'OPTIMAL_BUTCHER_TABLE.json')
        
        table_path = None
        if os.path.exists(run1_path):
            table_path = run1_path
            print("📁 Found run_1 optimal table")
        elif os.path.exists(optimal_path):
            table_path = optimal_path
            print("📁 Found global optimal table")
        else:
            print("❌ No optimal table found")
            return None
        
        # Load and test the table
        with open(table_path, 'r') as f:
            data = json.load(f)
        
        if 'butcher_table' in data:
            table_data = data['butcher_table']
        else:
            table_data = data
            
        from src.core.butcher_tables import ButcherTable
        table = ButcherTable(
            A=np.array(table_data['A']),
            b=np.array(table_data['b']),
            c=np.array(table_data['c'])
        )
        
        print(f"✅ Optimal table loaded - Stages: {len(table.b)}, Order: {table.consistency_order}")
        return table
        
    except Exception as e:
        print(f"❌ Optimal table loading failed: {e}")
        return None

def generate_test_dataset(n_odes: int = 1000):
    """Generate test dataset with progress bar."""
    print(f"\n🎯 Generating test dataset with {n_odes} ODEs...")
    
    from src.core.ode_dataset import ODEGenerator
    
    generator = ODEGenerator()
    n_stiff = int(n_odes * 0.3)
    n_nonstiff = n_odes - n_stiff
    
    all_odes = []
    
    print(f"📊 Generating {n_stiff} stiff ODEs...")
    with tqdm(total=n_stiff, desc="Stiff ODEs") as pbar:
        for i in range(n_stiff):
            # Generate stiff linear systems
            ode = generator.generate_linear_system(n=2, stiffness_ratio=10.0)
            ode.t_span = (0.0, 1.0)
            ode.is_stiff = True
            ode.ode_id = i
            all_odes.append(ode)
            pbar.update(1)
    
    print(f"📊 Generating {n_nonstiff} non-stiff ODEs...")
    with tqdm(total=n_nonstiff, desc="Non-stiff ODEs") as pbar:
        for i in range(n_nonstiff):
            # Generate non-stiff linear systems
            ode = generator.generate_linear_system(n=2, stiffness_ratio=1.0)
            ode.t_span = (0.0, 1.0)
            ode.is_stiff = False
            ode.ode_id = n_stiff + i
            all_odes.append(ode)
            pbar.update(1)
    
    np.random.shuffle(all_odes)
    
    print(f"✅ Dataset generated: {len(all_odes)} total ODEs")
    return all_odes

def evaluate_method(method_name: str, butcher_table, test_dataset, benchmark):
    """Evaluate a method on the test dataset with progress bar."""
    print(f"\n🧪 Evaluating {method_name}...")
    
    results = []
    successful_evaluations = 0
    total_runtime = 0.0
    total_steps = 0
    
    # Evaluate with progress bar
    for ode_params in tqdm(test_dataset, desc=f"Testing {method_name}"):
        try:
            start_time = time.time()
            eval_result = benchmark.evaluate_butcher_table(butcher_table, ode_params, h=0.01)
            eval_time = time.time() - start_time
            
            total_runtime += eval_time
            
            if eval_result['success']:
                successful_evaluations += 1
                total_steps += eval_result['n_steps']
                results.append({
                    'max_error': eval_result['max_error'],
                    'l2_error': eval_result['l2_error'],
                    'runtime': eval_time,
                    'n_steps': eval_result['n_steps'],
                    'is_stiff': ode_params.is_stiff
                })
        except Exception as e:
            continue
    
    if successful_evaluations == 0:
        return {
            'method': method_name,
            'success_rate': 0.0,
            'max_error': float('inf'),
            'l2_error': float('inf'),
            'mean_error': float('inf'),
            'error_percentile_95': float('inf'),
            'total_runtime': total_runtime,
            'total_steps': total_steps,
            'steps_per_second': 0.0,
            'efficiency_score': 0.0,
            'stability_score': 0.0,
            'composite_score': 0.0,
            'n_successful': 0,
            'n_total': len(test_dataset)
        }
    
    # Calculate metrics
    max_error = max(result['max_error'] for result in results)
    l2_error = np.sqrt(sum(result['l2_error']**2 for result in results))
    mean_error = np.mean([result['max_error'] for result in results])
    error_percentile_95 = np.percentile([result['max_error'] for result in results], 95)
    
    steps_per_second = total_steps / total_runtime if total_runtime > 0 else 0
    
    # Calculate stability score (performance on stiff problems)
    stiff_results = [r for r in results if r['is_stiff']]
    stability_score = 0.0
    if stiff_results:
        stiff_success_rate = len(stiff_results) / len([ode for ode in test_dataset if ode.is_stiff])
        stability_score = min(1.0, stiff_success_rate)
    
    # Calculate efficiency score
    efficiency_score = min(1.0, steps_per_second / 1000.0)
    
    # Calculate composite score
    success_rate = successful_evaluations / len(test_dataset)
    accuracy_score = 1.0 / (1.0 + np.log10(max(max_error, 1e-16)))
    composite_score = 0.4 * accuracy_score + 0.3 * efficiency_score + 0.3 * stability_score
    
    print(f"✅ {method_name} completed:")
    print(f"   Success rate: {success_rate:.3f}")
    print(f"   Max error: {max_error:.2e}")
    print(f"   Efficiency: {efficiency_score:.3f}")
    print(f"   Stability: {stability_score:.3f}")
    print(f"   Composite: {composite_score:.3f}")
    
    return {
        'method': method_name,
        'success_rate': success_rate,
        'max_error': max_error,
        'l2_error': l2_error,
        'mean_error': mean_error,
        'error_percentile_95': error_percentile_95,
        'total_runtime': total_runtime,
        'total_steps': total_steps,
        'steps_per_second': steps_per_second,
        'efficiency_score': efficiency_score,
        'stability_score': stability_score,
        'composite_score': composite_score,
        'n_successful': successful_evaluations,
        'n_total': len(test_dataset)
    }

def run_comprehensive_test(n_odes: int = 1000):
    """Run the comprehensive test with progress bars."""
    print("🚀 COMPREHENSIVE ODE TESTING SUITE")
    print("=" * 50)
    print(f"Start time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Number of ODEs: {n_odes:,}")
    print("")
    
    start_time = time.time()
    
    # Step 1: Test imports
    if not test_imports():
        print("❌ Import test failed. Exiting.")
        return False
    
    # Step 2: Load optimal table
    optimal_table = load_optimal_table()
    if optimal_table is None:
        print("❌ Could not load optimal table. Exiting.")
        return False
    
    # Step 3: Get baseline methods
    print("\n📚 Loading baseline methods...")
    from src.core.butcher_tables import get_rk4, get_rk45_dormand_prince, get_gauss_legendre_2, get_gauss_legendre_3
    
    baseline_methods = {
        'rk4': get_rk4(),
        'rk45_dormand_prince': get_rk45_dormand_prince(),
        'gauss_legendre_2': get_gauss_legendre_2(),
        'gauss_legendre_3': get_gauss_legendre_3()
    }
    print(f"✅ Loaded {len(baseline_methods)} baseline methods")
    
    # Step 4: Generate test dataset
    test_dataset = generate_test_dataset(n_odes)
    
    # Step 5: Initialize benchmark
    print("\n🔧 Initializing benchmark...")
    from src.core.integrator_runner import IntegratorBenchmark
    benchmark = IntegratorBenchmark()
    print("✅ Benchmark initialized")
    
    # Step 6: Run tests
    print("\n🧪 RUNNING COMPREHENSIVE TESTS")
    print("=" * 40)
    
    all_results = []
    
    # Test optimal method
    optimal_result = evaluate_method("Optimal (Run 1)", optimal_table, test_dataset, benchmark)
    all_results.append(optimal_result)
    
    # Test baseline methods
    for method_name, butcher_table in baseline_methods.items():
        method_result = evaluate_method(method_name, butcher_table, test_dataset, benchmark)
        all_results.append(method_result)
    
    # Step 7: Generate summary
    print("\n📊 TEST RESULTS SUMMARY")
    print("=" * 50)
    
    # Sort by composite score
    all_results.sort(key=lambda x: x['composite_score'], reverse=True)
    
    print(f"{'Rank':<4} {'Method':<20} {'Success':<8} {'Max Error':<12} {'Efficiency':<10} {'Stability':<10} {'Composite':<10}")
    print("-" * 80)
    
    for i, result in enumerate(all_results, 1):
        print(f"{i:<4} {result['method']:<20} {result['success_rate']:<8.3f} "
              f"{result['max_error']:<12.2e} {result['efficiency_score']:<10.3f} "
              f"{result['stability_score']:<10.3f} {result['composite_score']:<10.3f}")
    
    # Find best performers
    best_overall = all_results[0]
    best_accuracy = min(all_results, key=lambda x: x['max_error'])
    best_efficiency = max(all_results, key=lambda x: x['efficiency_score'])
    best_stability = max(all_results, key=lambda x: x['stability_score'])
    
    print(f"\n🏆 BEST PERFORMERS:")
    print(f"Overall Best: {best_overall['method']} (composite: {best_overall['composite_score']:.3f})")
    print(f"Most Accurate: {best_accuracy['method']} (max_error: {best_accuracy['max_error']:.2e})")
    print(f"Most Efficient: {best_efficiency['method']} (efficiency: {best_efficiency['efficiency_score']:.3f})")
    print(f"Most Stable: {best_stability['method']} (stability: {best_stability['stability_score']:.3f})")
    
    # Step 8: Save results
    print(f"\n💾 Saving results...")
    results_path = os.path.join(os.path.dirname(__file__), '..', 'results', 'test_results.json')
    
    # Ensure results directory exists
    os.makedirs(os.path.dirname(results_path), exist_ok=True)
    
    # Save results
    with open(results_path, 'w') as f:
        json.dump(all_results, f, indent=2)
    
    print(f"✅ Results saved to: {results_path}")
    
    total_time = time.time() - start_time
    print(f"\n🎉 TEST COMPLETED!")
    print(f"Total runtime: {total_time:.1f} seconds ({total_time/60:.1f} minutes)")
    print(f"End time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    return True

def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Run comprehensive ODE test with progress bars')
    parser.add_argument('--odes', type=int, default=1000, 
                       help='Number of ODEs to test (default: 1000)')
    
    args = parser.parse_args()
    
    success = run_comprehensive_test(args.odes)
    
    if success:
        print("\n✅ Test completed successfully!")
        print("Check the results directory for detailed outputs.")
    else:
        print("\n❌ Test failed. Check the output above for details.")

if __name__ == "__main__":
    main()
