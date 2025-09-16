"""
Main Runner Script for Comprehensive ODE Testing Suite

This script orchestrates the entire comprehensive testing process:
1. Runs the main comprehensive test
2. Performs extended comparison with additional methods
3. Generates performance analysis and visualizations
4. Creates summary reports

Author: AI Assistant
Date: 2025-09-15
"""

import os
import sys
import time
import argparse
import json
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

def run_main_test(n_odes: int = 10000, n_processes: int = None):
    """Run the main comprehensive test."""
    print("=" * 80)
    print("RUNNING MAIN COMPREHENSIVE TEST")
    print("=" * 80)
    
    from comprehensive_ode_test import ComprehensiveTester, TestConfig
    
    config = TestConfig(
        n_odes=n_odes,
        n_stiff_odes=int(n_odes * 0.3),
        n_nonstiff_odes=int(n_odes * 0.7),
        n_processes=n_processes
    )
    
    tester = ComprehensiveTester(config)
    tester.run_comprehensive_test()
    
    return True

def run_extended_comparison():
    """Run extended comparison with additional methods."""
    print("\n" + "=" * 80)
    print("RUNNING EXTENDED COMPARISON")
    print("=" * 80)
    
    try:
        from extended_comparison import ExtendedComparison
        from ode_dataset import ODEDataset
        
        # Generate smaller dataset for extended comparison (faster)
        dataset_generator = ODEDataset()
        test_dataset = dataset_generator.generate_stiff_odes(500, 0.0, 1.0) + \
                      dataset_generator.generate_nonstiff_odes(500, 0.0, 1.0)
        
        extended_comp = ExtendedComparison()
        methods = extended_comp.get_extended_methods()
        
        results = {}
        for method_name, method_func in methods.items():
            print(f"\nTesting {method_name}...")
            method_results = extended_comp.evaluate_method_on_dataset(
                method_name, method_func, test_dataset
            )
            results[method_name] = method_results
            
            print(f"  Success rate: {method_results['success_rate']:.3f}")
            print(f"  Composite score: {method_results['composite_score']:.3f}")
        
        # Save results
        results_path = os.path.join(os.path.dirname(__file__), '..', 'results', 'extended_comparison_results.json')
        with open(results_path, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\nExtended comparison results saved to: {results_path}")
        return True
        
    except Exception as e:
        print(f"Extended comparison failed: {e}")
        return False

def run_performance_analysis():
    """Run performance analysis and generate plots."""
    print("\n" + "=" * 80)
    print("RUNNING PERFORMANCE ANALYSIS")
    print("=" * 80)
    
    try:
        from performance_analyzer import PerformanceAnalyzer
        
        results_path = os.path.join(os.path.dirname(__file__), '..', 'results', 'comprehensive_test_results.json')
        
        if not os.path.exists(results_path):
            print(f"Results file not found: {results_path}")
            return False
        
        analyzer = PerformanceAnalyzer(results_path)
        
        # Generate report
        report = analyzer.generate_performance_report()
        print(report)
        
        # Save report
        report_path = os.path.join(os.path.dirname(__file__), '..', 'results', 'performance_report.txt')
        with open(report_path, 'w') as f:
            f.write(report)
        
        # Generate plots
        analyzer.create_detailed_comparison_plots()
        
        # Statistical analysis
        df = analyzer.create_statistical_analysis()
        
        # Save data
        csv_path = os.path.join(os.path.dirname(__file__), '..', 'results', 'performance_data.csv')
        df.to_csv(csv_path, index=False)
        
        return True
        
    except Exception as e:
        print(f"Performance analysis failed: {e}")
        return False

def create_summary_report():
    """Create a comprehensive summary report."""
    print("\n" + "=" * 80)
    print("CREATING SUMMARY REPORT")
    print("=" * 80)
    
    summary = []
    summary.append("COMPREHENSIVE ODE TESTING SUITE - SUMMARY REPORT")
    summary.append("=" * 60)
    summary.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    summary.append("")
    
    # Check what files exist
    results_dir = os.path.join(os.path.dirname(__file__), '..', 'results')
    plots_dir = os.path.join(os.path.dirname(__file__), '..', 'plots')
    
    summary.append("GENERATED FILES:")
    summary.append("-" * 30)
    
    # Check main results
    main_results = os.path.join(results_dir, 'comprehensive_test_results.json')
    if os.path.exists(main_results):
        summary.append("✓ Main comprehensive test results")
        
        # Load and summarize main results
        with open(main_results, 'r') as f:
            data = json.load(f)
        
        methods = [k for k in data.keys() if k != 'config']
        if methods:
            summary.append(f"  - Tested {len(methods)} methods on {data['config']['n_odes']:,} ODEs")
            
            # Find best method
            best_method = max(methods, key=lambda m: data[m]['metrics']['composite_score'])
            summary.append(f"  - Best performing method: {best_method}")
            summary.append(f"  - Best composite score: {data[best_method]['metrics']['composite_score']:.3f}")
    
    # Check extended results
    extended_results = os.path.join(results_dir, 'extended_comparison_results.json')
    if os.path.exists(extended_results):
        summary.append("✓ Extended comparison results")
        
        with open(extended_results, 'r') as f:
            ext_data = json.load(f)
        
        if ext_data:
            summary.append(f"  - Tested {len(ext_data)} additional methods")
            best_ext = max(ext_data.keys(), key=lambda m: ext_data[m]['composite_score'])
            summary.append(f"  - Best extended method: {best_ext}")
    
    # Check performance report
    perf_report = os.path.join(results_dir, 'performance_report.txt')
    if os.path.exists(perf_report):
        summary.append("✓ Performance analysis report")
    
    # Check plots
    plot_files = []
    if os.path.exists(plots_dir):
        plot_files = [f for f in os.listdir(plots_dir) if f.endswith('.png')]
    
    if plot_files:
        summary.append(f"✓ Generated {len(plot_files)} visualization plots")
        for plot_file in plot_files:
            summary.append(f"  - {plot_file}")
    
    summary.append("")
    summary.append("NEXT STEPS:")
    summary.append("-" * 20)
    summary.append("1. Review the performance report for detailed analysis")
    summary.append("2. Examine the generated plots for visual comparisons")
    summary.append("3. Use the CSV data for further statistical analysis")
    summary.append("4. Consider the optimal method for your specific applications")
    
    # Save summary
    summary_text = "\n".join(summary)
    summary_path = os.path.join(results_dir, 'test_summary.txt')
    with open(summary_path, 'w') as f:
        f.write(summary_text)
    
    print(summary_text)
    print(f"\nSummary saved to: {summary_path}")
    
    return True

def main():
    """Main function to run the complete test suite."""
    parser = argparse.ArgumentParser(description='Comprehensive ODE Testing Suite')
    parser.add_argument('--odes', type=int, default=10000, 
                       help='Number of ODEs to test (default: 10000)')
    parser.add_argument('--processes', type=int, default=None,
                       help='Number of parallel processes (default: auto)')
    parser.add_argument('--skip-main', action='store_true',
                       help='Skip main comprehensive test')
    parser.add_argument('--skip-extended', action='store_true',
                       help='Skip extended comparison')
    parser.add_argument('--skip-analysis', action='store_true',
                       help='Skip performance analysis')
    
    args = parser.parse_args()
    
    print("COMPREHENSIVE ODE TESTING SUITE")
    print("=" * 50)
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Number of ODEs: {args.odes:,}")
    print(f"Parallel processes: {args.processes or 'auto'}")
    print("")
    
    start_time = time.time()
    
    # Create directories if they don't exist
    results_dir = os.path.join(os.path.dirname(__file__), '..', 'results')
    plots_dir = os.path.join(os.path.dirname(__file__), '..', 'plots')
    os.makedirs(results_dir, exist_ok=True)
    os.makedirs(plots_dir, exist_ok=True)
    
    success_count = 0
    total_tests = 0
    
    # Run main comprehensive test
    if not args.skip_main:
        total_tests += 1
        if run_main_test(args.odes, args.processes):
            success_count += 1
    else:
        print("Skipping main comprehensive test")
    
    # Run extended comparison
    if not args.skip_extended:
        total_tests += 1
        if run_extended_comparison():
            success_count += 1
    else:
        print("Skipping extended comparison")
    
    # Run performance analysis
    if not args.skip_analysis:
        total_tests += 1
        if run_performance_analysis():
            success_count += 1
    else:
        print("Skipping performance analysis")
    
    # Create summary report
    create_summary_report()
    
    total_time = time.time() - start_time
    
    print("\n" + "=" * 80)
    print("TEST SUITE COMPLETED")
    print("=" * 80)
    print(f"Total runtime: {total_time:.1f} seconds ({total_time/60:.1f} minutes)")
    print(f"Tests completed: {success_count}/{total_tests}")
    
    if success_count == total_tests:
        print("✓ All tests completed successfully!")
        print("\nCheck the 'results' and 'plots' directories for detailed outputs.")
    else:
        print("⚠ Some tests failed. Check the output above for details.")
    
    print(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()
